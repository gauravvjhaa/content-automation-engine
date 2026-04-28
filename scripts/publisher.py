import requests
import sys
import os
import csv
import json
from datetime import datetime
sys.path.append(os.path.dirname(__file__))
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD, OUTPUT_LOG

def login():
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    r = requests.post(url, json={
        "identifier": BLUESKY_HANDLE,
        "password": BLUESKY_APP_PASSWORD
    })
    if r.status_code == 200:
        data = r.json()
        return data["accessJwt"], data["did"]
    print(f"Login failed: {r.status_code}")
    return None, None

def publish_post(text):
    token, did = login()
    if not token:
        return None

    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        }
    }

    r = requests.post(url, headers=headers, json=payload)

    if r.status_code == 200:
        data = r.json()
        uri = data.get("uri", "")
        print(f"\nPost published successfully!")
        print(f"URI: {uri}")
        return uri
    else:
        print(f"Publish failed: {r.status_code}")
        print(r.text)
        return None

def log_publish(post_data, uri):
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.exists(OUTPUT_LOG)

    with open(OUTPUT_LOG, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "published_at", "keyword", "text",
            "score", "sentiment", "uri"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "published_at": datetime.now().isoformat(),
            "keyword": post_data.get("keyword", ""),
            "text": post_data.get("text", ""),
            "score": post_data.get("score", ""),
            "sentiment": post_data.get("sentiment", ""),
            "uri": uri or ""
        })
    print(f"Logged to {OUTPUT_LOG}")

def run_publisher(best_post, dry_run=False):
    print("\n" + "="*55)
    print("Auto Publisher")
    print("="*55)

    print(f"\nPost to publish:")
    print(f"  {best_post['text']}")
    print(f"  Characters: {len(best_post['text'])}")
    print(f"  Keyword: {best_post['keyword']}")
    print(f"  Score: {best_post['score']}")

    if dry_run:
        print("\nDRY RUN MODE — post not actually published")
        print("Set dry_run=False to publish for real")
        return

    confirm = input("\nPublish this post? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Publishing cancelled.")
        return

    uri = publish_post(best_post["text"])
    if uri:
        log_publish(best_post, uri)
        print("\nFull pipeline complete!")
        print(f"Post is live at: https://bsky.app/profile/{BLUESKY_HANDLE}")

if __name__ == "__main__":
    from trend_detector import detect_trends
    from trend_filter import filter_trends
    from content_generator import generate_for_trends

    trends = detect_trends()
    filtered = filter_trends(trends)
    results = generate_for_trends(filtered)

    if results:
        run_publisher(results[0], dry_run=False)