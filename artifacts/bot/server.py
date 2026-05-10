"""
Flask keep-alive server for Render free web service.
This keeps the bot running 24/7 by providing an HTTP endpoint.
"""
import threading
import os
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)
START_TIME = datetime.now()


@app.route("/")
def home():
    uptime = datetime.now() - START_TIME
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    return jsonify({
        "status": "online",
        "bot": "Netflix Kingdom",
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "message": "🎬 Netflix Kingdom Bot is running!",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "bot": "Netflix Kingdom"})


@app.route("/ping")
def ping():
    return "pong", 200


def run_flask():
    port = int(os.environ.get("BOT_PORT", 6000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def start_flask_thread():
    """Start Flask in a background thread."""
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    return t
