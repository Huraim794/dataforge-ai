from __future__ import annotations

import json
import time
from typing import Any, Optional

from dataforge.backend.app.extraction.llm_client import LLMClient, LLMResponse
from dataforge.backend.app.monitoring.logger import get_logger
from dataforge.backend.app.monitoring.metrics import metrics_collector

logger = get_logger(__name__)


class AIExtractor:
    SYSTEM_PROMPT = """You are a precise data extraction AI. Extract structured data from web content according to the provided schema.

Rules:
1. Extract ONLY information explicitly present in the content
2. Return valid JSON matching the requested schema exactly
3. Use null for missing fields, never fabricate data
4. Preserve original text formatting for extracted values
5. If the content is not relevant, return an empty result with a note
6. Do not include explanations or markdown formatting in the response
7. Respond with clean JSON only"""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or LLMClient()

    async def extract(
        self,
        content: str,
        schema: Optional[dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
        fields: Optional[list[dict[str, Any]]] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        start_time = time.time()
        result: dict[str, Any] = {
            "success": False,
            "data": None,
            "error": None,
            "processing_time_ms": None,
            "model_used": None,
            "tokens_used": 0,
            "confidence_score": None,
        }

        try:
            if prompt_template:
                user_prompt = prompt_template.format(
                    content=content[:100000],
                    url=url or "",
                    title=title or "",
                )
            elif schema:
                user_prompt = f"""Extract data from the following web content according to this JSON schema:
Schema: {json.dumps(schema, indent=2)}

Web Content:
{content[:100000]}"""
            elif fields:
                field_descriptions = "\n".join(
                    [
                        f"- {f.get('name', 'field')}: {f.get('description', 'No description')} (type: {f.get('data_type', 'string')}, required: {f.get('required', False)})"
                        for f in fields
                    ]
                )
                user_prompt = f"""Extract the following fields from the web content:
{field_descriptions}

Web Content:
{content[:100000]}"""
            else:
                user_prompt = f"""Extract all structured data from the following web content. Identify entities, relationships, attributes, and any structured information present.

Web Content:
{content[:100000]}"""

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response_format = {"type": "json_object"} if schema else None

            llm_response: LLMResponse = await self.llm.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
            )

            if llm_response.success and llm_response.content:
                try:
                    # Try to parse JSON from response
                    cleaned_content = llm_response.content.strip()
                    if cleaned_content.startswith("```json"):
                        cleaned_content = cleaned_content[7:]
                    if cleaned_content.startswith("```"):
                        cleaned_content = cleaned_content[3:]
                    if cleaned_content.endswith("```"):
                        cleaned_content = cleaned_content[:-3]
                    cleaned_content = cleaned_content.strip()

                    extracted_data = json.loads(cleaned_content)
                    result["data"] = extracted_data
                    result["success"] = True
                    result["model_used"] = llm_response.model
                    result["tokens_used"] = llm_response.tokens_total
                    result["confidence_score"] = self._calculate_confidence(
                        extracted_data, schema
                    )
                except json.JSONDecodeError:
                    result["data"] = {"raw": llm_response.content}
                    result["success"] = True
                    result["model_used"] = llm_response.model
            else:
                result["error"] = llm_response.error or "Empty LLM response"

            processing_time = (time.time() - start_time) * 1000
            result["processing_time_ms"] = int(processing_time)

            metrics_collector.observe_extraction(
                provider=self.llm.provider,
                success=result["success"],
                tokens=result["tokens_used"],
                cost=llm_response.cost_usd if hasattr(llm_response, "cost_usd") else 0,
            )

            logger.info(
                "AI extraction completed",
                extra={
                    "success": result["success"],
                    "tokens": result["tokens_used"],
                    "model": result["model_used"],
                    "processing_ms": result["processing_time_ms"],
                },
            )

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"AI extraction failed: {e}")

        return result

    def _calculate_confidence(
        self,
        data: Optional[dict],
        schema: Optional[dict],
    ) -> float:
        if not data or not schema:
            return 0.5

        required_fields = self._get_required_fields(schema)
        if not required_fields:
            return 0.8

        filled = sum(1 for f in required_fields if data.get(f) is not None)
        return round(filled / len(required_fields), 2) if required_fields else 0.8

    def _get_required_fields(self, schema: dict, prefix: str = "") -> list[str]:
        fields = []
        for key, value in schema.get("properties", {}).items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and value.get("type") == "object":
                fields.extend(self._get_required_fields(value, full_key))
            else:
                fields.append(full_key)
        return fields

    async def classify(
        self,
        content: str,
        categories: list[str],
        url: Optional[str] = None,
    ) -> dict[str, Any]:
        system_prompt = f"""Classify the following web content into one or more of these categories: {", ".join(categories)}
Return a JSON object with:
- "category": the primary category
- "subcategories": list of applicable subcategories
- "confidence": confidence score 0-1
- "reasoning": brief explanation"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content[:50000]},
        ]

        response = await self.llm.chat(
            messages=messages, response_format={"type": "json_object"}
        )
        try:
            return json.loads(response.content)
        except (json.JSONDecodeError, AttributeError):
            return {"category": "unknown", "confidence": 0, "error": response.error}

    async def extract_contacts(self, content: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "emails": {"type": "array", "items": {"type": "string"}},
                "phones": {"type": "array", "items": {"type": "string"}},
                "addresses": {"type": "array", "items": {"type": "string"}},
                "social_links": {"type": "object"},
                "contact_names": {"type": "array", "items": {"type": "string"}},
            },
        }
        return await self.extract(content, schema=schema)

    async def extract_table(
        self, content: str, table_selector: Optional[str] = None
    ) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "headers": {"type": "array", "items": {"type": "string"}},
                "rows": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "row_count": {"type": "integer"},
                "column_count": {"type": "integer"},
            },
        }
        return await self.extract(content, schema=schema)
