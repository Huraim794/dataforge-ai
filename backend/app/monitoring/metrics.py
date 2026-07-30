from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Callable

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
)

from dataforge.backend.app.core.config import settings


class MetricsCollector:
    def __init__(self) -> None:
        self.info = Info("dataforge", "DataForge AI Platform")
        self.info.info({"version": settings.version, "environment": settings.environment})

        self.jobs_total = Counter(
            "dataforge_jobs_total",
            "Total jobs processed",
            ["status", "project_id"],
        )
        self.jobs_active = Gauge(
            "dataforge_jobs_active",
            "Currently active jobs",
            ["project_id"],
        )
        self.jobs_duration = Histogram(
            "dataforge_job_duration_seconds",
            "Job duration in seconds",
            ["status", "project_id"],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600],
        )

        self.scrapes_total = Counter(
            "dataforge_scrapes_total",
            "Total pages scraped",
            ["status", "project_id"],
        )
        self.scrape_duration = Histogram(
            "dataforge_scrape_duration_seconds",
            "Scrape duration in seconds",
            ["status"],
            buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
        )

        self.extractions_total = Counter(
            "dataforge_extractions_total",
            "Total AI extractions performed",
            ["provider", "success"],
        )
        self.extraction_tokens = Counter(
            "dataforge_extraction_tokens_total",
            "Total LLM tokens used",
            ["provider", "model"],
        )
        self.extraction_cost = Counter(
            "dataforge_extraction_cost_total",
            "Total LLM cost in USD",
            ["provider"],
        )

        self.proxy_active = Gauge(
            "dataforge_proxy_active",
            "Active proxies in pool",
            ["status"],
        )
        self.proxy_requests = Counter(
            "dataforge_proxy_requests_total",
            "Total proxy requests",
            ["status"],
        )

        self.browser_pool_size = Gauge(
            "dataforge_browser_pool_size",
            "Browser pool size",
            ["status"],
        )
        self.browser_launches = Counter(
            "dataforge_browser_launches_total",
            "Browser launch count",
            ["browser_type"],
        )

        self.queue_depth = Gauge(
            "dataforge_queue_depth",
            "Current queue depth",
            ["queue"],
        )
        self.queue_processed = Counter(
            "dataforge_queue_processed_total",
            "Jobs processed from queue",
            ["status"],
        )

        self.captcha_detected = Counter(
            "dataforge_captcha_detected_total",
            "CAPTCHAs detected",
            ["type"],
        )
        self.captcha_solved = Counter(
            "dataforge_captcha_solved_total",
            "CAPTCHAs solved",
            ["success"],
        )

        self.errors_total = Counter(
            "dataforge_errors_total",
            "Total errors",
            ["type", "source"],
        )

        self.cpu_usage = Gauge("dataforge_cpu_usage_percent", "CPU usage percent")
        self.memory_usage = Gauge("dataforge_memory_usage_bytes", "Memory usage bytes")
        self.active_workers = Gauge("dataforge_active_workers", "Active worker count")

    def collect_system_metrics(self) -> None:
        try:
            import psutil
            self.cpu_usage.set(psutil.cpu_percent(interval=0.1))
            self.memory_usage.set(psutil.virtual_memory().used)
        except ImportError:
            pass

    def observe_job(self, status: str, duration_ms: float, project_id: str = "unknown") -> None:
        self.jobs_total.labels(status=status, project_id=project_id).inc()
        self.jobs_duration.labels(status=status, project_id=project_id).observe(duration_ms / 1000)

    def observe_scrape(self, status: str, duration_ms: float) -> None:
        self.scrapes_total.labels(status=status, project_id="unknown").inc()
        self.scrape_duration.labels(status=status).observe(duration_ms / 1000)

    def observe_extraction(self, provider: str, success: bool, tokens: int, cost: float) -> None:
        self.extractions_total.labels(provider=provider, success=str(success)).inc()
        self.extraction_tokens.labels(provider=provider, model="").inc(tokens)
        self.extraction_cost.labels(provider=provider).inc(cost)

    @contextmanager
    def measure_time(self, metric_func: Callable, *args: Any) -> Any:
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            metric_func(duration_ms, *args)


metrics_collector = MetricsCollector()
