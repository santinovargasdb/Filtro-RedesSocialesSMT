import os
import json
import google.generativeai as genai
from ntscraper import Nitter

# 1. Configuración de Google AI Studio
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Inicializamos el modelo correcto sin el prefijo "models/"
model = genai.GenerativeModel("gemini-1.5-flash")

def fetch_posts(termino: str, fecha_desde: str = None, strict_mode: bool = False):
    """
    Función principal llamada por main.py. Raspa X (Twitter) usando ntscraper 
    y procesa los resultados con Gemini 1.5 Flash.
    """
    print(f"Iniciando búsqueda para: {termino}")
    
    # 2. Raspado de datos con ntscraper
    scraper = Nitter()
    tweets_crudos = []
    
    try:
        # Se usa 'get_tweets' que es el método real de la librería
        tweets_data = scraper.get_tweets(termino, mode='term', number=15)
        
        if tweets_data and 'tweets' in tweets_data:
            for t in tweets_data['tweets']:
                tweets_crudos.append({
                    "texto": t.get("text", ""),
                    "fecha": t.get("date", ""),
                    "url": t.get("link", ""),
                    "usuario": t.get("user", {}).get("username", "Anónimo")
                })
    except Exception as e:
        print(f"Error raspando X con ntscraper: {str(e)}")
        return []

    if not tweets_crudos:
        print("No se encontraron tweets para procesar.")
        return []

    # 3. Procesamiento y filtrado inteligente con Gemini
    prompt = f"""
    Actúa como un analista de prensa experto para el sindicato SMATA. 
    Tu tarea es filtrar y procesar la siguiente lista de publicaciones encontradas en redes sociales sobre el término '{termino}'.
    
    Analizá cada publicación y devolvé ÚNICAMENTE un arreglo en formato JSON structured con las publicaciones que tengan relevancia gremial o industrial para el sector automotriz.
    
    Reglas estrictas de formato:
    1. El campo 'title' DEBE estar completamente en MAYÚSCULAS y resumir la noticia de forma directa (estilo titular de diario).
    2. El campo 'score' debe ser un número del 1 al 100 que mida la relevancia para el sindicato.
    3. Si el parámetro strict_mode es True, filtra de forma más rigurosa y no incluyas posts con score menor a 50.
    4. Devolvé un JSON limpio, sin bloques de código tipo ```json ... ```, solo el arreglo [].
    
    Parámetros actuales:
    - Strict Mode: {strict_mode}
    - Fecha Límite Filtro: {fecha_desde}
    
    Publicaciones crudas a procesar:
    {json.dumps(tweets_crudos, ensure_ascii=False, indent=2)}
    
    Estructura requerida del JSON de salida:
    [
      {{
        "title": "TITULAR RELEVANTE EN MAYÚSCULAS",
        "post_url": "url_original_del_post",
        "score": 85
      }}
    ]
    """

    try:
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        resultado_final = json.loads(text_response)
        return resultado_final
        
    except Exception as e:
        print(f"Error procesando con Google AI Studio o parseando JSON: {str(e)}")
        return []
