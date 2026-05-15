from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime

client = ApifyClient(APIFY_API_KEY)

def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    
    # Unificamos términos de búsqueda
    search_queries = keywords + [f"#{h}" for h in hashtags]
    if not search_queries:
        search_queries = ["SMATA"] # Búsqueda por defecto de seguridad

    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id: continue
            
        run_input = {}
        
        if network == "twitter":
            run_input = {
                "searchTerms": search_queries,
                "maxItems": 15,
                "sort": "Latest"
            }
        elif network == "instagram":
            # REFORZADO: Generamos URLs directas de búsqueda para hashtags
            instagram_urls = [{"url": f"https://www.instagram.com/explore/tags/{q.replace('#','')}/"} for q in search_queries]
            run_input = {
                "directUrls": instagram_urls,
                "resultsLimit": 10
            }
        elif network == "tiktok":
            # REFORZADO: Buscamos por hashtag general, no solo por perfil
            run_input = {
                "hashtags": [q.replace("#","") for q in search_queries],
                "maxMessages": 10
            }

        try:
            run = client.actor(actor_id).call(run_input=run_input)
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                normalized_post = normalize_item(item, network)
                if normalized_post:
                    all_posts.append(normalized_post)
        except Exception as e:
            print(f"Error fetching from {network}: {e}")
            
    return all_posts

def normalize_item(item, network):
    try:
        if network == "twitter":
            # Búsqueda profunda en la estructura de X (Legacy -> Full Text)
            legacy = item.get("legacy", {})
            text = legacy.get("full_text") or item.get("text") or item.get("full_text")
            user = item.get("user", {}).get("screen_name") or legacy.get("user_id_str") or "Usuario de X"
            
            return {
                "id": str(item.get("id_str") or item.get("id")),
                "network": "twitter",
                "author": user,
                "text": text or "Sin contenido visible",
                "date": legacy.get("created_at") or datetime.datetime.now().isoformat(),
                "post_url": f"https://x.com/i/web/status/{item.get('id_str') or item.get('id')}",
            }
        elif network == "instagram":
            return {
                "id": item.get("id"),
                "network": "instagram",
                "author": item.get("ownerUsername") or "Instagram User",
                "text": item.get("caption") or "Post de Instagram",
                "date": item.get("timestamp") or datetime.datetime.now().isoformat(),
                "post_url": item.get("url"),
            }
    except:
        return None
    return None
