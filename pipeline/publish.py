"""
Publish an article to Dev.to via their API.
Docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
"""
import os
import requests

DEVTO_API = "https://dev.to/api/articles"


def publish(title: str, body: str, tags: list[str], published: bool = True) -> dict:
    api_key = os.environ["DEVTO_API_KEY"]
    payload = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": published,
            "tags": tags[:4],  # Dev.to max 4 tags
        }
    }
    response = requests.post(
        DEVTO_API,
        json=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "id": data["id"],
        "url": data["url"],
        "title": data["title"],
    }
