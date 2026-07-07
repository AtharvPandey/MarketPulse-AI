"""
archive.py
----------
PHASE 7 of MarketPulse AI.

Job of this file: permanently store every briefing (India + Global news,
with sectors, sentiment, and stocks) into a local SQLite database, so
nothing is ever lost after a run finishes -- and so it's searchable
later, and ready to power the future web dashboard (Phase 8).

Why SQLite instead of just appending to a JSON file?
- Real querying: "show me all Banking news from last week" becomes a
  proper SQL query, not a manual loop through an ever-growing file.
- Still just ONE file (data/briefings.db) -- no external database
  server needed, and it's small/portable enough to commit straight back
  into the GitHub repo after every automated run.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = "../data/briefings.db"
FINAL_BRIEFING_PATH = "../data/final_briefing.json"


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db(conn):
    """Creates the briefings table if it doesn't already exist -- safe
    to call on every run, won't wipe existing data."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS briefings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp TEXT NOT NULL,
            time_of_day TEXT NOT NULL,
            category TEXT NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT,
            link TEXT,
            sector TEXT,
            sentiment TEXT,
            top_stocks TEXT,
            degraded_mode INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def get_time_of_day_label():
    hour = datetime.now().hour
    return "Morning Briefing" if hour < 15 else "Evening Wrap-up"


def load_final_briefing(filepath=FINAL_BRIEFING_PATH):
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Could not find '{filepath}'. Run sector_stock_mapper.py "
            f"(Phase 3) first."
        )
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def archive_briefing(data):
    """
    Inserts every news item from today's briefing as its own row --
    one row per India item, one row per Global item -- tagged with the
    run's timestamp and whether it ran in degraded (AI-unavailable) mode.
    """
    conn = get_connection()
    init_db(conn)

    run_timestamp = datetime.now(timezone.utc).isoformat()
    time_of_day = get_time_of_day_label()
    degraded = 1 if data.get("degraded_mode") else 0

    rows_inserted = 0
    for category, label in (("india_top5", "India"), ("global_top5", "Global")):
        for item in data.get(category, []):
            conn.execute("""
                INSERT INTO briefings
                (run_timestamp, time_of_day, category, headline, summary,
                 link, sector, sentiment, top_stocks, degraded_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_timestamp,
                time_of_day,
                label,
                item.get("headline", ""),
                item.get("summary", ""),
                item.get("link", ""),
                item.get("sector", ""),
                item.get("sentiment", ""),
                ", ".join(item.get("top_stocks", [])),
                degraded,
            ))
            rows_inserted += 1

    conn.commit()
    conn.close()
    print(f"Archived {rows_inserted} news items to {DB_PATH} (run: {run_timestamp})")


def main():
    print("Loading final briefing for archiving...")
    data = load_final_briefing()
    archive_briefing(data)


if __name__ == "__main__":
    main()