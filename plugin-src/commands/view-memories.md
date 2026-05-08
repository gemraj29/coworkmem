---
description: Launch the CoworkMem web viewer at localhost:4242
allowed-tools: Bash(python3:*, lsof:*, kill:*, bash:*)
---

Launch the CoworkMem local web viewer so the user can browse, search, and manage all their memory cards.

1. Check if the viewer is already running:
   ```
   lsof -ti tcp:4242
   ```
   If it returns a PID, the server is already up — tell the user to open http://localhost:4242 and stop.

2. If not running, start it in the background:
   ```
   nohup python3 ~/Documents/Claude/Projects/Coworkmem/scripts/memory_server.py > /tmp/coworkmem-server.log 2>&1 &
   ```

3. Wait 1 second, then verify it started:
   ```
   lsof -ti tcp:4242
   ```

4. If successful, tell the user:
   "CoworkMem viewer is running at http://localhost:4242 — open it in your browser.
   
   Features: search memories, filter by type, click cards to expand details, click 👁 to mark any card as private."

5. If it failed to start, show the last 10 lines of `/tmp/coworkmem-server.log` and suggest checking that Python 3 is installed.
