"""
main.py
-------
Runs the full MarketPulse AI pipeline, in order:
  Phase 1: News Collector
  Phase 2: AI Analyzer
  Phase 3: Sector-Stock Mapper
  Phase 4: Message Sender

This is the ONE file GitHub Actions (Phase 5) will run on schedule.

Safety net: if ANY phase throws an unhandled error (e.g. a config
problem, or a failure Phase 1-4's own internal fallbacks couldn't
recover from), we don't just fail silently -- we try to send a WhatsApp
alert explaining that today's run failed, so you know to check on it
instead of just wondering why no briefing showed up.
"""

import os
import traceback
from dotenv import load_dotenv

import news_collector
import ai_analyzer
import sector_stock_mapper
import message_sender

load_dotenv()


def send_failure_alert(error_summary):
    """
    Best-effort attempt to notify you via WhatsApp that the pipeline
    failed. Wrapped in its own try/except -- if even THIS fails (e.g.
    Twilio credentials are the actual problem), we don't want a second
    crash to hide the original error.
    """
    try:
        from twilio.rest import Client

        client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        client.messages.create(
            from_=os.getenv("TWILIO_WHATSAPP_FROM"),
            to=os.getenv("TWILIO_WHATSAPP_TO"),
            body=(
                "⚠️ *MarketPulse AI -- run failed today*\n\n"
                f"Reason: {error_summary}\n\n"
                "Check the GitHub Actions logs for full details."
            ),
        )
        print("Failure alert sent via WhatsApp.")
    except Exception as alert_error:
        print(f"Could not send failure alert either: {alert_error}")


def main():
    try:
        print("\n===== PHASE 1: News Collector =====")
        news_collector.main()

        print("\n===== PHASE 2: AI Analyzer =====")
        ai_analyzer.main()

        print("\n===== PHASE 3: Sector-Stock Mapper =====")
        sector_stock_mapper.main()

        print("\n===== PHASE 4: Message Sender =====")
        message_sender.main()

        print("\n✅ Full pipeline completed successfully.")

    except Exception as e:
        error_summary = f"{type(e).__name__}: {e}"
        print(f"\n❌ Pipeline failed: {error_summary}")
        traceback.print_exc()

        send_failure_alert(error_summary)

        # Re-raise so GitHub Actions also marks this run as failed
        # (shows up red in the Actions tab, not hidden as a false "success").
        raise


if __name__ == "__main__":
    main()