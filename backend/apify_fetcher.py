from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime

client = ApifyClient(APIFY_API_KEY)

def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    
    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id:
            continue
            
        run_input = {}
        
        if network == "twitter":
            run_input = {
                "searchTerms": keywords + [f"#{h}" for h in hashtags],
                "twitterHandles": accounts,
                "maxItems": 20,
                "since": date_since
            }
        elif network == "instagram":
            # Corrección: Instagram Scraper necesita URLs directas para los hashtags
            start_urls = [{"url": f"https://www.instagram.com/explore/tags/{h}/"} for h in hashtags]
            run_input = {
                "directUrls": start_urls,
                "resultsLimit": 20
            }
        elif network == "tiktok":
            run_input = {
                "resultsPerPage": 20,
                "profiles": accounts
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
    """
    Normaliza las salidas de diferentes actores al modelo de SMATA Post
    """
    if network == "twitter":
        # Intentar obtener el nombre de usuario de varias ubicaciones posibles en el JSON
        user_data = item.get("user", {})
        author = user_data.get("screen_name") or item.get("screen_name") or "Usuario de X"
        
        return {
            "id": str(item.get("id_str") or item.get("id")),
            "network": "twitter",
            "author": author,
            "author_url": f"https://x.com/{author}",
            "text": item.get("full_text") or item.get("text") or "Sin contenido",
            "date": item.get("created_at"),
            "post_url": f"https://x.com/i/web/status/{item.get('id_str') or item.get('id')}",
        }
    elif network == "instagram":
        return {
            "id": item.get("id"),
            "network": "instagram",
            "author": item.get("ownerUsername") or item.get("ownerFullName") or "Usuario de Instagram",
            "author_url": f"https://instagram.com/{item.get('ownerUsername')}",
            "text": item.get("caption") or "Sin descripción",
            "date": item.get("timestamp"), 
            "post_url": item.get("url"),
        }
    elif network == "tiktok":
        author_meta = item.get("authorMeta", {})
        author = author_meta.get("name") or author_meta.get("nickName") or "Usuario de TikTok"
        
        # Convertir timestamp de TikTok a formato ISO para evitar el error de 1969
        date_val = item.get("createTime")
        if date_val:
            try:
                formatted_date = datetime.datetime.fromtimestamp(int(date_val)).isoformat()
            except:
                formatted_date = str(date_val)
        else:
            formatted_date = None

        return {
            "id": item.get("id"),
            "network": "tiktok",
            "author": author,
            "author_url": f"https://www.tiktok.com/@{author}",
            "text": item.get("text") or "Sin descripción",
            "date": formatted_date,
            "post_url": item.get("webVideoUrl"),
            "video_url": item.get("videoUrl")
        }
    return None
