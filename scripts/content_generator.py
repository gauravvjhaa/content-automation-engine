import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import GROQ_API_KEY, CLIENT_CONFIG, POSTS_PER_TREND
from groq import Groq
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

client = Groq(api_key=GROQ_API_KEY)
analyzer = SentimentIntensityAnalyzer()

def generate_posts(trend):
    keyword = trend["keyword"]
    top_post = trend["top_post"]
    product = CLIENT_CONFIG["product_description"]
    voice = CLIENT_CONFIG["brand_voice"]

    print(f"\n  Generating posts for: {keyword}")

    prompt = f"""You are a social media content expert. Generate {POSTS_PER_TREND} different social media posts.

TRENDING TOPIC: {keyword}
WHAT PEOPLE ARE SAYING: {top_post}
CLIENT PRODUCT: {product}
BRAND VOICE: {voice}

Requirements:
- Each post must be under 280 characters
- Each post should naturally connect the trending topic to the client's product
- Do NOT be salesy or pushy — be conversational and relevant
- Use 1-2 relevant hashtags per post
- Number each post clearly: POST 1:, POST 2:, POST 3:

Generate the posts now:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=600
    )

    raw = response.choices[0].message.content
    posts = parse_posts(raw)
    return posts

def parse_posts(raw_text):
    posts = []
    lines = raw_text.strip().split('\n')
    current_post = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("POST") and any(
            c.isdigit() for c in line[:8]
        ):
            if current_post:
                posts.append(' '.join(current_post).strip())
                current_post = []
            # Remove the POST X: prefix
            content = line.split(':', 1)[-1].strip()
            if content:
                current_post.append(content)
        else:
            if current_post is not None:
                current_post.append(line)

    if current_post:
        posts.append(' '.join(current_post).strip())

    return [p for p in posts if len(p) > 20]

def score_posts(posts):
    scored = []
    for post in posts:
        sentiment = analyzer.polarity_scores(post)
        length_score = 1.0 if 100 <= len(post) <= 250 else 0.7
        hashtag_score = 1.1 if '#' in post else 0.9
        engagement_score = (sentiment['compound'] + 1) / 2
        final_score = round(
            (length_score * 0.3) +
            (hashtag_score * 0.2) +
            (engagement_score * 0.5),
            3
        )
        scored.append({
            "text": post,
            "score": final_score,
            "length": len(post),
            "sentiment": sentiment['compound']
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

def generate_for_trends(trends):
    print("\n" + "="*55)
    print("Content Generation Engine")
    print("="*55)

    all_results = []

    for trend in trends:
        posts = generate_posts(trend)
        scored = score_posts(posts)

        print(f"\n  Generated {len(scored)} posts for '{trend['keyword']}':")
        for i, p in enumerate(scored, 1):
            print(f"\n  Post {i} (score: {p['score']}):")
            print(f"  {p['text']}")
            print(f"  Length: {p['length']} chars | Sentiment: {p['sentiment']}")

        if scored:
            best = scored[0]
            best["keyword"] = trend["keyword"]
            best["trend_score"] = trend["score"]
            all_results.append(best)

    # Pick the single best post overall
    all_results.sort(key=lambda x: x["score"], reverse=True)

    print("\n" + "="*55)
    print("BEST POST SELECTED FOR PUBLISHING:")
    print("="*55)
    print(f"\nKeyword: {all_results[0]['keyword']}")
    print(f"Post: {all_results[0]['text']}")
    print(f"Score: {all_results[0]['score']}")

    return all_results

if __name__ == "__main__":
    from trend_detector import detect_trends
    from trend_filter import filter_trends

    trends = detect_trends()
    filtered = filter_trends(trends)
    results = generate_for_trends(filtered)