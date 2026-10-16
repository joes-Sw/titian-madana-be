from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402
from app.scraper.service import ScraperService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape data SPSE Inaproc")
    parser.add_argument("--tahun", type=int, default=settings.tahun)
    parser.add_argument("--no-tender", action="store_true")
    parser.add_argument("--no-nontender", action="store_true")
    parser.add_argument("--no-detail", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    setup_logging()
    init_db()

    db = SessionLocal()
    try:
        service = ScraperService(db)
        if args.delay is not None:
            service.client.delay = args.delay
        run = service.scrape(
            tahun=args.tahun,
            tender=not args.no_tender,
            nontender=not args.no_nontender,
            detail=not args.no_detail,
            limit=args.limit,
        )
        print("\n===== HASIL SCRAPE =====")
        print(f"status        : {run.status}")
        print(f"tahun         : {run.tahun}")
        print(f"scope         : {run.jenis_paket}")
        print(f"records_found : {run.records_found}")
        print(f"records_new   : {run.records_new}")
        print(f"records_updated: {run.records_updated}")
        if run.error:
            print(f"error         : {run.error}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
