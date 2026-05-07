import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import GROQ_API_KEY, CLIENT_CONFIG, POSTS_PER_TREND
from groq import Groq
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

client = Groq(api_key=GROQ_API_KEY)
analyzer = SentimentIntensityAnalyzer()

def generate_posts(trend, product_override=None, voice_override=None, min_length=100, max_length=280):
    keyword = trend["keyword"]
    top_post = trend["top_post"]
    product = product_override or CLIENT_CONFIG["product_description"]
    voice = voice_override or CLIENT_CONFIG["brand_voice"]

    print(f"\n  Generating posts for: {keyword}")

    length_instruction = f"Each post must be between {min_length} and {max_length} characters."

    prompt = f"""You are a sharp, witty social media writer — not a corporate bot. You write like a real person who actually cares about the topic.

TRENDING TOPIC RIGHT NOW: {keyword}
WHAT REAL PEOPLE ARE SAYING: {top_post}
CLIENT PRODUCT: {product}
BRAND VOICE: {voice}

YOUR TASK: Write {POSTS_PER_TREND} completely different social media posts. Each one must:
- Sound like a real human wrote it — no corporate fluff, no "In today's fast-paced world", no "It's clear that"
- Actually reference the specific trend context above — not just the keyword
- Naturally weave in the client product without being pushy or salesy
- Have a distinct angle: Post 1 = punchy and bold, Post 2 = conversational question, Post 3 = storytelling or insight
- Use 1-2 relevant hashtags that feel organic, not forced
- {length_instruction}

BANNED PHRASES (never use these): "In today's world", "It's no secret", "game-changer", "revolutionize", "leverage", "unlock your potential", "fast-paced", "It's clear that", "Now more than ever"

Number each post: POST 1:, POST 2:, POST 3:

Write them now — make them feel real:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=2400
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