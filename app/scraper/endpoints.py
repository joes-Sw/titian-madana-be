LELANG_LIST = "/lelang"
NONTENDER_LIST = "/nontender"

DT_LELANG = "/dt/lelang"
DT_PL = "/dt/pl"


def pengumumanlelang(tender_id: str) -> str:
    return f"/lelang/{tender_id}/pengumumanlelang"


def jadwal_tender(tender_id: str) -> str:
    return f"/lelang/{tender_id}/jadwal"


def pemenang(tender_id: str) -> str:
    return f"/evaluasi/{tender_id}/pemenang"


def pemenang_berkontrak(tender_id: str) -> str:
    return f"/evaluasi/{tender_id}/pemenangberkontrak"


def pengumumanpl(tender_id: str) -> str:
    return f"/nontender/{tender_id}/pengumumanpl"


def jadwal_nontender(tender_id: str) -> str:
    return f"/nontender/{tender_id}/jadwal"
