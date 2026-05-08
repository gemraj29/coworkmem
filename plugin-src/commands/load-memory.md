---
description: Load and display memories from past sessions
allowed-tools: Read, Glob
argument-hint: [search-query or topic]
---

Retrieve and display CoworkMem context cards from past sessions.

1. Read `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md` to get the full card list.

2. If $ARGUMENTS is provided, treat it as a search query. Filter to cards whose title, topics, or type contain any of the query terms (case-insensitive). If no argument, show all cards.

3. Sort results by date descending (newest first). Show at most 15 cards unless the user asked for more.

4. For each matching card, read the full file and display:
   - Title, type badge, date, importance level
   - TL;DR
   - Key Facts (bullet list)
   - Open Threads if present
   - Whether it is marked private (show a 🔒 but do NOT display the body of private cards)

5. End with a one-line summary: "X cards found. Run `/view-memories` to open the full browser at localhost:4242."

If no cards match, say so clearly and suggest running `/save-memory` to start building memory.
