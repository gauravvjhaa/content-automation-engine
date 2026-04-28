import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import CLIENT_CONFIG

IRRELEVANT_INDICATORS = [
    "spam", "follow back", "giveaway", "click here",
    "buy now", "discount", "promo", "free followers",
    "dm for", "link in bio only"
]

def is_relevant(trend):
    keyword = trend["keyword"].lower()
    top_post = trend["top_post"].lower()
    score = trend["score"]

    # Filter out low engagement
    if score < 50:
        print(f"  Filtered out '{trend['keyword']}' — low score ({score})")
        return False

    # Filter out spam indicators
    for indicator in IRRELEVANT_INDICATORS:
        if indicator in top_post:
            print(f"  Filtered out '{trend['keyword']}' — spam detected")
            return False

    # Filter out if keyword not matching niche
    niche_words = [k.lower() for k in CLIENT_CONFIG["niche_keywords"]]
    if not any(word in keyword for word in niche_words):
        if score < 200:
            print(f"  Filtered out '{trend['keyword']}' — low relevance")
            return False

    return True

def filter_trends(trends):
    print("\n" + "="*55)
    print("Niche Filtering and Ranking")
    print("="*55)

    print(f"\nFiltering {len(trends)} trends for niche relevance...")
    filtered = [t for t in trends if is_relevant(t)]

    if not filtered:
        print("No trends passed filtering — using top trend anyway")
        filtered = trends[:1]

    # Final ranking by score
    filtered.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n{len(filtered)} trends passed filtering:")
    for i, t in enumerate(filtered, 1):
        print(f"  {i}. {t['keyword']} — score: {t['score']}")
        print(f"     Top post preview: {t['top_post'][:100]}...")

    return filtered

if __name__ == "__main__":
    # Test with mock data
    from trend_detector import detect_trends
    trends = detect_trends()
    filtered = filter_trends(trends)