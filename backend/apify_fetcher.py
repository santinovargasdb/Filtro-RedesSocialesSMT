import os
import json
import requests
import uuid
from datetime import datetime

SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"

# Una variable global temporal para cazar el error
LAST_DEBUG_INFO = {"status": "No se ejecutó búsqueda aún"}

def _search_with_serpapi(termino: str, max_results: int = 10, fecha_desde: str = None) -> list[dict]:
    global LAST_DEBUG_INFO
    if not SERPAPI_API_KEY:
        LAST_DEBUG_INFO = {"status": "ERROR", "reason": "La API KEY de SerpAPI está vacía en Vercel"}
        return []

    # Probemos con una query híper limpia de Google, sin añadidos, para asegurar resultados
    query = f"{termino}"
    if fecha_desde:
        query += f" after:{fecha_desde}"
    
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
        LAST_DEBUG_INFO = {
            "status_code_serpapi": response.status_code,
            "json_keys_recibidas": list(response.json().keys()) if response.status_code == 200 else "N/A"
        }
        
        response.raise_for_status()
        data = response.json()

        organic_results = data.get("organic_results", [])
        if not organic_results:
            LAST_DEBUG_INFO["reason"] = f"Google no devolvió organic_results para '{query}'. Quizás SerpAPI cambió el JSON."
            return []

        results = []
        for item in organic_results[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
            })
        return results

    except requests.exceptions.RequestException as e:
        LAST_DEBUG_INFO = {"status": "ERROR_REQUEST", "exception": str(e)}
        return []


def _process_with_gemini(resultados: list[dict], termino: str, strict_mode: bool) -> list[dict]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return []

    resultados_text = json.dumps(resultados, ensure_ascii=False, indent=2)
    prompt = f"""Sos un asistente de análisis de redes sociales. Procesá este JSON y asigná un score del 0 al 100.
Devolvé ÚNICAMENTE un arreglo JSON válido (sin textos extras, ni bloques ```json). Formato requerido:
[
  {{
    "author": "@anonimo",
    "text": "Texto extraido",
    "relevance_score": 85,
    "matched_terms": ["{termino}"]
  }}
]
Resultados:
{resultados_text}"""

    url = f"[https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=){api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        res_data = response.json()
        raw = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        posts_ia = json.loads(raw)
        return posts_ia if isinstance(posts_ia, list) else []
    except Exception as e:
        return []


def fetch_posts(termino: str, fecha_desde: str = None, strict_mode: bool = False) -> list[dict]:
    # Limpiamos el debug antes de arrancar
    global LAST_DEBUG_INFO
    LAST_DEBUG_INFO = {"status": "Iniciando fetch_posts"}

    resultados_crudos = _search_with_serpapi(termino, max_results=10, fecha_desde=fecha_desde)

    if not resultados_crudos:
        # ¡HACK TRUCO! Si dio vacío, metemos la información del error dentro de la lista para leerla en la web
        return [{
            "id": "err-999",
            "network": "twitter",
            "author": "@SISTEMA_DEBUG",
            "author_url": "[https://x.com](https://x.com)",
            "text": f"DIAGNÓSTICO: {json.dumps(LAST_DEBUG_INFO)}",
            "date": "2026-05-26",
            "post_url": "[https://x.com](https://x.com)",
            "relevance_score": 99,
            "matched_terms": ["debug"]
        }]

    posts_procesados = _process_with_gemini(resultados_crudos, termino, strict_mode)
    
    if not posts_procesados:
        return [{
            "id": "err-888",
            "network": "twitter",
            "author": "@SISTEMA_DEBUG",
            "author_url": "[https://x.com](https://x.com)",
            "text": "DIAGNÓSTICO: SerpAPI trajo datos, pero Gemini falló al procesar o responder el formato.",
            "date": "2026-05-26",
            "post_url": "[https://x.com](https://x.com)",
            "relevance_score": 99,
            "matched_terms": ["debug"]
        }]

    # Si todo anduvo bien, armamos la lista final para el frontend
    fecha_actual = datetime.now().isoformat().split("T")[0]
    resultados_finales = []
    for idx, post in enumerate(posts_procesados):
        score = post.get("relevance_score", 50)
        if strict_mode and score < 50:
            continue
        original_url = resultados_crudos[idx]["url"] if idx < len(resultados_crudos) else "[https://x.com](https://x.com)"
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
