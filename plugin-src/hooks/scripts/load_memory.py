#!/usr/bin/env python3
"""
CoworkMem — SessionStart hook
Reads the top context cards and injects them as session context.
Output: JSON {"decision": "approve", "reason": "<memory context>"}
"""
import json
import os
import re
import sys
from datetime import date, datetime

MEMORIES_DIR = os.path.expanduser("~/Documents/Claude/Projects/Coworkmem/memories")
INDEX_FILE = os.path.join(MEMORIES_DIR, "INDEX.md")
MAX_TOKENS = 1200
MAX_CARDS = 6


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


def score_card(meta):
    s = 0
    imp = meta.get("importance", "medium")
    if imp == "high":
        s += 2
    elif imp == "medium":
        s += 1
    age = days_ago(str(meta.get("created", "")))
    if age <= 1:
        s += 3
    elif age <= 7:
        s += 2
    elif age <= 30:
        s += 1
    return s


def load_cards():
    if not os.path.isdir(MEMORIES_DIR):
        return []

    cards = []
    for fname in sorted(os.listdir(MEMORIES_DIR), reverse=True):
        if not fname.endswith(".md") or fname == "INDEX.md":
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
            "created": str(meta.get("created", "")),
            "tokens": int(meta.get("tokens", 50)),
            "tldr": tldr,
            "key_facts": key_facts[:3],
            "open_threads": open_threads[:3],
            "score": score_card(meta),
        })

    cards.sort(key=lambda c: c["score"], reverse=True)
    return cards


def build_context(cards):
    if not cards:
        return ""

    selected = []
    tokens_used = 0
    for c in cards:
        if len(selected) >= MAX_CARDS:
            break
        card_tokens = 20 + len(c["key_facts"]) * 15  # title+tldr + ~15 tokens per fact
        if tokens_used + card_tokens > MAX_TOKENS:
            break
        selected.append(c)
        tokens_used += card_tokens

    if not selected:
        return ""

    lines = [f"🧠 CoworkMem ({len(selected)} cards):"]
    for c in selected:
        lines.append(f"\n[{c['type']}] {c['title']}")
        lines.append(f"  {c['tldr']}")
        for fact in c["key_facts"]:
            lines.append(f"  · {fact}")

    # Compact open threads across all cards
    all_threads = []
    for c in selected:
        all_threads.extend(c["open_threads"])

    if all_threads:
        lines.append("")
        lines.append("⚡ Open: " + " · ".join(all_threads[:5]))

    return "\n".join(lines)


def main():
    cards = load_cards()
    context = build_context(cards)

    if context:
        output = {"decision": "approve", "reason": context}
    else:
        output = {"decision": "approve", "reason": ""}

    print(json.dumps(output))


if __name__ == "__main__":
    main()
