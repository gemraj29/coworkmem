# CoworkMem Plugin

Persistent long-term memory for Claude Cowork sessions. Never lose context between sessions again.

## How it works

When you start a new session, CoworkMem automatically reads your saved context cards and injects the most relevant ones into Claude's context — so Claude already knows your project state, past decisions, and preferences without you having to repeat yourself.

## Components

| Component | Purpose |
|-----------|---------|
| Skill: `coworkmem` | Guides Claude on capturing, compressing, and injecting memory cards |
| Command: `/save-memory` | Save the current session to a context card |
| Command: `/load-memory [query]` | Browse and search past memory cards |
| Command: `/view-memories` | Launch the local web viewer at http://localhost:4242 |
| Command: `/capture-session` | AI-compress a full session transcript into cards |
| Hook: `SessionStart` | Auto-injects top memory cards at the start of every session |

## Setup

1. **Install this plugin** — accept it in Cowork
2. **Create the memories folder** — it's created automatically on first use at `~/Documents/Claude/Projects/Coworkmem/memories/`
3. **Install the viewer scripts** — the web viewer and capture script live at `~/Documents/Claude/Projects/Coworkmem/scripts/`

For the `/capture-session` command, set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Install the capture script dependency (one-time):
```bash
pip3 install anthropic --break-system-packages
```

## Usage

### Saving memory during a session
Say "save this to memory" or run `/save-memory [optional title]` at any point.

### Searching past work
Run `/load-memory api design` to find cards about API design, or `/load-memory` to see all.

### Browsing the memory viewer
Run `/view-memories` — Claude will launch a local web app at http://localhost:4242 with search, type filters, and privacy controls.

### Auto-compressing a full session
Run `/capture-session` and paste your session transcript. Claude Haiku will extract 2–6 structured cards automatically.

### Marking something private
Say "mark that as private" or "don't save that." Private cards are stored with `private: true`, never injected into sessions, and hidden in the viewer.

## Context Card Format

Each memory is a markdown file with YAML frontmatter:

```
memories/
├── INDEX.md                           ← card index (auto-maintained)
├── 2026-05-07_project-architecture.md
├── 2026-05-07_api-decisions.md
└── 2026-05-08_auth-refactor.md
```

Cards have types: `project`, `task`, `decision`, `learning`, `feedback`, `reference`, `summary`.

## Session Injection Budget

The hook injects up to **1,500 tokens** of context per session, prioritizing:
1. High-importance cards
2. Recently created cards (within 7 days)
3. Cards matching topics in your opening message
