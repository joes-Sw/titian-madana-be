from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Pemenang, SppjKontrak, Tender  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        total = db.scalar(select(func.count()).select_from(Tender)) or 0
        print(f"TOTAL PAKET      : {total}")
        for paket in ("tender", "nontender"):
            n = db.scalar(
                select(func.count())
                .select_from(Tender)
                .where(Tender.jenis_paket == paket)
            )
            print(f"  - {paket:<10}: {n}")
        print(f"TOTAL PEMENANG   : {db.scalar(select(func.count()).select_from(Pemenang))}")
        print(f"TOTAL KONTRAK    : {db.scalar(select(func.count()).select_from(SppjKontrak))}")

        print("\n--- Distribusi jenis pengadaan ---")
        for jenis, n in db.execute(
            select(Tender.jenis_pengadaan, func.count()).group_by(Tender.jenis_pengadaan)
        ).all():
            print(f"  {jenis}: {n}")

        print("\n--- Contoh data (10 teratas) ---")
        tenders = db.scalars(select(Tender).limit(10)).all()
        for t in tenders:
            p = db.scalar(select(Pemenang).where(Pemenang.tender_id == t.id))
            s = db.scalar(select(SppjKontrak).where(SppjKontrak.tender_id == t.id))
            print("=" * 88)
            print(f"[{t.jenis_paket}] {t.id} | TA {t.tahun_anggaran} | {t.jenis_pengadaan}")
            print(f"  Judul    : {(t.judul or '')[:78]}")
            print(f"  Instansi : {t.instansi}")
            print(f"  HPS      : {t.nilai_hps}  | Status: {t.status_tahap}")
            print(
                f"  Pengumuman: {t.tgl_mulai_pengumuman} -> {t.tgl_selesai_pengumuman}"
                f" | Sanggah: {t.tgl_mulai_sanggah} -> {t.tgl_selesai_sanggah}"
            )
            if p:
                print(
                    f"  Pemenang : {p.nama_penyedia} | NPWP {p.npwp} | "
                    f"penawaran {p.harga_penawaran} | negosiasi {p.harga_negosiasi}"
                )
            if s:
                print(
                    f"  Kontrak  : {s.nama_penyedia} | nilai {s.nilai_kontrak} | "
                    f"status {s.status_kontrak}"
                )
    finally:
        db.close()


if __name__ == "__main__":
    main()
