#!/usr/bin/env python3
"""
CoworkMem — Stop hook v0.2
Fires when Claude finishes generating a response.
Checks if the session has accumulated enough significant content to warrant
a save reminder, then injects a gentle nudge into the context.
Output: JSON {"decision": "approve", "reason": "<nudge or empty>"}
"""
import json
import os
import sys
from datetime import date, datetime

MEMORIES_DIR = os.path.expanduser("~/Documents/Claude/Projects/Coworkmem/memories")
STATE_FILE = os.path.join(MEMORIES_DIR, ".session_state.json")

# Minimum number of tool calls / turns before we suggest saving
MIN_TURNS_BEFORE_NUDGE = 8

# Keywords that signal the user is wrapping up
END_OF_SESSION_SIGNALS = {
    "thanks", "thank you", "done", "finished", "that's all", "thats all",
    "goodbye", "bye", "end session", "all done", "wrap up", "wrapping up",
    "that's it", "thats it", "perfect", "great job", "looks good",
    "ship it", "merge it", "let's stop", "lets stop", "stop here",
}


def read_hook_event():
    """Read the Stop hook event from stdin."""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                return json.loads(raw)
    except Exception:
        pass
    return {}


def load_state():
    """Load session state — tracks turn count and whether we've already nudged."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            # Reset state if it's from a different calendar day
            if state.get("date") != str(date.today()):
                return fresh_state()
            return state
        except Exception:
            pass
    return fresh_state()


def fresh_state():
    return {"date": str(date.today()), "turns": 0, "nudged": False}


def save_state(state):
    os.makedirs(MEMORIES_DIR, exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def has_recent_save():
    """Check if a memory card was saved in the last 10 minutes."""
    if not os.path.isdir(MEMORIES_DIR):
        return False
    cutoff = datetime.now().timestamp() - 600
    for fname in os.listdir(MEMORIES_DIR):
        if fname.endswith(".md") and fname != "INDEX.md":
            fpath = os.path.join(MEMORIES_DIR, fname)
            if os.path.getmtime(fpath) > cutoff:
                return True
    return False


def is_end_of_session(prompt):
    """Check if the user's last message signals they're wrapping up."""
    if not prompt:
        return False
    lower = prompt.lower().strip()
    return any(signal in lower for signal in END_OF_SESSION_SIGNALS)


def main():
    event = read_hook_event()
    prompt = event.get("prompt", "") or event.get("message", "") or ""

    state = load_state()
    state["turns"] = state.get("turns", 0) + 1
    save_state(state)

    # Only nudge if:
    # 1. Enough turns have happened (session is substantial)
    # 2. We haven't already nudged this session
    # 3. No card was saved recently (they haven't already saved)
    # 4. The user's message looks like a session-ender
    if (
        state["turns"] >= MIN_TURNS_BEFORE_NUDGE
        and not state.get("nudged", False)
        and not has_recent_save()
        and is_end_of_session(prompt)
    ):
        state["nudged"] = True
        save_state(state)
        nudge = (
            "\n\n💾 CoworkMem: This looks like a good stopping point. "
            "Run `/save-memory` to capture this session before you go."
        )
        print(json.dumps({"decision": "approve", "reason": nudge}))
    else:
        print(json.dumps({"decision": "approve", "reason": ""}))


if __name__ == "__main__":
    main()
