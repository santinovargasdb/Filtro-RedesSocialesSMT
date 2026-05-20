import os
import json
import google.generativeai as genai

# ── Configuración de Gemini ──────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── Scraper de Twitter ───────────────────────────────────────────────────────
try:
    from ntscraper import Nitter
    scraper = Nitter(log_level=0, skip_instance_check=False)
    SCRAPER_AVAILABLE = True
except Exception:
    scraper = None
    SCRAPER_AVAILABLE = False
    print("WARNING: ntscraper no disponible, se devolverán resultados vacíos.")


def _scrape_tweets(termino: str, max_tweets: int = 10) -> list[dict]:
    """Raspa tweets crudos usando ntscraper."""
    if not SCRAPER_AVAILABLE or scraper is None:
        return []
    try:
        results = scraper.get_tweets(termino, mode="term", number=max_tweets)
        tweets = results.get("tweets", [])
        out = []
        for t in tweets:
            out.append({
                "text": t.get("text", ""),
                "url": t.get("link", ""),
                "date": t.get("date", ""),
                "user": t.get("user", {}).get("username", "unknown"),
            })
        return out
    except Exception as e:
        print(f"Error scrapeando tweets: {e}")
        return []


def _process_with_gemini(tweets: list[dict], termino: str, strict_mode: bool) -> list[dict]:
    """Pasa los tweets crudos a Gemini y devuelve JSON limpio."""
    if not tweets:
        return []

    tweets_text = json.dumps(tweets, ensure_ascii=False, indent=2)
    strict_note = "Solo incluí posts con score >= 50." if strict_mode else "Incluí todos los posts."

    prompt = f"""Sos un asistente de análisis de redes sociales para el sindicato SMATA (sector automotriz argentino).
Te voy a pasar una lista de tweets en formato JSON. Tu tarea es analizarlos y devolver un JSON limpio.

Término buscado: "{termino}"

Para cada tweet:
- "title": el texto del tweet en MAYÚSCULAS, recortado a 120 caracteres si es muy largo
- "post_url": la URL del tweet original
- "score": un número del 0 al 100 indicando qué tan relevante es el tweet para SMATA y el sector automotriz/sindical argentino

{strict_note}

Tweets crudos:
{tweets_text}

Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, sin bloques de código. Formato:
[
  {{"title": "...", "post_url": "...", "score": 75}},
  ...
]"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        posts = json.loads(raw)
        return posts if isinstance(posts, list) else []
    except Exception as e:
        print(f"Error procesando con Gemini: {e}")
        return []


def fetch_posts(termino: str, fecha_desde: str = None, strict_mode: bool = False) -> list[dict]:
    """
    Función principal. Raspa tweets y los procesa con Gemini.
    Devuelve lista de dicts con: title, post_url, score.
    """
    print(f"DEBUG: fetch_posts llamado con termino='{termino}', strict_mode={strict_mode}")

    tweets_crudos = _scrape_tweets(termino, max_tweets=10)
    print(f"DEBUG: {len(tweets_crudos)} tweets raspados")

    posts_procesados = _process_with_gemini(tweets_crudos, termino, strict_mode)
    print(f"DEBUG: {len(posts_procesados)} posts devueltos por Gemini")

    return posts_procesados
