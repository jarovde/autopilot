"""
Generate a full Dev.to-ready article using Google Gemini (free tier).
Returns: {"title": str, "body": str, "tags": list[str]}
"""
import os
import json
import re
import socket
import time
import urllib.error
import urllib.request

from pipeline.model_facts import MODEL_FACTS, repair, assert_current

GEMINI_BASIS = "https://generativelanguage.googleapis.com/v1beta/models"

# Meerdere modellen, in volgorde van voorkeur. Op 17 aug lag
# gemini-flash-latest er urenlang uit met 503 "high demand" — herkansen hielp
# niet, want het was geen piek van een minuut. De pijplijn hing aan één model
# en dus viel de weekrun weg. De namen hieronder zijn opgevraagd bij de API
# (models-endpoint), niet verzonnen. De lite-variant staat er expres achteraan:
# die heeft doorgaans capaciteit over als de gewone vollopen.
MODELLEN = [
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
]

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

# ── Antwoord uitlezen ─────────────────────────────────────────────────────────
# Het model krijgt een strikt formaat opgelegd, maar houdt zich daar niet altijd
# exact aan: het zet er weleens een zin voor, maakt er "**TITLE:**" van, of pakt
# het geheel in een ```-blok. Dat gaf eerder een kale StopIteration of
# ValueError, en dan faalt de hele run om opmaak in plaats van om inhoud. Deze
# lezers zijn daar tolerant in; alleen als een veld écht ontbreekt volgt een
# fout, mét het begin van wat het model dan wel schreef.

_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n\s*```\s*$", re.S)


def _ontdoe_van_fence(text: str) -> str:
    m = _FENCE.match(text)
    return m.group(1).strip() if m else text


def _veld(text: str, naam: str) -> str:
    """Waarde van TITLE:/TAGS:, ongeacht opmaak of inspringing."""
    patroon = re.compile(rf"^[\s>*_#-]*\**\s*{naam}\s*\**\s*:\s*(.+?)\s*$",
                         re.I | re.M)
    m = patroon.search(text)
    if not m:
        raise GeneratieFout(f"geen {naam}:-regel in het antwoord. "
                            f"Begin: {text[:300]!r}")
    # Overgebleven markdown-nadruk rond de waarde weghalen.
    return m.group(1).strip().strip("*_").strip()


def _lichaam(text: str) -> str:
    m = re.search(r"^[\s>*_#-]*\**\s*BODY\s*\**\s*:\s*", text, re.I | re.M)
    if not m:
        raise GeneratieFout(f"geen BODY:-blok in het antwoord. Begin: {text[:300]!r}")
    body = text[m.end():].strip()
    if not body:
        raise GeneratieFout("BODY: was leeg")
    return body


class GeneratieFout(Exception):
    """Fout met genoeg context om hem van buitenaf te kunnen duiden.

    Bestaat omdat run #12 (17 aug) faalde met alleen "Process completed with
    exit code 1" in de annotatie en afgeschermde logs. Daarmee viel van buitenaf
    niet vast te stellen wat er misging — precies het patroon dat we hier al
    vaker hadden: een mislukking die niets zegt. Elke stap hieronder faalt nu
    met een eigen, benoemde reden.
    """


# Codes die betekenen "probeer het straks nog eens", niet "je verzoek deugt
# niet". 503 velde run #12 op 17 aug: Gemini meldde "This model is currently
# experiencing high demand", en omdat er geen herkansing was viel de hele
# weekrun weg. Een 400 of 403 hoort juist NIET herhaald te worden — dan is er
# iets mis met het verzoek of de sleutel en helpt wachten niet.
TIJDELIJK = {429, 500, 502, 503, 504}
POGINGEN  = 4
WACHT     = [5, 15, 45]      # seconden tussen de pogingen


def _probeer_model(model: str, payload: bytes, api_key: str) -> tuple[bytes, str]:
    """Eén model, met herkansingen. Geeft (antwoord, "") of (b"", reden)."""
    req = urllib.request.Request(
        f"{GEMINI_BASIS}/{model}:generateContent",
        data=payload,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        method="POST",
    )
    laatste = ""
    for poging in range(POGINGEN):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read(), ""
        except urllib.error.HTTPError as e:
            lijf = e.read().decode("utf-8", "replace")[:300]
            laatste = f"HTTP {e.code}: {lijf}"
            if e.code == 404:
                return b"", f"model bestaat niet ({model})"
            if e.code not in TIJDELIJK:
                # 400/403 gaat over het verzoek of de sleutel: een ander model
                # lost dat niet op, dus meteen stoppen.
                raise GeneratieFout(f"Gemini gaf {laatste}") from None
        except (TimeoutError, socket.timeout) as e:
            laatste = f"timeout: {e}"
        except urllib.error.URLError as e:
            laatste = f"netwerkfout: {e.reason}"
        except Exception as e:
            raise GeneratieFout(
                f"Gemini niet bereikbaar: {type(e).__name__}: {e}") from None

        if poging < POGINGEN - 1:
            pauze = WACHT[poging]
            print(f"{model} niet beschikbaar ({laatste[:70]}) — "
                  f"poging {poging + 2}/{POGINGEN} over {pauze}s", flush=True)
            time.sleep(pauze)
    return b"", laatste


def _vraag_gemini(payload: bytes, api_key: str) -> bytes:
    redenen = []
    for model in MODELLEN:
        antwoord, reden = _probeer_model(model, payload, api_key)
        if antwoord:
            if redenen:
                print(f"Uitgeweken naar {model}", flush=True)
            return antwoord
        redenen.append(f"{model}: {reden[:120]}")
        print(f"{model} opgegeven — volgende model proberen", flush=True)
    raise GeneratieFout("geen enkel Gemini-model beschikbaar — " + " | ".join(redenen))


def generate_article(topic: str, affiliate_links: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeneratieFout("GEMINI_API_KEY ontbreekt in de omgeving "
                            "(secret verwijderd of hernoemd?)")

    payload = json.dumps({
        "contents": [
            {"parts": [{"text": PROMPT.format(topic=topic, model_facts=MODEL_FACTS)}]}
        ],
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.7},
    }).encode()
    rauw = _vraag_gemini(payload, api_key)

    try:
        data = json.loads(rauw)
    except Exception:
        raise GeneratieFout(f"Gemini gaf geen JSON: {rauw[:300]!r}") from None

    kandidaten = data.get("candidates") or []
    if not kandidaten:
        # Bij een blokkade zit de reden in promptFeedback, niet in candidates.
        raise GeneratieFout(f"Gemini gaf geen kandidaten — "
                            f"promptFeedback={data.get('promptFeedback')}")
    kandidaat = kandidaten[0]
    delen = (kandidaat.get("content") or {}).get("parts") or []
    if not delen:
        raise GeneratieFout(f"Gemini gaf een lege kandidaat — "
                            f"finishReason={kandidaat.get('finishReason')}")
    text = delen[0].get("text", "").strip()
    if not text:
        raise GeneratieFout("Gemini gaf lege tekst terug")

    # De parse hieronder eist het TITLE/TAGS/BODY-formaat. Wijkt het model
    # daarvan af, dan gaf dit eerder een kale StopIteration of ValueError
    # zonder enige aanwijzing. Nu staat het begin van het antwoord in de fout,
    # zodat te zien is wát het model dan wel schreef.
    text = _ontdoe_van_fence(text)
    title    = _veld(text, "TITLE")
    tags_raw = _veld(text, "TAGS")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()][:4]
    tags = _optimize_tags(topic, tags)
    body = _lichaam(text)
    if not body:
        raise GeneratieFout("BODY: was leeg")

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
