from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Pemenang, SppjKontrak, Tender
from app.schemas import PemenangOut, SppjOut, TenderDetailOut, TenderListOut

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=TenderListOut)
def list_tenders(
    db: Session = Depends(get_db),
    tahun: str | None = Query(None, description="Tahun anggaran, mis. 2026"),
    jenis_paket: str | None = Query(None, description="tender / nontender"),
    jenis_pengadaan: str | None = None,
    status: str | None = Query(None, description="cari pada status tahap"),
    q: str | None = Query(None, description="cari pada judul"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
) -> TenderListOut:
    stmt = select(Tender)
    if tahun:
        stmt = stmt.where(Tender.tahun_anggaran == tahun)
    if jenis_paket:
        stmt = stmt.where(Tender.jenis_paket == jenis_paket)
    if jenis_pengadaan:
        stmt = stmt.where(Tender.jenis_pengadaan.ilike(f"%{jenis_pengadaan}%"))
    if status:
        stmt = stmt.where(Tender.status_tahap.ilike(f"%{status}%"))
    if q:
        stmt = stmt.where(Tender.judul.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = (
        stmt.order_by(Tender.updated_at.desc(), Tender.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = list(db.scalars(stmt).all())
    return TenderListOut(total=total, page=page, size=size, items=items)


@router.get("/{tender_id}", response_model=TenderDetailOut)
def get_tender(tender_id: str, db: Session = Depends(get_db)) -> Tender:
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=404, detail="Tender tidak ditemukan")
    return tender


@router.get("/{tender_id}/pemenang", response_model=list[PemenangOut])
def get_pemenang(tender_id: str, db: Session = Depends(get_db)) -> list[Pemenang]:
    if db.get(Tender, tender_id) is None:
        raise HTTPException(status_code=404, detail="Tender tidak ditemukan")
    stmt = select(Pemenang).where(Pemenang.tender_id == tender_id)
    return list(db.scalars(stmt).all())


@router.get("/{tender_id}/sppj", response_model=list[SppjOut])
def get_sppj(tender_id: str, db: Session = Depends(get_db)) -> list[SppjKontrak]:
    if db.get(Tender, tender_id) is None:
        raise HTTPException(status_code=404, detail="Tender tidak ditemukan")
    stmt = select(SppjKontrak).where(SppjKontrak.tender_id == tender_id)
    return list(db.scalars(stmt).all())
