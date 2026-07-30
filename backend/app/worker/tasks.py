from __future__ import annotations

import time
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update

from app.core.database import async_session_factory
from app.models.job import Job, JobStatus
from app.models.run import Run, RunStatus
from app.models.result import ScrapeResult
from app.monitoring.logger import get_logger
from app.monitoring.metrics import metrics_collector
from app.proxy.manager import ProxyManager
from app.scraping.engine import ScrapingEngine
from app.worker.queue import QueueManager

logger = get_logger(__name__)


class TaskProcessor:
    def __init__(
        self,
        scraping_engine: ScrapingEngine,
        proxy_manager: ProxyManager,
        queue_manager: QueueManager,
    ) -> None:
        self.engine = scraping_engine
        self.proxy_manager = proxy_manager
        self.queue = queue_manager
        self._running = False
        self._worker_id = f"worker_{id(self)}_{int(time.time())}"

    async def start(self) -> None:
        self._running = True
        logger.info(f"Task processor started: {self._worker_id}")
        metrics_collector.active_workers.inc()

    async def stop(self) -> None:
        self._running = False
        metrics_collector.active_workers.dec()
        logger.info("Task processor stopped")

    async def process_next(self, timeout: int = 5) -> bool:
        if not self._running:
            return False

        payload = await self.queue.dequeue(timeout=timeout)
        if not payload:
            return False

        job_id = payload.get("id")
        job_data = payload.get("data", {})
        queue_name = payload.get("queue", "default")

        try:
            await self._process_job(job_id, job_data, queue_name)
        except Exception as e:
            logger.error(
                f"Job processing failed: {job_id}",
                extra={"error": str(e), "job_id": job_id},
            )
            await self.queue.requeue(payload)

        return True

    async def _process_job(
        self, job_id: str, job_data: dict[str, Any], queue_name: str
    ) -> None:
        start_time = time.time()
        run_id = None

        try:
            # Create run record
            async with async_session_factory() as session:
                run = Run(
                    job_id=job_id,
                    url=job_data.get("url", ""),
                    status=RunStatus.STARTING,
                    attempt_number=job_data.get("retry_count", 0) + 1,
                    worker_id=self._worker_id,
                )
                session.add(run)
                await session.commit()
                await session.refresh(run)
                run_id = run.id

            # Update job status
            async with async_session_factory() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == job_id)
                    .values(
                        status=JobStatus.RUNNING,
                        started_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

            # Update run status
            async with async_session_factory() as session:
                await session.execute(
                    update(Run)
                    .where(Run.id == run_id)
                    .values(status=RunStatus.NAVIGATING)
                )
                await session.commit()

            # Execute scrape
            scrape_result = await self.engine.scrape(
                url=job_data.get("url", ""),
                timeout_ms=job_data.get("timeout_ms"),
                wait_for_selector=job_data.get("wait_for_selector"),
                wait_time_ms=job_data.get("wait_time_ms", 0),
                javascript_enabled=job_data.get("javascript_enabled", True),
                screenshot=job_data.get("screenshot", False),
                pdf=job_data.get("pdf", False),
                headers=job_data.get("headers"),
                cookies=job_data.get("cookies"),
                user_agent=job_data.get("user_agent"),
                use_proxy=True,
            )

            # Save scrape result
            async with async_session_factory() as session:
                result = ScrapeResult(
                    job_id=job_id,
                    run_id=run_id,
                    url=scrape_result.get("url", ""),
                    title=scrape_result.get("title"),
                    status_code=scrape_result.get("status_code"),
                    raw_html=scrape_result.get("content"),
                    cleaned_text=scrape_result.get("cleaned_text"),
                    screenshot_path=scrape_result.get("screenshot_path"),
                    load_time_ms=scrape_result.get("load_time_ms"),
                    ttfb_ms=scrape_result.get("ttfb_ms"),
                    captcha_detected=scrape_result.get("captcha_detected", False),
                    blocked_detected=scrape_result.get("blocked_detected", False),
                    links=scrape_result.get("links"),
                    images=scrape_result.get("images"),
                    success=scrape_result.get("success", False),
                )
                session.add(result)
                await session.commit()
                await session.refresh(result)

            # Update run status
            async with async_session_factory() as session:
                status = (
                    RunStatus.COMPLETED
                    if scrape_result.get("success")
                    else RunStatus.FAILED
                )
                await session.execute(
                    update(Run)
                    .where(Run.id == run_id)
                    .values(
                        status=status,
                        total_time_ms=int((time.time() - start_time) * 1000),
                        http_status_code=scrape_result.get("status_code"),
                        captcha_detected=scrape_result.get("captcha_detected", False),
                        blocked_detected=scrape_result.get("blocked_detected", False),
                    )
                )
                await session.commit()

            # Update job status
            async with async_session_factory() as session:
                job_status = (
                    JobStatus.COMPLETED
                    if scrape_result.get("success")
                    else JobStatus.FAILED
                )
                await session.execute(
                    update(Job)
                    .where(Job.id == job_id)
                    .values(
                        status=job_status,
                        completed_at=datetime.now(timezone.utc),
                        duration_ms=int((time.time() - start_time) * 1000),
                        error_message=scrape_result.get("error"),
                        error_type=scrape_result.get("error_type"),
                    )
                )
                await session.commit()

            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.observe_job(
                status="completed" if scrape_result.get("success") else "failed",
                duration_ms=duration_ms,
            )

            logger.info(
                f"Job {job_id} completed in {duration_ms:.0f}ms",
                extra={
                    "job_id": job_id,
                    "run_id": run_id,
                    "duration_ms": int(duration_ms),
                    "success": scrape_result.get("success"),
                    "status_code": scrape_result.get("status_code"),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            error_tb = traceback.format_exc()

            logger.error(
                f"Task processing error for job {job_id}: {error_msg}",
                extra={"job_id": job_id, "run_id": run_id, "error": error_msg},
            )

            # Update run
            if run_id:
                async with async_session_factory() as session:
                    await session.execute(
                        update(Run)
                        .where(Run.id == run_id)
                        .values(
                            status=RunStatus.FAILED,
                            error_message=error_msg,
                            stack_trace=error_tb,
                            total_time_ms=int(duration_ms),
                        )
                    )
                    await session.commit()

            # Update job
            async with async_session_factory() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == job_id)
                    .values(
                        status=JobStatus.FAILED,
                        completed_at=datetime.now(timezone.utc),
                        duration_ms=int(duration_ms),
                        error_message=error_msg,
                        error_type=type(e).__name__,
                    )
                )
                await session.commit()

            metrics_collector.observe_job(status="failed", duration_ms=duration_ms)
