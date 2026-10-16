from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

ID_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}

_DT_RE = re.compile(
    r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?"
)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    value = re.sub(r"\s+", " ", text).strip()
    return value or None


def parse_amount(text: str | None) -> float | None:
    if not text:
        return None
    low = text.lower()
    if "belum" in low or "tidak" in low:
        return None
    value = text.replace("Rp", "").replace("rp", "").replace(" ", "").strip()
    value = value.replace(".", "").replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_datetime(text: str | None) -> datetime | None:
    if not text:
        return None
    match = _DT_RE.search(re.sub(r"\s+", " ", text).strip())
    if not match:
        return None
    day, month_name, year, hour, minute = match.groups()
    month = ID_MONTHS.get(month_name.lower())
    if not month:
        return None
    return datetime(
        int(year), month, int(day), int(hour or 0), int(minute or 0)
    )


def extract_year(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\b(20\d{2})\b", text)
    return match.group(1) if match else None


def first_number(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\d+", text)
    return match.group(0) if match else None


def parse_kv(soup: BeautifulSoup) -> dict[str, str]:
    data: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        pending: str | None = None
        for cell in cells:
            if cell.name == "th":
                pending = clean(cell.get_text(" ", strip=True))
            elif cell.name == "td" and pending:
                value = clean(cell.get_text(" ", strip=True))
                data.setdefault(pending, value or "")
                pending = None
    return data


def parse_rup(soup: BeautifulSoup) -> dict[str, str | None]:
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [
            clean(c.get_text(" ", strip=True)) or ""
            for c in rows[0].find_all(["th", "td"])
        ]
        joined = " ".join(headers).lower()
        if "kode rup" in joined and "sumber dana" in joined:
            values = [
                clean(c.get_text(" ", strip=True)) or ""
                for c in rows[1].find_all(["td", "th"])
            ]
            return {
                "kode_rup": values[0] if len(values) > 0 else None,
                "nama_paket_rup": values[1] if len(values) > 1 else None,
                "sumber_dana": values[2] if len(values) > 2 else None,
            }
    return {}


def find_data_table(
    soup: BeautifulSoup, required: list[str]
) -> tuple[list[str], list[list[str]]]:
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [
            clean(c.get_text(" ", strip=True)) or ""
            for c in rows[0].find_all(["th", "td"])
        ]
        joined = " | ".join(headers).lower()
        if all(req.lower() in joined for req in required):
            body: list[list[str]] = []
            for tr in rows[1:]:
                cells = [
                    clean(c.get_text(" ", strip=True)) or ""
                    for c in tr.find_all(["td", "th"])
                ]
                if len(cells) < 2:
                    continue
                body.append(cells)
            return headers, body
    return [], []


def _split_jenis_ta(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    parts = re.split(r"\s*-\s*TA\s*", text, maxsplit=1)
    jenis = clean(parts[0])
    tahun = None
    if len(parts) > 1:
        years = re.findall(r"\d{4}", parts[1])
        tahun = ",".join(years) if years else None
    return jenis, tahun


def parse_list_row_tender(row: list[Any]) -> dict[str, Any]:
    def at(i: int) -> Any:
        return row[i] if i < len(row) else None

    jenis, tahun = _split_jenis_ta(at(8))
    return {
        "id": str(at(0)),
        "jenis_paket": "tender",
        "judul": clean(at(1)),
        "instansi": clean(at(2)),
        "status_tahap": clean(at(3)),
        "nilai_hps": parse_amount(at(10)),
        "kualifikasi": clean(at(5)),
        "metode_pemilihan": clean(at(6)),
        "metode_evaluasi": clean(at(7)),
        "jenis_pengadaan": jenis,
        "tahun_anggaran": tahun,
        "versi_spse": clean(at(9)),
    }


def parse_list_row_nontender(row: list[Any]) -> dict[str, Any]:
    def at(i: int) -> Any:
        return row[i] if i < len(row) else None

    jenis, tahun = _split_jenis_ta(at(6))
    return {
        "id": str(at(0)),
        "jenis_paket": "nontender",
        "judul": clean((at(1) or "").lstrip(" ,")),
        "instansi": clean(at(2)),
        "status_tahap": clean(at(3)),
        "nilai_hps": parse_amount(at(8)),
        "kualifikasi": None,
        "metode_pemilihan": clean(at(5)),
        "metode_evaluasi": None,
        "jenis_pengadaan": jenis,
        "tahun_anggaran": tahun,
        "versi_spse": clean(at(7)),
    }


def parse_detail(html: str) -> dict[str, Any]:
    soup = make_soup(html)
    kv = parse_kv(soup)
    rup = parse_rup(soup)

    metode = kv.get("Metode Pengadaan")
    metode_pemilihan = None
    metode_evaluasi = None
    kualifikasi = None
    if metode:
        parts = [clean(p) for p in metode.split(" - ") if clean(p)]
        if parts:
            metode_pemilihan = parts[0]
            if len(parts) >= 3:
                kualifikasi = " - ".join(parts[1:-1])
                metode_evaluasi = parts[-1]
            elif len(parts) == 2:
                metode_evaluasi = parts[1]

    return {
        "judul": clean((kv.get("Nama Tender") or kv.get("Nama Paket") or "").lstrip(" ,")) or None,
        "kode_rup": rup.get("kode_rup"),
        "sumber_dana": rup.get("sumber_dana"),
        "satuan_kerja": kv.get("Satuan Kerja"),
        "jenis_pengadaan": kv.get("Jenis Pengadaan"),
        "metode_pemilihan": metode_pemilihan,
        "metode_evaluasi": metode_evaluasi,
        "kualifikasi": kualifikasi,
        "tahun_anggaran": extract_year(kv.get("Tahun Anggaran")),
        "nilai_pagu": parse_amount(kv.get("Nilai Pagu Paket")),
        "nilai_hps": parse_amount(kv.get("Nilai HPS Paket")),
        "jenis_kontrak": kv.get("Jenis Kontrak"),
        "lokasi": kv.get("Lokasi Pekerjaan"),
        "status_tahap": kv.get("Tahap Tender Saat Ini")
        or kv.get("Tahap Paket Saat Ini"),
    }


def parse_jadwal(html: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = make_soup(html)
    headers, rows = find_data_table(soup, ["tahap", "mulai", "sampai"])
    tahapan: list[dict[str, Any]] = []
    for cells in rows:
        if len(cells) < 4:
            continue
        tahapan.append(
            {
                "no": cells[0],
                "nama_tahap": cells[1],
                "mulai": cells[2],
                "sampai": cells[3],
                "perubahan": cells[4] if len(cells) > 4 else None,
            }
        )

    flat: dict[str, Any] = {
        "tgl_mulai_pengumuman": None,
        "tgl_selesai_pengumuman": None,
        "tgl_mulai_sanggah": None,
        "tgl_selesai_sanggah": None,
    }
    pengumuman_set = False
    for item in tahapan:
        name = (item["nama_tahap"] or "").lower()
        if not pengumuman_set and "pengumuman" in name:
            flat["tgl_mulai_pengumuman"] = parse_datetime(item["mulai"])
            flat["tgl_selesai_pengumuman"] = parse_datetime(item["sampai"])
            pengumuman_set = True
        if "sanggah" in name and flat["tgl_mulai_sanggah"] is None:
            flat["tgl_mulai_sanggah"] = parse_datetime(item["mulai"])
            flat["tgl_selesai_sanggah"] = parse_datetime(item["sampai"])

    return tahapan, flat


def _rows_to_dicts(
    headers: list[str], rows: list[list[str]]
) -> list[dict[str, str]]:
    normalized = [h.lower() for h in headers]
    result = []
    for cells in rows:
        item = {}
        for idx, header in enumerate(normalized):
            if idx < len(cells):
                item[header] = cells[idx]
        result.append(item)
    return result


def parse_pemenang(html: str) -> list[dict[str, Any]]:
    soup = make_soup(html)
    headers, rows = find_data_table(
        soup, ["nama pemenang", "npwp", "harga penawaran"]
    )
    out = []
    for item in _rows_to_dicts(headers, rows):
        out.append(
            {
                "nama_penyedia": clean(item.get("nama pemenang")),
                "alamat": clean(item.get("alamat")),
                "npwp": clean(item.get("npwp")),
                "harga_penawaran": parse_amount(item.get("harga penawaran")),
                "harga_terkoreksi": parse_amount(item.get("harga terkoreksi")),
                "harga_negosiasi": parse_amount(item.get("harga negosiasi")),
            }
        )
    return out


def parse_sppj(html: str) -> list[dict[str, Any]]:
    soup = make_soup(html)
    headers, rows = find_data_table(soup, ["nama pemenang", "harga kontrak"])
    out = []
    for item in _rows_to_dicts(headers, rows):
        out.append(
            {
                "nama_penyedia": clean(item.get("nama pemenang")),
                "alamat": clean(item.get("alamat")),
                "npwp": clean(item.get("npwp")),
                "nilai_kontrak": parse_amount(item.get("harga kontrak")),
                "nilai_pdn": parse_amount(item.get("nilai pdn")),
                "nilai_umk": parse_amount(item.get("nilai umk")),
                "status_kontrak": clean(item.get("status kontrak")),
            }
        )
    return out


def dumps_tahapan(tahapan: list[dict[str, Any]]) -> str:
    return json.dumps(tahapan, ensure_ascii=False)
