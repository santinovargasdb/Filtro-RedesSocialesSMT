"""
Capa 2 — Extracción / Fetcher (CIEGO).

Única responsabilidad: traer resultados crudos de Google vía SerpAPI, por red.
NO sabe nada de Gemini, scoring, normalización ni del shape final de los posts:
solo devuelve dicts crudos {title, snippet, url, date}.

Si cambia la conexión a la API externa o los parámetros de búsqueda -> SOLO acá.
"""
import os
import datetime
import requests

# ── Configuración de SerpAPI ──────────────────────────────────────────────────
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"

# ── Redes soportadas ──────────────────────────────────────────────────────────
SUPPORTED_NETWORKS = ("twitter", "instagram", "tiktok")

# ── Geolocalización (parámetro 'gl' de SerpAPI) ───────────────────────────────
# El frontend manda el país como código ISO 3166-1 alpha-2 (ar, br, us, es, ...),
# que es exactamente el formato que espera 'gl'. Por eso NO mantenemos una lista
# hardcodeada de países: cualquier código ISO válido funciona como gl.
#
# 'hl' (idioma de la interfaz de Google) sí conviene alinearlo al país para traer
# resultados nativos de esa región. Solo mapeamos los idiomas más comunes; para
# cualquier país no listado caemos a "es" (el operador lee español y, además, la
# Capa 3 traduce al español todo lo que venga en otro idioma — ver B.5).
_DEFAULT_GL = "ar"
_HL_BY_GL = {
    "ar": "es", "es": "es", "mx": "es", "cl": "es", "uy": "es", "co": "es",
    "pe": "es", "ve": "es", "bo": "es", "py": "es", "ec": "es",
    "br": "pt", "pt": "pt",
    "us": "en", "gb": "en", "au": "en", "ca": "en", "ie": "en", "nz": "en",
    "fr": "fr", "it": "it", "de": "de", "jp": "ja", "cn": "zh-cn",
}


def _geo_params(country: str | None) -> tuple[str, str]:
    """Devuelve (gl, hl) a partir del código ISO de país. gl = el código tal cual;
    hl = idioma alineado al país (default 'es')."""
    gl = (country or _DEFAULT_GL).strip().lower() or _DEFAULT_GL
    hl = _HL_BY_GL.get(gl, "es")
    return gl, hl

_SITE_BY_NETWORK = {
    "twitter": "site:x.com OR site:twitter.com",
    "instagram": "site:instagram.com",
    "tiktok": "site:tiktok.com",
}


def _date_to_qdr(fecha_desde: str | None) -> str | None:
    """Mapea YYYY-MM-DD a un valor qdr de SerpAPI (d/w/m) según antigüedad."""
    if not fecha_desde:
        return None
    try:
        d = datetime.date.fromisoformat(fecha_desde)
    except ValueError:
        return None
    delta_days = (datetime.date.today() - d).days
    if delta_days <= 0:
        return "d"
    if delta_days <= 7:
        return "w"
    if delta_days <= 31:
        return "m"
    return None


def _build_accounts_filter(accounts: list[str] | None) -> str:
    """'(from:user1 OR from:user2)' — operador específico de X/Twitter."""
    if not accounts:
        return ""
    clean = [a.lstrip("@").strip() for a in accounts if a and a.strip()]
    if not clean:
        return ""
    return "(" + " OR ".join(f"from:{u}" for u in clean) + ")"


def _clean_serp_results(items: list[dict]) -> list[dict]:
    """
    Limpia los resultados crudos de SerpAPI antes de devolverlos:
    - descarta items sin snippet ni title (no hay texto que analizar)
    - dedupea por URL exacta
    - dedupea por snippet exacto (distinto URL, mismo contenido)
    Reduce tokens del prompt aguas abajo y baja la chance de tocar el rate limit.
    """
    seen_urls: set[str] = set()
    seen_text: set[str] = set()
    out: list[dict] = []
    for it in items:
        url = (it.get("url") or "").strip()
        snippet = (it.get("snippet") or "").strip()
        title = (it.get("title") or "").strip()
        if not snippet and not title:
            continue
        if url and url in seen_urls:
            continue
        text_key = snippet or title
        if text_key in seen_text:
            continue
        if url:
            seen_urls.add(url)
        seen_text.add(text_key)
        out.append(it)
    return out


def search_serpapi(
    termino: str,
    network: str = "twitter",
    max_results: int = 10,
    fecha_desde: str | None = None,
    accounts: list[str] | None = None,
    country: str = "ar",
) -> list[dict] | None:
    """
    Busca en Google vía SerpAPI con `site:` correspondiente a la red.
    `country` es el código ISO 3166-1 alpha-2 que se pasa como 'gl' para forzar
    resultados nativos de esa región (B.4).
    Devuelve lista de dicts {title, snippet, url, date}, [] si no hay resultados,
    o None ante errores de red/upstream (para no cachear vacíos espurios).
    """
    if not SERPAPI_API_KEY:
        print("ERROR: SERPAPI_API_KEY no configurada en las variables de entorno.")
        return None

    site_filter = _SITE_BY_NETWORK.get(network, _SITE_BY_NETWORK["twitter"])
    query_parts = [site_filter, termino]
    # (from:user) es operador propio de X — IG/TikTok no tienen equivalente directo
    # vía Google search, así que para esas redes ignoramos el filtro por cuenta.
    if network == "twitter":
        accounts_filter = _build_accounts_filter(accounts)
        if accounts_filter:
            query_parts.append(accounts_filter)
    query = " ".join(query_parts)
    gl, hl = _geo_params(country)
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": max_results,
        "hl": hl,
        "gl": gl,
    }
    qdr = _date_to_qdr(fecha_desde)
    if qdr:
        params["tbs"] = f"qdr:{qdr}"

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallo en la petición a SerpAPI[{network}]: {e}")
        return None

    organic_results = data.get("organic_results", [])
    if not organic_results:
        print(f"DEBUG: SerpAPI[{network}] sin resultados orgánicos para '{termino}'.")
        return []

    raw_results = []
    for item in organic_results[:max_results]:
        raw_results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("link", ""),
            "date": item.get("date", ""),
        })
    results = _clean_serp_results(raw_results)
    if len(results) != len(raw_results):
        print(f"DEBUG: SerpAPI[{network}] limpieza: {len(raw_results)} -> {len(results)} (vacíos/duplicados descartados)")
    print(f"DEBUG: SerpAPI[{network}] devolvió {len(results)} resultados útiles para '{termino}'.")
    return results
