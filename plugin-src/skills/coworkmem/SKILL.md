---
name: coworkmem
description: >
  This skill should be used when the user wants to manage long-term memory across
  Claude Cowork sessions. Trigger phrases: "save this to memory", "remember that",
  "what do you know about X", "capture this session", "add to memory", "mark as private",
  "forget that", "/save-memory", "/load-memory". Also auto-activates at session start
  to inject relevant context cards from past work.
version: 0.2.0
---

# CoworkMem — Long-Term Memory Skill

Give Claude persistent, cross-session memory using local **context cards** — compact markdown files that capture decisions, tasks, learnings, and project state. Inject the most relevant cards at session start so the user never has to repeat themselves.

---

## Auto-Inject at Session Start

At the start of every conversation, **before responding**:

1. Read `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md`
2. Score each card using all signals — skip `private: true` cards entirely:
   - `high` importance = +2, `medium` = +1
   - Created ≤1 day ago = +3, ≤7 days = +2, ≤30 days = +1
   - Topics or title overlap with user's opening message = +3 **(topic-aware, v0.2)**
   - Card's `project` field matches active project from `.coworkmem_config.json` = +2 **(project-aware, v0.2)**
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

**Auto-save nudge (v0.2):** When the user signals they are wrapping up (says "thanks", "done", "that's it", "looks good", "goodbye", etc.) and the session has been substantial, proactively offer to save before they leave:
> "This looks like a good stopping point — want me to save a memory card for this session? Just say yes or run `/save-memory`."

Only offer once per session. Skip if a card was already saved recently.

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

## Project Namespacing (v0.2)

Cards can be tagged with a `project` field in their frontmatter:
```
project: my-project-name
```

Use `/set-project <name>` to set the active project for a session. Cards matching the active project get a **+2 score boost** during injection, ensuring the most relevant project context surfaces first.

Use `/set-project clear` to unset and score all cards equally again.

When saving a card with `/save-memory`, Claude will automatically include the active project field if one is set.

---

## Memory Viewer

To browse, search, and manage all cards:
```bash
bash ~/Documents/Claude/Projects/Coworkmem/run_coworkmem.sh
```
Opens at **http://localhost:4242** with search, type filters, project filter, and private toggle.
