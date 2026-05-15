from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime
import dateutil.parser # Asegurate de tener python-dateutil en requirements.txt

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
                "maxItems": 15,
                "since": date_since
            }
        elif network == "instagram":
            start_urls = [{"url": f"https://www.instagram.com/explore/tags/{h}/"} for h in hashtags]
            run_input = {"directUrls": start_urls, "resultsLimit": 15}
        
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
        # Buscamos el texto en todos los lugares posibles donde Twitter lo guarda
        text = item.get("full_text") or item.get("text") or item.get("description")
        if not text and "legacy" in item:
            text = item["legacy"].get("full_text")
        
        # Buscamos el usuario
        user_data = item.get("user", {})
        author = user_data.get("screen_name") or item.get("screen_name")
        if not author and "core" in item: # Estructura nueva de algunos actores
            author = item["core"]["user_results"]["result"]["legacy"].get("screen_name")

        # Limpieza de fecha para evitar el 1969
        raw_date = item.get("created_at") or item.get("createdAt")
        try:
            clean_date = dateutil.parser.parse(raw_date).isoformat()
        except:
            clean_date = datetime.datetime.now().isoformat()

        return {
            "id": str(item.get("id_str") or item.get("id")),
            "network": "twitter",
            "author": author or "Usuario de X",
            "author_url": f"https://x.com/{author}" if author else "#",
            "text": text or "Post informativo (ver original)",
            "date": clean_date,
            "post_url": f"https://x.com/i/web/status/{item.get('id_str') or item.get('id')}",
        }
    # (Mantené el resto de instagram y tiktok igual que antes)
    return None
