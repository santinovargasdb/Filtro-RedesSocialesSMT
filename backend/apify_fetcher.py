import os
import re
import json
import time
import datetime
import requests

# ── Configuración de SerpAPI ──────────────────────────────────────────────────
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"

# ── Cache en memoria de fetch_posts ───────────────────────────────────────────
_CACHE_TTL_SECONDS = 600  # 10 minutos
_CACHE: dict[tuple, tuple[float, list[dict]]] = {}

_TWITTER_URL_RE = re.compile(r"(?:x|twitter)\.com/([^/?#]+)/status/(\d+)", re.IGNORECASE)


def _parse_twitter_url(url: str) -> tuple[str, str, str]:
    """Devuelve (author, author_url, post_id) extraídos de un URL de X/Twitter."""
    m = _TWITTER_URL_RE.search(url or "")
    if not m:
        return "", "", url or ""
    user, post_id = m.group(1), m.group(2)
    return user, f"https://x.com/{user}", post_id


def _level_from_score(score: int) -> str:
    if score >= 70:
        return "alta"
    if score >= 40:
        return "media"
    return "baja"


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


def _find_matched_terms(text: str, keywords: list[str]) -> list[str]:
    if not text or not keywords:
        return []
    text_lower = text.lower()
    seen = []
    for k in keywords:
        kl = (k or "").strip().lower()
        if kl and kl in text_lower and kl not in [s.lower() for s in seen]:
            seen.append(k)
    return seen


def _build_accounts_filter(accounts: list[str] | None) -> str:
    """Devuelve '(from:user1 OR from:user2)' o '' si no hay cuentas válidas."""
    if not accounts:
        return ""
    clean = [a.lstrip("@").strip() for a in accounts if a and a.strip()]
    if not clean:
        return ""
    return "(" + " OR ".join(f"from:{u}" for u in clean) + ")"


def _search_with_serpapi(
    termino: str,
    max_results: int = 10,
    fecha_desde: str | None = None,
    accounts: list[str] | None = None,
) -> list[dict] | None:
    """
    Realiza una búsqueda en Google vía SerpAPI filtrando resultados de X/Twitter.
    Devuelve lista de dicts con: title, snippet, url, date.
    Retorna None ante errores de red/upstream (para distinguir de 'cero resultados legítimos').
    """
    if not SERPAPI_API_KEY:
        print("ERROR: SERPAPI_API_KEY no configurada en las variables de entorno.")
        return None

    accounts_filter = _build_accounts_filter(accounts)
    query_parts = ["site:x.com OR site:twitter.com", termino]
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
        print(f"ERROR: Fallo en la petición a SerpAPI: {e}")
        return None

    organic_results = data.get("organic_results", [])
    if not organic_results:
        print(f"DEBUG: SerpAPI no devolvió resultados orgánicos para '{termino}'.")
        return []

    results = []
    for item in organic_results[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("link", ""),
            "date": item.get("date", ""),
        })

    print(f"DEBUG: SerpAPI devolvió {len(results)} resultados para '{termino}'.")
    return results


def _process_with_gemini(
    resultados: list[dict],
    termino: str,
    strict_mode: bool,
    keywords: list[str],
) -> list[dict]:
    """
    Pide a Gemini scores de relevancia y mapea cada resultado al shape PostOut:
    {id, network, author, author_url, text, date, post_url,
     relevance_score, relevance_level, matched_terms, video_url}.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no configurada.")
        return []

    resultados_text = json.dumps(resultados, ensure_ascii=False, indent=2)
    strict_note = "Solo incluí posts con score >= 50." if strict_mode else "Incluí todos los posts."

    prompt = f"""Sos un asistente de análisis de redes sociales para el sindicato SMATA (sector automotriz argentino).
Te paso resultados reales de Google sobre publicaciones en X (Twitter) relacionadas con el término: "{termino}".

Cada resultado tiene: "title" (título del resultado en Google), "snippet" (extracto del tweet/post), "url" (link directo), "date" (fecha si está disponible).

Tu tarea:
1. Analizá cada resultado y determiná si es relevante para SMATA y el sector automotriz/sindical argentino.
2. Asigná un score del 0 al 100 según su relevancia.
3. {strict_note}

Devolvé ÚNICAMENTE un JSON válido, sin texto adicional ni bloques de código. Formato exacto:
[
  {{
    "post_url": "url_del_resultado",
    "score": 75
  }}
]

Resultados de SerpAPI:
{resultados_text}"""

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        res_data = response.json()
        raw = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        scored = json.loads(raw)
        if not isinstance(scored, list):
            return []
    except Exception as e:
        print(f"ERROR procesando con Gemini directo: {e}")
        return []

    # Index original SerpAPI items por URL para enriquecer cada post
    by_url = {r.get("url", ""): r for r in resultados}

    posts: list[dict] = []
    for item in scored:
        post_url = item.get("post_url", "") or ""
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0

        src = by_url.get(post_url, {})
        snippet = src.get("snippet", "") or src.get("title", "")
        date = src.get("date", "") or ""
        author, author_url, post_id = _parse_twitter_url(post_url)

        posts.append({
            "id": post_id or post_url,
            "network": "twitter",
            "author": author,
            "author_url": author_url,
            "text": snippet,
            "date": date,
            "post_url": post_url,
            "relevance_score": score,
            "relevance_level": _level_from_score(score),
            "matched_terms": _find_matched_terms(snippet, keywords),
            "video_url": None,
        })

    return posts


def fetch_posts(
    termino: str,
    fecha_desde: str = None,
    strict_mode: bool = False,
    keywords: list[str] | None = None,
    accounts: list[str] | None = None,
) -> list[dict]:
    """
    Función principal. Devuelve lista de dicts compatibles con el modelo PostOut.
    """
    print(f"DEBUG: fetch_posts llamado con termino='{termino}', strict_mode={strict_mode}")

    cache_key = (
        termino,
        fecha_desde,
        strict_mode,
        tuple(sorted(keywords or [])),
        tuple(sorted(accounts or [])),
    )
    cached = _CACHE.get(cache_key)
    if cached is not None:
        ts, data = cached
        if time.time() - ts < _CACHE_TTL_SECONDS:
            print(f"DEBUG: cache HIT para {cache_key}")
            return data
        del _CACHE[cache_key]

    resultados_crudos = _search_with_serpapi(
        termino, max_results=10, fecha_desde=fecha_desde, accounts=accounts
    )
    if resultados_crudos is None:
        print("DEBUG: SerpAPI falló (error de red/upstream). No se cachea, reintentar.")
        return []
    print(f"DEBUG: {len(resultados_crudos)} resultados obtenidos de SerpAPI")

    posts_procesados = _process_with_gemini(
        resultados_crudos, termino, strict_mode, keywords or []
    )
    print(f"DEBUG: {len(posts_procesados)} posts devueltos tras análisis de Gemini")

    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for p in posts_procesados:
        url = p.get("post_url") or ""
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(p)
    if len(deduped) != len(posts_procesados):
        print(f"DEBUG: dedupe quitó {len(posts_procesados) - len(deduped)} duplicados por post_url")
    posts_procesados = deduped

    # No cachear vacíos espurios: si SerpAPI trajo resultados pero quedamos en 0 posts,
    # asumimos que Gemini falló (503, rate-limit, etc.) y dejamos pasar el próximo intento.
    if not posts_procesados and resultados_crudos:
        print("DEBUG: no se cachea (resultado vacío con SerpAPI no vacío — probable fallo upstream)")
    else:
        _CACHE[cache_key] = (time.time(), posts_procesados)
    return posts_procesados
