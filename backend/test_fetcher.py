"""
Tests de la Capa 2 (fetcher): helpers puros de armado de query y limpieza del
raw de SerpAPI. No se pega a la red (search_serpapi no se invoca acá).

Correr desde backend/:  python -m pytest -q
"""
import datetime
import fetcher as ft


# ── _build_accounts_filter ────────────────────────────────────────────────────
def test_build_accounts_filter():
    assert ft._build_accounts_filter(["@smata", "user2"]) == "(from:smata OR from:user2)"
    assert ft._build_accounts_filter([]) == ""
    assert ft._build_accounts_filter(None) == ""
    assert ft._build_accounts_filter(["@user"]) == "(from:user)"


def test_build_accounts_filter_limpia_vacios():
    assert ft._build_accounts_filter(["", "  ", "@valido"]) == "(from:valido)"


# ── _clean_serp_results ───────────────────────────────────────────────────────
def test_clean_serp_descarta_sin_texto_y_dedup():
    items = [
        {"url": "u1", "snippet": "hola", "title": "t1"},
        {"url": "u1", "snippet": "otro", "title": "t2"},   # url duplicada -> fuera
        {"url": "u2", "snippet": "hola", "title": "t3"},   # snippet duplicado -> fuera
        {"url": "u3", "snippet": "", "title": ""},          # sin texto -> fuera
        {"url": "u4", "snippet": "nuevo", "title": "t4"},
    ]
    out = ft._clean_serp_results(items)
    urls = [o["url"] for o in out]
    assert urls == ["u1", "u4"]


# ── _date_to_qdr ──────────────────────────────────────────────────────────────
def test_date_to_qdr_none_y_invalida():
    assert ft._date_to_qdr(None) is None
    assert ft._date_to_qdr("no-es-fecha") is None


def test_date_to_qdr_rangos():
    hoy = datetime.date.today()
    assert ft._date_to_qdr(hoy.isoformat()) == "d"
    assert ft._date_to_qdr((hoy - datetime.timedelta(days=5)).isoformat()) == "w"
    assert ft._date_to_qdr((hoy - datetime.timedelta(days=20)).isoformat()) == "m"
    assert ft._date_to_qdr((hoy - datetime.timedelta(days=200)).isoformat()) is None
