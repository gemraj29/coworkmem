# CoworkMem Roadmap

> Planned improvements, in priority order. Each phase builds on the last.

---

## Current State — v0.1.0

- SessionStart hook injects top cards (TL;DR + key facts, 1,200-token budget)
- Cards scored by importance + recency
- Manual save via `/save-memory`, search via `/load-memory`
- `/capture-session` compresses pasted transcripts into cards
- Google Search-style web viewer at localhost:4242
- Privacy controls — `private: true` cards never injected or shown
- Local markdown files, zero external dependencies

---

## Phase 1 — Smarter Injection `v0.2`

**Goal:** Make the right cards show up at the right time without the user doing anything.

### Topic-aware injection scoring

Parse the user's opening message and boost cards whose topics match. If the session starts with "let's work on the auth flow", auth-related cards rank higher regardless of age.

- Add topic-matching score: +3 if card topics overlap with opening message keywords
- Extract keywords from first user message in the hook script
- Update `load_memory.py` scoring logic

### Project-aware filtering

Add a `project` field to context cards. The hook detects which project is active (from the opening message or an explicit `/set-project` command) and filters to relevant cards only.

- New frontmatter field: `project: my-project-name`
- `/set-project <name>` command to set active project for session
- Hook reads active project and boosts matching cards

### SessionEnd auto-save prompt

When a session ends or goes idle, Claude checks if anything significant happened and prompts to save — so nothing gets lost even if the user forgets.

- New `SessionStop` hook
- Detects if session had meaningful content (decisions, tasks, technical facts)
- Prompts: "This session covered X — save a memory card?"

---

## Phase 2 — Better Search `v0.3`

**Goal:** Find the right memory even when you don't remember the exact words.

### Semantic search

Replace keyword matching in `/load-memory` with embedding-based similarity search. "What did I decide about the database?" finds the right card even if it never uses the word "database".

- Use `sentence-transformers` (local, no API key needed) to embed cards on save
- Store embeddings alongside card files
- `/load-memory` queries by cosine similarity, not just string match

### Full-text search in viewer

The web viewer currently filters on title and topics only. Extend to search across TL;DR, key facts, detail, and open threads.

- Update `memory_server.py` search endpoint to index full card content
- Highlight matching text in results

### Related cards

When viewing a card, surface other cards that share topics or were created in the same session.

- Add "Related" section at the bottom of expanded cards in the viewer
- Link by shared topics or `session` field

---

## Phase 3 — Memory Management `v0.4`

**Goal:** Keep the memory store clean and manageable over time.

### Card deduplication

Detect cards with similar titles or overlapping topics and suggest merging them into one updated card.

- `/dedupe-memory` command
- Claude compares all cards, flags near-duplicates
- User confirms merge; Claude combines and removes the old cards

### Auto-archive

Cards older than 90 days with no recent access move to an "archived" state — still searchable but excluded from session injection.

- Add `archived: true` frontmatter field
- Archiving runs automatically when the hook loads cards
- `/load-memory` shows archived cards with a faded badge
- `/unarchive <title>` to restore a card to active

### Card editing in viewer

Edit cards directly in the browser — fix a key fact, update the TL;DR, mark an open thread as done — without needing to open the markdown file.

- Edit button on each card in the viewer
- Inline form for TL;DR, key facts, open threads
- Saves back to the `.md` file via a `POST /api/update-card` endpoint

### Scheduled review reminders

Periodically prompt the user to review and update old cards so they stay accurate.

- New `/review-memory` command
- Shows cards not updated in 30+ days, one at a time
- User can confirm still accurate, update, or archive

---

## Phase 4 — Multi-project Support `v0.5`

**Goal:** Work on multiple projects without memory bleeding between them.

### Project namespacing

Cards belong to a project. Sessions only inject cards from the active project.

```
memories/
├── my-app/
│   ├── INDEX.md
│   └── 2026-05-08_auth-decisions.md
├── blog-redesign/
│   ├── INDEX.md
│   └── 2026-05-07_layout-choices.md
└── personal/
    └── INDEX.md
```

- `/set-project <name>` — sets active project for session
- `/list-projects` — shows all projects with card counts
- Hook reads active project from a config file
- Viewer has a project switcher in the top bar

### Cross-project search

Search across all projects at once when needed.

- `/load-memory --all <query>` flag to search globally
- Viewer has an "All Projects" tab

---

## Phase 5 — MCP Server Mode `v0.6`

**Goal:** Let Claude query memory on-demand mid-session, not just at the start.

### CoworkMem as an MCP tool

Expose memory as an MCP server so Claude can do real-time lookups during a session — not just rely on what was injected at startup.

Tools exposed:
- `search_memory(query)` — semantic search across all cards
- `save_card(title, type, tldr, key_facts, topics)` — save a new card
- `update_card(id, changes)` — update an existing card
- `list_cards(project, type, limit)` — list cards with filters

Benefits:
- Claude can say "let me check my memory" mid-conversation
- Cards can be saved without a slash command
- Much more responsive than hook-based injection

---

## Phase 6 — Backup and Sync `v0.7`

**Goal:** Never lose memories, access them anywhere.

### Auto git backup

After every `/save-memory`, automatically commit the memories folder to a git repo. Full history of every card ever written.

- Config option: `backup_git_repo: ~/Documents/Claude/Projects/Coworkmem`
- Auto-commit message: `CoworkMem: saved "<card title>"`
- Optional auto-push to remote (requires GitHub token in config)

### iCloud sync

Store memories in iCloud Drive so they're available across your devices.

- Config option: `memories_dir: ~/Library/Mobile Documents/com~apple~CloudDocs/CoworkMem/memories`
- Works automatically once the path is changed

### Export and import

- `/export-memory` — export all cards as a single JSON or ZIP file
- `/import-memory <file>` — import cards from another machine or backup
- Import from Obsidian vault (reads existing markdown frontmatter)

---

## Phase 7 — Analytics and Insights `v0.8`

**Goal:** Understand your own working patterns through your memory store.

### Usage dashboard in viewer

A new "Insights" tab in the web viewer showing:

- Cards saved per week (bar chart)
- Breakdown by card type (pie chart)
- Most active topics
- Injection budget usage per session
- Cards approaching auto-archive threshold

### Memory health score

A simple score (0–100) reflecting the quality and freshness of your memory store:

- Penalises stale cards, duplicate topics, cards with empty open threads that were never closed
- Surfaces actionable suggestions: "3 cards haven't been reviewed in 60 days"

---

## Backlog — No Fixed Phase

Ideas being considered but not yet scheduled:

- **Dark mode toggle** in the web viewer
- **Card templates** per type — pre-filled structure for decisions, tasks, etc.
- **Notion import** — pull pages from a Notion workspace as reference cards
- **Sharing** — export a read-only HTML snapshot of your memory store
- **Card links** — reference one card from another (e.g. a task card links to its parent project)
- **Voice save** — dictate a memory card using macOS speech recognition
- **Weekly digest** — auto-generated summary of what was saved that week

---

## Contributing

Issues and PRs welcome at [github.com/gemraj29/coworkmem](https://github.com/gemraj29/coworkmem).

When suggesting a feature, please describe: the problem it solves, the user interaction, and which phase it fits into.

---

_Last updated: 2026-05-08_
