"""
Tracks which topics have been published so we never repeat.
State stored in state.json (committed to repo by the workflow).
"""
import json
import os
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "state.json"


def load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"published": []}


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def next_topic(all_topics: list[str]) -> str | None:
    state = load()
    published = set(state["published"])
    for topic in all_topics:
        if topic not in published:
            return topic
    return None  # all topics exhausted


def mark_published(topic: str):
    state = load()
    if topic not in state["published"]:
        state["published"].append(topic)
    save(state)
