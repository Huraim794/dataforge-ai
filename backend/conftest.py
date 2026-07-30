import asyncio

import pytest

from app.core.config import settings  # noqa: F401


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_client():
    from httpx import AsyncClient

    async with AsyncClient(base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        yield session
        await session.rollback()
