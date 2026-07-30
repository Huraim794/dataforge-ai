from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.schedule import Schedule, ScheduleInterval
from app.monitoring.logger import get_logger
from app.worker.queue import QueueManager

logger = get_logger(__name__)

INTERVAL_MAP: dict[str, tuple[type, dict[str, int]]] = {
    ScheduleInterval.EVERY_MINUTE.value: (IntervalTrigger, {"minutes": 1}),
    ScheduleInterval.EVERY_5_MINUTES.value: (IntervalTrigger, {"minutes": 5}),
    ScheduleInterval.EVERY_15_MINUTES.value: (IntervalTrigger, {"minutes": 15}),
    ScheduleInterval.EVERY_30_MINUTES.value: (IntervalTrigger, {"minutes": 30}),
    ScheduleInterval.HOURLY.value: (IntervalTrigger, {"hours": 1}),
    ScheduleInterval.EVERY_2_HOURS.value: (IntervalTrigger, {"hours": 2}),
    ScheduleInterval.EVERY_4_HOURS.value: (IntervalTrigger, {"hours": 4}),
    ScheduleInterval.EVERY_6_HOURS.value: (IntervalTrigger, {"hours": 6}),
    ScheduleInterval.EVERY_12_HOURS.value: (IntervalTrigger, {"hours": 12}),
    ScheduleInterval.DAILY.value: (IntervalTrigger, {"days": 1}),
    ScheduleInterval.WEEKLY.value: (IntervalTrigger, {"weeks": 1}),
    ScheduleInterval.BIWEEKLY.value: (IntervalTrigger, {"weeks": 2}),
    ScheduleInterval.MONTHLY.value: (IntervalTrigger, {"days": 30}),
}


class JobScheduler:
    def __init__(self, queue_manager: QueueManager) -> None:
        self.queue = queue_manager
        self.scheduler = AsyncIOScheduler(
            timezone=settings.scheduler_timezone,
            job_defaults={
                "coalesce": settings.scheduler_job_defaults_coalesce,
                "max_instances": settings.scheduler_job_defaults_max_instances,
            },
        )
        self._running = False

    async def start(self) -> None:
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled")
            return

        self.scheduler.start()
        await self._load_schedules()
        self._running = True
        logger.info("Job scheduler started")

    async def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Job scheduler stopped")

    async def _load_schedules(self) -> None:
        async with async_session_factory() as session:
            result = await session.execute(select(Schedule).where(Schedule.is_active))
            schedules = list(result.scalars().all())

        for schedule in schedules:
            await self._register_schedule(schedule)

        logger.info(f"Loaded {len(schedules)} schedules")

    async def _register_schedule(self, schedule: Schedule) -> None:
        try:
            if (
                schedule.interval == ScheduleInterval.CUSTOM_CRON
                and schedule.cron_expression
            ):
                trigger = CronTrigger.from_crontab(schedule.cron_expression)
            elif schedule.interval.value in INTERVAL_MAP:
                trigger_cls, kwargs = INTERVAL_MAP[schedule.interval.value]
                trigger = trigger_cls(**kwargs)
            elif schedule.interval == ScheduleInterval.ONCE:
                return
            else:
                logger.warning(f"Unknown schedule interval: {schedule.interval}")
                return

            self.scheduler.add_job(
                func=self._execute_schedule,
                trigger=trigger,
                id=f"schedule_{schedule.id}",
                name=schedule.name,
                args=[schedule.id],
                replace_existing=True,
                next_run_time=schedule.next_run_at,
                start_date=schedule.start_at,
                end_date=schedule.end_at,
                max_instances=settings.scheduler_max_instances,
            )

            logger.info(
                f"Registered schedule: {schedule.name} ({schedule.interval.value})",
                extra={"schedule_id": schedule.id},
            )

        except Exception as e:
            logger.error(
                f"Failed to register schedule {schedule.id}: {e}",
                extra={"schedule_id": schedule.id},
            )

    async def _execute_schedule(self, schedule_id: str) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule or not schedule.is_active:
                if schedule:
                    self.scheduler.remove_job(f"schedule_{schedule_id}")
                return

            if schedule.max_runs > 0 and schedule.runs_so_far >= schedule.max_runs:
                schedule.is_active = False
                await session.commit()
                self.scheduler.remove_job(f"schedule_{schedule_id}")
                logger.info(
                    f"Schedule {schedule.name} reached max runs, deactivating and removing job"
                )
                return

            job_data = {
                "url": schedule.url,
                "schedule_id": schedule.id,
                "headers": schedule.config.get("headers") if schedule.config else None,
                "javascript_enabled": schedule.config.get("javascript_enabled", True)
                if schedule.config
                else True,
                "wait_for_selector": schedule.config.get("wait_for_selector")
                if schedule.config
                else None,
                "wait_time_ms": schedule.config.get("wait_time_ms", 0)
                if schedule.config
                else 0,
                "screenshot": schedule.config.get("screenshot", False)
                if schedule.config
                else False,
                "max_retries": schedule.max_retries,
                "tags": schedule.tags,
            }

            schedule.last_run_at = datetime.now(timezone.utc)
            schedule.runs_so_far += 1
            await session.commit()

        await self.queue.enqueue(job_data, queue="default")
        logger.info(
            f"Schedule {schedule.name} triggered job",
            extra={"schedule_id": schedule_id},
        )

    async def add_schedule(self, schedule: Schedule) -> None:
        await self._register_schedule(schedule)

    async def remove_schedule(self, schedule_id: str) -> None:
        job_id = f"schedule_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    async def pause_schedule(self, schedule_id: str) -> None:
        job_id = f"schedule_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)

    async def resume_schedule(self, schedule_id: str) -> None:
        job_id = f"schedule_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)

    async def reload_schedules(self) -> None:
        self.scheduler.remove_all_jobs()
        await self._load_schedules()
