from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Pemenang, SppjKontrak, Tender
from app.schemas import StatsOut

router = APIRouter(tags=["stats"])


def _group_count(db: Session, column) -> dict[str, int]:
    rows = db.execute(
        select(column, func.count()).group_by(column).order_by(func.count().desc())
    ).all()
    return {(key or "(kosong)"): count for key, count in rows}


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)) -> StatsOut:
    total = db.scalar(select(func.count()).select_from(Tender)) or 0
    total_tender = (
        db.scalar(
            select(func.count())
            .select_from(Tender)
            .where(Tender.jenis_paket == "tender")
        )
        or 0
    )
    total_nontender = (
        db.scalar(
            select(func.count())
            .select_from(Tender)
            .where(Tender.jenis_paket == "nontender")
        )
        or 0
    )
    total_pemenang = db.scalar(select(func.count()).select_from(Pemenang)) or 0
    total_kontrak = db.scalar(select(func.count()).select_from(SppjKontrak)) or 0

    return StatsOut(
        total=total,
        total_tender=total_tender,
        total_nontender=total_nontender,
        total_pemenang=total_pemenang,
        total_kontrak=total_kontrak,
        by_status=_group_count(db, Tender.status_tahap),
        by_jenis_pengadaan=_group_count(db, Tender.jenis_pengadaan),
        by_tahun=_group_count(db, Tender.tahun_anggaran),
    )
