from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from dataforge.backend.app.core.config import settings
from dataforge.backend.app.monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error: Optional[str] = None


class LLMClient:
    PROVIDER_CONFIGS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "headers": lambda key: {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "cost_per_1k_prompt": 0.0025,
            "cost_per_1k_completion": 0.01,
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "headers": lambda key: {"Content-Type": "application/json"},
            "models": ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
            "cost_per_1k_prompt": 0.00125,
            "cost_per_1k_completion": 0.005,
        },
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "headers": lambda key: {
                "x-api-key": key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            "models": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "cost_per_1k_prompt": 0.003,
            "cost_per_1k_completion": 0.015,
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "headers": lambda key: {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            "models": ["deepseek-chat", "deepseek-coder"],
            "cost_per_1k_prompt": 0.0005,
            "cost_per_1k_completion": 0.002,
        },
    }

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.provider = provider or settings.llm_provider
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

        config = self.PROVIDER_CONFIGS.get(self.provider)
        if not config:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        self._config = config

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
        timeout: int = 120,
    ) -> LLMResponse:
        model = model or self.model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        try:
            if self.provider == "openai":
                return await self._call_openai(
                    messages, model, temperature, max_tokens, response_format, timeout
                )
            elif self.provider == "gemini":
                return await self._call_gemini(
                    messages, model, temperature, max_tokens, timeout
                )
            elif self.provider == "claude":
                return await self._call_claude(
                    messages, model, temperature, max_tokens, timeout
                )
            elif self.provider == "deepseek":
                return await self._call_deepseek(
                    messages, model, temperature, max_tokens, response_format, timeout
                )
            else:
                return LLMResponse(
                    content="",
                    model=model,
                    provider=self.provider,
                    success=False,
                    error=f"Unsupported provider: {self.provider}",
                )

        except Exception as e:
            logger.error(
                f"LLM call failed: {e}",
                extra={"provider": self.provider, "model": model},
            )
            return LLMResponse(
                content="",
                model=model,
                provider=self.provider,
                success=False,
                error=str(e),
            )

    async def _call_openai(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[dict],
        timeout: int,
    ) -> LLMResponse:
        headers = self._config["headers"](self.api_key)
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._config['base_url']}/chat/completions",
                headers=headers,
                json=body,
            )
            data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        tokens_prompt = usage.get("prompt_tokens", 0)
        tokens_completion = usage.get("completion_tokens", 0)
        cost = (tokens_prompt / 1000 * self._config["cost_per_1k_prompt"]) + (
            tokens_completion / 1000 * self._config["cost_per_1k_completion"]
        )

        return LLMResponse(
            content=choice["message"]["content"],
            model=model,
            provider=self.provider,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_prompt + tokens_completion,
            cost_usd=round(cost, 6),
        )

    async def _call_gemini(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> LLMResponse:
        # Convert OpenAI format to Gemini format
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        headers = self._config["headers"](self.api_key)
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._config['base_url']}/models/{model}:generateContent",
                headers=headers,
                json=body,
                params={"key": self.api_key},
            )
            data = resp.json()

        candidate = data["candidates"][0]
        content = candidate["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        tokens = usage.get("totalTokenCount", 0)

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider,
            tokens_total=tokens,
        )

    async def _call_claude(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> LLMResponse:
        # Convert to Claude format
        system_msg = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                role = "assistant" if msg["role"] == "assistant" else "user"
                claude_messages.append({"role": role, "content": msg["content"]})

        headers = self._config["headers"](self.api_key)
        body: dict[str, Any] = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            body["system"] = system_msg

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._config['base_url']}/messages",
                headers=headers,
                json=body,
            )
            data = resp.json()

        usage = data.get("usage", {})
        tokens_input = usage.get("input_tokens", 0)
        tokens_output = usage.get("output_tokens", 0)
        cost = (tokens_input / 1000 * self._config["cost_per_1k_prompt"]) + (
            tokens_output / 1000 * self._config["cost_per_1k_completion"]
        )

        return LLMResponse(
            content=data["content"][0]["text"],
            model=model,
            provider=self.provider,
            tokens_prompt=tokens_input,
            tokens_completion=tokens_output,
            tokens_total=tokens_input + tokens_output,
            cost_usd=round(cost, 6),
        )

    async def _call_deepseek(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[dict],
        timeout: int,
    ) -> LLMResponse:
        headers = self._config["headers"](self.api_key)
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._config['base_url']}/chat/completions",
                headers=headers,
                json=body,
            )
            data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        tokens_prompt = usage.get("prompt_tokens", 0)
        tokens_completion = usage.get("completion_tokens", 0)
        cost = (tokens_prompt / 1000 * self._config["cost_per_1k_prompt"]) + (
            tokens_completion / 1000 * self._config["cost_per_1k_completion"]
        )

        return LLMResponse(
            content=choice["message"]["content"],
            model=model,
            provider=self.provider,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_prompt + tokens_completion,
            cost_usd=round(cost, 6),
        )
