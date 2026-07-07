"""
dashboard_generator.py
------------------------
PHASE 8 of MarketPulse AI.

Job of this file: read every archived briefing from data/briefings.db
(Phase 7's database) and generate a single static HTML file --
docs/index.html -- that displays the full history as a browsable,
searchable "ledger" of past briefings.

Why static HTML instead of a live Flask server?
- No server to keep running, no hosting cost, no uptime to babysit.
- GitHub Pages serves this file for free, straight out of the repo.
- Since we already commit briefings.db back to the repo after each
  run (Phase 7), committing this generated HTML alongside it costs
  nothing extra -- the dashboard updates itself automatically on every
  scheduled run.
"""

import sqlite3
import os
import html as html_lib
from datetime import datetime, timezone
from collections import defaultdict

DB_PATH = "../data/briefings.db"
OUTPUT_PATH = "../docs/index.html"

SENTIMENT_META = {
    "Positive": ("stamp-gain", "G"),
    "Negative": ("stamp-loss", "L"),
    "Neutral": ("stamp-neutral", "N"),
}


def load_all_rows():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Could not find '{DB_PATH}'. Run archive.py (Phase 7) at least once first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM briefings ORDER BY run_timestamp ASC, id ASC"
    ).fetchall()
    conn.close()
    return rows


def group_by_run(rows):
    """Groups flat DB rows back into one entry per pipeline run, each
    holding its India items and Global items separately."""
    runs = defaultdict(lambda: {"time_of_day": "", "degraded": False, "India": [], "Global": []})

    for row in rows:
        run = runs[row["run_timestamp"]]
        run["time_of_day"] = row["time_of_day"]
        run["degraded"] = run["degraded"] or bool(row["degraded_mode"])
        run[row["category"]].append(row)

    # Return as a list ordered chronologically (oldest first), each with its
    # timestamp -- lets us number entries meaningfully (Entry 1 = earliest).
    return sorted(runs.items(), key=lambda kv: kv[0])


def format_timestamp(iso_string):
    dt = datetime.fromisoformat(iso_string).replace(tzinfo=timezone.utc)
    return dt.strftime("%d %b %Y, %I:%M %p UTC")


def esc(text):
    """Escape text for safe HTML embedding -- news headlines/summaries
    are external content, never trust them blindly when injecting into HTML.

    We unescape first because some RSS sources (and occasionally the AI's
    summary) already contain HTML entities like '&amp;' -- without this,
    we'd double-encode it into '&amp;amp;', which renders literally as
    "S&amp;P 500" instead of "S&P 500" on the page.
    """
    return html_lib.escape(html_lib.unescape(text or ""))


def render_item(row):
    css_class, stamp_letter = SENTIMENT_META.get(row["sentiment"], ("stamp-neutral", "N"))
    sector = esc(row["sector"] or "General")
    headline = esc(row["headline"])
    summary = esc(row["summary"])
    stocks = esc(row["top_stocks"])
    link = esc(row["link"])
    search_text = esc(f"{row['headline']} {row['summary']}".lower())

    return f"""
        <article class="item" data-sector="{sector}" data-text="{search_text}">
          <span class="stamp {css_class}">{stamp_letter}</span>
          <div class="item-body">
            <div class="item-top">
              <span class="sector-tag">{sector}</span>
              <h4 class="headline">{headline}</h4>
            </div>
            <p class="summary">{summary}</p>
            <p class="stocks"><span class="label">Stocks</span> {stocks}</p>
            <a class="link" href="{link}" target="_blank" rel="noopener">Read source →</a>
          </div>
        </article>"""


def render_entry(entry_number, run_timestamp, run_data):
    degraded_badge = (
        '<span class="degraded-badge">AI unavailable this run</span>'
        if run_data["degraded"] else ""
    )

    india_html = "\n".join(render_item(r) for r in run_data["India"]) or \
        '<p class="empty-col">No India items recorded.</p>'
    global_html = "\n".join(render_item(r) for r in run_data["Global"]) or \
        '<p class="empty-col">No Global items recorded.</p>'

    return f"""
      <section class="entry" data-entry>
        <div class="entry-head">
          <span class="entry-no">Entry {entry_number}</span>
          <span class="entry-time">{format_timestamp(run_timestamp)} &middot; {esc(run_data['time_of_day'])}</span>
          {degraded_badge}
        </div>
        <div class="entry-body">
          <div class="col">
            <h3 class="col-title">India</h3>
            {india_html}
          </div>
          <div class="col">
            <h3 class="col-title">Global</h3>
            {global_html}
          </div>
        </div>
      </section>"""


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MarketPulse AI — Briefing Ledger</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #F7F3E9;
    --ink: #1C3D3A;
    --gain: #2F6844;
    --loss: #8C2F39;
    --neutral: #B8860B;
    --rule: #C9BFA0;
    --rule-light: #E4DCC5;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    line-height: 1.5;
  }
  header {
    padding: 48px 24px 32px;
    max-width: 900px;
    margin: 0 auto;
    border-bottom: 2px solid var(--ink);
  }
  h1 {
    font-family: 'Fraunces', serif;
    font-optical-sizing: auto;
    font-weight: 600;
    font-size: clamp(2rem, 5vw, 3rem);
    margin: 0 0 8px;
  }
  .subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    color: var(--ink);
    opacity: 0.7;
  }
  .stats {
    margin-top: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
  }
  .controls {
    max-width: 900px;
    margin: 24px auto;
    padding: 0 24px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .controls input, .controls select {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.95rem;
    padding: 10px 14px;
    border: 1.5px solid var(--ink);
    background: var(--paper);
    color: var(--ink);
    border-radius: 2px;
  }
  .controls input { flex: 1; min-width: 200px; }
  main { max-width: 900px; margin: 0 auto; padding: 0 24px 80px; }
  .entry {
    border-bottom: 1px dashed var(--rule);
    padding: 32px 0;
  }
  .entry:last-child { border-bottom: none; }
  .entry-head {
    display: flex;
    align-items: baseline;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }
  .entry-no {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.3rem;
  }
  .entry-time {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    opacity: 0.75;
  }
  .degraded-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    background: var(--neutral);
    color: var(--paper);
    padding: 2px 8px;
    border-radius: 2px;
  }
  .entry-body {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
  }
  @media (max-width: 700px) {
    .entry-body { grid-template-columns: 1fr; }
  }
  .col-title {
    font-family: 'IBM Plex Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.75rem;
    opacity: 0.6;
    margin: 0 0 16px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--rule-light);
  }
  .item {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }
  .stamp {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 2px solid currentColor;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    font-size: 0.75rem;
    transform: rotate(-8deg);
  }
  .stamp-gain { color: var(--gain); }
  .stamp-loss { color: var(--loss); }
  .stamp-neutral { color: var(--neutral); }
  .item-top { display: flex; flex-direction: column; gap: 2px; }
  .sector-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    opacity: 0.65;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .headline { margin: 0; font-size: 1rem; font-weight: 500; line-height: 1.35; }
  .summary { font-size: 0.9rem; opacity: 0.85; margin: 6px 0; }
  .stocks { font-size: 0.82rem; margin: 4px 0; }
  .stocks .label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    opacity: 0.6;
    text-transform: uppercase;
    margin-right: 6px;
  }
  .link {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--ink);
  }
  .empty-col { font-size: 0.85rem; opacity: 0.5; font-style: italic; }
  footer {
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    opacity: 0.5;
  }
</style>
</head>
<body>

<header>
  <h1>MarketPulse AI</h1>
  <div class="subtitle">Briefing Ledger — every automated run, archived and searchable</div>
  <div class="stats">
    <span>{{TOTAL_ENTRIES}} entries logged</span>
    <span>{{FIRST_DATE}} → {{LAST_DATE}}</span>
  </div>
</header>

<div class="controls">
  <input type="text" id="searchBox" placeholder="Search headlines &amp; summaries...">
  <select id="sectorFilter">
    <option value="">All sectors</option>
    {{SECTOR_OPTIONS}}
  </select>
</div>

<main id="ledger">
  {{ENTRIES}}
</main>

<footer>Generated {{GENERATED_AT}} &middot; MarketPulse AI</footer>

<script>
  const searchBox = document.getElementById('searchBox');
  const sectorFilter = document.getElementById('sectorFilter');
  const items = Array.from(document.querySelectorAll('.item'));
  const entries = Array.from(document.querySelectorAll('.entry'));

  function applyFilter() {
    const keyword = searchBox.value.trim().toLowerCase();
    const sector = sectorFilter.value;

    items.forEach(item => {
      const matchesKeyword = !keyword || item.dataset.text.includes(keyword);
      const matchesSector = !sector || item.dataset.sector === sector;
      item.style.display = (matchesKeyword && matchesSector) ? '' : 'none';
    });

    entries.forEach(entry => {
      const visibleItems = entry.querySelectorAll('.item:not([style*="display: none"])');
      entry.style.display = visibleItems.length > 0 ? '' : 'none';
    });
  }

  searchBox.addEventListener('input', applyFilter);
  sectorFilter.addEventListener('change', applyFilter);
</script>

</body>
</html>
"""


def build_dashboard():
    rows = load_all_rows()
    if not rows:
        print("No archived data yet -- dashboard will show an empty ledger.")

    grouped_runs = group_by_run(rows)

    all_sectors = sorted({esc(row["sector"] or "General") for row in rows})
    sector_options = "\n    ".join(f'<option value="{s}">{s}</option>' for s in all_sectors)

    entries_html = "\n".join(
        render_entry(i + 1, ts, data)
        for i, (ts, data) in enumerate(grouped_runs)
    )
    # Show most recent entries first
    entries_html = "\n".join(
        render_entry(len(grouped_runs) - i, ts, data)
        for i, (ts, data) in enumerate(reversed(grouped_runs))
    )

    total_entries = len(grouped_runs)
    first_date = format_timestamp(grouped_runs[0][0]) if grouped_runs else "—"
    last_date = format_timestamp(grouped_runs[-1][0]) if grouped_runs else "—"
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")

    page = PAGE_TEMPLATE
    page = page.replace("{{TOTAL_ENTRIES}}", str(total_entries))
    page = page.replace("{{FIRST_DATE}}", first_date)
    page = page.replace("{{LAST_DATE}}", last_date)
    page = page.replace("{{SECTOR_OPTIONS}}", sector_options)
    page = page.replace("{{ENTRIES}}", entries_html)
    page = page.replace("{{GENERATED_AT}}", generated_at)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"Dashboard generated: {OUTPUT_PATH} ({total_entries} entries)")


def main():
    print("Building dashboard from archive...")
    build_dashboard()


if __name__ == "__main__":
    main()