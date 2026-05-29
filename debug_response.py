import os, json, urllib.request

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
api_key = os.environ["GEMINI_API_KEY"]

payload = json.dumps({
    "contents": [{"parts": [{"text": "Write a JSON object with keys: title (string), tags (array of 4 strings), body (string with 3 sentences). Nothing else."}]}],
    "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.7},
}).encode()

req = urllib.request.Request(GEMINI_URL, data=payload,
    headers={"Content-Type": "application/json", "X-goog-api-key": api_key}, method="POST")

with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read())

text = data["candidates"][0]["content"]["parts"][0]["text"]
print(repr(text[:500]))
