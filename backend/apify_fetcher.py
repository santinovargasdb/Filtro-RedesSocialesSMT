from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime

client = ApifyClient(APIFY_API_KEY)

def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    
    # Limpiamos y aseguramos que haya al menos un término para buscar
    clean_keywords = [k for k in keywords if k]
    clean_hashtags = [h.replace('#', '') for h in hashtags if h]
    
    # Si todo está vacío, usamos SMATA por defecto para que no falle el actor
    if not clean_keywords and not clean_hashtags:
        clean_keywords = ["SMATA"]

    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id: continue
            
        run_input = {}
        
        if network == "twitter":
            run_input = {
                "searchTerms": clean_keywords + [f"#{h}" for h in clean_hashtags],
                "maxItems": 15
            }
        elif network == "instagram":
            # Instagram Scraper REQUIERE 'directUrls'. No acepta 'hashtags' como campo simple.
            # Creamos una URL válida por cada hashtag o keyword
            tags_to_search = clean_hashtags if clean_hashtags else clean_keywords
            run_input = {
                "directUrls": [f"https://www.instagram.com/explore/tags/{t}/" for t in tags_to_search],
                "resultsLimit": 10
            }
        elif network == "tiktok":
            # TikTok Scraper requiere o 'hashtags' o 'searchQueries'
            run_input = {
                "hashtags": clean_hashtags if clean_hashtags else clean_keywords,
                "maxMessages": 10
            }

        try:
            print(f"Llamando a {network} con input: {run_input}") # Esto saldrá en tus logs de Railway
            run = client.actor(actor_id).call(run_input=run_input)
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                normalized = normalize_item(item, network)
                if normalized:
                    all_posts.append(normalized)
        except Exception as e:
            print(f"Error en {network}: {str(e)}")
            
    return all_posts

def normalize_item(item, network):
    try:
        if network == "twitter":
            legacy = item.get("legacy", {})
            text = legacy.get("full_text") or item.get("text")
            return {
                "id": str(item.get("id_str") or item.get("id")),
                "network": "twitter",
                "author": item.get("user", {}).get("screen_name") or "Usuario",
                "text": text or "Ver en X",
                "date": legacy.get("created_at") or datetime.datetime.now().isoformat(),
                "post_url": f"https://x.com/i/web/status/{item.get('id_str')}"
            }
        elif network == "instagram":
            return {
                "id": item.get("id"),
                "network": "instagram",
                "author": item.get("ownerUsername") or "Instagram User",
                "text": item.get("caption") or "Post de Instagram",
                "date": item.get("timestamp") or datetime.datetime.now().isoformat(),
                "post_url": item.get("url")
            }
        elif network == "tiktok":
            return {
                "id": item.get("id"),
                "network": "tiktok",
                "author": item.get("authorMeta", {}).get("name") or "TikTok User",
                "text": item.get("text") or "Video de TikTok",
                "date": datetime.datetime.now().isoformat(),
                "post_url": item.get("webVideoUrl")
            }
    except:
        return None
    return None
