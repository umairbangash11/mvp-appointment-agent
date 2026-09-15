"""
Integration tests for appointments API.
Run: pytest backend/tests/test_appointments.py -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from main import app
from db.session import get_db
from models.base import Base

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_booking_agent"

_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with _TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_list_appointments_requires_auth(client: AsyncClient):
    res = await client.get("/appointments")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient):
    res = await client.get("/appointments/stats")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_appointment_not_found_requires_auth(client: AsyncClient):
    res = await client.get("/appointments/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 401
