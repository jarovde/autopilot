"""
Publish an article to Dev.to via their API.
Docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
"""
import os
import requests

DEVTO_API = "https://dev.to/api/articles"
SERIES_NAME = "Building with Claude API"


def publish(title: str, body: str, tags: list[str], published: bool = True) -> dict:
    api_key = os.environ["DEVTO_API_KEY"]

    ai_keywords = ["claude", "ai", "llm", "api", "python", "agent", "prompt", "gpt"]
    in_series = any(kw in title.lower() for kw in ai_keywords)

    # GEEN canonical_url. Die stond hier als f"https://dev.to/{user}/{slug}",
    # maar Dev.to hangt zelf een random suffix aan de slug (…-4e23), dus die
    # URL bestaat niet. Een canonical naar een 404 vertelt Google dat DIT niet
    # de echte pagina is — precies het tegenovergestelde van de SEO waar deze
    # pipeline voor bestaat. canonical_url hoort alleen bij cross-posten vanaf
    # je eigen blog; een native Dev.to-artikel canonicaliseert zichzelf.
    payload = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": published,
            "tags": tags[:4],
            "description": title,
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
