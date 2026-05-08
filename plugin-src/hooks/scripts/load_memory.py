#!/usr/bin/env python3
"""
CoworkMem — SessionStart hook v0.2
- Topic-aware scoring: boosts cards matching the user's opening message (+3)
- Project-aware filtering: boosts cards matching the active project (+2)
- Active project read from memories/.coworkmem_config.json
Output: JSON {"decision": "approve", "reason": "<memory context>"}
"""
import json
import os
import re
import sys
from datetime import date, datetime

MEMORIES_DIR = os.path.expanduser("~/Documents/Claude/Projects/Coworkmem/memories")
CONFIG_FILE = os.path.join(MEMORIES_DIR, ".coworkmem_config.json")
MAX_TOKENS = 1200
MAX_CARDS = 6


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config():
    """Read active project and other settings from config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ─── Hook input ───────────────────────────────────────────────────────────────

def read_hook_event():
    """Try to read the hook event JSON from stdin (Claude Code passes this)."""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                return json.loads(raw)
    except Exception:
        pass
    return {}


def extract_keywords(text):
    """Extract meaningful keywords from user's opening message for topic matching."""
    if not text:
        return set()
    stop_words = {
        "a", "an", "the", "is", "it", "in", "on", "at", "to", "for", "of",
        "and", "or", "but", "with", "this", "that", "i", "me", "my", "we",
        "you", "can", "let", "do", "be", "are", "was", "has", "have", "had",
        "will", "would", "should", "could", "please", "help", "want", "need",
        "make", "get", "go", "now", "just", "about", "more", "some", "from",
        "use", "also", "so", "up", "what", "how", "when", "where", "why",
        "hey", "hi", "hello", "ok", "okay", "let", "lets", "gonna", "yes",
    }
    words = re.findall(r"\b[a-z][a-z0-9_-]{2,}\b", text.lower())
    return {w for w in words if w not in stop_words}


# ─── Frontmatter parser ───────────────────────────────────────────────────────

def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().split("\n"):
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [i.strip().strip("\"'") for i in v[1:-1].split(",") if i.strip()]
        elif v.lower() == "true":
            v = True
        elif v.lower() == "false":
            v = False
        elif v.isdigit():
            v = int(v)
        elif v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        meta[k] = v
    return meta, parts[2].strip()


def extract_section(body, name):
    lines = body.split("\n")
    collecting = False
    result = []
    for line in lines:
        if line.startswith("## "):
            if collecting:
                break
            if line[3:].strip() == name:
                collecting = True
        elif collecting:
            result.append(line)
    return "\n".join(result).strip()


def days_ago(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 999


# ─── Scoring ──────────────────────────────────────────────────────────────────

def score_card(meta, keywords=None, active_project=None):
    s = 0

    # Importance score
    imp = meta.get("importance", "medium")
    if imp == "high":
        s += 2
    elif imp == "medium":
        s += 1

    # Recency score
    age = days_ago(str(meta.get("created", "")))
    if age <= 1:
        s += 3
    elif age <= 7:
        s += 2
    elif age <= 30:
        s += 1

    # Topic-aware score (v0.2) — boost cards whose topics match the opening message
    if keywords:
        topics = meta.get("topics", [])
        if isinstance(topics, list):
            topic_words = {t.lower().strip() for t in topics}
        else:
            topic_words = set()
        title_words = set(re.findall(r"\b[a-z][a-z0-9_-]{2,}\b", str(meta.get("title", "")).lower()))
        card_words = topic_words | title_words
        overlap = card_words & keywords
        if overlap:
            s += 3

    # Project-aware score (v0.2) — boost cards from the active project
    if active_project:
        card_project = str(meta.get("project", "")).strip().lower()
        if card_project and card_project == active_project.strip().lower():
            s += 2

    return s


# ─── Card loading ─────────────────────────────────────────────────────────────

def load_cards(keywords=None, active_project=None):
    if not os.path.isdir(MEMORIES_DIR):
        return []

    cards = []
    for fname in sorted(os.listdir(MEMORIES_DIR), reverse=True):
        if not fname.endswith(".md") or fname in ("INDEX.md",):
            continue
        fpath = os.path.join(MEMORIES_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        meta, body = parse_frontmatter(content)
        if not meta:
            continue
        if meta.get("private") is True:
            continue

        tldr = extract_section(body, "TL;DR")
        key_facts_raw = extract_section(body, "Key Facts")
        open_threads_raw = extract_section(body, "Open Threads")

        key_facts = [
            line.lstrip("-• *").strip()
            for line in key_facts_raw.split("\n")
            if line.strip().startswith(("-", "•", "*"))
        ]
        open_threads = [
            line.lstrip("-• *").strip()
            for line in open_threads_raw.split("\n")
            if line.strip().startswith(("-", "•", "*"))
        ]

        cards.append({
            "title": meta.get("title", fname),
            "type": meta.get("type", "summary"),
            "importance": meta.get("importance", "medium"),
            "project": str(meta.get("project", "")),
            "created": str(meta.get("created", "")),
            "tokens": int(meta.get("tokens", 50)),
            "tldr": tldr,
            "key_facts": key_facts[:3],
            "open_threads": open_threads[:3],
            "score": score_card(meta, keywords=keywords, active_project=active_project),
        })

    cards.sort(key=lambda c: c["score"], reverse=True)
    return cards


# ─── Context builder ──────────────────────────────────────────────────────────

def build_context(cards, active_project=None):
    if not cards:
        return ""

    selected = []
    tokens_used = 0
    for c in cards:
        if len(selected) >= MAX_CARDS:
            break
        card_tokens = 20 + len(c["key_facts"]) * 15
        if tokens_used + card_tokens > MAX_TOKENS:
            break
        selected.append(c)
        tokens_used += card_tokens

    if not selected:
        return ""

    header = f"🧠 CoworkMem ({len(selected)} cards)"
    if active_project:
        header += f" · project: {active_project}"
    lines = [header + ":"]

    for c in selected:
        lines.append(f"\n[{c['type']}] {c['title']}")
        lines.append(f"  {c['tldr']}")
        for fact in c["key_facts"]:
            lines.append(f"  · {fact}")

    all_threads = []
    for c in selected:
        all_threads.extend(c["open_threads"])
    if all_threads:
        lines.append("")
        lines.append("⚡ Open: " + " · ".join(all_threads[:5]))

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Read hook event from stdin (may contain user's opening message)
    event = read_hook_event()
    prompt = event.get("prompt", "") or event.get("message", "") or ""

    # Extract keywords for topic-aware scoring
    keywords = extract_keywords(prompt) if prompt else None

    # Read active project from config
    config = load_config()
    active_project = config.get("active_project") or None

    cards = load_cards(keywords=keywords, active_project=active_project)
    context = build_context(cards, active_project=active_project)

    output = {"decision": "approve", "reason": context if context else ""}
    print(json.dumps(output))


if __name__ == "__main__":
    main()
