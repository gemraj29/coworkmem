# CoworkMem — Context Card Format Reference

## File Format

```markdown
---
id: <8-char lowercase hex — sha1(title+created)[:8]>
created: YYYY-MM-DD
session: "Brief description of this work session"
type: project | task | decision | learning | feedback | reference | summary
topics: [topic1, topic2, topic3]
title: "Descriptive title in sentence case"
importance: high | medium | low
private: false
tokens: <integer — word count of TL;DR + Key Facts + Open Threads>
---

## TL;DR
One sentence capturing the core fact or decision.

## Detail
2–4 sentences of compressed context. Include *why* decisions were made and *what* outcomes occurred.

## Key Facts
- Concrete, self-contained fact (≤15 words each)
- File path, config value, preference, or technical detail
- As many as needed

## Open Threads
- Work still in progress
- Next steps decided but not done
```

The `## Open Threads` section is optional — omit if nothing is pending.

---

## Card Types and Token Targets

| Type | Use when | Target tokens |
|------|----------|--------------|
| `project` | Ongoing project state, goals, architecture | ≤ 150 |
| `task` | A specific task completed or started | ≤ 80 |
| `decision` | A choice made with rationale | ≤ 90 |
| `learning` | Discovery, fix found, technique learned | ≤ 100 |
| `feedback` | User preference, correction, style guidance | ≤ 70 |
| `reference` | URL, file path, credential name, resource | ≤ 60 |
| `summary` | End-of-session rollup of multiple activities | ≤ 180 |

---

## Generating the ID

```python
import hashlib
card_id = hashlib.sha1(f"{title}{created}".encode()).hexdigest()[:8]
```

---

## Example Card

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
CoworkMem stores context cards as markdown files and injects them at session start within a 1,500-token budget.

## Detail
Cards use YAML frontmatter for metadata and markdown sections for content. The web viewer is a zero-dependency Python HTTP server. Private cards are stored but never injected or shown in search results.

## Key Facts
- Memory dir: ~/Documents/Claude/Projects/Coworkmem/memories/
- Viewer port: 4242
- Token budget per session injection: 1500
- Launcher: bash ~/Documents/Claude/Projects/Coworkmem/run_coworkmem.sh

## Open Threads
- Add semantic search using embeddings
```
