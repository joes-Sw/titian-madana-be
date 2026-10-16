"""Entry point aplikasi FastAPI.

Mendaftarkan seluruh router (auth, tenders, stats, admin), mengaktifkan CORS,
dan menjalankan bootstrap saat startup: setup logging, buat tabel DB, seed
akun dummy, lalu jalankan scheduler scraping.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import admin, auth, stats, tenders
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.seed import seed_default_users
from app.db.session import SessionLocal, init_db
from app.scheduler.jobs import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap saat aplikasi start dan cleanup saat shutdown."""
    setup_logging()
    init_db()
    # Buat akun dummy (superadmin/manager/marketing) bila belum ada.
    with SessionLocal() as db:
        created = seed_default_users(db)
    if created:
        logger.info("Akun dummy dibuat: {}", ", ".join(created))
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(tenders.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
