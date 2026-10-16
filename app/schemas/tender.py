from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PemenangOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama_penyedia: str | None = None
    alamat: str | None = None
    npwp: str | None = None
    harga_penawaran: float | None = None
    harga_terkoreksi: float | None = None
    harga_negosiasi: float | None = None


class SppjOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama_penyedia: str | None = None
    alamat: str | None = None
    npwp: str | None = None
    nilai_kontrak: float | None = None
    nilai_pdn: float | None = None
    nilai_umk: float | None = None
    status_kontrak: str | None = None


class TenderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    jenis_paket: str | None = None
    judul: str | None = None
    instansi: str | None = None
    satuan_kerja: str | None = None
    jenis_pengadaan: str | None = None
    metode_pemilihan: str | None = None
    metode_evaluasi: str | None = None
    kualifikasi: str | None = None
    tahun_anggaran: str | None = None
    kode_rup: str | None = None
    sumber_dana: str | None = None
    jenis_kontrak: str | None = None
    lokasi: str | None = None
    nilai_pagu: float | None = None
    nilai_hps: float | None = None
    status_tahap: str | None = None
    versi_spse: str | None = None
    tgl_mulai_pengumuman: datetime | None = None
    tgl_selesai_pengumuman: datetime | None = None
    tgl_mulai_sanggah: datetime | None = None
    tgl_selesai_sanggah: datetime | None = None
    url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TenderDetailOut(TenderOut):
    pemenang: list[PemenangOut] = []
    sppj: list[SppjOut] = []


class TenderListOut(BaseModel):
    total: int
    page: int
    size: int
    items: list[TenderOut]


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    tahun: str | None = None
    jenis_paket: str | None = None
    status: str | None = None
    records_found: int = 0
    records_new: int = 0
    records_updated: int = 0
    error: str | None = None


class StatsOut(BaseModel):
    total: int
    total_tender: int
    total_nontender: int
    total_pemenang: int
    total_kontrak: int
    by_status: dict[str, int]
    by_jenis_pengadaan: dict[str, int]
    by_tahun: dict[str, int]
