import os
import re
import math
import random
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import wikipedia
from duckduckgo_search import DDGS

# If your files (chat.html, styles.css, app.js) are in the same folder as app.py,
# tell Flask to use current folder for templates/static.
app = Flask(__name__, static_folder='.', template_folder='.')
CORS(app)

# ---------------- Helpers ----------------
def basic_reply(msg):
    msg = msg.lower()
    if "who are you" in msg or "your name" in msg:
        return "I'm A.S.I.A 🤖 — your intelligent assistant developed by Pixel Studio. I can answer almost anything!"
    if "how are you" in msg:
        return "I'm doing great 😄 and ready to help you. What do you want to know?"
    if msg in ["hi","hii", "hiii", "hey", "hello", "hola"]:
        return random.choice(["Hey 👋", "Hi there!", "Hello!", "Hey, how can I help?"])
    return None

def fetch_from_duckduckgo(query):
    try:
        res = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
            timeout=6
        )
        data = res.json()
        if data.get("AbstractText"):
            return data["AbstractText"]
        if data.get("Answer"):
            return data["Answer"]
        if data.get("RelatedTopics"):
            for t in data["RelatedTopics"]:
                if isinstance(t, dict) and t.get("Text"):
                    return t["Text"]
        # fallback to DDGS text search
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            for r in results:
                if r.get("body"):
                    return r["body"]
                if r.get("title"):
                    return r["title"]
    except Exception as e:
        app.logger.error("DuckDuckGo error: %s", e)
    return None

def fetch_from_wiki(query):
    try:
        return wikipedia.summary(query, sentences=3, auto_suggest=True)
    except Exception as e:
        app.logger.error("Wiki error: %s", e)
        return None

def math_solver(msg):
    try:
        q = msg.lower()
        if re.match(r"^[\d\s\+\-\*\/\%\.\(\)]+$", q):
            # safe-ish eval (only arithmetic chars allowed by the regex)
            return f"The answer is {eval(q)}"
        if "square root" in q:
            found = re.findall(r"\d+(\.\d+)?", q)
            if found:
                n = float(found[0])
                return f"The square root of {n} is {math.sqrt(n):.4f}"
        if "cube root" in q:
            found = re.findall(r"\d+(\.\d+)?", q)
            if found:
                n = float(found[0])
                return f"The cube root of {n} is {n ** (1/3):.4f}"
    except Exception:
        pass
    return None

def get_best_answer(user_query):
    app.logger.info("Processing query: %s", user_query)
    msg = (user_query or "").strip()
    if not msg:
        return "Please send a question."

    base = basic_reply(msg)
    if base:
        return base

    math_res = math_solver(msg)
    if math_res:
        return math_res

    ddg_ans = fetch_from_duckduckgo(msg)
    if ddg_ans and len(ddg_ans) > 15:
        return ddg_ans

    wiki_ans = fetch_from_wiki(msg)
    if wiki_ans:
        return wiki_ans

    deeper = fetch_from_duckduckgo(f"explain {msg}")
    if deeper:
        return deeper

    return "I tried searching everywhere 🕵️‍♂️ but couldn’t find a solid answer. Try rephrasing or asking something else!"

# ---------------- Routes ----------------
# Serve main page (chat.html) at root
@app.route("/")
def index():
    # chat.html should be in same folder as app.py
    return render_template("index.html")

# Serve any static file in the same folder (styles.css, app.js, index.html etc.)
@app.route("/<path:filename>")
def serve_file(filename):
    return send_from_directory('.', filename)

# API endpoint used by frontend (POST /chat)
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"response": "Please type a question so I can reply!"})
        reply = get_best_answer(message)
        return jsonify({"response": reply})
    except Exception as e:
        app.logger.exception("Error in /chat:")
        return jsonify({"response": "Internal server error"}), 500

# ---------------- Run ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
