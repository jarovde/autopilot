"""
Generate a full Dev.to-ready article using Google Gemini (free tier).
Returns: {"title": str, "body": str, "tags": list[str]}
"""
import os
import json
import re
import urllib.request

from pipeline.model_facts import MODEL_FACTS, repair, assert_current

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

PROMPT = """You are an expert technical writer for developers. Write engaging,
practical articles that rank on Google and get read on Dev.to.
Always include working code examples. Be direct and useful — no fluff.

{model_facts}

Write a complete Dev.to article about: {topic}

Requirements:
- 600-900 words
- At least 2 code blocks with real, working code
- Practical takeaways, friendly but expert tone
- End with a call to action

Respond in exactly this format — no extra text before or after:

TITLE: your title here
TAGS: tag1,tag2,tag3,tag4
BODY:
full markdown article body here"""



def _optimize_tags(topic: str, generated_tags: list) -> list:
    """Override generated tags with high-reach Dev.to tags based on topic."""
    t = topic.lower()
    if any(k in t for k in ["claude", "anthropic", "llm", "agent", "prompt", "mcp"]):
        return ["ai", "claude", "python", "tutorial"]
    if any(k in t for k in ["api", "chatbot", "openai", "gpt"]):
        return ["ai", "python", "api", "tutorial"]
    if any(k in t for k in ["fastapi", "flask", "django", "async", "python"]):
        return ["python", "webdev", "programming", "tutorial"]
    if any(k in t for k in ["passive", "income", "saas", "gumroad", "monetize"]):
        return ["career", "productivity", "programming", "ai"]
    if any(k in t for k in ["github", "automation", "pipeline", "cron"]):
        return ["devops", "automation", "python", "ai"]
    return generated_tags[:4]

def generate_article(topic: str, affiliate_links: dict) -> dict:
    api_key = os.environ["GEMINI_API_KEY"]
    payload = json.dumps({
        "contents": [
            {"parts": [{"text": PROMPT.format(topic=topic, model_facts=MODEL_FACTS)}]}
        ],
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.7},
    }).encode()
    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    lines = text.split("\n")
    title = next(l.removeprefix("TITLE:").strip() for l in lines if l.startswith("TITLE:"))
    tags_raw = next(l.removeprefix("TAGS:").strip() for l in lines if l.startswith("TAGS:"))
    tags = [t.strip() for t in tags_raw.split(",")][:4]
    tags = _optimize_tags(topic, tags)
    body_start = text.index("BODY:") + len("BODY:")
    body = text[body_start:].strip()

    # Vangnet achter de prompt-feiten. De prompt houdt Gemini meestal bij de
    # les, maar niet altijd — het artikel van 10 aug ging mis in de TITEL, dus
    # die gaat hier net zo goed doorheen als de body.
    title, title_fixes = repair(title)
    body, body_fixes = repair(body)
    for fix in title_fixes + body_fixes:
        print(f"Verouderde modelnaam gerepareerd: {fix}")
    assert_current(body)

    body = _inject_affiliate_links(body, affiliate_links)
    word_count = len(body.split())
    read_time = max(1, round(word_count / 200))
    read_banner = f"> {read_time} min read · {word_count} words\n\n"
    body = read_banner + body
    return {"title": title, "tags": tags, "body": body}


def _inject_affiliate_links(body: str, links: dict) -> str:
    """Replace placeholder refs with real affiliate links."""
    replacements = {
        "Anthropic API": f"[Anthropic API]({links.get('anthropic', '#')})",
        "DigitalOcean": f"[DigitalOcean]({links.get('digitalocean', '#')})",
        "Gumroad": f"[Gumroad]({links.get('gumroad', '#')})",
    }
    for text, link in replacements.items():
        body = body.replace(text, link, 1)  # replace first occurrence only
    return body
