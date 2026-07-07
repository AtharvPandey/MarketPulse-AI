# 📊 MarketPulse AI

**An autonomous AI agent that delivers twice-daily Indian stock market briefings straight to WhatsApp** — curated news, AI-generated summaries, sector tagging, and relevant stock suggestions, fully automated with zero manual effort after setup.

---

## What it does

Every morning (8:50 AM IST) and evening (8:50 PM IST), MarketPulse AI automatically:

1. **Collects** fresh headlines from multiple trusted financial news sources (Moneycontrol, Economic Times, LiveMint, Investing.com)
2. **Analyzes** them with Google's Gemini AI — selecting the top 5 India-relevant and top 5 Global-market-impact stories, summarizing each, tagging the affected sector, and reading market sentiment
3. **Maps** each news item to the top 5 relevant stocks in that sector
4. **Delivers** the final briefing straight to WhatsApp — no app to open, no dashboard to check

All of this runs on a schedule in the cloud (GitHub Actions) — no laptop required.

---

## Example output

```
📊 MarketPulse AI — Morning Briefing
🇮🇳 INDIA TOP NEWS

1. 🟢 [Banking] Nifty Bank rises 400 points as HDFC Bank, IndusInd jump up to 3%
   The banking sector shows strong performance following positive Q1 updates...
   📈 Stocks: HDFC Bank, ICICI Bank, State Bank of India, Kotak Mahindra Bank, Axis Bank
   🔗 https://...
```

---

## Architecture

The system is built as 5 independent, single-responsibility modules — if one breaks (e.g. a news source changes its feed URL), only that piece needs fixing, nothing else.

```
News Collector → AI Brain (Gemini) → Sector-Stock Mapper → Message Formatter → WhatsApp (Twilio)
                                                                                       ↑
                                                                          GitHub Actions (schedule)
```

| Phase | File | Job |
|---|---|---|
| 1 | `news_collector.py` | Pulls fresh headlines + links from RSS feeds |
| 2 | `ai_analyzer.py` | Gemini summarizes, sector-tags, and sentiment-reads the top stories |
| 3 | `sector_stock_mapper.py` | Attaches top 5 relevant stocks per sector |
| 4 | `message_sender.py` | Formats and sends via WhatsApp (Twilio) |
| 5 | `main.py` | Orchestrates all 4 phases in sequence |

---

## Reliability features (this isn't a fragile script)

- **Per-source failure isolation** — if one RSS feed is down, the others still work; the pipeline never crashes from a single bad source
- **Deduplication** — near-identical stories from different sources are merged before analysis
- **Retry with exponential backoff** — transient API failures (Gemini, Twilio) are retried automatically
- **Permanent-failure detection** — errors that retrying can't fix (e.g. message too long) fail fast instead of wasting retries
- **Graceful AI degradation** — if Gemini is completely unavailable, the pipeline still delivers raw headlines rather than sending nothing
- **Failure alerting** — if the entire pipeline fails, you get a WhatsApp message explaining why, instead of silently missing a briefing
- **Message chunking** — long briefings automatically split across multiple WhatsApp messages to respect platform length limits

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| News | `feedparser` (RSS) | Free, no API key, reliable |
| AI | Gemini 2.5 Flash-Lite | Fast, generous free tier, strong at structured summarization |
| Stock mapping | Static JSON lookup | Zero scraping risk; upgradeable to live Dhan API later |
| Delivery | Twilio WhatsApp API | Instant, mobile-first |
| Scheduling | GitHub Actions | Free, cloud-based, runs independent of any local machine |

---

## Project structure

```
MarketPulse-AI/
├── .env.example              # Template for required API keys (copy to .env, never commit .env)
├── .gitignore
├── requirements.txt
├── README.md
│
├── src/
│   ├── news_collector.py      # Phase 1
│   ├── ai_analyzer.py          # Phase 2
│   ├── sector_stock_mapper.py   # Phase 3
│   ├── message_sender.py         # Phase 4
│   └── main.py                    # Orchestrator (Phase 5 entry point)
│
├── data/
│   └── sector_stock_map.json    # Static sector -> stock lookup table (tracked in git)
│   # raw_news.json, analyzed_news.json, final_briefing.json are regenerated each run (git-ignored)
│
├── logs/                          # Failure logs (git-ignored)
│
└── .github/workflows/
    └── daily_run.yml               # Scheduled automation (8:50 AM & 8:50 PM IST)
```

---

## Setup

**1. Clone and install:**
```bash
git clone https://github.com/YOUR_USERNAME/MarketPulse-AI.git
cd MarketPulse-AI
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

**2. Configure environment:**
```bash
cp .env.example .env
```
Fill in `.env` with:
- `GEMINI_API_KEY` — from [aistudio.google.com](https://aistudio.google.com)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `TWILIO_WHATSAPP_TO` — from your [Twilio Console](https://twilio.com) + WhatsApp Sandbox setup

**3. Run the full pipeline manually:**
```bash
cd src
python main.py
```

**4. Automate it:**
Add the same 6 values as **GitHub repository secrets** (Settings → Secrets and variables → Actions), then the workflow in `.github/workflows/daily_run.yml` runs automatically twice a day.

---

## Roadmap / future improvements

- [ ] Replace the static sector-stock table with live data from Dhan's trading API
- [ ] Upgrade from Twilio WhatsApp Sandbox to an approved WhatsApp Business sender (removes the 3-day re-opt-in requirement)
- [ ] Add historical briefing archive / searchable log
- [ ] Add a simple web dashboard to view past briefings

---

## Disclaimer

This project surfaces and summarizes publicly available financial news for informational purposes only. It is not financial advice. All investment decisions should be made independently or with a licensed financial advisor.

---

## Author

Built by Atharv as a hands-on project exploring AI agent design, API orchestration, and cloud automation.
