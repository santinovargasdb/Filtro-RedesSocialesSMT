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
) -> list[dict] | None:
    """
    Busca en Google vía SerpAPI con `site:` correspondiente a la red.
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
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": max_results,
        "hl": "es",
        "gl": "ar",
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
