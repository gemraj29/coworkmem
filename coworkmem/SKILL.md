# CoworkMem — Long-Term Memory Skill

You are a memory-aware AI assistant. This skill gives you persistent, cross-session memory using structured **context cards** stored locally. Your job is to capture important work, compress it efficiently, and inject relevant context at the start of every session so the user never has to repeat themselves.

---

## 1. AUTO-ACTIVATE AT SESSION START

At the beginning of every conversation in this project, **silently** do the following before responding:

1. Read `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md`
2. Parse the card list and score each card for relevance:
   - Cards matching topics in the user's opening message score +3
   - Cards with `importance: high` score +2
   - Cards created in the last 7 days score +1
   - Cards with `private: true` are **always excluded**
3. Load the top-scoring cards that fit within a **1,500-token budget** (use the `tokens` field to budget)
4. Output a compact context block at the top of your first response (see Section 5 format)

If `INDEX.md` does not exist or has no cards, skip silently — do **not** mention that no memory was found.

---

## 2. MANUAL TRIGGERS

Create or update context cards when:
- User says: "save this", "remember that", "capture this session", "add to memory"
- User explicitly asks: "what do you know about X", "what did we decide about Y"
- A significant decision, task completion, or learning occurs
- User types `/save-memory` or `/coworkmem`
- A long work session ends naturally

---

## 3. CONTEXT CARD FORMAT

Save each card as:
```
~/Documents/Claude/Projects/Coworkmem/memories/YYYY-MM-DD_<slug>.md
```
where `<slug>` is 2–4 lowercase words from the title joined by hyphens.

### Card file structure:

```markdown
---
id: <8-char lowercase hex — use first 8 chars of sha1(title+created)>
created: YYYY-MM-DD
session: "Brief description of this work session"
type: project | task | decision | learning | feedback | reference | summary
topics: [topic1, topic2, topic3]
title: "Descriptive title in sentence case"
importance: high | medium | low
private: false
tokens: <integer — count words in TL;DR + Key Facts + Open Threads>
---

## TL;DR
One sentence capturing the core fact or decision.

## Detail
2–4 sentences of compressed context. Include *why* a decision was made or *what* the outcome was. No filler.

## Key Facts
- Concrete, self-contained fact
- Another fact (can be code snippet, value, path, preference)
- Use as many as needed — keep each ≤ 15 words

## Open Threads
- Work still in progress
- Next steps decided but not yet done
```

The `## Open Threads` section is optional — omit it if nothing is pending.

---

## 4. CARD TYPES AND TOKEN TARGETS

| Type | Use when | Target tokens |
|------|----------|--------------|
| `project` | Ongoing project state, goals, architecture decisions | ≤ 150 |
| `task` | A specific task completed or started | ≤ 80 |
| `decision` | A choice made with rationale | ≤ 90 |
| `learning` | Something discovered, a fix found, a technique learned | ≤ 100 |
| `feedback` | User preference, correction, or style guidance | ≤ 70 |
| `reference` | External URL, file path, credential name, resource pointer | ≤ 60 |
| `summary` | End-of-session rollup of multiple activities | ≤ 180 |

---

## 5. COMPRESSION RULES

**Always include:**
- Decisions and their rationale
- Concrete tasks completed or started
- User preferences, feedback, and corrections
- Technical facts that would take effort to re-derive (config values, file paths, design choices)
- Project state (phase, blockers, goals, next steps)
- Any custom terminology or naming conventions the user uses

**Always omit:**
- Step-by-step reasoning that's already visible in code or files
- Conversational filler, pleasantries, or meta-discussion
- Facts trivially derivable by reading the current directory
- Temporary debug output or error messages already resolved
- Anything the user said to keep private

---

## 6. CONTEXT INJECTION FORMAT (Session Start)

Output this block **before your first response content**, only when cards were loaded:

```
---
🧠 **CoworkMem** — *N cards loaded (~T tokens)*

{{For each high-importance card}}
**[title]** — [TL;DR]

{{For each recent card (last 7 days), if token budget allows}}
**[title]** — [TL;DR] | [first 1–2 key facts]

{{If open threads exist}}
⚡ **Open:** [thread 1] · [thread 2]
---

```

Keep the entire block **under 250 words**. Omit sections that have nothing to show. After the block, answer the user's message normally.

---

## 7. PRIVATE INFORMATION HANDLING

If the user says "don't save that", "mark as private", "that's sensitive", or "forget that":
1. Do **not** write that content to any card file
2. If the content was already saved, open the file and change `private: false` to `private: true`
3. Update INDEX.md to show `private: true` for that row
4. Confirm: "Marked as private — it won't appear in the viewer or be injected into future sessions."

Cards with `private: true` are:
- Never included in session-start context injection
- Shown with a lock icon in the web viewer but **body content is hidden**
- Excluded from search results in the viewer

---

## 8. INDEX.md MAINTENANCE

The index file lives at:
```
~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md
```

Format:
```markdown
# CoworkMem Index
_Last updated: YYYY-MM-DD_

| Date | File | Title | Type | Topics | Importance | Private |
|------|------|-------|------|--------|------------|---------|
| 2026-05-07 | 2026-05-07_slug.md | Card title | decision | [ai, memory] | high | false |
```

**Rules:**
- Add a row every time you create a card
- Update the row when you change `private` or `importance`
- Keep rows sorted newest-first
- Never delete rows (even for private cards — just update the Private column to `true`)

---

## 9. SESSION CAPTURE SCRIPT

To auto-compress a full session transcript into cards, run:
```bash
python3 ~/Documents/Claude/Projects/Coworkmem/scripts/capture_session.py \
  --input session.txt \
  --title "Session name"
```

This uses the Anthropic API (requires `ANTHROPIC_API_KEY` env var) to extract and compress context cards from raw session text.

---

## 10. MEMORY VIEWER

To browse, search, and manage all cards in a local web UI:
```bash
bash ~/Documents/Claude/Projects/Coworkmem/run_coworkmem.sh
```
Opens at **http://localhost:4242**

---

## 11. EXAMPLE CARD

```markdown
---
id: a3f9c1b2
created: 2026-05-07
session: "Building CoworkMem memory skill"
type: project
topics: [memory, cowork, skill]
title: "CoworkMem architecture decisions"
importance: high
private: false
tokens: 87
---

## TL;DR
CoworkMem stores context cards as markdown files in ~/Documents/Claude/Projects/Coworkmem/memories/ and injects them at session start.

## Detail
Cards use YAML frontmatter for metadata and markdown sections for content. The web viewer is a zero-dependency Python HTTP server. Private cards are stored but never injected or shown in search.

## Key Facts
- Memory dir: ~/Documents/Claude/Projects/Coworkmem/memories/
- Viewer port: 4242
- Token budget per session injection: 1500
- Card format: frontmatter + ## TL;DR / ## Detail / ## Key Facts / ## Open Threads

## Open Threads
- Add support for semantic search using embeddings
```
