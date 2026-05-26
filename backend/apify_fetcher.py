import os
import json
import requests
import uuid
from datetime import datetime

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
    Toma los resultados crudos de SerpAPI y usa Gemini para estructurarlos y puntuarlos
    adaptando la respuesta exactamente al tipado que el Frontend espera.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no configurada.")
        return []

    resultados_text = json.dumps(resultados, ensure_ascii=False, indent=2)

    prompt = f"""Sos un asistente de análisis de redes sociales para un monitor de feeds. 
Te paso resultados crudos obtenidos desde Google sobre la red social X (Twitter) relacionados con: "{termino}".

Tu tarea es procesar y estructurar la información. Asignale a cada post un puntaje de relevancia (0 a 100).
Si el post menciona temas sindicales, laboralistas o de SMATA/industria automotriz, dale prioridad alta (>70). Si habla de otra temática general, puntualo igual según qué tan informativo sea (no lo dejes en 0).

Devolvé ÚNICAMENTE un arreglo JSON válido (sin textos extras, ni bloques ```json). Formato estricto requerido:
[
  {{
    "author": "@usuario_extrapolado_del_titulo_o_anonimo",
    "text": "Texto completo extraído del snippet o title",
    "relevance_score": 85,
    "matched_terms": ["{termino}"]
  }}
]

Resultados de SerpAPI:
{resultados_text}"""

    url = f"[https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=){api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        res_data = response.json()
        
        raw = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        
        posts_ia = json.loads(raw)
        if not isinstance(posts_ia, list):
            return []

        # Re-mapeo final en Python para garantizar IDs únicos y fechas correctas
        fecha_actual = datetime.now().isoformat().split("T")[0]
        resultados_finales = []

        for idx, post in enumerate(posts_ia):
            # Filtro del modo estricto en Python
            score = post.get("relevance_score", 50)
            if strict_mode and score < 50:
                continue

            # Conseguimos la URL original de la lista cruda
            original_url = resultados[idx]["url"] if idx < len(resultados) else "[https://x.com](https://x.com)"

            resultados_finales.append({
                "id": str(uuid.uuid4())[:8],
                "network": "twitter",
                "author": post.get("author", "@anonimo"),
                "author_url": f"[https://x.com/](https://x.com/){post.get('author', 'anonimo').lstrip('@')}",
                "text": post.get("text", "Sin contenido"),
                "date": fecha_actual,
                "post_url": original_url,
                "relevance_score": score,
                "matched_terms": post.get("matched_terms", [termino])
            })

        return resultados_finales

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

    if not resultados_crudos:
        return []

    posts_procesados = _process_with_gemini(resultados_crudos, termino, strict_mode)
    print(f"DEBUG: {len(posts_procesados)} posts devueltos tras análisis de Gemini")

    return posts_procesados
