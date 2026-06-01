"""
Tests de las funciones puras y de la lógica de scoring/batch de apify_fetcher.

Cubren la lógica que más cambió (y regresionó) en el tiempo: formateo de URLs de
TikTok/Instagram, piso de score por modo, bifurcación del prompt y el batch de una
sola llamada a Gemini. Las llamadas a Gemini se mockean: no se pega a la red.

Correr desde backend/:  python -m pytest -q
"""
import apify_fetcher as af


# ── _is_specific_post_url ─────────────────────────────────────────────────────
def test_is_specific_post_url_instagram():
    assert af._is_specific_post_url("instagram", "https://www.instagram.com/p/Cabc/")
    assert af._is_specific_post_url("instagram", "https://www.instagram.com/u/reel/Cxyz/")
    assert af._is_specific_post_url("instagram", "https://www.instagram.com/u/tv/C1/")
    assert not af._is_specific_post_url("instagram", "https://www.instagram.com/usuario/")


def test_is_specific_post_url_tiktok_y_twitter():
    assert af._is_specific_post_url("tiktok", "https://www.tiktok.com/@u/video/123")
    assert not af._is_specific_post_url("tiktok", "https://www.tiktok.com/@u")
    assert not af._is_specific_post_url("tiktok", "https://www.tiktok.com/search?q=smata")
    assert af._is_specific_post_url("twitter", "https://x.com/u/status/9")
    assert not af._is_specific_post_url("twitter", "https://x.com/u")


def test_is_specific_post_url_vacio():
    assert not af._is_specific_post_url("instagram", "")
    assert not af._is_specific_post_url("tiktok", None)


# ── _tiktok_search_fallback_url ───────────────────────────────────────────────
def test_tiktok_fallback_autor_valido_va_a_perfil():
    assert af._tiktok_search_fallback_url("elrulomanok", "smata") == "https://www.tiktok.com/@elrulomanok"
    # limpia el arroba inicial
    assert af._tiktok_search_fallback_url("@user", "kw") == "https://www.tiktok.com/@user"


def test_tiktok_fallback_sin_autor_usa_keyword():
    assert af._tiktok_search_fallback_url("", "salud") == "https://www.tiktok.com/search?q=salud"
    assert af._tiktok_search_fallback_url("?", "paro automotriz") == "https://www.tiktok.com/search?q=paro%20automotriz"


def test_tiktok_fallback_sin_nada_es_none():
    assert af._tiktok_search_fallback_url("", "") is None
    assert af._tiktok_search_fallback_url("?", "") is None


def test_tiktok_fallback_nunca_devuelve_home_pelada():
    for a, k in [("u", "kw"), ("", "kw"), ("?", "x"), ("u", "")]:
        url = af._tiktok_search_fallback_url(a, k)
        if url is not None:
            assert url.rstrip("/").lower() not in ("https://www.tiktok.com", "https://tiktok.com")


# ── _score_floor ──────────────────────────────────────────────────────────────
def test_score_floor_modo_amplio():
    assert af._score_floor("twitter", smata_mode=False) == af.SCORE_FLOOR_DEFAULT
    assert af._score_floor("instagram", smata_mode=False) == af.SCORE_FLOOR_DEFAULT
    assert af._score_floor("tiktok", smata_mode=False) == 50  # tiktok siempre 50


def test_score_floor_modo_smata_nunca_baja_de_50():
    assert af._score_floor("twitter", smata_mode=True) == 50
    assert af._score_floor("instagram", smata_mode=True) == 50
    assert af._score_floor("tiktok", smata_mode=True) == 50


# ── _level_from_score ─────────────────────────────────────────────────────────
def test_level_from_score():
    assert af._level_from_score(100) == "alta"
    assert af._level_from_score(70) == "alta"
    assert af._level_from_score(69) == "media"
    assert af._level_from_score(40) == "media"
    assert af._level_from_score(39) == "baja"
    assert af._level_from_score(0) == "baja"


# ── _find_matched_terms ───────────────────────────────────────────────────────
def test_find_matched_terms():
    assert af._find_matched_terms("Paro de SMATA en Córdoba", ["smata", "paro"]) == ["smata", "paro"]
    assert af._find_matched_terms("texto sin match", ["smata"]) == []
    assert af._find_matched_terms("", ["smata"]) == []
    assert af._find_matched_terms("hola", []) == []


# ── _parse_post_url ───────────────────────────────────────────────────────────
def test_parse_post_url_por_red():
    net, author, _, pid = af._parse_post_url("https://x.com/eluser/status/123")
    assert (net, author, pid) == ("twitter", "eluser", "123")

    net, author, _, pid = af._parse_post_url("https://www.tiktok.com/@creador/video/999")
    assert (net, author, pid) == ("tiktok", "creador", "999")

    net, _, _, _ = af._parse_post_url("https://www.instagram.com/u/p/AAA/")
    assert net == "instagram"


def test_parse_post_url_usa_hint_cuando_no_resuelve():
    net, _, _, _ = af._parse_post_url("https://desconocido.com/algo", hint_network="tiktok")
    assert net == "tiktok"


# ── _process_with_gemini: batch de 1 sola llamada + mapeo ─────────────────────
def _fake_scored(items):
    """Devuelve un _call_gemini_model fake que responde una lista fija."""
    def _fake(model, api_key, prompt):
        return (items, None)
    return _fake


def test_process_una_sola_llamada_para_todas_las_redes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    llamadas = {"n": 0}

    def fake(model, api_key, prompt):
        llamadas["n"] += 1
        # Gemini responde por ID (espejo de los Post_N enviados).
        return ([
            {"id": "Post_0", "score": 90, "razon": "x"},
            {"id": "Post_1", "score": 80, "razon": "x"},
            {"id": "Post_2", "score": 75, "razon": "x"},
        ], None)

    monkeypatch.setattr(af, "_call_gemini_model", fake)
    serp = [
        {"title": "t", "snippet": "smata", "url": "https://x.com/u/status/1", "date": "", "network": "twitter"},
        {"title": "t", "snippet": "smata", "url": "https://www.instagram.com/u/p/AAA/", "date": "", "network": "instagram"},
        {"title": "t", "snippet": "smata", "url": "https://www.tiktok.com/@creador/video/123", "date": "", "network": "tiktok"},
    ]
    posts = af._process_with_gemini(serp, "smata", smata_mode=False, keywords=["smata"])

    assert llamadas["n"] == 1, "debe ser UNA sola llamada a Gemini para las 3 redes"
    assert sorted(p["network"] for p in posts) == ["instagram", "tiktok", "twitter"]
    # El deep-link válido de TikTok se respeta (no se pisa con el perfil).
    tt = next(p for p in posts if p["network"] == "tiktok")
    assert tt["post_url"] == "https://www.tiktok.com/@creador/video/123"


def test_process_descarta_bajo_el_piso(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(af, "_call_gemini_model",
                        _fake_scored([{"id": "Post_0", "score": 40, "razon": "x"}]))
    serp = [{"title": "", "snippet": "x", "url": "https://www.tiktok.com/@u/video/9", "date": "", "network": "tiktok"}]
    # En amplio el piso de TikTok es 50 -> 40 se descarta.
    assert af._process_with_gemini(serp, "smata", smata_mode=False, keywords=[]) == []


def test_process_tiktok_sin_deeplink_cae_al_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(af, "_call_gemini_model",
                        _fake_scored([{"id": "Post_0", "score": 90, "razon": "x"}]))
    serp = [{"title": "", "snippet": "x", "url": "https://www.tiktok.com/@creador", "date": "", "network": "tiktok"}]
    posts = af._process_with_gemini(serp, "smata", smata_mode=False, keywords=[])
    # URL de perfil (sin /video/): no es deep-link, se reemplaza por búsqueda segura.
    assert posts[0]["post_url"].startswith("https://www.tiktok.com/search?q=")


def test_process_mapea_por_id_y_respeta_url_original(monkeypatch):
    """Gemini responde fuera de orden y con un id inexistente; el backend mapea
    por id, ignora el id basura y NUNCA toma la URL de la respuesta de Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(af, "_call_gemini_model", _fake_scored([
        {"id": "Post_1", "score": 88, "razon": "x"},              # fuera de orden
        {"id": "Post_999", "score": 100, "razon": "inventado"},   # id que no enviamos
        {"id": "Post_0", "score": 70, "razon": "x"},
    ]))
    serp = [
        {"title": "", "snippet": "uno", "url": "https://x.com/a/status/1", "date": "", "network": "twitter"},
        {"title": "", "snippet": "dos", "url": "https://x.com/b/status/2", "date": "", "network": "twitter"},
    ]
    posts = af._process_with_gemini(serp, "smata", smata_mode=False, keywords=[])
    by_url = {p["post_url"]: p for p in posts}
    # Solo 2 posts (el id inventado se ignora).
    assert len(posts) == 2
    # El score de Post_1 va al segundo serp (url .../2), no se mezcla.
    assert by_url["https://x.com/b/status/2"]["relevance_score"] == 88
    assert by_url["https://x.com/a/status/1"]["relevance_score"] == 70


def test_process_sin_api_key_devuelve_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    serp = [{"title": "", "snippet": "x", "url": "https://x.com/u/status/1", "date": "", "network": "twitter"}]
    assert af._process_with_gemini(serp, "smata", smata_mode=False, keywords=[]) is None


# ── Bifurcación del prompt según smata_mode ───────────────────────────────────
def test_prompt_bifurca_estricto_vs_amplio(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    capturado = {}

    def fake(model, api_key, prompt):
        capturado["p"] = prompt
        return ([], None)

    monkeypatch.setattr(af, "_call_gemini_model", fake)
    serp = [{"title": "", "snippet": "x", "url": "https://x.com/u/status/1", "date": "", "network": "twitter"}]

    af._process_with_gemini(serp, "salud", smata_mode=True, keywords=[])
    assert "DEBE estar ligado a SMATA" in capturado["p"]

    af._process_with_gemini(serp, "salud", smata_mode=False, keywords=[])
    assert "NO exijas" in capturado["p"]


def test_prompt_blindado_ids_y_aislamiento(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    capturado = {}

    def fake(model, api_key, prompt):
        capturado["p"] = prompt
        return ([], None)

    monkeypatch.setattr(af, "_call_gemini_model", fake)
    serp = [
        {"title": "", "snippet": "a", "url": "https://x.com/u/status/1", "date": "", "network": "twitter"},
        {"title": "", "snippet": "b", "url": "https://x.com/u/status/2", "date": "", "network": "twitter"},
    ]
    af._process_with_gemini(serp, "smata", smata_mode=True, keywords=[])
    p = capturado["p"]
    # IDs inyectados y formato espejo por id.
    assert "Post_0" in p and "Post_1" in p
    assert '"id"' in p
    # Regla de aislamiento explícita.
    assert "AISLAMIENTO" in p
    assert "PROHIBIDO" in p
