from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Pemenang(Base):
    __tablename__ = "pemenang"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tender_id: Mapped[str] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), index=True
    )
    nama_penyedia: Mapped[str | None] = mapped_column(Text)
    alamat: Mapped[str | None] = mapped_column(Text)
    npwp: Mapped[str | None] = mapped_column(String(64))
    harga_penawaran: Mapped[float | None] = mapped_column(Numeric(20, 2))
    harga_terkoreksi: Mapped[float | None] = mapped_column(Numeric(20, 2))
    harga_negosiasi: Mapped[float | None] = mapped_column(Numeric(20, 2))

    tender: Mapped[Tender] = relationship(back_populates="pemenang")
