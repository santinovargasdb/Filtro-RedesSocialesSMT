from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime

client = ApifyClient(APIFY_API_KEY)

def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    
    # FORZADO: Si el frontend manda listas vacías, creamos términos de búsqueda
    search_list = [str(k) for k in keywords if k] + [str(h) for h in hashtags if h]
    if not search_list:
        search_list = ["SMATA", "gremio"] # Términos de rescate

    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id: continue
        
        run_input = {}
        if network == "twitter":
            run_input = {"searchTerms": search_list, "maxItems": 10}
        elif network == "instagram":
            # Formato exacto para evitar el error de 'Start URLs'
            run_input = {
                "directUrls": [f"https://www.instagram.com/explore/tags/{t.replace('#','')}/" for t in search_list],
                "resultsLimit": 5
            }
        elif network == "tiktok":
            run_input = {"hashtags": [search_list[0].replace('#','')], "maxMessages": 5}

        try:
            print(f"DEBUG: Intentando {network} con: {run_input}")
            run = client.actor(actor_id).call(run_input=run_input)
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                normalized = normalize_item(item, network)
                if normalized: all_posts.append(normalized)
        except Exception as e:
            print(f"ERROR en {network}: {e}")
            
    return all_posts

def normalize_item(item, network):
    # Simplificado al máximo para que NO falle por campos faltantes
    try:
        if network == "twitter":
            legacy = item.get("legacy", {})
            return {
                "id": str(item.get("id_str") or item.get("id")),
                "network": "twitter",
                "author": item.get("user", {}).get("screen_name") or "Usuario X",
                "text": legacy.get("full_text") or item.get("text") or "Contenido en link",
                "date": legacy.get("created_at") or datetime.datetime.now().isoformat(),
                "post_url": f"https://x.com/i/web/status/{item.get('id_str') or item.get('id')}"
            }
        elif network == "instagram":
            return {
                "id": item.get("id"),
                "network": "instagram",
                "author": item.get("ownerUsername") or "IG User",
                "text": item.get("caption") or "Post de Instagram",
                "date": item.get("timestamp") or datetime.datetime.now().isoformat(),
                "post_url": item.get("url")
            }
    except: return None
    return None
