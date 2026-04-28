from flask import Flask, render_template, jsonify, request
import sys
import os
sys.path.append(os.path.dirname(__file__))
from trend_detector import detect_trends
from trend_filter import filter_trends
from content_generator import generate_for_trends
from publisher import publish_post, log_publish
import pandas as pd
from datetime import datetime

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/detect', methods=['GET'])
def api_detect():
    try:
        trends = detect_trends()
        filtered = filter_trends(trends)
        return jsonify({
            "success": True,
            "trends": filtered
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        data = request.json
        trends = data.get('trends', [])
        results = generate_for_trends(trends)
        return jsonify({
            "success": True,
            "posts": results
        })
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