import os
import re
import json
import time
import datetime
import requests
from urllib.parse import quote


class UpstreamUnavailableError(Exception):
    """SerpAPI o Gemini fallaron (rate limit / cuota / red) y no quedó ningún
    resultado utilizable. Permite al endpoint devolver un 503 con mensaje claro
    en vez de un listado vacío que se confunde con 'no hay resultados'."""

# ── Configuración de SerpAPI ──────────────────────────────────────────────────
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"

# ── Cache en memoria de fetch_posts ───────────────────────────────────────────
_CACHE_TTL_SECONDS = 600  # 10 minutos
_CACHE: dict[tuple, tuple[float, list[dict]]] = {}

# ── Redes soportadas ──────────────────────────────────────────────────────────
SUPPORTED_NETWORKS = ("twitter", "instagram", "tiktok")

_SITE_BY_NETWORK = {
    "twitter": "site:x.com OR site:twitter.com",
    "instagram": "site:instagram.com",
    "tiktok": "site:tiktok.com",
}

_NETWORK_PROMPT_LABEL = {
    "twitter": "X (Twitter)",
    "instagram": "Instagram",
    "tiktok": "TikTok",
}

# ── Gemini: modelos en cascada y límite por red ───────────────────────────────
# Si el primer modelo devuelve 429 (rate limit), 503 (saturación) o 404
# (modelo no disponible en esta key/región), se reintenta con el siguiente.
# Cada modelo Flash tiene cuotas independientes, así que el fallback ayuda
# cuando un modelo se queda sin créditos diarios.
GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",  # antes 'gemini-flash-latest' -> daba 404 en la API
)
GEMINI_RETRY_STATUSES = (429, 503, 404)
# Tope de resultados por red que se mandan a Gemini para reducir tokens
# y bajar la chance de tocar el rate limit con multi-red activo.
GEMINI_MAX_PER_NETWORK = 8

# ── Piso de score por red ─────────────────────────────────────────────────────
# Se aplica como filtro duro en Python después del scoring de Gemini.
# TikTok tiene umbral más alto porque sus snippets en Google son pobres
# (descripciones cortas / multi-idioma / cuentas extranjeras) y generan
# falsos positivos con scores moderados.
SCORE_FLOOR_DEFAULT = 30
SCORE_FLOOR_BY_NETWORK = {
    "tiktok": 50,
}


def _score_floor(network: str, smata_mode: bool) -> int:
    base = SCORE_FLOOR_BY_NETWORK.get(network, SCORE_FLOOR_DEFAULT)
    # En Modo SMATA (estricto) el piso nunca baja de 50. En modo amplio se usan
    # los pisos por red (30 default, TikTok 50 por la baja calidad de snippets).
    if smata_mode:
        return max(base, 50)
    return base

# ── Regex de URLs por red ─────────────────────────────────────────────────────
_TWITTER_URL_RE = re.compile(r"(?:x|twitter)\.com/([^/?#]+)/status/(\d+)", re.IGNORECASE)
_INSTAGRAM_USER_POST_RE = re.compile(r"instagram\.com/([^/?#]+)/(p|reel|tv)/([^/?#]+)", re.IGNORECASE)
_INSTAGRAM_POST_RE = re.compile(r"instagram\.com/(?:p|reel|tv)/([^/?#]+)", re.IGNORECASE)
_TIKTOK_URL_RE = re.compile(r"tiktok\.com/@([^/?#]+)/video/(\d+)", re.IGNORECASE)

# Patrones que identifican un deep-link a un POST PUNTUAL (no a un perfil ni a la
# home de la plataforma). Si la URL original ya matchea, se respeta tal cual.
_SPECIFIC_POST_PATTERNS = {
    "twitter": re.compile(r"/status/\d+", re.IGNORECASE),
    "instagram": re.compile(r"/(?:p|reel|tv)/[^/?#]+", re.IGNORECASE),
    "tiktok": re.compile(r"/video/\d+", re.IGNORECASE),
}


def _is_specific_post_url(network: str, url: str) -> bool:
    """True si la URL apunta a un post puntual indexado (no perfil ni home).

    Instagram: /p/, /reel/, /tv/ · TikTok: /video/ · X/Twitter: /status/.
    """
    if not url:
        return False
    pat = _SPECIFIC_POST_PATTERNS.get(network)
    return bool(pat and pat.search(url))

# Paths de IG que parecen "user" en la URL pero no lo son
_IG_RESERVED_PATHS = {
    "p", "reel", "tv", "explore", "accounts", "direct",
    "stories", "web", "developer", "about", "legal",
}


def _parse_twitter_url(url: str) -> tuple[str, str, str]:
    m = _TWITTER_URL_RE.search(url or "")
    if not m:
        return "", "", url or ""
    user, post_id = m.group(1), m.group(2)
    return user, f"https://x.com/{user}", post_id


def _parse_instagram_url(url: str) -> tuple[str, str, str]:
    m = _INSTAGRAM_USER_POST_RE.search(url or "")
    if m and m.group(1).lower() not in _IG_RESERVED_PATHS:
        user, post_id = m.group(1), m.group(3)
        return user, f"https://instagram.com/{user}", post_id
    m = _INSTAGRAM_POST_RE.search(url or "")
    if m:
        return "", "", m.group(1)
    return "", "", url or ""


def _parse_tiktok_url(url: str) -> tuple[str, str, str]:
    m = _TIKTOK_URL_RE.search(url or "")
    if not m:
        return "", "", url or ""
    user, video_id = m.group(1), m.group(2)
    return user, f"https://tiktok.com/@{user}", video_id


def _tiktok_search_fallback_url(author: str, keyword: str) -> str | None:
    """Link de TikTok robusto, a prueba de fallos.

    SerpAPI a veces devuelve la URL del último video del creador en lugar del
    post que matcheó en texto. Además, meter "@usuario keyword" en el buscador
    interno marea al algoritmo (muestra perfiles sueltos o videos random en
    Populares). Por eso evitamos la búsqueda mixta:

    1. Autor válido -> perfil directo del creador:  tiktok.com/@usuario
                       (Prensa audita su feed al toque).
    2. Sin autor (vacío o "?") -> búsqueda global SOLO por la keyword, sin arroba:
                       tiktok.com/search?q=keyword
    3. Nada de lo anterior -> None (el caller conserva la URL original).

    NUNCA devuelve "tiktok.com" sin path/parámetros (eso mandaba al FYP random).
    """
    clean_author = (author or "").lstrip("@").strip()
    # SerpAPI deja "?" (u otros placeholders) cuando no logró extraer el autor.
    if clean_author in ("", "?", "-"):
        clean_author = ""
    clean_kw = (keyword or "").strip()

    if clean_author:
        return f"https://www.tiktok.com/@{quote(clean_author, safe='')}"
    if clean_kw:
        return f"https://www.tiktok.com/search?q={quote(clean_kw)}"
    # Sin autor ni keyword no hay forma de armar un link con sentido.
    return None


def _detect_network_from_url(url: str) -> str | None:
    u = (url or "").lower()
    if "instagram.com/" in u:
        return "instagram"
    if "tiktok.com/" in u:
        return "tiktok"
    if "x.com/" in u or "twitter.com/" in u:
        return "twitter"
    return None


def _parse_post_url(url: str, hint_network: str | None = None) -> tuple[str, str, str, str]:
    """Devuelve (network, author, author_url, post_id). Usa hint_network si la URL no resuelve."""
    network = _detect_network_from_url(url) or hint_network or "twitter"
    if network == "twitter":
        a, au, pid = _parse_twitter_url(url)
    elif network == "instagram":
        a, au, pid = _parse_instagram_url(url)
    elif network == "tiktok":
        a, au, pid = _parse_tiktok_url(url)
    else:
        a, au, pid = "", "", url or ""
    return network, a, au, pid


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
    """'(from:user1 OR from:user2)' — operador específico de X/Twitter."""
    if not accounts:
        return ""
    clean = [a.lstrip("@").strip() for a in accounts if a and a.strip()]
    if not clean:
        return ""
    return "(" + " OR ".join(f"from:{u}" for u in clean) + ")"


def _clean_serp_results(items: list[dict]) -> list[dict]:
    """
    Limpia los resultados crudos de SerpAPI antes de mandarlos a Gemini:
    - descarta items sin snippet ni title (no hay texto que analizar)
    - dedupea por URL exacta
    - dedupea por snippet exacto (distinto URL, mismo contenido)
    Reduce tokens del prompt y baja la chance de tocar el rate limit.
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


def _search_with_serpapi(
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


def _call_gemini_model(model: str, api_key: str, prompt: str) -> tuple[list | None, int | None]:
    """
    Llama a un modelo Gemini específico. Devuelve (lista_scored, http_status_si_error).
    - (lista, None): éxito
    - (None, status): error HTTP con status code (puede disparar fallback)
    - (None, None): error de otro tipo (red, parseo) — no tiene sentido fallback de modelo
    """
    # v1beta expone todos los modelos flash/lite actuales; v1 devolvía 404 en
    # algunos alias (p. ej. gemini-flash-latest), rompiendo la cascada de fallback.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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
            print(f"ERROR Gemini[{model}]: respuesta no es lista JSON")
            return None, None
        return scored, None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        body_msg = ""
        if e.response is not None:
            try:
                body = e.response.json()
                body_msg = body.get("error", {}).get("message", "") or str(body)[:200]
            except Exception:
                body_msg = (e.response.text or "")[:200]
        print(f"ERROR Gemini[{model}]: HTTP {status} — {body_msg}")
        return None, status
    except Exception as e:
        print(f"ERROR Gemini[{model}]: {e}")
        return None, None


def _process_with_gemini(
    resultados: list[dict],
    termino: str,
    smata_mode: bool,
    keywords: list[str],
) -> list[dict] | None:
    """
    Pide a Gemini scores de relevancia para TODAS las redes en UNA sola llamada
    (cada resultado trae su campo "network") y mapea cada uno al shape PostOut.
    Una sola llamada en vez de una por red reduce ~66% el consumo de cuota.
    Retorna None ante errores upstream (auth, 503, parseo) para que fetch_posts
    no cachee un vacío espurio. [] indica vacío legítimo.

    Cascada de modelos GEMINI_MODELS con fallback en 429/503.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no configurada.")
        return None

    # El tope por red ya se aplicó en fetch_posts antes de mergear; acá usamos
    # el lote combinado tal cual.
    resultados_limitados = resultados
    redes_presentes = sorted({r.get("network", "") for r in resultados if r.get("network")})
    redes_label = ", ".join(_NETWORK_PROMPT_LABEL.get(n, n) for n in redes_presentes) or "redes sociales"

    # Inyección de IDs únicos e inequívocos ("Post_0", "Post_1", ...). El scoring
    # vuelve a asociarse por ese ID (no por URL), para que Gemini no pueda mezclar
    # publicaciones ni alterar la asociación. by_id mapea ID -> resultado crudo.
    by_id: dict[str, dict] = {}
    items_para_prompt: list[dict] = []
    for i, r in enumerate(resultados_limitados):
        pid = f"Post_{i}"
        by_id[pid] = r
        items_para_prompt.append({
            "id": pid,
            "network": r.get("network", ""),
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "url": r.get("url", ""),
            "date": r.get("date", ""),
        })
    resultados_text = json.dumps(items_para_prompt, ensure_ascii=False, indent=2)

    # ── Bifurcación del criterio según el switch "Modo SMATA" ──────────────────
    if smata_mode:
        # MODO SMATA (hiper-estricto): el contenido DEBE estar ligado a SMATA, a la
        # industria automotriz o a los mecánicos en Argentina. Cualquier desvío
        # del tema (p. ej. contenido de Indonesia u otro país sin relación) → 0.
        system_role = (
            "Sos un asistente de análisis de redes sociales para el sindicato SMATA "
            "(sector automotriz argentino)."
        )
        criterio = (
            "1. Analizá cada resultado y determiná si es relevante para SMATA y el "
            "sector automotriz/sindical argentino.\n"
            "2. El contenido DEBE estar ligado a SMATA, a la industria automotriz o a "
            "los mecánicos en Argentina. Cualquier desvío del tema (por ejemplo "
            "contenido de Indonesia u otro país sin relación) va a score 0.\n"
            "3. Asigná un score del 0 al 100 según su relevancia.\n"
            "4. Solo incluí posts con score >= 50."
        )
        tiktok_warning = ""
        if "tiktok" in redes_presentes:
            tiktok_warning = (
                "\nATENCIÓN — REGLAS ADICIONALES PARA LOS RESULTADOS CON network='tiktok':\n"
                "Los snippets de TikTok en Google suelen ser pobres, en otros idiomas o "
                "de cuentas internacionales sin relación con el sindicato SMATA ni con la "
                "industria automotriz argentina. Aplicá estas reglas estrictas:\n"
                "- Si el snippet NO menciona explícitamente al sindicato SMATA, a la "
                "industria automotriz argentina, o a un actor argentino del rubro "
                "(empresas como Ford/Volkswagen/Toyota Argentina, dirigentes gremiales, "
                "políticos del sector, etc.) → score 0-15.\n"
                "- Posts en otro idioma que no sea español rioplatense → score 0.\n"
                "- Cuentas o handles que parezcan extranjeros o no tengan contexto "
                "argentino → score 0-10.\n"
                "- No asumas relevancia si el texto es muy corto o ambiguo: en caso de "
                "duda, score bajo.\n"
            )
    else:
        # MODO AMPLIO (Monitor de Prensa): dejá pasar lo relevante a nivel político,
        # gremial, social, económico o cultural en Argentina, SIN exigir SMATA.
        system_role = (
            "Sos un monitor de prensa amplio para un sindicato argentino. Analizás "
            "tendencias en redes sociales del ámbito argentino."
        )
        criterio = (
            "1. Dejá pasar cualquier publicación que coincida con la keyword y que sea "
            "relevante a nivel político, gremial, social, económico o cultural en "
            "Argentina. NO exijas que el post mencione a SMATA.\n"
            "2. Asigná un score del 0 al 100 según esa relevancia informativa.\n"
            "3. Penalizá con score 0 ÚNICAMENTE: spam evidente, bots, contenido "
            "internacional fuera de LATAM, o posteos completamente vacíos de valor "
            "informativo.\n"
            "4. Incluí todos los posts que superen ese criterio amplio."
        )
        tiktok_warning = ""
        if "tiktok" in redes_presentes:
            tiktok_warning = (
                "\nNOTA PARA LOS RESULTADOS CON network='tiktok':\n"
                "Los snippets de TikTok en Google suelen ser pobres o multi-idioma. "
                "Penalizá con score bajo solo el contenido internacional fuera de LATAM, "
                "el spam o los videos sin valor informativo. NO exijas mención de SMATA.\n"
            )

    prompt = f"""{system_role}

Vas a recibir una lista de publicaciones en formato JSON sobre publicaciones en {redes_label} relacionadas con el término: "{termino}". Cada publicación tiene un "id" único ("Post_0", "Post_1", ...), más "title", "snippet", "url", "date" y "network" (twitter, instagram o tiktok).

REGLA DE AISLAMIENTO (OBLIGATORIA): Debés evaluar cada publicación de forma totalmente AISLADA e INDEPENDIENTE, aplicando exactamente los mismos criterios de filtrado a todas. Está TERMINANTEMENTE PROHIBIDO que el contexto, el tema o el puntaje de una publicación influya en el de otra. Tratá cada "id" como un caso separado, como si lo analizaras solo. No agrupes ni promedies ni "contagies" relevancia entre publicaciones.

Criterios de evaluación (idénticos para cada publicación):
{criterio}{tiktok_warning}

Devolvé ÚNICAMENTE un JSON válido (sin texto adicional ni bloques de código) que sea un ESPEJO EXACTO de los IDs recibidos: un objeto por cada publicación enviada, con su mismo "id". No agregues ni omitas ninguno. Formato exacto:
[
  {{ "id": "Post_0", "score": 90, "razon": "breve justificación del puntaje" }},
  {{ "id": "Post_1", "score": 0, "razon": "breve justificación del puntaje" }}
]

Publicaciones a evaluar:
{resultados_text}"""

    # Cascada de modelos: el primero que responda OK gana. Solo se intenta el
    # próximo si el anterior fue 429 (rate limit) o 503 (saturación).
    scored: list | None = None
    for idx, model in enumerate(GEMINI_MODELS):
        scored, status = _call_gemini_model(model, api_key, prompt)
        if scored is not None:
            if idx > 0:
                print(f"DEBUG Gemini: fallback EXITOSO con {model}")
            break
        if status not in GEMINI_RETRY_STATUSES:
            break
        if idx + 1 < len(GEMINI_MODELS):
            print(f"DEBUG Gemini: HTTP {status} en {model}, probando fallback {GEMINI_MODELS[idx + 1]}")

    if scored is None:
        return None

    posts: list[dict] = []
    for item in scored:
        # Mapeo de retorno por ID: recuperamos el post crudo ORIGINAL por su id.
        # La URL sale de NUESTROS datos (no de lo que devuelve Gemini), así la
        # asociación es inequívoca y la IA no puede alterar el link.
        pid = item.get("id", "") or ""
        src = by_id.get(pid)
        if src is None:
            # id inexistente (Gemini lo inventó o repitió): lo ignoramos.
            continue
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0

        post_url = src.get("url", "") or ""
        snippet = src.get("snippet", "") or src.get("title", "")
        date = src.get("date", "") or ""
        network, author, author_url, post_id = _parse_post_url(post_url, hint_network=src.get("network"))

        # Prioridad ABSOLUTA al post real: si la URL ya es un deep-link válido al
        # posteo (/p/, /reel/, /tv/ en IG; /video/ en TikTok; /status/ en X), la
        # respetamos sin pisarla. Solo cuando la URL está vacía, rota, apunta a la
        # home/perfil o no se pudo extraer el autor ("?"), caemos al fallback de
        # TikTok (perfil del creador o búsqueda global por keyword).
        link = post_url
        if not _is_specific_post_url(network, post_url) and network == "tiktok":
            fallback = _tiktok_search_fallback_url(author, termino)
            if fallback:
                link = fallback

        posts.append({
            "id": post_id or post_url,
            "network": network,
            "author": author,
            "author_url": author_url,
            "text": snippet,
            "date": date,
            "post_url": link,
            "relevance_score": score,
            "relevance_level": _level_from_score(score),
            "matched_terms": _find_matched_terms(snippet, keywords),
            "video_url": None,
        })

    # Filtro duro por piso de score: defiende contra falsos positivos que el
    # prompt no logró bajar (especialmente en TikTok, donde aplicamos piso 50).
    filtered: list[dict] = []
    dropped_by_floor: dict[str, int] = {}
    for p in posts:
        floor = _score_floor(p["network"], smata_mode)
        if p["relevance_score"] >= floor:
            filtered.append(p)
        else:
            dropped_by_floor[p["network"]] = dropped_by_floor.get(p["network"], 0) + 1
    if dropped_by_floor:
        details = ", ".join(f"{n}:{c}" for n, c in dropped_by_floor.items())
        print(f"DEBUG filtro score floor: descartados por red {{{details}}}")

    return filtered


def fetch_posts(
    termino: str,
    fecha_desde: str = None,
    smata_mode: bool = False,
    keywords: list[str] | None = None,
    accounts: list[str] | None = None,
    networks: list[str] | None = None,
) -> list[dict]:
    """
    Función principal. Itera las redes solicitadas y mergea resultados.
    """
    nets = [n for n in (networks or []) if n in SUPPORTED_NETWORKS]
    if not nets:
        nets = ["twitter"]  # fallback seguro si el front no manda nada válido

    print(f"DEBUG: fetch_posts termino='{termino}' redes={nets} smata_mode={smata_mode}")

    # Barrido de entradas vencidas: evita que _CACHE crezca sin límite con
    # búsquedas que no se repiten (la instancia de Render vive mucho tiempo).
    now = time.time()
    for k in [k for k, (ts, _) in _CACHE.items() if now - ts >= _CACHE_TTL_SECONDS]:
        del _CACHE[k]

    cache_key = (
        termino,
        fecha_desde,
        smata_mode,
        tuple(sorted(keywords or [])),
        tuple(sorted(accounts or [])),
        tuple(sorted(nets)),
    )
    cached = _CACHE.get(cache_key)
    if cached is not None:
        ts, data = cached
        if time.time() - ts < _CACHE_TTL_SECONDS:
            print(f"DEBUG: cache HIT para {cache_key}")
            return data
        del _CACHE[cache_key]

    all_posts: list[dict] = []
    any_upstream_error = False
    total_serp_results = 0

    # 1) SerpAPI por red (su cuota es amplia), aplicando el tope por red ANTES de
    #    mergear. Cada resultado se etiqueta con su "network".
    serp_merged: list[dict] = []
    for net in nets:
        resultados = _search_with_serpapi(
            termino,
            network=net,
            max_results=10,
            fecha_desde=fecha_desde,
            accounts=accounts,
        )
        if resultados is None:
            any_upstream_error = True
            continue
        if not resultados:
            continue
        lote = resultados[:GEMINI_MAX_PER_NETWORK]
        if len(lote) < len(resultados):
            print(f"DEBUG Gemini[{net}]: lote reducido {len(resultados)} -> {len(lote)}")
        for r in lote:
            item = dict(r)
            item["network"] = net
            serp_merged.append(item)
        total_serp_results += len(lote)

    # 2) UNA sola llamada a Gemini para TODAS las redes juntas (en vez de una por
    #    red): reduce ~66% el consumo de la cuota free-tier.
    if serp_merged:
        posts = _process_with_gemini(serp_merged, termino, smata_mode, keywords or [])
        if posts is None:
            any_upstream_error = True
        else:
            all_posts.extend(posts)

    print(f"DEBUG: total posts pre-dedupe = {len(all_posts)} (sobre {total_serp_results} resultados SerpAPI, upstream_error={any_upstream_error})")

    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for p in all_posts:
        url = p.get("post_url") or ""
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(p)
    if len(deduped) != len(all_posts):
        print(f"DEBUG: dedupe quitó {len(all_posts) - len(deduped)} duplicados por post_url")
    all_posts = deduped

    # Si hubo error upstream (SerpAPI/Gemini) y NO quedó ningún post utilizable,
    # lo señalamos como 503 en vez de devolver [] (que se ve como "no hay nada").
    # El caso típico es el rate limit / cuota agotada de Gemini free-tier.
    if any_upstream_error and not all_posts:
        raise UpstreamUnavailableError(
            "El analizador de IA (Gemini) o el buscador (SerpAPI) no respondieron, "
            "probablemente por límite de cuota. Reintentá en un minuto."
        )

    # Política de cache: no cachear si SerpAPI o Gemini fallaron en cualquier red.
    # Así un reintento posterior puede recuperar las redes faltantes en vez de
    # quedar pegado con un resultado parcial durante 10 min.
    if any_upstream_error:
        print("DEBUG: no se cachea (error upstream en alguna red — SerpAPI o Gemini)")
    else:
        _CACHE[cache_key] = (time.time(), all_posts)
    return all_posts
