#!/usr/bin/env python3
"""
CoworkMem — Session Capture & Compression
==========================================
Reads a session transcript (from file or stdin) and uses Claude Haiku
to extract structured context cards, saving them to the memories directory.

Usage:
    python3 capture_session.py --input session.txt --title "Session name"
    cat session.txt | python3 capture_session.py --title "Session name"
    python3 capture_session.py --input session.txt --title "Session name" --dry-run

Requirements:
    pip install anthropic --break-system-packages

Environment:
    ANTHROPIC_API_KEY — your Anthropic API key
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import textwrap

MEMORIES_DIR = os.path.expanduser("~/Documents/Claude/Projects/Coworkmem/memories")
INDEX_FILE = os.path.join(MEMORIES_DIR, "INDEX.md")

CARD_TYPES = {"project", "task", "decision", "learning", "feedback", "reference", "summary"}
IMPORTANCE_LEVELS = {"high", "medium", "low"}

EXTRACTION_PROMPT = """You are a memory compression agent for an AI assistant. Your job is to read a session transcript and extract the most important information into structured context cards.

Extract 2–6 cards from this session. Each card should capture a distinct topic, decision, task, learning, or piece of project state.

For each card, output a JSON object in this exact format:
{
  "type": "project|task|decision|learning|feedback|reference|summary",
  "title": "Descriptive title in sentence case (max 10 words)",
  "importance": "high|medium|low",
  "topics": ["topic1", "topic2"],
  "tldr": "One sentence capturing the core fact. Max 25 words.",
  "detail": "2-4 sentences of compressed context. Include why decisions were made and what outcomes occurred. No filler.",
  "key_facts": ["Concrete fact ≤15 words", "Another concrete fact", "File path or value if relevant"],
  "open_threads": ["In-progress item or next step"]
}

Rules:
- `open_threads` can be an empty array [] if nothing is pending
- `key_facts` must have at least 1 item
- Choose `high` importance for decisions that affect project direction, user preferences discovered, or major work completed
- Choose `low` for minor tasks or reference lookups
- `topics` should be 1–4 lowercase single-word or short-phrase tags
- Be ruthlessly concise. Every word must earn its place.
- Do NOT include private/sensitive information (passwords, personal data, secrets)

Return a JSON array of card objects. No other text. No markdown fences.

SESSION TITLE: {title}

SESSION TRANSCRIPT:
{transcript}
"""


def make_id(title: str, created: str) -> str:
    raw = f"{title}{created}"
    return hashlib.sha1(raw.encode()).hexdigest()[:8]


def make_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", "", title.lower()).split()
    return "-".join(words[:4])


def count_tokens(text: str) -> int:
    """Rough word-count approximation of token count."""
    return len(text.split())


def format_card(card: dict, created: str, session_title: str) -> str:
    """Format a card dict into the markdown file format."""
    card_id = make_id(card["title"], created)
    topics_str = "[" + ", ".join(card.get("topics", [])) + "]"

    key_facts = card.get("key_facts", [])
    open_threads = card.get("open_threads", [])

    # Estimate tokens
    body_parts = [card.get("tldr", ""), card.get("detail", "")]
    body_parts += key_facts
    body_parts += open_threads
    token_est = count_tokens(" ".join(body_parts))

    lines = [
        "---",
        f'id: {card_id}',
        f'created: {created}',
        f'session: "{session_title}"',
        f'type: {card.get("type", "summary")}',
        f'topics: {topics_str}',
        f'title: "{card["title"]}"',
        f'importance: {card.get("importance", "medium")}',
        f'private: false',
        f'tokens: {token_est}',
        "---",
        "",
        "## TL;DR",
        card.get("tldr", "").strip(),
        "",
        "## Detail",
        card.get("detail", "").strip(),
        "",
        "## Key Facts",
    ]
    for fact in key_facts:
        lines.append(f"- {fact.strip()}")

    if open_threads:
        lines.append("")
        lines.append("## Open Threads")
        for thread in open_threads:
            lines.append(f"- {thread.strip()}")

    lines.append("")
    return "\n".join(lines)


def update_index(card: dict, filename: str, created: str):
    """Append a row to INDEX.md."""
    topics_str = "[" + ", ".join(card.get("topics", [])) + "]"
    row = f"| {created} | {filename} | {card['title']} | {card.get('type', 'summary')} | {topics_str} | {card.get('importance', 'medium')} | false |"

    if not os.path.exists(INDEX_FILE):
        header = (
            "# CoworkMem Index\n"
            f"_Last updated: {created}_\n\n"
            "| Date | File | Title | Type | Topics | Importance | Private |\n"
            "|------|------|-------|------|--------|------------|---------|"
        )
        with open(INDEX_FILE, "w") as f:
            f.write(header + "\n")

    # Read current content
    with open(INDEX_FILE, "r") as f:
        content = f.read()

    # Update the "Last updated" line
    content = re.sub(r"_Last updated: .*?_", f"_Last updated: {created}_", content)

    # Append row after the header separator line
    if "| --- |" in content or "|------|" in content:
        # Find end of table header and insert new row after it
        lines = content.split("\n")
        insert_idx = None
        for i, line in enumerate(lines):
            if line.startswith("|---"):
                insert_idx = i + 1
                break
        if insert_idx is not None:
            lines.insert(insert_idx, row)
            content = "\n".join(lines)
    else:
        content += f"\n{row}"

    with open(INDEX_FILE, "w") as f:
        f.write(content)


def extract_cards_with_ai(transcript: str, session_title: str) -> list[dict]:
    """Call Claude Haiku to extract context cards from session text."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed.")
        print("Run: pip install anthropic --break-system-packages")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Export your API key: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate transcript if very long (keep first 6000 chars and last 2000)
    max_chars = 8000
    if len(transcript) > max_chars:
        keep_start = 5000
        keep_end = 3000
        transcript = (
            transcript[:keep_start]
            + f"\n\n[...{len(transcript) - keep_start - keep_end} chars truncated...]\n\n"
            + transcript[-keep_end:]
        )

    prompt = EXTRACTION_PROMPT.format(title=session_title, transcript=transcript)

    print(f"Calling Claude Haiku to extract context cards...")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        cards = json.loads(raw)
        if not isinstance(cards, list):
            cards = [cards]
        return cards
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse AI response as JSON: {e}")
        print("Raw response:")
        print(raw[:500])
        sys.exit(1)


def create_manual_card(session_title: str) -> list[dict]:
    """Create a minimal placeholder card for manual editing."""
    return [
        {
            "type": "summary",
            "title": f"Session: {session_title[:50]}",
            "importance": "medium",
            "topics": ["session"],
            "tldr": "Session captured — edit this card to add details.",
            "detail": "This is a placeholder card. Edit the generated .md file to fill in the actual context from your session.",
            "key_facts": ["Captured on " + datetime.date.today().isoformat()],
            "open_threads": [],
        }
    ]


def save_cards(cards: list[dict], session_title: str, dry_run: bool = False) -> list[str]:
    """Save card dicts to markdown files and update the index."""
    today = datetime.date.today().isoformat()
    os.makedirs(MEMORIES_DIR, exist_ok=True)

    saved_files = []
    for card in cards:
        # Validate type
        if card.get("type") not in CARD_TYPES:
            card["type"] = "summary"
        if card.get("importance") not in IMPORTANCE_LEVELS:
            card["importance"] = "medium"

        slug = make_slug(card.get("title", "untitled"))
        filename = f"{today}_{slug}.md"
        filepath = os.path.join(MEMORIES_DIR, filename)

        # Handle filename collisions
        counter = 1
        while os.path.exists(filepath) and not dry_run:
            filename = f"{today}_{slug}-{counter}.md"
            filepath = os.path.join(MEMORIES_DIR, filename)
            counter += 1

        content = format_card(card, today, session_title)

        if dry_run:
            print(f"\n{'='*60}")
            print(f"DRY RUN — would save to: {filepath}")
            print(f"{'='*60}")
            print(content)
        else:
            with open(filepath, "w") as f:
                f.write(content)
            update_index(card, filename, today)
            print(f"  ✓ Saved: {filename} [{card.get('type')}] [{card.get('importance')}]")
            saved_files.append(filepath)

    return saved_files


def main():
    parser = argparse.ArgumentParser(
        description="CoworkMem — Capture and compress a session into context cards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python3 capture_session.py --input session.txt --title "Building the API"
          cat session.txt | python3 capture_session.py --title "Debug session"
          python3 capture_session.py --input session.txt --title "My session" --dry-run
          python3 capture_session.py --input session.txt --title "My session" --no-ai
        """),
    )
    parser.add_argument("--input", "-i", help="Path to session transcript file (default: stdin)")
    parser.add_argument("--title", "-t", required=True, help="Short name for this session")
    parser.add_argument("--dry-run", action="store_true", help="Print cards but don't save")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI extraction, create a placeholder card")
    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input, "r") as f:
            transcript = f.read()
    else:
        if sys.stdin.isatty():
            print("Reading from stdin... (Ctrl+D to finish)")
        transcript = sys.stdin.read()

    if not transcript.strip():
        print("ERROR: Empty transcript. Nothing to compress.")
        sys.exit(1)

    print(f"\nCoworkMem — Session Capture")
    print(f"Session: {args.title}")
    print(f"Input length: {len(transcript)} chars ({count_tokens(transcript)} approx tokens)")
    print()

    # Extract cards
    if args.no_ai:
        print("Skipping AI extraction — creating placeholder card.")
        cards = create_manual_card(args.title)
    else:
        cards = extract_cards_with_ai(transcript, args.title)

    print(f"Extracted {len(cards)} card(s):")
    for c in cards:
        print(f"  • [{c.get('type', '?')}] {c.get('title', 'Untitled')} — {c.get('importance', '?')} importance")

    print()
    saved = save_cards(cards, args.title, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\nDone. {len(saved)} card(s) saved to {MEMORIES_DIR}")
        print(f"Index updated: {INDEX_FILE}")


if __name__ == "__main__":
    main()
