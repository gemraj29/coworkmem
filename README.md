# CoworkMem

> Persistent long-term memory for Claude Cowork sessions. Never lose context between sessions again.

---

## What is CoworkMem?

Claude Cowork starts every session fresh — it has no memory of past conversations, decisions, or project state. CoworkMem solves this by saving your work as compact **context cards** (structured markdown files) and automatically injecting the most relevant ones at the start of each new session.

The result: Claude already knows your project, your preferences, and where you left off — without you ever having to explain it again.

---

## How it works

```
Session ends  →  Claude saves a context card  →  stored locally as .md file
                                                              ↓
New session starts  →  SessionStart hook fires  →  top cards injected into context
                                                              ↓
                                             Claude greets you already up to speed
```

Cards are scored by importance and recency. Only TL;DR + key facts are injected (up to 1,200 tokens) — enough signal to orient Claude without wasting your context window.

---

## Quick Start

### 1. Install the plugin

Double-click `coworkmem.plugin` in Finder, or drag it into Cowork's plugin manager. The plugin installs:

- A **SessionStart hook** that auto-injects memory at the start of every session
- Four slash commands: `/save-memory`, `/load-memory`, `/capture-session`, `/view-memories`
- The **coworkmem skill** that guides Claude on capturing and compressing context

### 2. Save your first memory

At any point in a Cowork session, say:

```
save this to memory
```

or run:

```
/save-memory  My project setup
```

Claude will review the conversation, extract what matters, and write a context card to `~/Documents/Claude/Projects/Coworkmem/memories/`.

### 3. Start a new session

Open a new Cowork session. Before responding to anything, Claude will output something like:

```
🧠 CoworkMem (2 cards):

[project] Blisstravel
  Next.js travel app with Groq AI for POI discovery, deployed on Vercel
  · Groq streaming API for POI search, not OpenAI
  · Env vars set in Vercel dashboard, not .env.local

[decision] Auth approach
  Chose Clerk over NextAuth — simpler managed session handling
  · Clerk free tier covers up to 10k MAU
  · Webhook endpoint: /api/webhooks/clerk

⚡ Open: POI pagination · mobile layout review
```

Claude is now oriented. Ask your question and continue working.

---

## Commands

### `/save-memory [title]`

Saves the current session to a context card. Claude reviews the conversation, picks the right card type and importance, writes the file, and updates the index.

```
/save-memory
/save-memory  Auth redesign decisions
```

### `/load-memory [query]`

Searches and displays past memory cards. Without a query, shows all cards newest-first. With a query, filters by title, topics, or type.

```
/load-memory
/load-memory  api design
/load-memory  project
```

### `/capture-session [title]`

Compresses a full session transcript (pasted by you) into 2–6 context cards. Useful for backfilling memory from older sessions.

```
/capture-session  Onboarding flow work
```

Claude will ask you to paste the transcript, then extract structured cards automatically — no API key needed.

### `/view-memories`

Launches the local web viewer at `http://localhost:4242`. Claude starts the server in the background and confirms when it's ready.

---

## Memory Viewer

The viewer is a Google Search-style light mode web app that runs locally at `http://localhost:4242`.

**Features:**
- Search across all cards (titles, summaries, key facts, topics)
- Filter by card type (Project, Task, Decision, Learning, Feedback, Reference, Summary)
- Expand cards to see full key facts and open threads
- Mark any card as private (hidden from viewer and future sessions)
- Auto-refreshes every 30 seconds

**Launch manually:**
```bash
bash ~/Documents/Claude/Projects/Coworkmem/run_coworkmem.sh
```

---

## Context Cards

Each memory is a markdown file with YAML frontmatter stored in `~/Documents/Claude/Projects/Coworkmem/memories/`.

### Card format

```markdown
---
id: a3f9c1b2
created: 2026-05-07
session: "Brief description of this work session"
type: project
topics: [nextjs, vercel, groq]
title: "Blisstravel architecture"
importance: high
private: false
tokens: 94
---

## TL;DR
One sentence capturing the core fact or decision.

## Detail
2–4 sentences of compressed context. Includes why decisions were made and what outcomes occurred.

## Key Facts
- Concrete, self-contained fact (≤15 words each)
- File path, config value, preference, or technical detail

## Open Threads
- Work still in progress or next steps not yet done
```

### Card types

| Type | When to use | Token target |
|------|-------------|-------------|
| `project` | Ongoing project state, goals, architecture | ≤ 150 |
| `task` | A specific task completed or started | ≤ 80 |
| `decision` | A choice made with rationale | ≤ 90 |
| `learning` | Discovery, fix found, technique learned | ≤ 100 |
| `feedback` | User preference, correction, style guidance | ≤ 70 |
| `reference` | URL, file path, credential name, resource | ≤ 60 |
| `summary` | End-of-session rollup of multiple activities | ≤ 180 |

### Importance levels

| Level | Meaning |
|-------|---------|
| `high` | Critical context — always inject |
| `medium` | Useful background — inject if budget allows |
| `low` | Nice-to-have — only inject if very recent |

### Index file

Every card is tracked in `memories/INDEX.md`:

```markdown
# CoworkMem Index
_Last updated: 2026-05-08_

| Date | File | Title | Type | Topics | Importance | Private |
|------|------|-------|------|--------|------------|---------|
| 2026-05-08 | 2026-05-08_auth-redesign.md | Auth redesign decisions | decision | [auth, clerk] | high | false |
| 2026-05-07 | 2026-05-07_blisstravel.md | Blisstravel architecture | project | [nextjs, vercel] | high | false |
```

Claude maintains this automatically. Never delete rows — mark `private: true` instead.

---

## Session Injection

At the start of every session, the SessionStart hook:

1. Reads `INDEX.md` and scores all non-private cards
2. Scores each card: `high` importance +2, created ≤ 1 day ago +3, ≤ 7 days +2, ≤ 30 days +1
3. Selects top cards within the **1,200-token budget**
4. Injects TL;DR + up to 3 key facts per card

If `INDEX.md` doesn't exist or is empty, the hook fires silently with no output.

### What gets injected vs what stays hidden

| Content | Injected? |
|---------|-----------|
| TL;DR | ✅ Always |
| Key Facts (up to 3) | ✅ Always |
| Detail prose | ❌ Only via `/load-memory` |
| Open Threads | ✅ Surfaced as `⚡ Open:` line |
| Private cards | ❌ Never |

---

## Privacy

To keep something out of memory:

- Say **"don't save that"** or **"mark as private"** — Claude won't write the content and will set `private: true` if the card already exists
- Click the **👁 icon** in the web viewer to toggle any card private
- Private cards are stored on disk but never injected into sessions and are hidden by default in the viewer

CoworkMem stores everything **locally** on your machine. Nothing is sent to any server.

---

## File Structure

```
~/Documents/Claude/Projects/Coworkmem/
├── coworkmem.plugin          ← install this in Cowork
├── run_coworkmem.sh          ← launch the web viewer
├── plugin-src/               ← plugin source files
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── hooks/
│   │   ├── hooks.json        ← SessionStart hook config
│   │   └── scripts/
│   │       └── load_memory.py  ← hook script
│   ├── commands/
│   │   ├── save-memory.md
│   │   ├── load-memory.md
│   │   ├── capture-session.md
│   │   └── view-memories.md
│   └── skills/
│       └── coworkmem/
│           ├── SKILL.md
│           └── references/
│               └── card-format.md
├── scripts/
│   ├── memory_server.py      ← web viewer (zero-dependency Python)
│   ├── capture_session.py    ← standalone capture script
│   └── requirements.txt
└── memories/                 ← your context cards live here
    ├── INDEX.md
    ├── 2026-05-08_auth-redesign.md
    └── 2026-05-07_blisstravel.md
```

---

## Tips

**Save often.** Say "save this to memory" before ending any significant session. A 30-second save now prevents a 10-minute re-explanation later.

**Use specific titles.** `/save-memory API rate limiting decision` is more useful than `/save-memory notes`. Clear titles make `/load-memory` searches more accurate.

**One card per topic.** If a session covered three different things, Claude will naturally split them into separate cards. Don't try to force everything into one.

**Update project cards in place.** For ongoing projects, Claude will update an existing `project` card rather than creating a new one — keeping your index tidy.

**Private by default for sensitive content.** If you're discussing credentials, personal details, or anything sensitive, say "don't save this part" before sharing it.

---

## Troubleshooting

**Sessions aren't getting memory injected**

- Confirm the plugin is installed and enabled in Cowork
- Check that `memories/INDEX.md` exists and has rows
- Make sure cards don't all have `private: true`

**Web viewer won't start**

```bash
# Check if port 4242 is already in use
lsof -i tcp:4242

# Kill any existing process and restart
kill $(lsof -ti tcp:4242)
bash ~/Documents/Claude/Projects/Coworkmem/run_coworkmem.sh
```

**`/save-memory` saved a card but it doesn't appear in the viewer**

- Refresh the viewer (it auto-refreshes every 30s, or hit Reload)
- Check that the card file exists in `memories/` and isn't marked `private: true`

---

## Requirements

- **Claude Cowork** (desktop app)
- **Python 3** — for the web viewer (`python3 --version` to check)
- No other dependencies — the viewer uses Python's standard library only

---

## Repository

[github.com/gemraj29/coworkmem](https://github.com/gemraj29/coworkmem)
