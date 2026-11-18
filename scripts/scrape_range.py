"""Scrape paket SPSE berdasarkan rentang tanggal pengumuman.

Alur:
1. Enumerasi seluruh paket pada tahun anggaran tertentu dari datatable SPSE.
2. Ambil halaman jadwal tiap paket untuk membaca tanggal mulai pengumuman.
3. Filter paket yang tanggal mulainya berada di dalam rentang (inklusif).
4. Enrich (detail + jadwal + pemenang/kontrak) hanya untuk paket yang cocok.

Contoh pemakaian::

    python -m scripts.scrape_range --tahun 2026 \
        --dari 2026-08-12 --sampai 2026-09-01

Tambahkan ``--dry-run`` untuk sekadar memeriksa berapa paket yang cocok tanpa
menyimpan ke database.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402
from app.models import ScrapeRun  # noqa: E402
from app.scraper import endpoints as ep  # noqa: E402
from app.scraper import parser  # noqa: E402
from app.scraper.client import SpseClient  # noqa: E402
from app.scraper.service import ScraperService  # noqa: E402

JENIS_CONFIG = {
    "tender": (
        ep.DT_LELANG,
        ep.LELANG_LIST,
        parser.parse_list_row_tender,
        ep.jadwal_tender,
        ep.pengumumanlelang,
    ),
    "nontender": (
        ep.DT_PL,
        ep.NONTENDER_LIST,
        parser.parse_list_row_nontender,
        ep.jadwal_nontender,
        ep.pengumumanpl,
    ),
}


def created_date(html: str | None) -> datetime | None:
    """Ambil 'Tanggal Pembuatan' dari halaman detail sebagai fallback tanggal."""
    if not html:
        return None
    kv = parser.parse_kv(parser.make_soup(html))
    raw = kv.get("Tanggal Pembuatan") or kv.get("Tanggal Pengumuman")
    return parser.parse_datetime(raw)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Scrape paket SPSE dalam rentang tanggal pengumuman")
    p.add_argument("--tahun", type=int, default=settings.tahun)
    p.add_argument("--dari", required=True, help="tanggal awal (YYYY-MM-DD), inklusif")
    p.add_argument("--sampai", required=True, help="tanggal akhir (YYYY-MM-DD), inklusif")
    p.add_argument("--jenis", choices=["semua", "tender", "nontender"], default="semua")
    p.add_argument("--delay", type=float, default=0.7, help="jeda antar request (detik)")
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--limit-scan", type=int, default=None, help="batasi jumlah paket yang dipindai (uji coba)")
    p.add_argument("--dry-run", action="store_true", help="jangan simpan ke database")
    return p


def main() -> None:
    args = build_parser().parse_args()
    dari = date.fromisoformat(args.dari)
    sampai = date.fromisoformat(args.sampai)
    if sampai < dari:
        raise SystemExit("--sampai tidak boleh lebih awal dari --dari")

    setup_logging()
    init_db()

    jenis_list = ["tender", "nontender"] if args.jenis == "semua" else [args.jenis]
    client = SpseClient(delay=args.delay)

    db = SessionLocal()
    service = ScraperService(db, client)

    logger.info(
        f"scan window {dari} .. {sampai} | tahun={args.tahun} | jenis={','.join(jenis_list)}"
    )

    scanned = 0
    matched: list[tuple[str, dict, str, bool]] = []
    unknown: list[tuple[str, str, str | None]] = []
    seen: set[str] = set()
    run: ScrapeRun | None = None

    try:
        for jenis in jenis_list:
            dt_path, list_path, row_parser, jadwal_fn, detail_fn = JENIS_CONFIG[jenis]
            for row in client.iter_list(dt_path, args.tahun, list_path, args.page_size):
                if args.limit_scan is not None and scanned >= args.limit_scan:
                    break
                base = row_parser(row)
                tender_id = base["id"]
                if tender_id in seen:
                    logger.warning(f"duplikat id dari list: {tender_id}")
                    continue
                seen.add(tender_id)
                scanned += 1

                html = client.html(jadwal_fn(tender_id), list_path)
                tahapan, flat = parser.parse_jadwal(html) if html else ([], {})
                mulai = flat.get("tgl_mulai_pengumuman")
                sumber = "jadwal"

                if mulai is None:
                    # Sebagian paket tidak menampilkan tahap pengumuman pada
                    # halaman jadwal; pakai tanggal pembuatan sebagai perkiraan.
                    dibuat = created_date(client.html(detail_fn(tender_id), list_path))
                    if dibuat is None:
                        unknown.append((jenis, tender_id, base.get("judul")))
                        logger.warning(f"[{jenis}] {tender_id}: tanggal tidak terbaca")
                    elif dari <= dibuat.date() <= sampai:
                        sumber = "tanggal_pembuatan"
                        matched.append((jenis, base, sumber, False))
                        logger.info(
                            f"[COCOK-PERKIRAAN] {jenis} {tender_id} | {dibuat:%Y-%m-%d} | "
                            f"{(base.get('judul') or '')[:60]}"
                        )
                    else:
                        logger.info(f"[{jenis}] {tender_id}: di luar rentang (dibuat {dibuat:%Y-%m-%d})")
                elif dari <= mulai.date() <= sampai:
                    matched.append((jenis, base, sumber, True))
                    logger.info(
                        f"[COCOK] {jenis} {tender_id} | {mulai:%Y-%m-%d} | "
                        f"{(base.get('judul') or '')[:70]}"
                    )

                if scanned % 25 == 0:
                    logger.info(
                        f"progress: {scanned} paket dipindai, {len(matched)} cocok, "
                        f"{len(unknown)} tanpa tanggal"
                    )

        print(f"\nSelesai memindai {scanned} paket; {len(matched)} masuk rentang, "
              f"{len(unknown)} tanpa tanggal.")

        if args.dry_run:
            print("DRY RUN: tidak ada yang disimpan (database tidak disentuh).")
            return

        run = ScrapeRun(
            started_at=datetime.now(),
            tahun=str(args.tahun),
            jenis_paket=",".join(jenis_list),
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        for jenis, base, sumber, pasti in matched:
            try:
                tender, is_new = service._upsert_tender(base)
                service._enrich(tender, jenis)
                db.commit()
                run.records_found += 1
                if is_new:
                    run.records_new += 1
                else:
                    run.records_updated += 1
                logger.info(
                    f"tersimpan: {jenis} {base['id']} (new={is_new}, tanggal via {sumber})"
                )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.exception(f"gagal menyimpan {jenis} {base['id']}: {exc}")

        run.status = "success"
    except Exception as exc:  # noqa: BLE001
        logger.exception("scrape_range gagal")
        if run is not None:
            run.status = "failed"
            run.error = str(exc)[:500]
    finally:
        if run is not None:
            run.finished_at = datetime.now()
            db.add(run)
            db.commit()
            db.refresh(run)
        db.close()

    if run is None:
        return

    print("\n===== HASIL =====")
    print(f"status         : {run.status}")
    print(f"tahun          : {run.tahun}")
    print(f"rentang        : {dari} .. {sampai}")
    print(f"jenis          : {','.join(jenis_list)}")
    print(f"dipindai       : {scanned}")
    print(f"cocok          : {len(matched)}")
    print(f"records_found  : {run.records_found}")
    print(f"records_new    : {run.records_new}")
    print(f"records_updated: {run.records_updated}")
    if matched:
        print(f"\ncocok ({len(matched)}):")
        for jenis, base, sumber, pasti in matched:
            tanda = "" if pasti else " [PERKIRAAN]"
            print(f"  - [{jenis}] {base['id']} {sumber}{tanda} | {(base.get('judul') or '')[:62]}")
    if unknown:
        print(f"tanpa tanggal  : {len(unknown)} (tidak disimpan)")
        for jenis, tid, judul in unknown[:20]:
            print(f"  - [{jenis}] {tid} {(judul or '')[:60]}")
    if run.error:
        print(f"error          : {run.error}")


if __name__ == "__main__":
    main()
