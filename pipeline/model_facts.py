"""
Single source of truth for Claude model names, IDs and API shape.

Waarom dit bestand bestaat: Gemini schrijft de artikelen, en Gemini's
trainingsdata stopt bij een oudere Claude-generatie. Zonder deze feiten in de
prompt verzint het `claude-3-5-sonnet-20241022` en `thinking={"budget_tokens":
N}` — code die vandaag een 404 respectievelijk een 400 oplevert.

Dat is precies wat er op 10 aug misging: het topic "Claude Sonnet vs Opus"
werd door Gemini uitgeklapt tot een artikel getiteld "Claude 3.5 Sonnet vs
Claude 3 Opus". De topic-lijst was niet fout, de prompt had geen feiten.

Twee lagen:
  1. MODEL_FACTS  — gaat mee in de prompt (preventief)
  2. repair()/assert_current() — controleert de output (vangnet)

Bij een nieuwe modelrelease: pas CURRENT_MODELS aan, en voeg de nu verouderde
naam toe aan REPAIRS. Verder hoeft er niets te veranderen.
"""
import re

# id -> (weergavenaam, input $/1M, output $/1M, contextvenster)
CURRENT_MODELS = {
    "claude-opus-5": ("Claude Opus 5", 5.00, 25.00, "1M"),
    "claude-sonnet-5": ("Claude Sonnet 5", 3.00, 15.00, "1M"),
    "claude-haiku-4-5": ("Claude Haiku 4.5", 1.00, 5.00, "200K"),
}

DEFAULT_MODEL = "claude-opus-5"

MODEL_FACTS = """
FACTUAL CONSTRAINTS — these override anything you think you know about Claude.
Your training data is older than these facts. Do not "correct" them.

Current Claude models (the ONLY model IDs you may write in code):
- claude-opus-5     — Claude Opus 5, $5/$25 per 1M tokens, 1M context. The default choice.
- claude-sonnet-5   — Claude Sonnet 5, $3/$15 per 1M tokens, 1M context. High-volume work.
- claude-haiku-4-5  — Claude Haiku 4.5, $1/$5 per 1M tokens, 200K context. Simple, fast tasks.

Model IDs are complete as written. Never append a date suffix.
Claude 3, Claude 3.5, and Claude 4 models are retired or superseded — never
reference them, not in code and not in prose.

Current Python SDK usage (pip install anthropic):

    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": "..."}],
    )

API rules that changed — code that ignores these returns HTTP 400:
- Extended thinking uses thinking={"type": "adaptive"}. The old
  {"type": "enabled", "budget_tokens": N} form is removed.
- temperature, top_p and top_k are removed. Steer with the prompt instead.
- Control reasoning depth with output_config={"effort": "low"|"medium"|"high"}.
- Assistant-turn prefilling is removed. Use output_config={"format": {...}} for
  structured JSON output.
- Stream any request with max_tokens above ~16000.

Every code block you write must run against the API as described above.
""".strip()

# Verouderd -> huidig. Deterministisch, dus veilig automatisch toe te passen.
REPAIRS = [
    # model-IDs (met of zonder datumsuffix)
    (r"claude-3[-.]5-sonnet(-\d{8})?", "claude-sonnet-5"),
    (r"claude-3[-.]7-sonnet(-\d{8})?", "claude-sonnet-5"),
    (r"claude-sonnet-4(-\d|-\d{8})?\b", "claude-sonnet-5"),
    (r"claude-3-opus(-\d{8})?", "claude-opus-5"),
    (r"claude-opus-4(-\d|-\d{8})?\b", "claude-opus-5"),
    (r"claude-3[-.]5-haiku(-\d{8})?", "claude-haiku-4-5"),
    (r"claude-3-haiku(-\d{8})?", "claude-haiku-4-5"),
    # prozanamen
    (r"Claude 3\.5 Sonnet", "Claude Sonnet 5"),
    (r"Claude 3\.7 Sonnet", "Claude Sonnet 5"),
    (r"Claude 4(\.\d)? Sonnet", "Claude Sonnet 5"),
    (r"Claude Sonnet 4(\.\d)?", "Claude Sonnet 5"),
    (r"Claude 3 Opus", "Claude Opus 5"),
    (r"Claude 4(\.\d)? Opus", "Claude Opus 5"),
    (r"Claude Opus 4(\.\d)?", "Claude Opus 5"),
    (r"Claude 3\.5 Haiku", "Claude Haiku 4.5"),
    (r"Claude 3 Haiku", "Claude Haiku 4.5"),
]

# Hier is geen veilige tekstvervanging voor: de hele parametervorm klopt niet
# meer. Publiceren met deze code betekent lezers een HTTP 400 sturen, dus dit
# is een harde stop.
FATAL = [
    (r"budget_tokens", 'thinking={"type": "adaptive"} — budget_tokens is verwijderd'),
    (r'"type"\s*:\s*"enabled"', 'thinking={"type": "adaptive"} — "enabled" is verwijderd'),
    (r"\btemperature\s*=", "temperature is verwijderd uit de Messages API"),
    (r"\btop_[pk]\s*=", "top_p/top_k zijn verwijderd uit de Messages API"),
]


def repair(text: str) -> tuple[str, list[str]]:
    """Vervang verouderde modelnamen door huidige. Geeft (tekst, wat-er-veranderde)."""
    fixed = []
    for pattern, replacement in REPAIRS:
        text, n = re.subn(pattern, replacement, text)
        if n:
            fixed.append(f"{pattern} -> {replacement} ({n}x)")
    return text, fixed


def assert_current(text: str) -> None:
    """Stop de run als er onrepareerbaar verouderde API-vormen in de tekst staan."""
    problems = [
        f"{reason} (patroon: {pattern})"
        for pattern, reason in FATAL
        if re.search(pattern, text)
    ]
    if problems:
        raise ValueError(
            "Artikel bevat verouderde Claude API-code en is NIET gepubliceerd:\n  - "
            + "\n  - ".join(problems)
        )
