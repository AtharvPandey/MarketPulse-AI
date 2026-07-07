"""
ai_analyzer.py
--------------
PHASE 2 of MarketPulse AI.

Job of this file: take the raw headlines from Phase 1 (data/raw_news.json)
and turn them into a clean, decision-ready briefing --
    - Top 5 India-relevant news
    - Top 5 Global news that impact Indian markets
each with: a short summary, the original link, a tagged sector, and a
simple sentiment read (Positive / Negative / Neutral for markets).

Design principles followed here (and why, for the beginner reading this):
1. NEVER trust an LLM's output blindly -- always validate the structure
   before using it downstream. AI can occasionally return malformed JSON,
   miss fields, or misunderstand instructions.
2. NEVER let one failure crash the whole pipeline -- retry transient
   errors, and if all retries fail, save enough debug info to fix it later
   instead of just crashing with no trace.
3. Keep this file's ONLY job as "raw news in -> structured analysis out".
   It doesn't know about sectors-to-stocks mapping or message formatting --
   that's Phase 3 and Phase 4's job.
"""

import os
import json
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher

import google.generativeai as genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 0. CONFIGURATION
# ---------------------------------------------------------------------------

load_dotenv()  # reads the .env file and loads GEMINI_API_KEY into the environment

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

RAW_NEWS_PATH = "../data/raw_news.json"
ANALYZED_NEWS_PATH = "../data/analyzed_news.json"
FAILURE_LOG_PATH = "../logs/ai_analyzer_failures.log"

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5  # doubles each retry: 5s, 10s, 20s

# Similarity threshold for treating two headlines as duplicates of the same
# story (0.0 = totally different, 1.0 = identical). 0.6 catches most
# reworded duplicates without merging genuinely different stories.
DUPLICATE_SIMILARITY_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# 1. LOAD & CLEAN THE RAW NEWS
# ---------------------------------------------------------------------------

def load_raw_news(filepath=RAW_NEWS_PATH):
    """
    Load Phase 1's output. Fails loudly and clearly if it's missing --
    this is a genuine "you forgot a step" situation, not something to
    silently work around.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Could not find '{filepath}'. Run news_collector.py (Phase 1) "
            f"first to generate this file."
        )

    with open(filepath, "r", encoding="utf-8") as f:
        news = json.load(f)

    if not news:
        raise ValueError(
            "raw_news.json exists but is empty -- no headlines were "
            "collected. Check Phase 1's output before running Phase 2."
        )

    return news


def deduplicate_news(news_items):
    """
    Multiple sources often cover the exact same story with slightly
    different wording (e.g. Moneycontrol and ET both report the same RBI
    news). Sending near-duplicates to the AI wastes tokens and can cause
    it to "double count" one story as two separate news items.

    We compare each headline to ones we've already kept, using simple
    text similarity, and skip anything too similar to something already
    in our list.
    """
    unique_items = []

    for item in news_items:
        title = item["title"].lower().strip()
        is_duplicate = False

        for kept in unique_items:
            similarity = SequenceMatcher(None, title, kept["title"].lower().strip()).ratio()
            if similarity >= DUPLICATE_SIMILARITY_THRESHOLD:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_items.append(item)

    return unique_items


# ---------------------------------------------------------------------------
# 2. BUILD THE PROMPT
# ---------------------------------------------------------------------------

def build_prompt(news_items):
    """
    Construct the instruction we send to Gemini. Being extremely explicit
    about the exact JSON shape we want is what makes AI output reliable
    enough to use in real code -- this is the core skill of "prompt
    engineering" in production systems.
    """
    headlines_block = "\n".join(
        f"{i+1}. [{item['source']}] {item['title']} (LINK: {item['link']})"
        for i, item in enumerate(news_items)
    )

    prompt = f"""You are a financial news analyst for Indian stock market investors.

Below is a list of today's raw headlines from multiple sources. Your job:

1. Select the TOP 5 headlines most relevant to INDIAN stock markets specifically.
2. Select the TOP 5 headlines from GLOBAL markets that will likely impact Indian
   stock markets (e.g. US Fed decisions, crude oil prices, China economic data,
   global tech/semiconductor news).
3. If two headlines describe the same underlying story, only include it once.
4. For each selected headline provide:
   - "headline": the original headline text (do not rewrite it)
   - "summary": a plain-English 1-2 sentence summary of why this matters for
     investors (NOT just restating the headline)
   - "link": the exact original LINK provided for that headline
   - "sector": the single most relevant stock market sector this affects.
     Use ONE of exactly these sector names: Banking, IT, Auto, Pharma, FMCG,
     Energy, Metals, Real Estate, Infrastructure, Telecom, Chemicals, PSU,
     Electronics, Aviation, General
   - "sentiment": one of exactly "Positive", "Negative", or "Neutral" --
     your read on whether this is bullish, bearish, or neutral for that sector

Respond with ONLY valid JSON in exactly this shape, nothing else -- no
markdown code fences, no explanation before or after:

{{
  "india_top5": [
    {{"headline": "...", "summary": "...", "link": "...", "sector": "...", "sentiment": "..."}}
  ],
  "global_top5": [
    {{"headline": "...", "summary": "...", "link": "...", "sector": "...", "sentiment": "..."}}
  ]
}}

Here are today's raw headlines:

{headlines_block}
"""
    return prompt


# ---------------------------------------------------------------------------
# 3. CALL GEMINI (with retries + fallback)
# ---------------------------------------------------------------------------

def call_gemini_with_retries(prompt):
    """
    Calls the Gemini API, retrying on transient failures (network blips,
    temporary rate limits) with exponential backoff. Returns the raw text
    response, or None if every retry failed.
    """
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL_NAME,
        generation_config={"response_mime_type": "application/json"},
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Calling Gemini ({GEMINI_MODEL_NAME}) -- attempt {attempt}/{MAX_RETRIES}...")
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            last_error = e
            wait_time = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"  [warning] Gemini call failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)

    print(f"  [error] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return None


# ---------------------------------------------------------------------------
# 4. VALIDATE & CLEAN THE AI'S RESPONSE
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["headline", "summary", "link", "sector", "sentiment"]
VALID_SENTIMENTS = {"Positive", "Negative", "Neutral"}


def parse_and_validate(raw_text):
    """
    Never trust AI output blindly. This function:
    1. Strips accidental markdown code fences (AI sometimes adds ```json
       even when told not to).
    2. Parses the JSON.
    3. Checks the top-level shape is correct.
    4. Checks each item has all required fields, filling safe defaults
       for anything missing rather than crashing.
    Returns a clean dict, or None if the response is unusable.
    """
    if raw_text is None:
        return None

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("json", "", 1)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  [error] Could not parse AI response as JSON: {e}")
        _save_failure_log(raw_text)
        return None

    if "india_top5" not in data or "global_top5" not in data:
        print("  [error] AI response is missing 'india_top5' or 'global_top5' keys.")
        _save_failure_log(raw_text)
        return None

    for category in ("india_top5", "global_top5"):
        cleaned_items = []
        for item in data.get(category, []):
            if not isinstance(item, dict):
                continue

            # Fill any missing field with a safe placeholder rather than
            # dropping the whole item -- partial data is still useful.
            for field in REQUIRED_FIELDS:
                item.setdefault(field, "Not available")

            if item["sentiment"] not in VALID_SENTIMENTS:
                item["sentiment"] = "Neutral"

            cleaned_items.append(item)

        data[category] = cleaned_items

    return data


def _save_failure_log(raw_text):
    """
    When the AI response can't be used, save it to a log file instead of
    just losing it. This is what lets you debug "why did this fail?"
    later instead of guessing.
    """
    os.makedirs(os.path.dirname(FAILURE_LOG_PATH), exist_ok=True)
    with open(FAILURE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n--- Failure at {datetime.now(timezone.utc).isoformat()} ---\n")
        f.write(str(raw_text))
        f.write("\n")
    print(f"  Raw response saved to {FAILURE_LOG_PATH} for debugging.")


# ---------------------------------------------------------------------------
# 5. FALLBACK: what happens if Gemini fails completely
# ---------------------------------------------------------------------------

def build_fallback_response(news_items):
    """
    If the AI is completely unavailable (API down, no internet, bad key),
    we still don't want the pipeline to just crash and send nothing.
    This fallback picks the first 5 + next 5 raw headlines with no
    summarization/sector-tagging, clearly marked as a degraded result,
    so you at least get *something* useful in your message.
    """
    print("  [fallback] Using raw headlines without AI analysis.")

    def to_basic_item(item):
        return {
            "headline": item["title"],
            "summary": "(AI analysis unavailable -- showing raw headline only)",
            "link": item["link"],
            "sector": "General",
            "sentiment": "Neutral",
        }

    return {
        "india_top5": [to_basic_item(i) for i in news_items[:5]],
        "global_top5": [to_basic_item(i) for i in news_items[5:10]],
        "degraded_mode": True,
    }


# ---------------------------------------------------------------------------
# 6. INTERACTIVE TERMINAL PREVIEW
# ---------------------------------------------------------------------------

SENTIMENT_ICONS = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}


def print_preview(data):
    """
    A clean, readable preview in your terminal -- so you can sanity-check
    the analysis before it ever gets formatted into a WhatsApp/email
    message in Phase 4.
    """
    print("\n" + "=" * 70)
    print("MARKETPULSE AI -- ANALYSIS PREVIEW")
    print("=" * 70)

    if data.get("degraded_mode"):
        print("\n⚠️  DEGRADED MODE -- AI analysis failed, showing raw headlines only.\n")

    for category, label in [("india_top5", "🇮🇳 INDIA TOP 5"), ("global_top5", "🌍 GLOBAL TOP 5")]:
        print(f"\n{label}")
        print("-" * 70)
        for i, item in enumerate(data.get(category, []), start=1):
            icon = SENTIMENT_ICONS.get(item["sentiment"], "⚪")
            print(f"{i}. {icon} [{item['sector']}] {item['headline']}")
            print(f"   -> {item['summary']}")
            print(f"   -> {item['link']}")
            print()

    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# 7. SAVE OUTPUT
# ---------------------------------------------------------------------------

def save_analyzed_news(data, filepath=ANALYZED_NEWS_PATH):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved analyzed news to {filepath}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if not GEMINI_API_KEY:
        raise EnvironmentError(
            "GEMINI_API_KEY not found. Copy .env.example to .env and add "
            "your Gemini API key from https://aistudio.google.com"
        )

    print("Loading raw news from Phase 1...")
    raw_news = load_raw_news()
    print(f"  Loaded {len(raw_news)} raw headlines.")

    print("Removing near-duplicate stories...")
    deduped_news = deduplicate_news(raw_news)
    print(f"  {len(deduped_news)} unique stories remain after deduplication.\n")

    prompt = build_prompt(deduped_news)
    raw_response = call_gemini_with_retries(prompt)
    data = parse_and_validate(raw_response)

    if data is None:
        # Every retry + validation attempt failed -- fall back gracefully
        # instead of crashing the whole pipeline.
        data = build_fallback_response(deduped_news)

    print_preview(data)
    save_analyzed_news(data)


if __name__ == "__main__":
    main()