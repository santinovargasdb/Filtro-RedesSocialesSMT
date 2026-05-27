import os
import json
import requests

# ── Configuración de SerpAPI ──────────────────────────────────────────────────
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"


def _search_with_serpapi(termino: str, max_results: int = 10) -> list[dict]:
    """
    Realiza una búsqueda en Google vía SerpAPI filtrando resultados de X/Twitter.
    Devuelve lista de dicts con: title, snippet, url.
    """
    if not SERPAPI_API_KEY:
        print("ERROR: SERPAPI_API_KEY no configurada en las variables de entorno.")
        return []

    query = f"site:x.com OR site:twitter.com {termino}"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": max_results,
        "hl": "es",
        "gl": "ar",
    }

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

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
            })

        print(f"DEBUG: SerpAPI devolvió {len(results)} resultados para '{termino}'.")
        return results

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallo en la petición a SerpAPI: {e}")
        return []


def _process_with_gemini(resultados: list[dict], termino: str, strict_mode: bool) -> list[dict]:
    """
    Toma los resultados crudos de SerpAPI y usa Gemini vía HTTP directo (evita librerías viejas).
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no configurada.")
        return []

    resultados_text = json.dumps(resultados, ensure_ascii=False, indent=2)
    strict_note = "Solo incluí posts con score >= 50." if strict_mode else "Incluí todos los posts."

    prompt = f"""Sos un asistente de análisis de redes sociales para el sindicato SMATA (sector automotriz argentino).
Te paso resultados reales de Google sobre publicaciones en X (Twitter) relacionadas con el término: "{termino}".

Cada resultado tiene: "title" (título del resultado en Google), "snippet" (extracto del tweet/post), "url" (link directo).

Tu tarea:
1. Analizá cada resultado y determiná si es relevante para SMATA y el sector automotriz/sindical argentino.
2. Asigná un score del 0 al 100 según su relevancia.
3. {strict_note}

Devolvé ÚNICAMENTE un JSON válido, sin texto adicional ni bloques de código. Formato exacto:
[
  {{
    "title": "TEXTO DEL SNIPPET EN MAYÚSCULAS (máx. 120 caracteres)",
    "post_url": "url_del_resultado",
    "score": 75
  }}
]

Resultados de SerpAPI:
{resultados_text}"""

    # URL directa a la API estable v1 de Google, saltándonos el problema de la librería
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        res_data = response.json()
        
        # Extraemos el texto de la respuesta de Google
        raw = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Limpieza por si mete bloques de markdown tipo ```json
        raw = raw.replace("```json", "").replace("```", "").strip()
        
        posts = json.loads(raw)
        return posts if isinstance(posts, list) else []
    except Exception as e:
        print(f"ERROR procesando con Gemini directo: {e}")
        return []


def fetch_posts(termino: str, fecha_desde: str = None, strict_mode: bool = False) -> list[dict]:
    """
    Función principal.
    """
    print(f"DEBUG: fetch_posts llamado con termino='{termino}', strict_mode={strict_mode}")

    resultados_crudos = _search_with_serpapi(termino, max_results=10)
    print(f"DEBUG: {len(resultados_crudos)} resultados obtenidos de SerpAPI")

    posts_procesados = _process_with_gemini(resultados_crudos, termino, strict_mode)
    print(f"DEBUG: {len(posts_procesados)} posts devueltos tras análisis de Gemini")

    return posts_procesados