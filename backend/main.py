import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config.settings import settings

STATIC_DIR = Path(__file__).resolve().parent / "static"
AUDIO_DIR = STATIC_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _sweep_old_audio() -> None:
    cutoff = time.time() - 86400
    for f in AUDIO_DIR.glob("*.mp3"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,  # override uvicorn's pre-configured root logger
)
logger = logging.getLogger(__name__)


async def _create_tables() -> None:
    from db.session import engine
    from models import Base  # noqa: F401 — imports all models so metadata is populated
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # logger.info("DATABASE_URL: %s", settings.DATABASE_URL)  # never log secrets
    await _create_tables()

    # Start reminder scheduler
    from scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    _sweep_old_audio()

    yield

    stop_scheduler()


app = FastAPI(title="Doctor Appointment Booking API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, ms)
    return response

# Routers registered after models are importable
from routes.auth import router as auth_router
from routes.appointments import router as appointments_router
from routes.whatsapp import router as whatsapp_router
from routes.patients import router as patients_router

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(appointments_router, prefix="/appointments", tags=["appointments"])
app.include_router(patients_router, prefix="/patients", tags=["patients"])
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["whatsapp"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
