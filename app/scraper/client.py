from __future__ import annotations

import random
import re
import time
from collections.abc import Iterator
from typing import Any

from curl_cffi import requests
from loguru import logger

from app.core.config import settings

TOKEN_RE = re.compile(r"authenticityToken\s*=\s*'([a-f0-9]+)'")


class SpseBlocked(Exception):
    """Raised when SPSE/Cloudflare rejects a request after retries."""


class SpseClient:
    def __init__(self, delay: float | None = None) -> None:
        self.session = requests.Session(impersonate="chrome")
        self.delay = settings.request_delay if delay is None else delay
        self._token: str | None = None
        self._token_source: str | None = None

    def _throttle(self) -> None:
        time.sleep(self.delay + random.uniform(0, self.delay * 0.3))

    def _headers(self, referer: str) -> dict[str, str]:
        return {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{settings.base_url}{referer}",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def bootstrap(self, list_path: str) -> str:
        url = f"{settings.base_url}{list_path}"
        last_exc: Exception | None = None
        for attempt in range(1, settings.max_retries + 1):
            try:
                self._throttle()
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    match = TOKEN_RE.search(resp.text)
                    if match:
                        self._token = match.group(1)
                        self._token_source = list_path
                        logger.debug(f"token refreshed from {list_path}")
                        return self._token
                last_exc = SpseBlocked(f"bootstrap {list_path} -> {resp.status_code}")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
            logger.warning(f"bootstrap attempt {attempt} failed: {last_exc}")
            time.sleep(self.delay * attempt)
        raise SpseBlocked(f"could not bootstrap token from {list_path}: {last_exc}")

    def _ensure_token(self, list_path: str) -> str:
        if not self._token or self._token_source != list_path:
            return self.bootstrap(list_path)
        return self._token

    def datatable(
        self, dt_path: str, tahun: int, start: int, length: int, list_path: str
    ) -> dict[str, Any]:
        url = f"{settings.base_url}{dt_path}?tahun={tahun}"
        for attempt in range(1, settings.max_retries + 1):
            token = self._ensure_token(list_path)
            self._throttle()
            try:
                resp = self.session.post(
                    url,
                    data={
                        "draw": str(start),
                        "start": str(start),
                        "length": str(length),
                        "authenticityToken": token,
                    },
                    headers=self._headers(list_path),
                    timeout=60,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"datatable request error ({attempt}): {exc}")
                time.sleep(self.delay * attempt)
                continue

            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    logger.warning(f"datatable non-json response ({attempt})")
            elif resp.status_code in (401, 403, 419):
                logger.warning(f"datatable blocked {resp.status_code}, refreshing token")
                self._token = None
            else:
                logger.warning(f"datatable status {resp.status_code} ({attempt})")
            time.sleep(self.delay * attempt)
        raise SpseBlocked(f"datatable {dt_path} failed after retries")

    def html(self, path: str, referer: str) -> str | None:
        url = f"{settings.base_url}{path}"
        for attempt in range(1, settings.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.get(
                    url, headers=self._headers(referer), timeout=60
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"html request error {path} ({attempt}): {exc}")
                time.sleep(self.delay * attempt)
                continue

            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                logger.debug(f"html 404 {path}")
                return None
            if resp.status_code in (401, 403, 419):
                logger.warning(f"html blocked {resp.status_code} for {path}")
            time.sleep(self.delay * attempt)
        logger.error(f"html {path} failed after retries")
        return None

    def iter_list(
        self, dt_path: str, tahun: int, list_path: str, page_size: int | None = None
    ) -> Iterator[list[Any]]:
        size = page_size or settings.page_size
        start = 0
        total = 0
        while True:
            payload = self.datatable(dt_path, tahun, start, size, list_path)
            rows = payload.get("data") or []
            if not rows:
                break
            for row in rows:
                total += 1
                yield row
            if len(rows) < size:
                break
            start += size
        logger.info(f"list {dt_path}?tahun={tahun}: {total} rows")
