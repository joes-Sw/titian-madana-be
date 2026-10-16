from datetime import datetime

from app.scraper import parser

DETAIL_HTML = """
<table>
  <tr><th class="bgwarning">Kode Tender</th><td colspan="3">10104147000</td></tr>
  <tr><th class="bgwarning">Nama Tender</th><td colspan="3">Facility Management LKPP</td></tr>
  <tr>
    <th class="bgwarning">Rencana Umum Pengadaan</th>
    <td colspan="3">
      <table>
        <tr><th>Kode RUP</th><th>Nama Paket</th><th>Sumber Dana</th></tr>
        <tr><td>61896955</td><td>Facility Management LKPP</td><td>APBN</td></tr>
      </table>
    </td>
  </tr>
  <tr><th class="bgwarning">Tahap Tender Saat Ini</th><td colspan="3">Tender Sudah Selesai</td></tr>
  <tr><th class="bgwarning">Jenis Pengadaan</th><td colspan="3">Jasa Lainnya</td></tr>
  <tr><th class="bgwarning">Metode Pengadaan</th><td colspan="3">Tender - Pascakualifikasi Dua File - Sistem Nilai</td></tr>
  <tr><th class="bgwarning">Tahun Anggaran</th><td colspan="3">APBN 2026</td></tr>
  <tr>
    <th class="bgwarning">Nilai Pagu Paket</th>
    <td width="200">Rp. 14.498.579.000,00</td>
    <th class="bgwarning" width="200">Nilai HPS Paket</th>
    <td>Rp. 14.171.087.838,39</td>
  </tr>
  <tr><th class="bgwarning">Jenis Kontrak</th><td colspan="3">Lumsum</td></tr>
  <tr><th class="bgwarning">Lokasi Pekerjaan</th><td colspan="3">Jakarta Selatan</td></tr>
</table>
"""

JADWAL_HTML = """
<table>
  <tr><th>No</th><th>Tahap</th><th>Mulai</th><th>Sampai</th><th>Perubahan</th></tr>
  <tr><td>1</td><td>Pengumuman Pascakualifikasi</td><td>16 Desember 2025 12:10</td><td>22 Desember 2025 12:00</td><td>Tidak Ada</td></tr>
  <tr><td>2</td><td>Masa Sanggah</td><td>24 Desember 2025 23:00</td><td>30 Desember 2025 10:00</td><td>Tidak Ada</td></tr>
</table>
"""

PEMENANG_HTML = """
<table>
  <tr><th>Nama Pemenang</th><th>Alamat</th><th>NPWP</th><th>Harga Penawaran</th><th>Harga Terkoreksi</th><th>Harga Negosiasi</th></tr>
  <tr><td>PT AIRKON PRATAMA</td><td>Jakarta</td><td>00*8**9</td><td>Rp. 13.714.586.254,00</td><td>Rp. 13.714.586.254,00</td><td>-</td></tr>
</table>
"""

SPPJ_HTML = """
<table>
  <tr><th>Nama Pemenang</th><th>Alamat</th><th>NPWP</th><th>Harga Kontrak</th><th>Nilai PDN</th><th>Nilai UMK</th><th>Status Kontrak</th></tr>
  <tr><td>PT. DETA DECON</td><td>Jakarta</td><td>0*.6**</td><td>Rp. 22.120.344.299,88</td><td>Rp. 0,00</td><td>Rp. 22.120.344.299,88</td><td>Selesai</td></tr>
</table>
"""


def test_parse_amount():
    assert parser.parse_amount("Rp. 14.498.579.000,00") == 14498579000.0
    assert parser.parse_amount("Rp. 0,00") == 0.0
    assert parser.parse_amount("Nilai Kontrak belum dibuat") is None
    assert parser.parse_amount("-") is None
    assert parser.parse_amount(None) is None


def test_parse_datetime():
    assert parser.parse_datetime("16 Desember 2025 12:10") == datetime(
        2025, 12, 16, 12, 10
    )
    assert parser.parse_datetime("22 Desember 2025 12:00") == datetime(
        2025, 12, 22, 12, 0
    )
    assert parser.parse_datetime("bukan tanggal") is None


def test_parse_detail_double_pair_and_rup():
    detail = parser.parse_detail(DETAIL_HTML)
    assert detail["judul"] == "Facility Management LKPP"
    assert detail["nilai_pagu"] == 14498579000.0
    assert detail["nilai_hps"] == 14171087838.39
    assert detail["kode_rup"] == "61896955"
    assert detail["sumber_dana"] == "APBN"
    assert detail["tahun_anggaran"] == "2026"
    assert detail["metode_pemilihan"] == "Tender"
    assert detail["metode_evaluasi"] == "Sistem Nilai"
    assert detail["kualifikasi"] == "Pascakualifikasi Dua File"


def test_parse_jadwal_flatten():
    tahapan, flat = parser.parse_jadwal(JADWAL_HTML)
    assert len(tahapan) == 2
    assert flat["tgl_mulai_pengumuman"] == datetime(2025, 12, 16, 12, 10)
    assert flat["tgl_selesai_pengumuman"] == datetime(2025, 12, 22, 12, 0)
    assert flat["tgl_mulai_sanggah"] == datetime(2025, 12, 24, 23, 0)
    assert flat["tgl_selesai_sanggah"] == datetime(2025, 12, 30, 10, 0)


def test_parse_pemenang():
    rows = parser.parse_pemenang(PEMENANG_HTML)
    assert len(rows) == 1
    assert rows[0]["nama_penyedia"] == "PT AIRKON PRATAMA"
    assert rows[0]["harga_penawaran"] == 13714586254.0
    assert rows[0]["harga_negosiasi"] is None


def test_parse_sppj():
    rows = parser.parse_sppj(SPPJ_HTML)
    assert len(rows) == 1
    assert rows[0]["nama_penyedia"] == "PT. DETA DECON"
    assert rows[0]["nilai_kontrak"] == 22120344299.88
    assert rows[0]["status_kontrak"] == "Selesai"


def test_parse_list_row_tender():
    row = [
        "10104147000",
        "Facility Management LKPP",
        "LKPP",
        "Tender Sudah Selesai",
        "14,2 M",
        "Pascakualifikasi Dua File",
        "Tender",
        "Sistem Nilai",
        "Jasa Lainnya - TA 2026",
        "5",
        "Rp. 14.171.087.838,39",
        "0",
        "0",
        None,
        None,
    ]
    parsed = parser.parse_list_row_tender(row)
    assert parsed["id"] == "10104147000"
    assert parsed["jenis_paket"] == "tender"
    assert parsed["jenis_pengadaan"] == "Jasa Lainnya"
    assert parsed["tahun_anggaran"] == "2026"
    assert parsed["nilai_hps"] == 14171087838.39


def test_parse_list_row_nontender():
    row = [
        "10744625000",
        "Jasa Lainnya Pendukung",
        "LKPP",
        "Paket Sudah Selesai",
        "81,5 Jt",
        "Pengadaan Langsung",
        "Jasa Lainnya - TA 2026",
        "5",
        "Rp. 81.528.000,00",
        "1",
        "0",
        "0",
    ]
    parsed = parser.parse_list_row_nontender(row)
    assert parsed["jenis_paket"] == "nontender"
    assert parsed["jenis_pengadaan"] == "Jasa Lainnya"
    assert parsed["nilai_hps"] == 81528000.0
