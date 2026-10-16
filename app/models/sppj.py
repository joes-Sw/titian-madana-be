from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SppjKontrak(Base):
    __tablename__ = "sppj_kontrak"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tender_id: Mapped[str] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), index=True
    )
    nama_penyedia: Mapped[str | None] = mapped_column(Text)
    alamat: Mapped[str | None] = mapped_column(Text)
    npwp: Mapped[str | None] = mapped_column(String(64))
    nilai_kontrak: Mapped[float | None] = mapped_column(Numeric(20, 2))
    nilai_pdn: Mapped[float | None] = mapped_column(Numeric(20, 2))
    nilai_umk: Mapped[float | None] = mapped_column(Numeric(20, 2))
    status_kontrak: Mapped[str | None] = mapped_column(Text)

    tender: Mapped[Tender] = relationship(back_populates="sppj")
