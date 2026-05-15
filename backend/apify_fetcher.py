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
            
        # Common inputs (simplified, each actor might need specific mapping)
        run_input = {}
        
        if network == "twitter":
            run_input = {
                "searchTerms": keywords + [f"#{h}" for h in hashtags],
                "twitterHandles": accounts,
                "maxItems": 20,
                "since": date_since
            }
        elif network == "instagram":
            run_input = {
                "hashtags": hashtags,
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
                # Normalize post structure
                normalized_post = normalize_item(item, network)
                if normalized_post:
                    all_posts.append(normalized_post)
        except Exception as e:
            print(f"Error fetching from {network}: {e}")
            
    return all_posts

def normalize_item(item, network):
    """
    Normalizes different actor outputs to SMATA Post model
    """
    if network == "twitter":
        return {
            "id": item.get("id_str") or item.get("id"),
            "network": "twitter",
            "author": item.get("user", {}).get("screen_name", "Unknown"),
            "author_url": f"https://x.com/{item.get('user', {}).get('screen_name')}",
            "text": item.get("full_text") or item.get("text"),
            "date": item.get("created_at"),
            "post_url": f"https://x.com/status/{item.get('id_str')}",
        }
    elif network == "instagram":
        return {
            "id": item.get("id"),
            "network": "instagram",
            "author": item.get("ownerUsername", "Unknown"),
            "author_url": f"https://instagram.com/{item.get('ownerUsername')}",
            "text": item.get("caption"),
            "date": item.get("timestamp"),
            "post_url": item.get("url"),
        }
    elif network == "tiktok":
            return {
                "id": item.get("id"),
                "network": "tiktok",
                "author": item.get("authorMeta", {}).get("name") or item.get("authorMeta", {}).get("nickName", "Unknown"),
                "author_url": f"https://www.tiktok.com/@{item.get('authorMeta', {}).get('name')}",
                "text": item.get("text", ""),
                "date": str(item.get("createTime")),
                "post_url": item.get("webVideoUrl"),
                "video_url": item.get("videoUrl")
            }
    return None
