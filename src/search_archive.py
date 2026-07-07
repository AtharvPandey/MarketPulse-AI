"""
search_archive.py
------------------
Simple command-line search over the historical briefing archive
(data/briefings.db). This is the "searchable log" piece of Phase 7 --
a lightweight way to look back through past briefings before Phase 8
builds a full web dashboard on top of the same database.

Usage examples:
    python search_archive.py --keyword "RBI"
    python search_archive.py --sector Banking
    python search_archive.py --stock "HDFC Bank"
    python search_archive.py --date 2026-07-08
    python search_archive.py --sector IT --keyword "AI"
"""

import sqlite3
import argparse
import os

DB_PATH = "../data/briefings.db"


def search(keyword=None, sector=None, stock=None, date=None):
    if not os.path.exists(DB_PATH):
        print(f"No archive found yet at {DB_PATH} -- run the pipeline "
              f"(or at least archive.py) at least once first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM briefings WHERE 1=1"
    params = []

    if keyword:
        query += " AND (headline LIKE ? OR summary LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if sector:
        query += " AND sector = ?"
        params.append(sector)

    if stock:
        query += " AND top_stocks LIKE ?"
        params.append(f"%{stock}%")

    if date:
        query += " AND run_timestamp LIKE ?"
        params.append(f"{date}%")

    query += " ORDER BY run_timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print("No matching results found.")
        return

    print(f"\nFound {len(rows)} matching result(s):\n")
    for row in rows:
        print(f"[{row['run_timestamp']}] ({row['time_of_day']}, {row['category']}) "
              f"[{row['sector']}] {row['headline']}")
        print(f"   {row['summary']}")
        print(f"   Stocks: {row['top_stocks']}")
        print(f"   {row['link']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Search MarketPulse AI's historical briefing archive."
    )
    parser.add_argument("--keyword", help="Search headline/summary text")
    parser.add_argument("--sector", help="Filter by exact sector name (e.g. Banking, IT)")
    parser.add_argument("--stock", help="Filter by stock name mentioned")
    parser.add_argument("--date", help="Filter by date, format YYYY-MM-DD")
    args = parser.parse_args()

    search(keyword=args.keyword, sector=args.sector, stock=args.stock, date=args.date)


if __name__ == "__main__":
    main()