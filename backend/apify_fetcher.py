from apify_client import ApifyClient
from config import APIFY_API_KEY, APIFY_ACTORS

client = ApifyClient(APIFY_API_KEY)


def compute_score(text: str, keywords: list, hashtags: list) -> tuple[int, list]:
    """Calcula relevance_score y matched_terms en base al texto del post."""
    if not text:
        return 0, []

    text_lower = text.lower()
    matched = []

    for kw in keywords:
        if kw.lower() in text_lower:
            matched.append(kw)

    for ht in hashtags:
        ht_clean = ht.lstrip("#").lower()
        if ht_clean in text_lower or f"#{ht_clean}" in text_lower:
            matched.append(f"#{ht_clean}")

    total_terms = len(keywords) + len(hashtags)
    if total_terms == 0:
        score = 50
    else:
        score = min(100, int((len(matched) / total_terms) * 100))
        if score == 0 and matched:
            score = 30

    return score, matched


def fetch_posts(networks, keywords, hashtags, accounts, date_since):
    all_posts = []
    hashtags_clean = [h.lstrip("#") for h in hashtags]

    for network in networks:
        actor_id = APIFY_ACTORS.get(network)
        if not actor_id:
            continue

        run_input = {}

        if network == "twitter":
            search_list = keywords + [f"#{h}" for h in hashtags_clean]
            run_input = {
                "searchTerms": search_list,
                "maxItems": 3  # LÍMITE BAJO CONTROLADO (Ahorro crítico de saldo)
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
                "resultsLimit": 10
            }

       elif network == "tiktok":
    # Combinar keywords y hashtags en un solo término de búsqueda
    search_terms = keywords + hashtags_clean
    if not search_terms:
        print("TikTok: no hay keywords ni hashtags, saltando.")
        continue

    run_input = {
        "keyword": search_terms[0],  # TikTok solo acepta un keyword a la vez
        "maxItems": 10
    }
    if accounts:
        run_input["profiles"] = [
            f"https://www.tiktok.com/@{acc.lstrip('@')}" for acc in accounts
        ]

        print(f"DEBUG: Intentando {network} con: {run_input}")

        try:
            run = client.actor(actor_id).call(run_input=run_input)
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                normalized_post = normalize_item(item, network, keywords, hashtags_clean)
                if normalized_post:
                    all_posts.append(normalized_post)
        except Exception as e:
            print(f"Error fetching from {network}: {e}")

    return all_posts


def normalize_item(item, network, keywords=None, hashtags=None):
    keywords = keywords or []
    hashtags = hashtags or []

    if network == "twitter":
        legacy = item.get("legacy", {})
        user = item.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {})

        text = legacy.get("full_text") or item.get("full_text") or item.get("text", "")
        author = user.get("screen_name") or item.get("author_id", "unknown")
        tweet_id = legacy.get("id_str") or item.get("id_str") or item.get("id", "")
        created_at = legacy.get("created_at") or item.get("created_at", "")

        if not text:
            return None

        score, matched = compute_score(text, keywords, hashtags)

        return {
            "id": str(tweet_id),
            "network": "twitter",
            "author": author,
            "author_url": f"https://x.com/{author}",
            "text": text,
            "date": created_at,
            "post_url": f"https://x.com/{author}/status/{tweet_id}",
            "relevance_score": score,
            "matched_terms": matched,
        }

    elif network == "instagram":
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

        score, matched = compute_score(caption, keywords, hashtags)

        return {
            "id": str(item.get("id", "")),
            "network": "instagram",
            "author": owner,
            "author_url": f"https://instagram.com/{owner}",
            "text": caption,
            "date": str(timestamp),
            "post_url": url,
            "relevance_score": score,
            "matched_terms": matched,
        }

    elif network == "tiktok":
        author_meta = item.get("authorMeta", {})
        author = author_meta.get("name") or author_meta.get("nickName", "unknown")
        text = item.get("text", "")

        score, matched = compute_score(text, keywords, hashtags)

        return {
            "id": str(item.get("id", "")),
            "network": "tiktok",
            "author": author,
            "author_url": f"https://www.tiktok.com/@{author}",
            "text": text,
            "date": str(item.get("createTime", "")),
            "post_url": item.get("webVideoUrl", ""),
            "video_url": item.get("videoUrl"),
            "relevance_score": score,
            "matched_terms": matched,
        }

    return None
