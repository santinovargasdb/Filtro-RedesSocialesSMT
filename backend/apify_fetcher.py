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
            search_terms = keywords + [f"#{h}" for h in hashtags]
            run_input = {
                "searchTerms": search_terms,
                "twitterHandles": accounts,
                "maxItems": 20,
                "since": date_since,
                "lang": "es"
            }

        elif network == "instagram":
            # ✅ FIX: el actor necesita URLs completas, no hashtags sueltos
            direct_urls = [
                f"https://www.instagram.com/explore/tags/{h}/"
                for h in hashtags
            ]
            # También agregar perfiles si hay accounts
            for acc in accounts:
                direct_urls.append(f"https://www.instagram.com/{acc}/")
            
            if not direct_urls:
                print("Instagram: no hay hashtags ni cuentas, saltando.")
                continue

            run_input = {
                "directUrls": direct_urls,
                "resultsType": "posts",
                "resultsLimit": 20,
                "addParentData": False
            }

        elif network == "tiktok":
            # ✅ FIX: el actor necesita searchQueries o hashtags, no solo profiles
            run_input = {
                "searchQueries": keywords + hashtags,
                "maxItems": 20,
            }
            # Agregar perfiles solo si hay
            if accounts:
                run_input["profiles"] = [
                    f"https://www.tiktok.com/@{acc}" for acc in accounts
                ]

        print(f"DEBUG: Intentando {network} con: {run_input}")

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
    if network == "twitter":
        # ✅ FIX: apidojo/tweet-scraper anida el texto en item["legacy"]
        legacy = item.get("legacy", {})
        user = item.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {})
        
        text = legacy.get("full_text") or item.get("full_text") or item.get("text", "")
        author = user.get("screen_name") or item.get("author_id", "unknown")
        tweet_id = legacy.get("id_str") or item.get("id_str") or item.get("id", "")
        created_at = legacy.get("created_at") or item.get("created_at", "")

        if not text:
            return None

        return {
            "id": str(tweet_id),
            "network": "twitter",
            "author": author,
            "author_url": f"https://x.com/{author}",
            "text": text,
            "date": created_at,
            "post_url": f"https://x.com/{author}/status/{tweet_id}",
        }

    elif network == "instagram":
        caption = item.get("caption") or item.get("alt") or ""
        return {
            "id": str(item.get("id", "")),
            "network": "instagram",
            "author": item.get("ownerUsername") or item.get("username", "unknown"),
            "author_url": f"https://instagram.com/{item.get('ownerUsername', '')}",
            "text": caption,
            "date": item.get("timestamp", ""),
            "post_url": item.get("url") or item.get("shortCode", ""),
        }

    elif network == "tiktok":
        author_meta = item.get("authorMeta", {})
        author = author_meta.get("name") or author_meta.get("nickName", "unknown")
        return {
            "id": str(item.get("id", "")),
            "network": "tiktok",
            "author": author,
            "author_url": f"https://www.tiktok.com/@{author}",
            "text": item.get("text", ""),
            "date": str(item.get("createTime", "")),
            "post_url": item.get("webVideoUrl", ""),
            "video_url": item.get("videoUrl")
        }

    return None
