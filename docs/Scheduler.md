# Scheduler

## Purpose and Architecture

The `JobScheduler` enables recurring web scraping jobs. It uses APScheduler's `AsyncIOScheduler` to manage scheduled tasks and integrates with the queue system to dispatch jobs asynchronously.

The scheduler loads active schedules from the database on startup, registers each as an APScheduler job, and triggers execution at the configured intervals.

## APScheduler Integration

The scheduler uses `AsyncIOScheduler` with the following defaults:

```python
self.scheduler = AsyncIOScheduler(
    timezone=settings.scheduler_timezone,
    job_defaults={
        "coalesce": settings.scheduler_job_defaults_coalesce,
        "max_instances": settings.scheduler_job_defaults_max_instances,
    },
)
```

- **Coalesce**: when `True` (default), if multiple missed runs accumulate, only the most recent run is executed.
- **Max instances**: limits concurrent executions of the same schedule (default 1).

## Schedule Intervals

The `ScheduleInterval` enum (`app/models/schedule.py`) defines the available intervals:

| Enum Value | APScheduler Trigger | Parameters |
|---|---|---|
| `every_minute` | `IntervalTrigger` | `minutes=1` |
| `every_5_minutes` | `IntervalTrigger` | `minutes=5` |
| `every_15_minutes` | `IntervalTrigger` | `minutes=15` |
| `every_30_minutes` | `IntervalTrigger` | `minutes=30` |
| `hourly` | `IntervalTrigger` | `hours=1` |
| `every_2_hours` | `IntervalTrigger` | `hours=2` |
| `every_4_hours` | `IntervalTrigger` | `hours=4` |
| `every_6_hours` | `IntervalTrigger` | `hours=6` |
| `every_12_hours` | `IntervalTrigger` | `hours=12` |
| `daily` | `IntervalTrigger` | `days=1` |
| `weekly` | `IntervalTrigger` | `weeks=1` |
| `biweekly` | `IntervalTrigger` | `weeks=2` |
| `monthly` | `IntervalTrigger` | `days=30` |
| `custom_cron` | `CronTrigger` | Parsed from `cron_expression` field |

The mapping is defined in `INTERVAL_MAP`:

```python
INTERVAL_MAP: dict[str, tuple[type, dict[str, int]]] = {
    ScheduleInterval.EVERY_MINUTE.value: (IntervalTrigger, {"minutes": 1}),
    ScheduleInterval.HOURLY.value: (IntervalTrigger, {"hours": 1}),
    ...
}
```

## Schedule Lifecycle

### Create

A schedule is persisted to the database with fields:
- `url` — target URL to scrape
- `interval` — one of the `ScheduleInterval` values
- `cron_expression` — custom cron string (for `CUSTOM_CRON`)
- `config` — JSON dict with headers, javascript_enabled, wait_for_selector, wait_time_ms, screenshot
- `max_runs` — maximum executions (0 = unlimited)
- `start_at` / `end_at` — optional time window
- `is_active` — whether the schedule is currently active

### Register

When the scheduler starts or a new schedule is created, `_register_schedule` converts the schedule into an APScheduler job:

```python
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
)
```

### Execute

On each trigger, `_execute_schedule(schedule_id)` runs:

1. Load the schedule from the database.
2. If `is_active` is `False`, remove the job and return.
3. If `max_runs > 0` and `runs_so_far >= max_runs`, deactivate the schedule and remove the job.
4. Build a job payload from the schedule config.
5. Update `last_run_at` and increment `runs_so_far`.
6. Enqueue the job via `QueueManager.enqueue()`.

```python
job_data = {
    "url": schedule.url,
    "schedule_id": schedule.id,
    "headers": schedule.config.get("headers"),
    "javascript_enabled": schedule.config.get("javascript_enabled", True),
    ...
}
await self.queue.enqueue(job_data, queue="default")
```

### Deactivate

Schedules can be deactivated manually via `remove_schedule`, `pause_schedule`, or automatically when `max_runs` is reached. Paused jobs remain in APScheduler but are not executed.

## Integration with Queue System

The scheduler does not execute scrapes directly. It enqueues jobs into the Redis-backed queue system (`QueueManager`), where worker processes pick them up. This decouples scheduling from execution and allows:

- Job retry with exponential backoff (handled by `QueueManager.requeue`)
- Priority queuing (critical, high, default, low, retry)
- Dead-letter handling after max retries
- Horizontal scaling of workers

## Job Execution Flow

```
Database ──► JobScheduler (loaded active schedules)
                 │
                 ▼
            APScheduler AsyncIOScheduler (cron/interval triggers)
                 │
                 ▼
            _execute_schedule(schedule_id)
                 │
                 ├── Check is_active, max_runs
                 ├── Update last_run_at, runs_so_far
                 └── QueueManager.enqueue(job_data)
                          │
                          ▼
                     Redis Queue
                          │
                          ▼
                     Worker (TaskProcessor.process_next)
                          │
                          ▼
                     ScrapingEngine.scrape(url)
```

## Configuration Reference

| Setting | Default | Description |
|---|---|---|
| `scheduler_enabled` | `True` | Enable scheduler on startup |
| `scheduler_timezone` | `UTC` | Timezone for schedule evaluation |
| `scheduler_max_instances` | `3` | Max concurrent jobs for a single trigger |
| `scheduler_job_defaults_coalesce` | `True` | Coalesce missed job runs |
| `scheduler_job_defaults_max_instances` | `1` | Default max concurrent instances per job |
