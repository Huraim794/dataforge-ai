from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.exceptions import DataForgeError
from app.core.redis import close_redis
from app.monitoring.logger import get_logger
from app.proxy.manager import ProxyManager
from app.scraping.browser_pool import BrowserPool
from app.scraping.captcha import CAPTCHAHandler
from app.scraping.engine import ScrapingEngine
from app.scheduler.scheduler import JobScheduler
from app.worker.queue import QueueManager
from app.worker.tasks import TaskProcessor

logger = get_logger(__name__)

# Global service instances
browser_pool: BrowserPool | None = None
proxy_manager: ProxyManager | None = None
captcha_handler: CAPTCHAHandler | None = None
scraping_engine: ScrapingEngine | None = None
queue_manager: QueueManager | None = None
task_processor: TaskProcessor | None = None
job_scheduler: JobScheduler | None = None
worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global browser_pool, proxy_manager, captcha_handler, scraping_engine
    global queue_manager, task_processor, job_scheduler, worker_task

    logger.info(f"Starting {settings.project_name} v{settings.version}")
    start_time = time.time()

    # Create tables before starting services
    from app.core.database import init_models

    init_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize services
    proxy_manager = ProxyManager()
    await proxy_manager.start()

    browser_pool = BrowserPool()
    await browser_pool.start()

    captcha_handler = CAPTCHAHandler()

    scraping_engine = ScrapingEngine(
        browser_pool=browser_pool,
        proxy_manager=proxy_manager,
        captcha_handler=captcha_handler,
    )

    queue_manager = QueueManager()
    await queue_manager.start()

    task_processor = TaskProcessor(
        scraping_engine=scraping_engine,
        proxy_manager=proxy_manager,
        queue_manager=queue_manager,
    )
    await task_processor.start()

    job_scheduler = JobScheduler(queue_manager=queue_manager)
    await job_scheduler.start()

    # Start background worker
    worker_task = asyncio.create_task(run_worker_loop())

    startup_time = time.time() - start_time
    logger.info(
        f"{settings.project_name} started in {startup_time:.2f}s",
        extra={"startup_time_ms": int(startup_time * 1000)},
    )

    yield

    # Shutdown
    logger.info("Shutting down services...")
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    if task_processor:
        await task_processor.stop()
    if job_scheduler:
        await job_scheduler.stop()
    if browser_pool:
        await browser_pool.stop()
    if proxy_manager:
        await proxy_manager.stop()
    if queue_manager:
        await queue_manager.stop()
    if captcha_handler:
        await captcha_handler.close()
    await close_redis()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Production-Grade Web Intelligence Powered by AI",
    lifespan=lifespan,
    root_path=settings.root_path,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
if settings.prometheus_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# API routes
app.include_router(api_v1_router, prefix="/api")


@app.exception_handler(DataForgeError)
async def dataforge_error_handler(
    request: Request, exc: DataForgeError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code or "INTERNAL_ERROR",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        },
    )


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.project_name,
        "version": settings.version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    from app.core.database import check_database_health
    from app.core.redis import check_redis_health

    db_ok = await check_database_health()
    redis_ok = await check_redis_health()
    overall = "healthy" if db_ok and redis_ok else "degraded"

    return {
        "status": overall,
        "version": settings.version,
        "database": "up" if db_ok else "down",
        "redis": "up" if redis_ok else "down",
        "browser_pool": browser_pool.available_count if browser_pool else 0,
        "proxy_pool": proxy_manager._pool.__len__()
        if proxy_manager and hasattr(proxy_manager, "_pool")
        else 0,
    }


async def run_worker_loop() -> None:
    """Background loop that processes jobs from the queue."""
    logger.info("Worker loop started")
    while True:
        try:
            if task_processor:
                processed = await task_processor.process_next(timeout=5)
                if not processed:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(5)
    logger.info("Worker loop stopped")
