---
description: Save current session context as a memory card
allowed-tools: Read, Write, Edit
argument-hint: [optional-title]
---

Create a CoworkMem context card capturing the most important content from this conversation.

1. Review the current session for significant content: decisions made, tasks completed or started, user preferences expressed, technical facts learned, project state changes, open threads.

2. Determine the best card type: project, task, decision, learning, feedback, reference, or summary.

3. Choose a title. If $ARGUMENTS is provided, use it as the card title. Otherwise derive a clear, descriptive title from the content.

4. Create the file at: `~/Documents/Claude/Projects/Coworkmem/memories/YYYY-MM-DD_<slug>.md`
   - Use today's date in YYYY-MM-DD format
   - `<slug>` = first 2–4 words of the title, lowercase, hyphen-separated

5. Write the card using the exact format from `${CLAUDE_PLUGIN_ROOT}/skills/coworkmem/references/card-format.md`.
   - Generate the `id` field: sha1(title+created)[:8]
   - Set `tokens` to the approximate word count of TL;DR + Key Facts + Open Threads
   - Set `private: false` unless the user has said the content is sensitive

6. Open `~/Documents/Claude/Projects/Coworkmem/memories/INDEX.md` and add a row at the top of the table (newest-first). If INDEX.md does not exist, create it with the standard header.

7. Confirm what was saved: show the card title, type, importance, and file path.

Do not include passwords, API keys, personal identifiable information, or anything the user has asked to keep private.
