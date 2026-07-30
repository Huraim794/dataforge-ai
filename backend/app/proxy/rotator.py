from __future__ import annotations

import random
import time
from typing import Any, Optional

from dataforge.backend.app.monitoring.logger import get_logger

logger = get_logger(__name__)


class ProxyRotator:
    def __init__(self, proxies: list[dict[str, Any]]) -> None:
        self._proxies = proxies
        self._index = 0
        self._last_rotation = time.time()
        self._rotation_interval = 60  # seconds

    def get_next(self) -> Optional[dict[str, Any]]:
        if not self._proxies:
            return None
        self._rotate_if_needed()
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy

    def get_random(self) -> Optional[dict[str, Any]]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def get_weighted(self) -> Optional[dict[str, Any]]:
        if not self._proxies:
            return None
        weights = [p.get("weight", 1.0) for p in self._proxies]
        total = sum(weights)
        if total <= 0:
            return random.choice(self._proxies)
        r = random.uniform(0, total)
        cumulative = 0
        for proxy, weight in zip(self._proxies, weights):
            cumulative += weight
            if r <= cumulative:
                return proxy
        return self._proxies[-1]

    def get_by_country(self, country: str) -> Optional[dict[str, Any]]:
        matches = [p for p in self._proxies if p.get("country", "").lower() == country.lower()]
        return random.choice(matches) if matches else None

    def update_proxies(self, proxies: list[dict[str, Any]]) -> None:
        self._proxies = proxies
        self._index = 0

    def _rotate_if_needed(self) -> None:
        if time.time() - self._last_rotation > self._rotation_interval:
            random.shuffle(self._proxies)
            self._last_rotation = time.time()
