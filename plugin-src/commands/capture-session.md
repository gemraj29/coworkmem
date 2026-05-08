---
description: Compress a session transcript into memory cards
allowed-tools: Read, Write, Edit
argument-hint: [session-title]
---

Compress a full session transcript into structured CoworkMem context cards — no API key needed.

The session title is: $ARGUMENTS

Steps:

1. If $ARGUMENTS is empty, ask the user: "What should I call this session? (e.g. 'API redesign', 'Onboarding flow work')"

2. Ask the user to paste their session transcript and send it.

3. Once the transcript is provided, read it carefully and extract 2–6 context cards. For each card, identify a distinct topic, decision, task, learning, or piece of project state.

4. Apply these compression rules:
   - Include: decisions + rationale, tasks completed/started, user preferences, technical facts, project state changes, open threads
   - Omit: conversational filler, step-by-step reasoning visible in files, temporary debug output, private/sensitive content
   - Be ruthlessly concise — every word must earn its place

5. For each card, create a file at `~/Documents/Claude/Projects/Coworkmem/memories/YYYY-MM-DD_<slug>.md` using the exact format from `${CLAUDE_PLUGIN_ROOT}/skills/coworkmem/references/card-format.md`.
   - Use today's date
   - Generate id: sha1(title+created)[:8]
   - Set tokens to approximate word count of TL;DR + Key Facts + Open Threads
   - Set private: false (unless content is clearly sensitive)

6. Add a row to `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md` for each card, newest-first.

7. Show a summary of what was saved: one line per card with title, type, and importance.
