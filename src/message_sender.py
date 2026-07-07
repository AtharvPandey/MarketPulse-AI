"""
message_sender.py
------------------
PHASE 4 of MarketPulse AI.

Job of this file: take Phase 3's final briefing (data/final_briefing.json)
and turn it into a clean, readable WhatsApp message, then send it via
Twilio.

Design choices explained:
- We send India news and Global news as TWO separate WhatsApp messages
  instead of one giant one. WhatsApp/Twilio have message length limits,
  and two shorter messages are also just easier to read on a phone than
  one huge wall of text.
- If sending fails (Twilio down, sandbox expired, bad credentials), we
  NEVER just lose the briefing -- we save the fully formatted message to
  a local file so you can still read it manually, and so you have a
  record of what should have been sent.
"""

import os
import json
import time
from datetime import datetime

from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

load_dotenv()

FINAL_BRIEFING_PATH = "../data/final_briefing.json"
UNDELIVERED_LOG_PATH = "../logs/undelivered_messages.log"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO")

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5

# Twilio's hard limit is 1600 characters per message. We use a lower
# threshold to leave a safety buffer for emoji/unicode encoding overhead.
WHATSAPP_CHAR_LIMIT = 1400

SENTIMENT_ICONS = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}

# Error messages that mean "this will NEVER succeed no matter how many
# times we retry" -- e.g. a message that's too long stays too long, and
# an invalid number stays invalid. Retrying these just wastes time.
NON_RETRYABLE_ERROR_HINTS = [
    "exceeds the 1600 character limit",
    "not a valid phone number",
    "is not currently reachable",
    "unverified",
]


def is_retryable(exception):
    """Distinguish transient failures (worth retrying) from permanent
    ones (retrying won't help -- fail fast instead)."""
    message = str(exception)
    return not any(hint in message for hint in NON_RETRYABLE_ERROR_HINTS)


# ---------------------------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------------------------

def load_final_briefing(filepath=FINAL_BRIEFING_PATH):
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Could not find '{filepath}'. Run sector_stock_mapper.py "
            f"(Phase 3) first."
        )
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. FORMAT MESSAGES
# ---------------------------------------------------------------------------

def get_time_of_day_label():
    """
    Picks 'Morning Briefing' or 'Evening Wrap-up' automatically based on
    the current hour -- so the same script works for both your 8:50 AM
    and night runs without needing a separate flag.
    """
    hour = datetime.now().hour
    return "Morning Briefing" if hour < 15 else "Evening Wrap-up"


def format_item_block(item, index):
    """Formats a single news item into its WhatsApp text block."""
    icon = SENTIMENT_ICONS.get(item.get("sentiment", "Neutral"), "⚪")
    stocks = ", ".join(item.get("top_stocks", []))

    return (
        f"{index}. {icon} *[{item['sector']}]* {item['headline']}\n"
        f"_{item['summary']}_\n"
        f"📈 Stocks: {stocks}\n"
        f"🔗 {item['link']}\n"
    )


def chunk_items_into_messages(items, header, char_limit=WHATSAPP_CHAR_LIMIT):
    """
    Splits a list of news items into one or more WhatsApp messages, each
    kept under `char_limit`. Items are never cut in half -- if adding the
    next item would push a message over the limit, that item starts a
    fresh message instead (labeled "cont'd" for clarity).

    This is the key fix for the "exceeds 1600 character limit" error --
    rather than retrying one oversized message, we never create an
    oversized message in the first place.
    """
    messages = []
    current_header = header
    current_lines = [f"*{current_header}*", ""]

    def current_text():
        return "\n".join(current_lines)

    for i, item in enumerate(items, start=1):
        item_text = format_item_block(item, i)

        # +1 for the blank line we'll add after the item
        if len(current_text()) + len(item_text) + 1 > char_limit and len(current_lines) > 2:
            messages.append(current_text().strip())
            current_header = f"{header} (cont'd)"
            current_lines = [f"*{current_header}*", ""]

        current_lines.append(item_text)

    if len(current_lines) > 2:
        messages.append(current_text().strip())

    return messages


def build_messages(data):
    """
    Returns a list of (label, message_text) tuples -- India news and
    Global news, each possibly split across multiple messages if long.
    Kept separate/chunked so every message stays safely within WhatsApp's
    length limits and reads cleanly on a phone screen.
    """
    time_label = get_time_of_day_label()

    india_header = f"📊 MarketPulse AI — {time_label}\n🇮🇳 INDIA TOP NEWS"
    global_header = "🌍 GLOBAL NEWS (impacting India)"

    messages = []

    india_items = data.get("india_top5", [])
    if india_items:
        chunks = chunk_items_into_messages(india_items, india_header)
        for idx, chunk in enumerate(chunks, start=1):
            label = "India" if len(chunks) == 1 else f"India ({idx}/{len(chunks)})"
            messages.append((label, chunk))

    global_items = data.get("global_top5", [])
    if global_items:
        chunks = chunk_items_into_messages(global_items, global_header)
        for idx, chunk in enumerate(chunks, start=1):
            label = "Global" if len(chunks) == 1 else f"Global ({idx}/{len(chunks)})"
            messages.append((label, chunk))

    if data.get("degraded_mode"):
        messages.insert(0, (
            "Notice",
            "ℹ️ _Quick note: today's briefing shows raw headlines only "
            "-- AI summarization hit a snag. Links below still work fine._"
        ))

    return messages


# ---------------------------------------------------------------------------
# 3. SEND VIA TWILIO (with retries + fallback)
# ---------------------------------------------------------------------------

def send_whatsapp_message(client, body, label):
    """
    Sends one WhatsApp message via Twilio, retrying only TRANSIENT
    failures (network blips, temporary Twilio issues). Permanent failures
    (message too long, bad number) fail fast on the first attempt instead
    of wasting time retrying something that can't change.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Sending '{label}' message -- attempt {attempt}/{MAX_RETRIES}...")
            client.messages.create(
                from_=TWILIO_WHATSAPP_FROM,
                to=TWILIO_WHATSAPP_TO,
                body=body,
            )
            print(f"  ✅ '{label}' message sent successfully.")
            return True

        except TwilioRestException as e:
            if not is_retryable(e):
                print(f"  [error] Permanent failure, not retrying: {e}")
                return False

            wait_time = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"  [warning] Twilio send failed (transient): {e}")
            if attempt < MAX_RETRIES:
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)

    print(f"  [error] Could not send '{label}' message after {MAX_RETRIES} attempts.")
    return False


def save_undelivered(label, body):
    """
    If Twilio sending fails completely (sandbox expired, bad credentials,
    Twilio outage), we NEVER just lose the briefing. Save it to a local
    log so you can still read it, and so you have a record for debugging.
    """
    os.makedirs(os.path.dirname(UNDELIVERED_LOG_PATH), exist_ok=True)
    with open(UNDELIVERED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n--- Undelivered '{label}' message at {datetime.now().isoformat()} ---\n")
        f.write(body)
        f.write("\n")
    print(f"  Message saved to {UNDELIVERED_LOG_PATH} so it isn't lost.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    missing = [
        name for name, val in [
            ("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
            ("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
            ("TWILIO_WHATSAPP_FROM", TWILIO_WHATSAPP_FROM),
            ("TWILIO_WHATSAPP_TO", TWILIO_WHATSAPP_TO),
        ] if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required .env values: {', '.join(missing)}. "
            f"Check your .env file against .env.example."
        )

    print("Loading final briefing from Phase 3...")
    data = load_final_briefing()

    print("Formatting messages...")
    messages = build_messages(data)

    print("\nPreview of what will be sent:\n")
    for label, body in messages:
        print("=" * 70)
        print(f"[{label}]")
        print("-" * 70)
        print(body)
        print()

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    print("=" * 70)
    print("Sending via WhatsApp...\n")
    for label, body in messages:
        success = send_whatsapp_message(client, body, label)
        if not success:
            save_undelivered(label, body)


if __name__ == "__main__":
    main()