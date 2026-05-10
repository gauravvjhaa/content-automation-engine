import os
import sys

sys.path.append(os.path.dirname(__file__))

from flask import Flask, jsonify, request, render_template
from config import CLIENT_CONFIG, OUTPUT_LOG, GROQ_API_KEY
from trend_detector import login, fetch_posts, score_trend
from trend_filter import is_relevant
from content_generator import generate_posts, score_posts
from publisher import publish_post, log_publish
import pandas as pd
from datetime import datetime

app = Flask(__name__)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return app.make_default_options_response()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

def detect_with_config(keywords, product, voice):
    token = login()
    if not token:
        return []

    trends = []
    for keyword in keywords:
        posts = fetch_posts(token, keyword, 100)
        score = score_trend(posts)
        top_post = ""
        if posts:
            top = max(posts, key=lambda p: p.get("likeCount", 0) + p.get("repostCount", 0))
            top_post = top.get("record", {}).get("text", "")[:200]

        trends.append({
            "keyword": keyword,
            "post_count": len(posts),
            "score": score,
            "top_post": top_post,
            "detected_at": datetime.now().isoformat()
        })

    trends.sort(key=lambda x: x["score"], reverse=True)

    filtered = [t for t in trends[:3] if is_relevant(t, keywords)]
    if not filtered:
        filtered = trends[:1]
    return filtered

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/api/detect', methods=['POST'])
def api_detect():
    try:
        data = request.json or {}
        keywords = [k.strip() for k in data.get('keywords', '').split(',') if k.strip()]
        product = data.get('product', CLIENT_CONFIG['product_description'])
        voice = data.get('voice', CLIENT_CONFIG['brand_voice'])

        if not keywords:
            keywords = CLIENT_CONFIG['niche_keywords']

        trends = detect_with_config(keywords, product, voice)
        return jsonify({"success": True, "trends": trends})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        data = request.json or {}
        trends = data.get('trends', [])
        product = data.get('product', CLIENT_CONFIG['product_description'])
        voice = data.get('voice', CLIENT_CONFIG['brand_voice'])

        all_results = []
        for trend in trends:
            min_len = int(data.get('min_length', 100))
            max_len = int(data.get('max_length', 280))
            posts = generate_posts(trend, product_override=product, voice_override=voice, min_length=min_len, max_length=max_len)
            scored = score_posts(posts)
            if scored:
                best = scored[0]
                best["keyword"] = trend["keyword"]
                best["trend_score"] = trend["score"]
                all_results.append(best)

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return jsonify({"success": True, "posts": all_results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/publish', methods=['POST'])
def api_publish():
    try:
        data = request.json or {}
        post = data.get('post', {})
        uri = publish_post(post.get('text', ''))
        if uri:
            log_publish(post, uri)
            return jsonify({
                "success": True,
                "uri": uri,
                "profile": "https://bsky.app/profile/vishuyadav.bsky.social"
            })
        return jsonify({"success": False, "error": "Publish failed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/history', methods=['GET'])
def api_history():
    try:
        log_file = os.path.join(os.path.dirname(__file__), "../data/publish_log.csv")
        if os.path.exists(log_file):
            df = pd.read_csv(log_file)
            records = df.tail(10).to_dict('records')
            return jsonify({"success": True, "history": records})
        return jsonify({"success": True, "history": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/suggest-keywords', methods=['POST'])
def api_suggest_keywords():
    try:
        from groq import Groq
        data = request.json or {}
        product = data.get('product', '')
        groq_client = Groq(api_key=GROQ_API_KEY)
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"""Given this product description: "{product}"

Suggest exactly 7 trending social media search keywords that would be relevant to this product's target audience.
Return ONLY a comma-separated list of keywords, nothing else.
Example format: keyword1, keyword2, keyword3, keyword4, keyword5, keyword6, keyword7"""
            }],
            max_tokens=100,
            temperature=0.7
        )
        keywords = response.choices[0].message.content.strip()
        return jsonify({"success": True, "keywords": keywords})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)