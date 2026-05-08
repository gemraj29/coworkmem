#!/usr/bin/env python3
"""
CoworkMem — Local Memory Viewer
================================
Zero-dependency web server for browsing, searching, and managing context cards.
Runs at http://localhost:4242

Usage:
    python3 memory_server.py
    python3 memory_server.py --port 4242 --memories-dir ~/Documents/Claude/Projects/Coworkmem/memories
"""

import argparse
import datetime
import http.server
import json
import os
import re
import socketserver
import sys
import urllib.parse
import webbrowser
from threading import Timer

MEMORIES_DIR = os.path.expanduser("~/Documents/Claude/Projects/Coworkmem/memories")
DEFAULT_PORT = 4242

# ─────────────────────────────────────────────────────────────────────────────
# FRONTMATTER PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    yaml_str = parts[1].strip()
    body = parts[2].strip()
    meta = {}

    for line in yaml_str.split("\n"):
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()

        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            val = [v.strip().strip("\"'") for v in inner.split(",") if v.strip()]
        elif val.lower() == "true":
            val = True
        elif val.lower() == "false":
            val = False
        elif val.isdigit():
            val = int(val)
        elif val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            val = val[1:-1]

        meta[key] = val

    return meta, body


def parse_sections(body: str) -> dict:
    """Parse ## Section headers from markdown body."""
    sections = {}
    current = None
    current_lines = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(current_lines).strip()
            current = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current is not None:
        sections[current] = "\n".join(current_lines).strip()

    return sections


def parse_list_section(text: str) -> list[str]:
    """Parse a markdown bullet list into a Python list."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
        elif line.startswith("• "):
            items.append(line[2:].strip())
    return items


def load_card(filepath: str) -> dict | None:
    """Load and parse a context card markdown file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError):
        return None

    meta, body = parse_frontmatter(content)
    if not meta:
        return None

    sections = parse_sections(body)

    key_facts_raw = sections.get("Key Facts", "")
    open_threads_raw = sections.get("Open Threads", "")

    card = {
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "id": meta.get("id", ""),
        "created": meta.get("created", ""),
        "session": meta.get("session", ""),
        "type": meta.get("type", "summary"),
        "topics": meta.get("topics", []) if isinstance(meta.get("topics"), list) else [],
        "title": meta.get("title", os.path.basename(filepath)),
        "importance": meta.get("importance", "medium"),
        "private": meta.get("private", False),
        "tokens": meta.get("tokens", 0),
        "tldr": sections.get("TL;DR", ""),
        "detail": sections.get("Detail", ""),
        "key_facts": parse_list_section(key_facts_raw),
        "open_threads": parse_list_section(open_threads_raw),
        "_raw": content,
    }

    return card


def load_all_cards(memories_dir: str) -> list[dict]:
    """Load all .md context cards from the memories directory."""
    if not os.path.isdir(memories_dir):
        return []

    cards = []
    for fname in sorted(os.listdir(memories_dir), reverse=True):
        if not fname.endswith(".md") or fname == "INDEX.md":
            continue
        card = load_card(os.path.join(memories_dir, fname))
        if card:
            cards.append(card)

    return cards


def toggle_private(filepath: str) -> bool:
    """Toggle the private flag in a card file. Returns new private value."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if "private: false" in content:
            new_content = content.replace("private: false", "private: true", 1)
            new_val = True
        elif "private: true" in content:
            new_content = content.replace("private: true", "private: false", 1)
            new_val = False
        else:
            return False

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Update INDEX.md
        index_path = os.path.join(os.path.dirname(filepath), "INDEX.md")
        fname = os.path.basename(filepath)
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                idx = f.read()
            # Find row with this filename and toggle its private column
            lines = idx.split("\n")
            for i, line in enumerate(lines):
                if fname in line:
                    if "| false |" in line and new_val:
                        lines[i] = line.replace("| false |", "| true |", 1)
                    elif "| true |" in line and not new_val:
                        lines[i] = line.replace("| true |", "| false |", 1)
                    break
            with open(index_path, "w") as f:
                f.write("\n".join(lines))

        return new_val
    except Exception as e:
        print(f"Error toggling private: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# HTML TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CoworkMem — Memory Viewer</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #fff;
    color: #202124;
    font-family: arial, sans-serif;
    min-height: 100vh;
  }

  /* ── Top bar (Google-style) ── */
  .topbar {
    display: flex; align-items: center; gap: 20px;
    padding: 12px 24px 0;
    border-bottom: 1px solid #e0e0e0;
    background: #fff;
    position: sticky; top: 0; z-index: 100;
    flex-wrap: wrap;
  }
  .logo {
    font-family: arial, sans-serif; font-size: 1.5rem; font-weight: 400;
    letter-spacing: -0.5px; white-space: nowrap;
    padding-bottom: 10px;
    text-decoration: none;
  }
  .logo .g1 { color: #4285f4; }
  .logo .g2 { color: #ea4335; }
  .logo .g3 { color: #fbbc05; }
  .logo .g4 { color: #4285f4; }
  .logo .g5 { color: #34a853; }
  .logo .g6 { color: #ea4335; }
  .logo .gm { color: #202124; }

  .search-wrap {
    flex: 1; max-width: 580px; position: relative; padding-bottom: 10px;
  }
  .search-wrap input {
    width: 100%;
    border: 1px solid #dfe1e5;
    border-radius: 24px;
    padding: 10px 46px 10px 18px;
    font-size: 0.95rem;
    color: #202124;
    outline: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    transition: box-shadow 0.2s, border-color 0.2s;
    background: #fff;
  }
  .search-wrap input:focus {
    border-color: rgba(223,225,229,0);
    box-shadow: 0 1px 6px rgba(32,33,36,0.28);
  }
  .search-wrap input::placeholder { color: #9aa0a6; }
  .search-icon {
    position: absolute; right: 16px; top: 50%; transform: translateY(-60%);
    color: #9aa0a6; pointer-events: none;
  }

  /* ── Filter chips (Google Search tabs style) ── */
  .filters {
    display: flex; gap: 0; overflow-x: auto; padding: 0 24px;
    border-bottom: 1px solid #e0e0e0;
    background: #fff;
    position: sticky; top: 57px; z-index: 99;
    scrollbar-width: none;
  }
  .filters::-webkit-scrollbar { display: none; }
  .filter-btn {
    padding: 11px 14px; border: none; border-bottom: 3px solid transparent;
    background: transparent; color: #5f6368; font-size: 0.8rem;
    cursor: pointer; font-family: arial, sans-serif; white-space: nowrap;
    transition: color 0.15s, border-color 0.15s;
    display: flex; align-items: center; gap: 5px;
  }
  .filter-btn:hover { color: #202124; background: #f8f9fa; }
  .filter-btn.active { color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 500; }
  .filter-btn .chip-dot { width: 7px; height: 7px; border-radius: 50%; }

  /* ── Results container ── */
  .results-meta {
    padding: 10px 24px; font-size: 0.82rem; color: #70757a;
  }
  .results-list { padding: 4px 24px 40px; max-width: 720px; }

  /* ── Search result card ── */
  .card {
    padding: 18px 0 20px;
    border-bottom: 1px solid #ebebeb;
  }
  .card:last-child { border-bottom: none; }
  .card.private-card { opacity: 0.6; }

  .card-source {
    display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
  }
  .card-favicon {
    width: 18px; height: 18px; border-radius: 50%; display: flex;
    align-items: center; justify-content: center; font-size: 10px;
    flex-shrink: 0; font-weight: 700; color: #fff;
  }
  .card-breadcrumb {
    font-size: 0.82rem; color: #202124; line-height: 1.3;
  }
  .card-breadcrumb .crumb-path { color: #5f6368; }

  .card-title-link {
    font-size: 1.12rem; color: #1a0dab; font-weight: 400; line-height: 1.4;
    cursor: default; display: block; margin-bottom: 5px;
  }
  .card-title-link:hover { text-decoration: underline; }
  .card.private-card .card-title-link { color: #5f6368; }

  .card-snippet {
    font-size: 0.875rem; color: #4d5156; line-height: 1.58; margin-bottom: 8px;
  }

  .card-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .chip {
    padding: 3px 10px; border-radius: 999px; font-size: 0.73rem;
    border: 1px solid; font-weight: 500; color: inherit;
    background: transparent;
  }

  .expand-btn {
    background: none; border: none; cursor: pointer; color: #1a73e8;
    font-size: 0.8rem; padding: 0; display: inline-flex; align-items: center; gap: 3px;
    font-family: arial, sans-serif;
  }
  .expand-btn:hover { text-decoration: underline; }

  .card-detail { display: none; margin-top: 10px; }
  .card-detail.open { display: block; }
  .detail-section { margin-bottom: 10px; }
  .section-label {
    font-size: 0.73rem; font-weight: 700; color: #5f6368;
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 5px;
  }
  .fact-list { list-style: none; }
  .fact-list li {
    font-size: 0.85rem; color: #4d5156; padding: 3px 0 3px 14px;
    position: relative; line-height: 1.5;
  }
  .fact-list li::before { content: "–"; position: absolute; left: 0; color: #9aa0a6; }
  .thread-list li::before { content: "⚡"; font-size: 0.75em; }
  .detail-text { font-size: 0.875rem; color: #4d5156; line-height: 1.6; }

  .private-overlay { font-size: 0.84rem; color: #9aa0a6; font-style: italic; margin-top: 6px; }

  .private-btn {
    background: none; border: none; cursor: pointer; font-size: 0.82rem;
    color: #9aa0a6; padding: 0 4px; transition: color 0.15s;
    margin-left: auto;
  }
  .private-btn:hover { color: #5f6368; }
  .private-btn.is-private { color: #ea4335; }
  .imp-badge {
    font-size: 0.68rem; padding: 1px 6px; border-radius: 3px;
    font-weight: 600; letter-spacing: 0.03em; text-transform: uppercase;
  }
  .imp-high { background: #fce8e6; color: #c5221f; }
  .imp-medium { background: #fef7e0; color: #b06000; }
  .imp-low { background: #f1f3f4; color: #5f6368; }

  /* ── Empty state ── */
  .empty { padding: 60px 0; color: #9aa0a6; font-size: 0.95rem; }
  .empty p { margin-bottom: 6px; }

  /* ── Highlight ── */
  mark { background: #fce8a4; color: inherit; border-radius: 1px; padding: 0 1px; }

  /* ── Type palette (light) ── */
  .c-project  { color: #1967d2; border-color: #c3d7f7; }
  .c-task     { color: #137333; border-color: #c8e6c9; }
  .c-decision { color: #681da8; border-color: #e8d5fb; }
  .c-learning { color: #b06000; border-color: #fde8a4; }
  .c-feedback { color: #c2185b; border-color: #fce4ec; }
  .c-reference{ color: #5f6368; border-color: #e0e0e0; }
  .c-summary  { color: #007b83; border-color: #b2ebf2; }

  .bg-project  { background: #4285f4; }
  .bg-task     { background: #34a853; }
  .bg-decision { background: #9c27b0; }
  .bg-learning { background: #f9ab00; }
  .bg-feedback { background: #e91e63; }
  .bg-reference{ background: #9aa0a6; }
  .bg-summary  { background: #00bcd4; }

  ::-webkit-scrollbar { width: 8px; }
  ::-webkit-scrollbar-track { background: #f1f3f4; }
  ::-webkit-scrollbar-thumb { background: #c8c9ca; border-radius: 4px; }
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">
    <span class="g1">C</span><span class="g2">o</span><span class="g3">w</span><span class="g4">o</span><span class="g5">r</span><span class="g6">k</span><span class="gm">Mem</span>
  </div>
  <div class="search-wrap">
    <input type="text" id="searchInput" placeholder="Search memories…" autocomplete="off" />
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
  </div>
</div>

<div class="filters" id="filterBar">
  <button class="filter-btn active" data-type="all">🧠 All</button>
  <button class="filter-btn" data-type="project"><span class="chip-dot bg-project"></span>Project</button>
  <button class="filter-btn" data-type="task"><span class="chip-dot bg-task"></span>Task</button>
  <button class="filter-btn" data-type="decision"><span class="chip-dot bg-decision"></span>Decision</button>
  <button class="filter-btn" data-type="learning"><span class="chip-dot bg-learning"></span>Learning</button>
  <button class="filter-btn" data-type="feedback"><span class="chip-dot bg-feedback"></span>Feedback</button>
  <button class="filter-btn" data-type="reference"><span class="chip-dot bg-reference"></span>Reference</button>
  <button class="filter-btn" data-type="summary"><span class="chip-dot bg-summary"></span>Summary</button>
  <button class="filter-btn" data-type="private">🔒 Private</button>
</div>

<div class="results-meta" id="statsBar">Loading…</div>
<div class="results-list" id="cardsGrid"></div>

<script>
const TYPE_COLORS = {
  project: '#3b82f6', task: '#10b981', decision: '#8b5cf6',
  learning: '#f59e0b', feedback: '#ec4899', reference: '#64748b', summary: '#14b8a6'
};

let allCards = [];
let activeType = 'all';
let searchQuery = '';

// ── Load cards from server ──────────────────────────────────────────────────
async function loadCards() {
  try {
    const res = await fetch('/api/memories');
    allCards = await res.json();
    render();
  } catch(e) {
    document.getElementById('cardsGrid').innerHTML = '<div class="empty"><p>Could not load memories</p><small>' + e.message + '</small></div>';
  }
}

// ── Render ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function highlight(text, query) {
  if (!query) return escHtml(text);
  const escaped = query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
  const re = new RegExp('(' + escaped + ')', 'gi');
  return escHtml(text).replace(re, '<mark>$1</mark>');
}

function matchesSearch(card, q) {
  if (!q) return true;
  const haystack = [
    card.title, card.tldr, card.detail, card.session,
    ...card.key_facts, ...card.open_threads, ...card.topics
  ].join(' ').toLowerCase();
  return q.toLowerCase().split(' ').every(word => haystack.includes(word));
}

function renderCard(card, query) {
  const isPrivate = card.private;
  const typeClass = 'c-' + (card.type || 'reference');
  const bgClass = 'bg-' + (card.type || 'reference');
  const typeLabel = (card.type || 'summary').charAt(0).toUpperCase() + (card.type || 'summary').slice(1);
  const dateStr = card.created ? escHtml(card.created) : '';
  const sessionStr = card.session ? escHtml(card.session) : '';

  const chipsHtml = (card.topics || []).map(t =>
    `<span class="chip ${typeClass}">${escHtml(t)}</span>`
  ).join('');

  const factsHtml = card.key_facts.length
    ? `<div class="detail-section"><div class="section-label">Key Facts</div><ul class="fact-list">${card.key_facts.map(f => `<li>${highlight(f, query)}</li>`).join('')}</ul></div>`
    : '';
  const threadsHtml = card.open_threads.length
    ? `<div class="detail-section"><div class="section-label">Open Threads</div><ul class="fact-list thread-list">${card.open_threads.map(t => `<li>${highlight(t, query)}</li>`).join('')}</ul></div>`
    : '';
  const detailTextHtml = card.detail
    ? `<div class="detail-section"><div class="detail-text">${highlight(card.detail, query)}</div></div>`
    : '';

  const hasDetail = !isPrivate && (card.detail || card.key_facts.length || card.open_threads.length);

  const snippetHtml = isPrivate
    ? `<div class="private-overlay">🔒 Content hidden — marked as private</div>`
    : `<div class="card-snippet">${highlight(card.tldr, query)}</div>`;

  return `
    <div class="card${isPrivate ? ' private-card' : ''}" data-filename="${escHtml(card.filename)}">
      <div class="card-source">
        <div class="card-favicon ${bgClass}">${typeLabel[0]}</div>
        <div class="card-breadcrumb">
          coworkmem › <span class="crumb-path">${escHtml(typeLabel)}</span>
          ${dateStr ? `<span class="crumb-path"> · ${dateStr}</span>` : ''}
          ${sessionStr ? `<span class="crumb-path"> · ${sessionStr}</span>` : ''}
        </div>
        <button class="private-btn${isPrivate ? ' is-private' : ''}" onclick="togglePrivate('${escHtml(card.filename)}', this)" title="${isPrivate ? 'Unmark private' : 'Mark as private'}">
          ${isPrivate ? '🔒' : '👁'}
        </button>
      </div>
      <div class="card-title-link">${highlight(card.title, query)}</div>
      ${snippetHtml}
      <div class="card-chips">
        ${chipsHtml}
        <span class="imp-badge imp-${card.importance}">${escHtml(card.importance)}</span>
      </div>
      ${hasDetail ? `
        <button class="expand-btn" onclick="toggleExpand(this)">
          <span class="expand-arrow">▾</span> More details
        </button>
        <div class="card-detail open">
          ${detailTextHtml}${factsHtml}${threadsHtml}
        </div>
      ` : ''}
    </div>
  `;
}

function render() {
  const q = searchQuery.trim();
  let filtered = allCards.filter(c => {
    if (activeType === 'private') return c.private === true;
    if (activeType !== 'all' && c.type !== activeType) return false;
    return matchesSearch(c, q);
  });

  const grid = document.getElementById('cardsGrid');
  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty"><p>No results found${q ? ` for "<strong>${escHtml(q)}</strong>"` : ''}</p><p style="margin-top:4px;font-size:0.85rem">Try different keywords or create some context cards to get started.</p></div>`;
  } else {
    grid.innerHTML = filtered.map(c => renderCard(c, q)).join('');
  }

  // Stats — Google-style "About N results"
  const total = allCards.length;
  const privateCount = allCards.filter(c => c.private).length;
  const shown = filtered.length;
  const statsEl = document.getElementById('statsBar');
  statsEl.innerHTML = shown === total
    ? `About <strong>${total}</strong> result${total !== 1 ? 's' : ''} &nbsp;·&nbsp; ${privateCount} private`
    : `About <strong>${shown}</strong> of ${total} result${total !== 1 ? 's' : ''} &nbsp;·&nbsp; ${privateCount} private`;
}

// ── Toggle expand ────────────────────────────────────────────────────────────
function toggleExpand(btn) {
  const detail = btn.nextElementSibling;
  const arrow = btn.querySelector('.expand-arrow');
  const isOpen = detail.classList.toggle('open');
  arrow.textContent = isOpen ? '▾' : '▸';
  btn.childNodes[1].textContent = isOpen ? ' Less' : ' More details';
}

// ── Toggle private ───────────────────────────────────────────────────────────
async function togglePrivate(filename, btn) {
  try {
    const res = await fetch('/api/toggle-private', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filename})
    });
    const data = await res.json();
    if (data.ok) {
      // Update local state
      const card = allCards.find(c => c.filename === filename);
      if (card) card.private = data.private;
      render();
    }
  } catch(e) {
    alert('Error toggling private: ' + e.message);
  }
}

// ── Search ───────────────────────────────────────────────────────────────────
document.getElementById('searchInput').addEventListener('input', e => {
  searchQuery = e.target.value;
  render();
});

// ── Filters ──────────────────────────────────────────────────────────────────
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeType = btn.dataset.type;
    render();
  });
});

// ── Keyboard shortcut: / to focus search ─────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== document.getElementById('searchInput')) {
    e.preventDefault();
    document.getElementById('searchInput').focus();
  }
  if (e.key === 'Escape') {
    document.getElementById('searchInput').value = '';
    searchQuery = '';
    render();
  }
});

// ── Init ─────────────────────────────────────────────────────────────────────
loadCards();

// Auto-refresh every 30s (catches new cards from Claude)
setInterval(loadCards, 30000);
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# HTTP SERVER
# ─────────────────────────────────────────────────────────────────────────────

memories_dir = MEMORIES_DIR  # set in main()


class CoworkmemHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default access logging; print a cleaner version
        if args[1] != "200":
            print(f"  {args[0]}  [{args[1]}]")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/" or path == "/index.html":
            self.send_html(HTML_TEMPLATE)

        elif path == "/api/memories":
            cards = load_all_cards(memories_dir)
            # Don't send _raw field to keep payload small
            safe = [{k: v for k, v in c.items() if k != "_raw"} for c in cards]
            self.send_json(safe)

        elif path == "/api/stats":
            cards = load_all_cards(memories_dir)
            stats = {
                "total": len(cards),
                "private": sum(1 for c in cards if c.get("private")),
                "by_type": {},
                "by_importance": {},
            }
            for c in cards:
                stats["by_type"][c.get("type", "?")] = stats["by_type"].get(c.get("type", "?"), 0) + 1
                stats["by_importance"][c.get("importance", "?")] = (
                    stats["by_importance"].get(c.get("importance", "?"), 0) + 1
                )
            self.send_json(stats)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if path == "/api/toggle-private":
            try:
                data = json.loads(body)
                filename = data.get("filename", "")
                if not filename or ".." in filename:
                    self.send_json({"ok": False, "error": "Invalid filename"}, 400)
                    return

                filepath = os.path.join(memories_dir, filename)
                if not os.path.isfile(filepath):
                    self.send_json({"ok": False, "error": "File not found"}, 404)
                    return

                new_val = toggle_private(filepath)
                print(f"  {'🔒' if new_val else '👁 '} {filename} → private={new_val}")
                self.send_json({"ok": True, "private": new_val})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    global memories_dir

    parser = argparse.ArgumentParser(description="CoworkMem — Local Memory Viewer")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    parser.add_argument(
        "--memories-dir",
        default=MEMORIES_DIR,
        help=f"Path to memories directory (default: {MEMORIES_DIR})",
    )
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    memories_dir = os.path.expanduser(args.memories_dir)
    os.makedirs(memories_dir, exist_ok=True)

    cards = load_all_cards(memories_dir)

    print()
    print("  🧠 CoworkMem Memory Viewer")
    print(f"  Memories: {memories_dir}")
    print(f"  Cards loaded: {len(cards)}")
    print(f"  URL: http://localhost:{args.port}")
    print("  Press Ctrl+C to stop")
    print()

    url = f"http://localhost:{args.port}"
    if not args.no_browser:
        Timer(0.8, lambda: webbrowser.open(url)).start()

    with socketserver.TCPServer(("", args.port), CoworkmemHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Stopped.")


if __name__ == "__main__":
    main()
