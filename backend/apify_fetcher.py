from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime

client = ApifyClient(APIFY_API_KEY)

def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id: continue
        
        run_input = {}
        if network == "twitter":
            run_input = {
                "searchTerms": keywords + [f"#{h}" for h in hashtags],
                "twitterHandles": accounts,
                "maxItems": 15
            }
        elif network == "instagram":
            # SOLUCIÓN: Convertimos hashtags en las URLs que pide el scraper
            start_urls = [{"url": f"https://www.instagram.com/explore/tags/{h}/"} for h in hashtags]
            if not start_urls and keywords:
                start_urls = [{"url": f"https://www.instagram.com/explore/tags/{keywords[0]}/"}]
            
            run_input = {
                "directUrls": start_urls,
                "resultsLimit": 15
            }
        elif network == "tiktok":
            # SOLUCIÓN: Si no hay cuentas, buscamos por hashtags/keywords
            query = keywords[0] if keywords else (hashtags[0] if hashtags else "SMATA")
            run_input = { "hashtags": [query], "maxMessages": 15 }

        try:
            run = client.actor(actor_id).call(run_input=run_input)
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                normalized = normalize_item(item, network)
                if normalized: all_posts.append(normalized)
        except Exception as e:
            print(f"Error en {network}: {e}")
    return all_posts

def normalize_item(item, network):
    if network == "twitter":
        # SOLUCIÓN: Buscamos en la estructura 'legacy' que es donde X guarda el texto real
        legacy = item.get("legacy", {})
        text = legacy.get("full_text") or item.get("text") or item.get("full_text")
        author = item.get("user", {}).get("screen_name") or legacy.get("user_id_str")
        
        return {
            "id": str(item.get("id_str") or item.get("id")),
            "network": "twitter",
            "author": author or "Usuario de X",
            "text": text or "Ver contenido en el link original",
            "date": legacy.get("created_at") or datetime.datetime.now().isoformat(),
            "post_url": f"https://x.com/i/web/status/{item.get('id_str')}"
        }
    elif network == "instagram":
        return {
            "id": item.get("id"),
            "network": "instagram",
            "author": item.get("ownerUsername") or "Instagram User",
            "text": item.get("caption") or "Imagen/Video de Instagram",
            "date": item.get("timestamp") or datetime.datetime.now().isoformat(),
            "post_url": item.get("url")
        }
    return None
