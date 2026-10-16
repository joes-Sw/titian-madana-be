from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    jenis_paket: Mapped[str | None] = mapped_column(String(16), index=True)
    judul: Mapped[str | None] = mapped_column(Text)
    instansi: Mapped[str | None] = mapped_column(Text)
    satuan_kerja: Mapped[str | None] = mapped_column(Text)
    jenis_pengadaan: Mapped[str | None] = mapped_column(Text, index=True)
    metode_pemilihan: Mapped[str | None] = mapped_column(Text)
    metode_evaluasi: Mapped[str | None] = mapped_column(Text)
    kualifikasi: Mapped[str | None] = mapped_column(Text)
    tahun_anggaran: Mapped[str | None] = mapped_column(String(32), index=True)
    kode_rup: Mapped[str | None] = mapped_column(String(64))
    sumber_dana: Mapped[str | None] = mapped_column(Text)
    jenis_kontrak: Mapped[str | None] = mapped_column(Text)
    lokasi: Mapped[str | None] = mapped_column(Text)
    nilai_pagu: Mapped[float | None] = mapped_column(Numeric(20, 2))
    nilai_hps: Mapped[float | None] = mapped_column(Numeric(20, 2))
    status_tahap: Mapped[str | None] = mapped_column(Text, index=True)
    versi_spse: Mapped[str | None] = mapped_column(String(16))

    tgl_mulai_pengumuman: Mapped[datetime | None] = mapped_column(DateTime)
    tgl_selesai_pengumuman: Mapped[datetime | None] = mapped_column(DateTime)
    tgl_mulai_sanggah: Mapped[datetime | None] = mapped_column(DateTime)
    tgl_selesai_sanggah: Mapped[datetime | None] = mapped_column(DateTime)

    raw_jadwal: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    pemenang: Mapped[list[Pemenang]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )
    sppj: Mapped[list[SppjKontrak]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )
