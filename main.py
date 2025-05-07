from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from newspaper import Article
import requests
from typing import List
import random
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== CONFIG ======
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

HUGGINGFACE_API_KEY = "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"  # <== Replace with your Hugging Face token
IMAGE_MODEL = "stabilityai/stable-diffusion-2"

RSS_FEED_URLS = [
    "https://english.onlinekhabar.com/feed",
    "http://english.ratopati.com/rss/",
    "https://techmandu.com/feed/"
]

AI_MODELS = ["llama3-8b-8192", "gemma2-9b-it"]

MAX_ARTICLES = 15
# ====================

def extract_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.title, article.text[:1500]
    except:
        return None, None

def turn_into_comedy(title, content, model_name):
    prompt = f"""Rewrite this news story as a short funny sarcastic summary\n\nTitle: {title}\n\nContent: {content}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        data = response.json()

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

def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": prompt
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            image_bytes = response.content
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return image_base64
        else:
            print(f"Image Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception while generating image: {e}")
        return None

@app.get("/comedy")
def get_comedy_articles(count: int = Query(10, description="Number of news articles to convert")):
    all_entries = []

    for feed_url in RSS_FEED_URLS:
        feed = feedparser.parse(feed_url)
        all_entries.extend(feed.entries)

    random.shuffle(all_entries)
    selected_entries = all_entries[:min(count, len(all_entries))]

    results = []

    for i, entry in enumerate(selected_entries):
        title, content = extract_article(entry.link)

        if not content:
            results.append({
                "index": i,
                "error": "Failed to extract content"
            })
            continue

        selected_model = random.choice(AI_MODELS)
        comedy = turn_into_comedy(title, content, selected_model)
        image_base64 = generate_image(title)

        results.append({
            "index": i,
            "original_title": title,
            "original_content": content,
            "comedy_version": comedy,
            "model_used": selected_model,
            "image_base64": image_base64,
            "source": entry.link
        })

    return results
