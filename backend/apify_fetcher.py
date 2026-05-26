import os
import json
import requests
import uuid
import re
from datetime import datetime

# ── Configuración de SerpAPI ──────────────────────────────────────────────────
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search"

# Variable global temporal para el chivato de diagnóstico
LAST_DEBUG_INFO = {"status": "No se ejecutó búsqueda aún"}


def _search_with_serpapi(termino: str, max_results: int = 10, fecha_desde: str = None) -> list[dict]:
    """
    Realiza una búsqueda global orientada a la red social X/Twitter vía SerpAPI,
    aplicando filtros de fecha dinámicos con 'after:' si el usuario los define.
    """
    global LAST_DEBUG_INFO
    if not SERPAPI_API_KEY:
        LAST_DEBUG_INFO = {"status": "ERROR", "reason": "La API KEY de SerpAPI está vacía en Vercel"}
        return []

    # Construcción de la Query optimizada para Google
    query = f"{termino} twitter posts"
    if fecha_desde:
        query += f" after:{fecha_desde}"
    
    print(f"DEBUG: Query enviada a SerpAPI = '{query}'")

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
        
        # Guardamos metadatos de la respuesta para el diagnóstico
        LAST_DEBUG_INFO = {
            "status_code_serpapi": response.status_code,
            "json_keys_recibidas": list(response.json().keys()) if response.status_code == 200 else "N/A"
        }
        
        response.raise_for_status()
        data = response.json()

        organic_results = data.get("organic_results", [])
        if not organic_results:
            LAST_DEBUG_INFO["reason"] = f"Google no devolvió organic_results para '{query}'."
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
        LAST_DEBUG_INFO = {"status": "ERROR_REQUEST", "exception": str(e)}
        return []


def _process_with_gemini(resultados: list[dict], termino: str, strict_mode: bool) -> list[dict]:
    """
    Toma los resultados crudos de SerpAPI y usa Gemini vía HTTP directo.
    Usa una limpieza robusta con Regex para aislar el JSON de cualquier texto extra.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY no configurada en Vercel.")
        return []

    resultados_text = json.dumps(resultados, ensure_ascii=False, indent=2)

    prompt = f"""Sos un asistente de análisis de redes sociales para un monitor de feeds. 
Te paso resultados crudos obtenidos desde Google sobre la red social X (Twitter) relacionados con: "{termino}".

Tu tarea es procesar la información. Asignale a cada post un puntaje de relevancia (0 a 100).
Si el post menciona temas sindicales, laboralistas o de SMATA/industria automotriz, dale prioridad alta (>70). Si habla de otra temática general, puntualo igual según qué tan informativo sea (no lo dejes en 0).

Devolvé ÚNICAMENTE un arreglo JSON válido. No agregues introducciones, ni explicaciones, ni bloques de código markdown. Formato requerido:
[
  {{
    "author": "@usuario",
    "text": "Texto completo extraído del snippet o title",
    "relevance_score": 85,
    "matched_terms": ["{termino}"]
  }}
]

Resultados de SerpAPI:
{resultados_text}"""

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
        
        # --- BLINDAJE CON REGEX ---
        # Busca el primer '[' y el último ']' para extraer solo la estructura limpia del JSON
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            json_limpio = match.group(0)
        else:
            json_limpio = raw
            
        posts_ia = json.loads(json_limpio)
        return posts_ia if isinstance(posts_ia, list) else []
        
    except Exception as e:
        print(f"ERROR crítico procesando con Gemini directo: {e}")
        return []


def fetch_posts(termino: str, fecha_desde: str = None, strict_mode: bool = False) -> list[dict]:
    """
    Función principal llamada desde main.py.
    """
    global LAST_DEBUG_INFO
    LAST_DEBUG_INFO = {"status": "Iniciando fetch_posts"}

    print(f"DEBUG: fetch_posts llamado con termino='{termino}', fecha_desde='{fecha_desde}', strict_mode={strict_mode}")

    # 1. Petición a SerpAPI
    resultados_crudos = _search_with_serpapi(termino, max_results=10, fecha_desde=fecha_desde)
    print(f"DEBUG: {len(resultados_crudos)} resultados obtenidos de SerpAPI")

    # Si SerpAPI dio vacío, inyectamos la tarjeta chivato de diagnóstico para ver en la web
    if not resultados_crudos:
        return [{
            "id": "err-999",
            "network": "twitter",
            "author": "@SISTEMA_DEBUG",
            "author_url": "https://x.com",
            "text": f"DIAGNÓSTICO SERPAPI: {json.dumps(LAST_DEBUG_INFO)}",
            "date": "2026-05-26",
            "post_url": "https://x.com",
            "relevance_score": 99,
            "matched_terms": ["debug"]
        }]

    # 2. Procesamiento con Gemini
    posts_procesados = _process_with_gemini(resultados_crudos, termino, strict_mode)
    print(f"DEBUG: {len(posts_procesados)} posts devueltos tras análisis de Gemini")

    # Si Gemini falló o el JSON se rompió, inyectamos la tarjeta de alerta
    if not posts_procesados:
        return [{
            "id": "err-888",
            "network": "twitter",
            "author": "@SISTEMA_DEBUG",
            "author_url": "https://x.com",
            "text": "DIAGNÓSTICO GEMINI: SerpAPI trajo datos, pero Gemini falló al procesar, responder el formato o validar la API KEY.",
            "date": "2026-05-26",
            "post_url": "https://x.com",
            "relevance_score": 99,
            "matched_terms": ["debug"]
        }]

    # 3. Armado del JSON final con el tipado exacto que espera el Frontend de Next.js
    fecha_actual = datetime.now().isoformat().split("T")[0]
    resultados_finales = []

    for idx, post in enumerate(posts_procesados):
        score = post.get("relevance_score", 50)
        
        # Filtro estricto (Modo Estricto) administrado en Python
        if strict_mode and score < 50:
            continue

        # Vinculamos la URL real obtenida de Google correspondiente a este índice
        original_url = resultados_crudos[idx]["url"] if idx < len(resultados_crudos) else "https://x.com"

        resultados_finales.append({
            "id": str(uuid.uuid4())[:8],
            "network": "twitter",
            "author": post.get("author", "@anonimo"),
            "author_url": f"https://x.com/{post.get('author', 'anonimo').lstrip('@')}",
            "text": post.get("text", "Sin contenido"),
            "date": fecha_actual,
            "post_url": original_url,
            "relevance_score": score,
            "matched_terms": post.get("matched_terms", [termino])
        })

    return resultados_finales
