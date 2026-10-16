from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.core.security import ROLE_MANAGER, ROLE_SUPERADMIN
from app.db.session import get_db
from app.models import ScrapeRun
from app.schemas import ScrapeRunOut
from app.scraper.service import SCRAPE_LOCK, ScraperService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/scrape",
    response_model=ScrapeRunOut,
    summary="Jalankan scrape manual",
    responses={
        401: {"description": "Belum login / token tidak valid"},
        403: {"description": "Role tidak diizinkan (hanya superadmin & manager)"},
        409: {"description": "Scrape lain sedang berjalan"},
    },
)
def trigger_scrape(
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER)),
    tahun: int = Query(default=settings.tahun),
    tender: bool = Query(default=True),
    nontender: bool = Query(default=True),
    detail: bool = Query(default=True),
    limit: int | None = Query(default=None, description="batasi jumlah paket (uji coba)"),
) -> ScrapeRun:
    """Trigger scraping SPSE secara manual.

    Hanya dapat diakses role **superadmin** dan **manager**. Mengembalikan
    ringkasan run (jumlah records). Diblokir dengan HTTP 409 bila ada proses
    scrape lain yang masih berjalan.
    """
    if not SCRAPE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Scrape sedang berjalan")
    try:
        service = ScraperService(db)
        return service.scrape(
            tahun=tahun, tender=tender, nontender=nontender, detail=detail, limit=limit
        )
    finally:
        SCRAPE_LOCK.release()


@router.get(
    "/scrape/runs",
    response_model=list[ScrapeRunOut],
    summary="Riwayat scrape",
    responses={401: {"description": "Belum login / token tidak valid"}},
)
def list_scrape_runs(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[ScrapeRun]:
    """Daftar riwayat scrape terbaru.

    Dapat diakses oleh semua role yang sudah login (superadmin, manager,
    marketing).
    """
    stmt = select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())
