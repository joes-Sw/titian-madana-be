from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Pemenang, ScrapeRun, SppjKontrak, Tender
from app.scraper import endpoints as ep
from app.scraper import parser
from app.scraper.client import SpseClient

SCRAPE_LOCK = threading.Lock()


class ScraperService:
    def __init__(self, db: Session, client: SpseClient | None = None) -> None:
        self.db = db
        self.client = client or SpseClient()

    def _upsert_tender(self, data: dict[str, Any]) -> tuple[Tender, bool]:
        tender = self.db.get(Tender, data["id"])
        is_new = tender is None
        if tender is None:
            tender = Tender(id=data["id"])
            self.db.add(tender)
        self._apply(tender, data)
        return tender, is_new

    @staticmethod
    def _apply(obj: Any, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if key == "id" or value is None:
                continue
            if hasattr(obj, key):
                setattr(obj, key, value)

    def _enrich_pemenang(self, tender: Tender) -> None:
        self.db.execute(
            delete(Pemenang).where(Pemenang.tender_id == tender.id)
        )
        self.db.execute(
            delete(SppjKontrak).where(SppjKontrak.tender_id == tender.id)
        )

        html = self.client.html(ep.pemenang(tender.id), ep.LELANG_LIST)
        if html:
            for item in parser.parse_pemenang(html):
                self.db.add(Pemenang(tender_id=tender.id, **item))

        html = self.client.html(
            ep.pemenang_berkontrak(tender.id), ep.LELANG_LIST
        )
        if html:
            for item in parser.parse_sppj(html):
                self.db.add(SppjKontrak(tender_id=tender.id, **item))

    def _enrich(self, tender: Tender, jenis: str) -> None:
        if jenis == "tender":
            detail_path = ep.pengumumanlelang(tender.id)
            jadwal_path = ep.jadwal_tender(tender.id)
            referer = ep.LELANG_LIST
        else:
            detail_path = ep.pengumumanpl(tender.id)
            jadwal_path = ep.jadwal_nontender(tender.id)
            referer = ep.NONTENDER_LIST

        html = self.client.html(detail_path, referer)
        if html:
            self._apply(tender, parser.parse_detail(html))
        tender.url = f"{settings.base_url}{detail_path}"

        jadwal_html = self.client.html(jadwal_path, referer)
        if jadwal_html:
            tahapan, flat = parser.parse_jadwal(jadwal_html)
            self._apply(tender, flat)
            tender.raw_jadwal = parser.dumps_tahapan(tahapan)

        if jenis == "tender":
            self._enrich_pemenang(tender)

    def _scrape_list(
        self,
        tahun: int,
        jenis: str,
        detail: bool,
        run: ScrapeRun,
        limit: int | None = None,
    ) -> None:
        if jenis == "tender":
            dt_path = ep.DT_LELANG
            list_path = ep.LELANG_LIST
            row_parser = parser.parse_list_row_tender
        else:
            dt_path = ep.DT_PL
            list_path = ep.NONTENDER_LIST
            row_parser = parser.parse_list_row_nontender

        count = 0
        for row in self.client.iter_list(dt_path, tahun, list_path):
            if limit is not None and count >= limit:
                break
            try:
                base = row_parser(row)
                tender, is_new = self._upsert_tender(base)
                if detail:
                    self._enrich(tender, jenis)
                self.db.commit()

                count += 1
                run.records_found += 1
                if is_new:
                    run.records_new += 1
                else:
                    run.records_updated += 1
            except Exception as exc:  # noqa: BLE001
                self.db.rollback()
                logger.warning(f"failed on {jenis} row {row[:1]}: {exc}")
            if count and count % 10 == 0:
                self.db.add(run)
                self.db.commit()

    def scrape(
        self,
        tahun: int | None = None,
        tender: bool | None = None,
        nontender: bool | None = None,
        detail: bool | None = None,
        limit: int | None = None,
    ) -> ScrapeRun:
        tahun = tahun or settings.tahun
        tender = settings.scrape_tender if tender is None else tender
        nontender = settings.scrape_nontender if nontender is None else nontender
        detail = settings.scrape_detail if detail is None else detail

        scope = ",".join(
            filter(
                None,
                [
                    "tender" if tender else None,
                    "nontender" if nontender else None,
                ],
            )
        )
        run = ScrapeRun(
            started_at=datetime.now(),
            tahun=str(tahun),
            jenis_paket=scope,
            status="running",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        logger.info(f"scrape start: tahun={tahun} scope={scope} detail={detail}")
        try:
            if tender:
                self._scrape_list(tahun, "tender", detail, run, limit)
            if nontender:
                self._scrape_list(tahun, "nontender", detail, run, limit)
            run.status = "success"
        except Exception as exc:  # noqa: BLE001
            logger.exception("scrape failed")
            run.status = "failed"
            run.error = str(exc)
        finally:
            run.finished_at = datetime.now()
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)

        logger.info(
            f"scrape done: status={run.status} found={run.records_found} "
            f"new={run.records_new} updated={run.records_updated}"
        )
        return run
