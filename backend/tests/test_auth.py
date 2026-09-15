"""
Integration tests for doctor auth endpoints.
Requires a running PostgreSQL instance via DATABASE_URL in .env.
Run: pytest backend/tests/test_auth.py -v
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


DOCTOR_PAYLOAD = {
    "name": "Dr. Test User",
    "email": "testdoctor@example.com",
    "password": "SecurePass123!",
    "clinic_name": "Test Clinic",
    "phone": "+15551234567",
    "state": "CA",
}


@pytest.mark.asyncio
async def test_signup_creates_doctor(client: AsyncClient):
    res = await client.post("/auth/signup", json=DOCTOR_PAYLOAD)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == DOCTOR_PAYLOAD["email"]
    assert "id" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    await client.post("/auth/signup", json=DOCTOR_PAYLOAD)
    res = await client.post("/auth/signup", json=DOCTOR_PAYLOAD)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_unverified_fails(client: AsyncClient):
    res = await client.post(
        "/auth/login",
        json={"email": DOCTOR_PAYLOAD["email"], "password": DOCTOR_PAYLOAD["password"]},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    res = await client.post(
        "/auth/login",
        json={"email": DOCTOR_PAYLOAD["email"], "password": "wrongpassword"},
    )
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_forgot_password_always_200(client: AsyncClient):
    res = await client.post("/auth/forgot-password", json={"email": "nonexistent@example.com"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_profile_requires_auth(client: AsyncClient):
    res = await client.get("/auth/profile")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient):
    res = await client.post("/auth/refresh", json={"refresh_token": "badtoken"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_doctor_signup(client: AsyncClient):
    payload = {
        "name": "Dr. Wasim",
        "email": "wasim@clinic.com",
        "password": "test123",
        "clinic_name": "Dr. Wasim Clinic",
        "phone": "+923125298755",
        "state": "Dubai",
    }

    res = await client.post("/auth/signup", json=payload)
    assert res.status_code == 201

    # /auth/signup returns {"message": "..."} not {"id": ...}
    # so we verify the doctor was saved by querying the DB directly
    async with _TestSession() as session:
        from sqlalchemy import select
        from models.doctor import Doctor
        result = await session.execute(
            select(Doctor).where(Doctor.email == payload["email"])
        )
        doctor = result.scalar_one_or_none()
        assert doctor is not None
        assert str(doctor.id) != ""  # id was assigned
        assert doctor.name == payload["name"]
