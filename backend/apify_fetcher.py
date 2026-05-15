from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS
import datetime

client = ApifyClient(APIFY_API_KEY)

def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    
    # Limpiar # si el frontend los manda incluidos
    hashtags_clean = [h.lstrip("#") for h in hashtags]

    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id:
            continue

        run_input = {}

        if network == "twitter":
            run_input = {
                "searchTerms": keywords + [f"#{h}" for h in hashtags_clean],
                "maxTweets": 20,
                "since": date_since,
                "lang": "es"
            }

        elif network == "instagram":
            start_urls = [
                {"url": f"https://www.instagram.com/explore/tags/{h}/"}
                for h in hashtags_clean
            ]
            for acc in accounts:
                start_urls.append({"url": f"https://www.instagram.com/{acc.lstrip('@')}/"})

            if not start_urls:
                print("Instagram: no hay hashtags ni cuentas, saltando.")
                continue

            run_input = {
                "startUrls": start_urls,
                "resultsLimit": 20
            }

        elif network == "tiktok":
            run_input = {
                "hashtags": hashtags_clean,
                "maxItems": 20
            }
            if keywords:
                run_input["keyword"] = keywords[0]
            if accounts:
                run_input["profiles"] = [
                    f"https://www.tiktok.com/@{acc.lstrip('@')}" for acc in accounts
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
        # DEBUG TEMPORAL - borrar después de confirmar la estructura
        print(f"DEBUG INSTAGRAM ITEM KEYS: {list(item.keys())}")
        print(f"DEBUG INSTAGRAM ITEM: {item}")

        caption = item.get("caption") or item.get("alt") or item.get("text") or ""
        owner = (
            item.get("ownerUsername") or
            item.get("username") or
            item.get("owner", {}).get("username") or
            "unknown"
        )
        timestamp = (
            item.get("timestamp") or
            item.get("taken_at_timestamp") or
            item.get("date") or
            ""
        )
        short_code = item.get("shortCode") or item.get("shortcode") or ""
        url = (
            item.get("url") or
            item.get("displayUrl") or
            (f"https://instagram.com/p/{short_code}" if short_code else "")
        )

        return {
            "id": str(item.get("id", "")),
            "network": "instagram",
            "author": owner,
            "author_url": f"https://instagram.com/{owner}",
            "text": caption,
            "date": timestamp,
            "post_url": url,
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
