"""
sector_stock_mapper.py
-----------------------
PHASE 3 of MarketPulse AI.

Job of this file (and only this file): take Phase 2's sector-tagged news
(data/analyzed_news.json) and attach the top 5 relevant stocks for each
news item's sector, using a static lookup table (data/sector_stock_map.json).

Why static instead of live-scraped? As decided in the project blueprint --
ship the simple, reliable version first. A hardcoded table has zero chance
of breaking from a site redesign or a blocked scraper. We can upgrade this
to pull live data from Dhan's API in a later phase without touching any
other part of the pipeline -- that's the whole point of keeping phases separate.
"""

import json
import os

ANALYZED_NEWS_PATH = "../data/analyzed_news.json"
SECTOR_MAP_PATH = "../data/sector_stock_map.json"
FINAL_BRIEFING_PATH = "../data/final_briefing.json"


def load_json(filepath, description):
    """Small reusable loader with a clear error if the file is missing."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Could not find {description} at '{filepath}'. "
            f"Make sure the previous phase ran successfully first."
        )
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_stocks_for_sector(sector, sector_map):
    """
    Look up stocks for a given sector. If the AI tagged something with a
    sector name that isn't in our table (e.g. a typo, or a sector we
    haven't added yet), we don't crash -- we fall back to the "General"
    list so the news item still gets useful stock context.
    """
    if sector in sector_map:
        return sector_map[sector]

    print(f"  [warning] Sector '{sector}' not found in sector_stock_map.json -- "
          f"using 'General' as fallback.")
    return sector_map.get("General", [])


def attach_stocks(news_data, sector_map):
    """
    Walk through both india_top5 and global_top5 lists, and add a
    "top_stocks" field to each item based on its sector.
    """
    for category in ("india_top5", "global_top5"):
        for item in news_data.get(category, []):
            item["top_stocks"] = get_stocks_for_sector(item["sector"], sector_map)

    return news_data


def print_preview(news_data):
    """Quick readable preview so you can confirm stocks attached correctly."""
    print("\n" + "=" * 70)
    print("PHASE 3 -- SECTOR-STOCK MAPPING PREVIEW")
    print("=" * 70)

    for category, label in [("india_top5", "🇮🇳 INDIA TOP 5"), ("global_top5", "🌍 GLOBAL TOP 5")]:
        print(f"\n{label}")
        print("-" * 70)
        for i, item in enumerate(news_data.get(category, []), start=1):
            print(f"{i}. [{item['sector']}] {item['headline']}")
            print(f"   Top stocks: {', '.join(item['top_stocks'])}")
            print()

    print("=" * 70 + "\n")


def save_final_briefing(news_data, filepath=FINAL_BRIEFING_PATH):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(news_data, f, indent=2, ensure_ascii=False)
    print(f"Saved final briefing to {filepath}")


def main():
    print("Loading Phase 2 output (analyzed news)...")
    news_data = load_json(ANALYZED_NEWS_PATH, "analyzed news")

    print("Loading sector-stock mapping table...")
    sector_map = load_json(SECTOR_MAP_PATH, "sector-stock map")

    print("Attaching top stocks to each news item...\n")
    news_data = attach_stocks(news_data, sector_map)

    print_preview(news_data)
    save_final_briefing(news_data)


if __name__ == "__main__":
    main()