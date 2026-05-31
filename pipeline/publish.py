"""
Publish an article to Dev.to via their API.
Docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
"""
import os
import re
import requests

DEVTO_API = "https://dev.to/api/articles"
SERIES_NAME = "Building with Claude API"
DEVTO_USERNAME = "syncore"


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug[:80]


def publish(title: str, body: str, tags: list[str], published: bool = True) -> dict:
    api_key = os.environ["DEVTO_API_KEY"]

    ai_keywords = ["claude", "ai", "llm", "api", "python", "agent", "prompt", "gpt"]
    in_series = any(kw in title.lower() for kw in ai_keywords)

    slug = _slugify(title)
    canonical_url = f"https://dev.to/{DEVTO_USERNAME}/{slug}"

    payload = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": published,
            "tags": tags[:4],
            "description": title,
            "canonical_url": canonical_url,
        }
    }
    if in_series:
        payload["article"]["series"] = SERIES_NAME

    response = requests.post(
        DEVTO_API,
        json=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    print(f"Title: {data['title']}")
    print(f"Published: {data['url']}")
    return {
        "id": data["id"],
        "url": data["url"],
        "title": data["title"],
    }
