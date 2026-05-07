from flask import Flask, render_template, jsonify, request
import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import CLIENT_CONFIG, OUTPUT_LOG
from trend_detector import login, fetch_posts, score_trend
from trend_filter import is_relevant
from content_generator import generate_posts, score_posts
from publisher import publish_post, log_publish
import pandas as pd
from datetime import datetime

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

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

@app.route('/')
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
        data = request.json
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
        data = request.json
        post = data.get('post', {})
        uri = publish_post(post['text'])
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)