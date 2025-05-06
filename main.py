from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from newspaper import Article
import requests
from typing import List
import random

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== CONFIG ====
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
STABILITY_API_KEY = "sk-CmryB7ap0s3JtoW6oKtHQnJN9mN6sUpphZDtzt8qChiYuwSt"
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

RSS_FEED_URLS = [
    "https://english.onlinekhabar.com/feed",
    "http://english.ratopati.com/rss/",
    "https://techmandu.com/feed/"
]

AI_MODELS = ["llama3-8b-8192", "gemma2-9b-it"]
MAX_ARTICLES = 15
# ================

def extract_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.title, article.text[:1500]
    except:
        return None, None

def turn_into_comedy(title, content, model_name):
    prompt = f"""Rewrite this news story as a funny sarcastic summary.\n\nTitle: {title}\n\nContent: {content}"""

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
            return f"❌ Groq Error: {data['error'].get('message', 'Unknown error')}"
        else:
            return "⚠️ Unexpected API response."
    except Exception as e:
        return f"❌ Exception occurred: {e}"

def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": 7,
        "clip_guidance_preset": "FAST_BLUE",
        "height": 512,
        "width": 512,
        "samples": 1,
        "steps": 30
    }

    try:
        response = requests.post(STABILITY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Return image URL or base64
        if result.get("artifacts"):
            base64_img = result["artifacts"][0]["base64"]
            return f"data:image/png;base64,{base64_img}"
        else:
            return "❌ Failed to generate image"
    except Exception as e:
        return f"❌ Stability AI error: {e}"

@app.get("/comedy")
def get_comedy_articles(count: int = Query(10, description="Number of articles")):
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
            results.append({"index": i, "error": "Failed to extract content"})
            continue

        selected_model = random.choice(AI_MODELS)
        comedy = turn_into_comedy(title, content, selected_model)

        # Generate image based on comedy content
        image_data = generate_image(comedy[:100])  # Limit prompt length

        results.append({
            "index": i,
            "original_title": title,
            "original_content": content,
            "comedy_version": comedy,
            "image": image_data,
            "model_used": selected_model,
            "source": entry.link
        })

    return results
