from __future__ import annotations

import threading

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.scraper.service import SCRAPE_LOCK, ScraperService

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def run_scrape_job() -> None:
    if not SCRAPE_LOCK.acquire(blocking=False):
        logger.warning("scrape job dilewati: masih ada proses scrape berjalan")
        return
    db = SessionLocal()
    try:
        ScraperService(db).scrape(tahun=settings.tahun)
    except Exception:  # noqa: BLE001
        logger.exception("scheduled scrape failed")
    finally:
        db.close()
        SCRAPE_LOCK.release()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    with _lock:
        if _scheduler is not None:
            return _scheduler
        _scheduler = BackgroundScheduler(timezone="Asia/Jakarta")
        _scheduler.add_job(
            run_scrape_job,
            "interval",
            hours=settings.scrape_interval_hours,
            id="auto_scrape",
            max_instances=1,
            coalesce=True,
        )
        _scheduler.start()
        logger.info(
            f"auto-grab aktif: setiap {settings.scrape_interval_hours} jam "
            f"(tahun={settings.tahun})"
        )
        return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    with _lock:
        if _scheduler is not None:
            _scheduler.shutdown(wait=False)
            _scheduler = None
            logger.info("scheduler dimatikan")
