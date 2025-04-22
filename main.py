from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from newspaper import Article
import requests
from typing import List

app = FastAPI()

# Optional: CORS support for frontend/mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to your app domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== CONFIG ======
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
RSS_FEED_URL = "https://english.onlinekhabar.com/feed"
MODEL_NAME = "llama3-8b-8192"  # or gemma-7b-it
MAX_ARTICLES = 10
# ====================

def extract_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.title, article.text[:1500]
    except:
        return None, None

def turn_into_comedy(title, content):
    prompt = f"""Rewrite this news story as a funny sarcastic article\n\nTitle: {title}\n\nContent: {content}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        data = response.json()

        # ✅ Improved error handling
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif "error" in data:
            print("❗ Groq API returned error:", data["error"])
            return f"❌ Groq Error: {data['error'].get('message', 'Unknown error')}"
        else:
            print("❗ Unexpected response from Groq:", data)
            return "⚠️ Unexpected API response. Please try again later."
    except Exception as e:
        print(f"Exception while calling Groq API: {e}")
        return "❌ Exception occurred while calling the comedy engine."

@app.get("/comedy")
def get_comedy_articles(count: int = Query(5, description="Number of news articles to convert")):
    feed = feedparser.parse(RSS_FEED_URL)
    entries = feed.entries[:min(count, len(feed.entries))]

    results = []

    for i, entry in enumerate(entries):
        title, content = extract_article(entry.link)

        if not content:
            results.append({
                "index": i,
                "error": "Failed to extract content"
            })
            continue

        comedy = turn_into_comedy(title, content)

        results.append({
            "index": i,
            "original_title": title,
            "original_content": content,
            "comedy_version": comedy
        })

    return results