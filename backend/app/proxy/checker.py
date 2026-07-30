from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.monitoring.logger import get_logger

logger = get_logger(__name__)


class ProxyChecker:
    def __init__(self) -> None:
        self.check_url = settings.proxy_check_url
        self.timeout = settings.proxy_check_timeout_seconds
        self._checking: dict[str, bool] = {}

    async def check_proxy(
        self,
        host: str,
        port: int,
        protocol: str = "http",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict[str, Any]:
        proxy_str = self._build_proxy_url(host, port, protocol, username, password)
        result: dict[str, Any] = {
            "alive": False,
            "latency_ms": None,
            "ip": None,
            "country": None,
            "error": None,
        }
        check_key = f"{protocol}://{host}:{port}"
        if self._checking.get(check_key):
            return result

        self._checking[check_key] = True
        start = time.time()

        try:
            async with httpx.AsyncClient(
                proxies=proxy_str,  # type: ignore[call-arg]
                timeout=self.timeout,
                verify=False,  # nosec - intentional for proxy connectivity checks
            ) as client:
                response = await client.get(self.check_url)
                elapsed = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    result["alive"] = True
                    result["latency_ms"] = round(elapsed, 2)
                    result["ip"] = data.get("origin", data.get("ip"))
                    result["country"] = data.get("country")
                else:
                    result["error"] = f"HTTP {response.status_code}"

        except httpx.ConnectError:
            result["error"] = "connection_failed"
        except httpx.TimeoutException:
            result["error"] = "timeout"
        except json.JSONDecodeError:
            result["alive"] = True
            result["latency_ms"] = round((time.time() - start) * 1000, 2)
        except Exception as e:
            result["error"] = str(e)[:200]
        finally:
            self._checking.pop(check_key, None)

        return result

    async def check_proxy_batch(
        self,
        proxies: list[dict[str, Any]],
        concurrency: int = 10,
    ) -> list[dict[str, Any]]:
        semaphore = asyncio.Semaphore(concurrency)

        async def check_one(p: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                result = await self.check_proxy(
                    host=p["host"],
                    port=p["port"],
                    protocol=p.get("protocol", "http"),
                    username=p.get("username"),
                    password=p.get("password"),
                )
                return {**p, **result}

        tasks = [check_one(p) for p in proxies]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def _build_proxy_url(
        self,
        host: str,
        port: int,
        protocol: str = "http",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        if username and password:
            return f"{protocol}://{username}:{password}@{host}:{port}"
        return f"{protocol}://{host}:{port}"
