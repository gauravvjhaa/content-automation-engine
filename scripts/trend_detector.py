import requests
import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD, CLIENT_CONFIG, TREND_FETCH_LIMIT
from collections import Counter
from datetime import datetime

def login():
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    r = requests.post(url, json={
        "identifier": BLUESKY_HANDLE,
        "password": BLUESKY_APP_PASSWORD
    })
    if r.status_code == 200:
        print("Bluesky login successful")
        return r.json()["accessJwt"]
    else:
        print(f"Login failed: {r.status_code}")
        return None

def fetch_posts(token, keyword, limit=100):
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
    params = {"q": keyword, "limit": limit}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 200:
        return r.json().get("posts", [])
    return []

def score_trend(posts):
    if not posts:
        return 0
    total_engagement = sum(
        p.get("likeCount", 0) +
        p.get("repostCount", 0) * 2 +
        p.get("replyCount", 0) * 1.5
        for p in posts
    )
    velocity = len(posts)
    score = (total_engagement * 0.7) + (velocity * 0.3)
    return round(score, 2)

def detect_trends():
    print("\n" + "="*55)
    print("Trend Detection Engine")
    print("="*55)

    token = login()
    if not token:
        return []

    keywords = CLIENT_CONFIG["niche_keywords"]
    trends = []

    print(f"\nScanning {len(keywords)} keywords...")

    for keyword in keywords:
        posts = fetch_posts(token, keyword, TREND_FETCH_LIMIT)
        score = score_trend(posts)

        # Get top post text as trend context
        top_post = ""
        if posts:
            top = max(posts,
                      key=lambda p: p.get("likeCount", 0) +
                      p.get("repostCount", 0))
            top_post = top.get("record", {}).get("text", "")[:200]

        trend = {
            "keyword": keyword,
            "post_count": len(posts),
            "score": score,
            "top_post": top_post,
            "detected_at": datetime.now().isoformat()
        }
        trends.append(trend)
        print(f"  {keyword}: {len(posts)} posts, score={score}")

    # Sort by score
    trends.sort(key=lambda x: x["score"], reverse=True)

    print(f"\nTop 3 trending topics:")
    for i, t in enumerate(trends[:3], 1):
        print(f"  {i}. {t['keyword']} (score: {t['score']})")

    return trends[:3]

if __name__ == "__main__":
    trends = detect_trends()