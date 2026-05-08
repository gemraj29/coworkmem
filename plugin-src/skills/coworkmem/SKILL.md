---
name: coworkmem
description: >
  This skill should be used when the user wants to manage long-term memory across
  Claude Cowork sessions. Trigger phrases: "save this to memory", "remember that",
  "what do you know about X", "capture this session", "add to memory", "mark as private",
  "forget that", "/save-memory", "/load-memory". Also auto-activates at session start
  to inject relevant context cards from past work.
version: 0.1.0
---

# CoworkMem — Long-Term Memory Skill

Give Claude persistent, cross-session memory using local **context cards** — compact markdown files that capture decisions, tasks, learnings, and project state. Inject the most relevant cards at session start so the user never has to repeat themselves.

---

## Auto-Inject at Session Start

At the start of every conversation, **before responding**:

1. Read `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md`
2. Score each card: `high` importance = +2, created ≤7 days ago = +1, topics match opening message = +3; skip `private: true` cards entirely
3. Load top cards within a **1,200-token budget** — TL;DR + key facts only, no detail prose
4. Output a single compact block then answer normally:

```
🧠 CoworkMem (N cards):

[type] Title
  TL;DR sentence
  · key fact 1
  · key fact 2

[type] Title
  TL;DR sentence
  · key fact 1

⚡ Open: thread · thread · thread
```

TL;DR + up to 3 key facts per card. No detail section. No full prose. If the user needs more, they run `/load-memory`.

If `INDEX.md` doesn't exist or is empty, skip silently.

---

## Creating Context Cards

Save cards to `~/Documents/Claude/Projects/Coworkmem/memories/YYYY-MM-DD_<slug>.md` where `<slug>` is 2–4 lowercase words from the title joined by hyphens.

See `references/card-format.md` for the exact file format and type/token guidance.

**Trigger on:**
- User says "save this", "remember that", "capture this session", "/save-memory"
- A significant decision, task completion, or user preference is expressed
- End of a substantial work session

**Compression rules — include:**
- Decisions and their rationale
- Tasks completed or in progress
- User preferences, corrections, and feedback
- Technical facts hard to re-derive (paths, config values, design choices)
- Project state: phase, blockers, goals, next steps

**Compression rules — omit:**
- Step-by-step reasoning visible in files/code
- Conversational filler and pleasantries
- Facts trivially readable from the project directory
- Anything the user marked private

---

## Private Information

When user says "don't save that", "mark as private", "that's sensitive", "forget that":
1. Do **not** write that content to any card
2. If already saved, set `private: true` in the card's frontmatter
3. Update `INDEX.md` private column to `true`
4. Confirm: "Marked as private — hidden from viewer and future sessions."

---

## INDEX.md

Maintain `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md`:

```markdown
# CoworkMem Index
_Last updated: YYYY-MM-DD_

| Date | File | Title | Type | Topics | Importance | Private |
|------|------|-------|------|--------|------------|---------|
| 2026-05-07 | 2026-05-07_slug.md | Card title | decision | [ai, memory] | high | false |
```

- Add a row every time a card is created; update when `private` or `importance` changes
- Rows newest-first; never delete rows (mark `private: true` instead)

---

## Memory Viewer

To browse, search, and manage all cards:
```bash
bash ~/Documents/Claude/Projects/Coworkmem/run_coworkmem.sh
```
Opens at **http://localhost:4242** with search, type filters, and private toggle.
