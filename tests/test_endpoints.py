from app.scraper import endpoints as ep


def test_path_paket_tender():
    assert ep.LELANG_LIST == "/lelang"
    assert ep.DT_LELANG == "/dt/lelang"
    assert ep.pengumumanlelang("123") == "/lelang/123/pengumumanlelang"
    assert ep.jadwal_tender("123") == "/lelang/123/jadwal"
    assert ep.pemenang("123") == "/evaluasi/123/pemenang"
    assert ep.pemenang_berkontrak("123") == "/evaluasi/123/pemenangberkontrak"


def test_path_paket_nontender():
    assert ep.NONTENDER_LIST == "/nontender"
    assert ep.DT_PL == "/dt/pl"
    assert ep.pengumumanpl("123") == "/nontender/123/pengumumanpl"
    assert ep.jadwal_nontender("123") == "/nontender/123/jadwal"
    # nontender memakai prefix evaluasinontender, bukan evaluasi
    assert ep.pemenang_nontender("123") == "/evaluasinontender/123/pemenang"
    assert (
        ep.pemenang_berkontrak_nontender("123")
        == "/evaluasinontender/123/pemenangberkontrak"
    )
