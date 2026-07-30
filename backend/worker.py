"""Worker entrypoint for background job processing.

Run: python -m backend.worker
Or:  python backend/worker.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import engine, Base, init_models
from app.monitoring.logger import get_logger
from app.proxy.manager import ProxyManager
from app.scraping.browser_pool import BrowserPool
from app.scraping.captcha import CAPTCHAHandler
from app.scraping.engine import ScrapingEngine
from app.worker.queue import QueueManager
from app.worker.tasks import TaskProcessor

logger = get_logger(__name__)


async def main() -> None:
    logger.info(f"Starting worker for {settings.project_name} v{settings.version}")

    init_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    processor = TaskProcessor(
        scraping_engine=scraping_engine,
        proxy_manager=proxy_manager,
        queue_manager=queue_manager,
    )
    await processor.start()

    logger.info("Worker ready, waiting for jobs...")
    try:
        while True:
            processed = await processor.process_next(timeout=10)
            if not processed:
                await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
    finally:
        await processor.stop()
        await queue_manager.stop()
        await browser_pool.stop()
        await proxy_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
