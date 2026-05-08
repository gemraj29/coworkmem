---
description: Set the active project so CoworkMem injects only relevant cards
allowed-tools: Read, Write, Bash(python3:*)
argument-hint: <project-name>
---

Set the active project for CoworkMem. Future sessions will boost cards tagged with this project and show it in the session injection header.

The project name is: $ARGUMENTS

Steps:

1. If $ARGUMENTS is empty, read the current config and tell the user:
   "Active project: <name> (or none set). Usage: `/set-project <name>` to switch, `/set-project clear` to unset."

2. If $ARGUMENTS is "clear" or "none":
   - Write `{}` to `~/Documents/Claude/Projects/Coworkmem/memories/.coworkmem_config.json`
   - Confirm: "Active project cleared — all cards will be scored equally."

3. Otherwise:
   - Normalise the project name: lowercase, replace spaces with hyphens, strip special chars
   - Write to `~/Documents/Claude/Projects/Coworkmem/memories/.coworkmem_config.json`:
     ```json
     {
       "active_project": "<normalised-name>",
       "updated": "<YYYY-MM-DD>"
     }
     ```
   - Confirm: "Active project set to **<name>**. Cards tagged `project: <name>` will get a +2 boost in future sessions."
   - Remind the user: "Tag your context cards with `project: <name>` in their frontmatter to take advantage of filtering."

4. Do not create the memories directory if it does not exist — just report an error if the path is inaccessible.
