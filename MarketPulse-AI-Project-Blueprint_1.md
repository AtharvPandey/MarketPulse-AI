# MarketPulse AI — Project Blueprint
### An Automated Indian Market News & Sector-Stock Intelligence Agent

---

## 1. The Vision (Elevator Pitch)

> "Every morning at 8:50 AM and every night, I get a message with the top 5 Indian market news + top 5 global news that affects India — each with a direct link to read more — and next to each news item, the top stocks in the sector that news impacts. No manual searching. No opening 5 apps. One message, twice a day."

This is a **real product**, not a script. So we build it like one — with proper structure, error handling, and room to grow. This blueprint treats it exactly like a startup would treat its first MVP (Minimum Viable Product).

---

## 2. Naming the Project

Give it a real name — this matters more than it sounds. A named project feels real, goes in your resume/portfolio properly, and forces you to think about it as a "product."

**Suggested name: `MarketPulse AI`**
(Feel free to rename — but we'll use this throughout so it feels concrete.)

---

## 3. High-Level System Architecture

Think of the system as **5 independent building blocks (services)**, each doing ONE job. This is called a **modular architecture** — the industry-standard way to build anything, because each piece can be fixed, replaced, or upgraded without breaking the others.

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  1. NEWS         │────▶│  2. AI BRAIN      │────▶│  3. SECTOR-STOCK   │
│  COLLECTOR       │     │  (Summarize +     │     │  MAPPER            │
│  (RSS feeds)     │     │   Sector Tag)     │     │  (Static + Dhan)   │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                            │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  5. SCHEDULER    │────▶│  4. MESSAGE       │◀────│   (data merges     │
│  (Cron / GitHub  │     │  FORMATTER +      │     │    here)           │
│   Actions)       │     │  DELIVERY (WhatsApp/│    └───────────────────┘
                         │  Email)           │
└─────────────────┘     └──────────────────┘
```

**Why this matters (the beginner lesson):**
Every big application you've ever used (Zomato, Swiggy, even Screener itself) is built this way — small independent pieces talking to each other, not one giant tangled file. If your news source breaks tomorrow, you only fix Block 1 — Blocks 2, 3, 4, 5 don't even notice.

---

## 4. The 6 Phases of the Project

We build this the way real software teams build products: **plan → design → build small → test → connect → launch**. Never build everything at once.

---

### **PHASE 0: Requirements & Research** (Day 1)
*Goal: Know exactly what "done" looks like before writing a single line of code.*

- Write down the exact message format you want (we already drafted this earlier)
- List your data sources: RSS feeds (Moneycontrol, ET Markets, Reuters), Dhan API docs
- Decide: WhatsApp or Email for delivery? *(WhatsApp — needs a Twilio account, free trial tier, feels more instant/mobile-first. Email — simpler to set up, no third-party approval needed, works great if you just want it in your inbox first thing.)*
- If WhatsApp: sign up for Twilio, get your WhatsApp Sandbox number + Account SID + Auth Token
- If Email: no signup needed, just use your own Gmail with an "app password" (Google's secure way of letting scripts send email on your behalf)
- Sign up for Gemini API key (AI Studio) — you already have this from earlier setup
- Sign up for Dhan API access (needs your existing Dhan trading account)

**Deliverable:** A one-page doc (even in Notes app) listing: data sources, API keys collected, exact message format.

---

### **PHASE 1: News Collector Module** (Days 2-4)
*Goal: A Python script that pulls fresh headlines + links from multiple sources into one clean list.*

**What you'll build:**
- A Python file `news_collector.py`
- Uses `feedparser` library to read RSS feeds (no API key needed — RSS is free and public)
- Pulls from: Moneycontrol RSS, ET Markets RSS, Reuters Business RSS, Business Standard RSS
- Cleans the data into a simple format: `{title, link, published_date, source}`
- Saves this as a JSON file (a simple structured text format) — this is your "raw material" for the next phase

**Beginner concept taught here:** RSS feeds, working with APIs/libraries, JSON data structure — these are foundational skills for literally any automation project you'll ever build.

**Deliverable:** Running the script prints 20-30 fresh headlines with links to your terminal.

---

### **PHASE 2: AI Brain — Summarize & Sector-Tag** (Days 5-8)
*Goal: Feed raw headlines to Gemini, get back the exact top 5 + top 5, each tagged with a sector, summarized in 1-2 lines.*

**What you'll build:**
- A Python file `ai_analyzer.py`
- Takes the JSON from Phase 1
- Sends it to Gemini API with a carefully written prompt (this is called **prompt engineering** — a real, valuable skill)
- Gemini returns structured output — you'll ask it to respond in **JSON format** so your code can easily use the answer (not just plain text)

**Example of what you're asking Gemini to return:**
```json
[
  {
    "headline": "RBI cuts repo rate by 25bps",
    "summary": "RBI reduced rates, positive for lending-driven sectors",
    "link": "https://...",
    "sector": "Banking",
    "type": "India"
  }
]
```

**Beginner concept taught here:** This is your first real hands-on experience with **structured output from an LLM** — a core skill in every serious AI application built today (this is literally how ChatGPT plugins, AI agents, and enterprise AI tools work internally).

**Deliverable:** Running the script takes raw headlines and prints back a clean, sector-tagged, summarized JSON.

---

### **PHASE 3: Sector → Stock Mapper** (Days 9-11)
*Goal: For each sector identified in Phase 2, return the top 5 relevant stocks.*

**Two approaches — build the simple one first, upgrade later:**

**3A — Static Mapping (build this first, ship it, it works great):**
- A simple Python dictionary/JSON file you write once:
```json
{
  "Banking": ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Bank", "Axis Bank"],
  "Auto": ["Maruti Suzuki", "Tata Motors", "M&M", "Bajaj Auto", "Eicher Motors"],
  "IT": ["TCS", "Infosys", "HCL Tech", "Wipro", "Tech Mahindra"],
  "Pharma": ["Sun Pharma", "Dr Reddy's", "Cipla", "Divi's Labs", "Lupin"],
  "FMCG": ["HUL", "ITC", "Nestle India", "Britannia", "Dabur"]
}
```
- Your code just looks up: sector tagged by AI → pulls top 5 from this table. Instant, zero risk of breaking, zero scraping needed.

**3B — Dynamic Upgrade (Phase 2.0 of the project, do this later once V1 is working):**
- Connect Dhan's official API to pull real-time top stocks by market cap/volume within a sector
- This makes the list "live" instead of fixed — a nice v2 upgrade once the core pipeline works

**Beginner concept taught here:** **Always ship the simple version first.** This is one of the most important lessons in real software engineering — called building an MVP. Perfect is the enemy of shipped.

**Deliverable:** Given a sector name, your code returns 5 stock names instantly.

---

### **PHASE 4: Message Formatter & Delivery** (Days 12-14)
*Goal: Combine everything into one clean message and send it to your WhatsApp or Email automatically.*

**What you'll build:**
- A Python file `message_sender.py`
- Formats the final combined data (news + link + sector + stocks) into a clean readable message
- **If WhatsApp:** Uses Twilio's WhatsApp API (a simple `requests.post()` call) to push the message to your phone
- **If Email:** Uses Python's built-in `smtplib` library to send the message straight to your inbox — no third-party service needed

**Example final output:**
```
📊 MARKETPULSE AI — Morning Briefing (8:50 AM)

🇮🇳 INDIA NEWS
1️⃣ RBI cuts repo rate by 25bps
   → Sector: Banking | Read more: [link]
   → Top stocks: HDFC Bank, ICICI, SBI, Kotak, Axis

2️⃣ Govt announces new PLI scheme for electronics
   → Sector: Electronics/Manufacturing | Read more: [link]
   → Top stocks: Dixon Tech, Amber Enterprises, ...

🌍 GLOBAL NEWS (impacts India)
1️⃣ US Fed signals rate pause
   → Sector: IT/Export | Read more: [link]
   → Top stocks: TCS, Infosys, HCL Tech, ...
```

**Deliverable:** A message like this lands in your WhatsApp or inbox automatically when you run the script.

---

### **PHASE 5: Scheduling & Automation** (Days 15-17)
*Goal: The whole pipeline runs itself — 8:50 AM and at night — without you touching your laptop.*

**Two options, pick based on comfort:**

- **Option A — Simple (Mac cron job):** Your Mac runs the script automatically at set times, but your Mac needs to be on and awake at that time.
- **Option B — Industry Standard (GitHub Actions):** Free, runs on GitHub's own servers on a schedule — works even if your laptop is off or closed. This is literally how real companies automate scheduled jobs (called "cron jobs in the cloud"). **Recommended**, since you're building this to be a genuine portfolio project.

**Beginner concept taught here:** **CI/CD and cloud automation** — a legit professional DevOps skill. Knowing how to schedule jobs in GitHub Actions is something real companies pay for.

**Deliverable:** You wake up and the message is already in your WhatsApp or inbox, without opening your laptop.

---

### **PHASE 6: Polish, Document & Publish** (Days 18-21)
*Goal: Make it look and feel like a real project you're proud to show.*

- Write a proper `README.md` — explain what it does, how it works, screenshots of the WhatsApp/email message
- Push clean code to **GitHub** — organized in folders, not one giant messy file
- Add a `.env` file for your API keys (NEVER hardcode API keys directly in code — industry-standard security practice)
- Add basic error handling — what happens if an RSS feed is down or Gemini API fails? (Should not crash silently — should log and retry)
- Optional: Add a simple logging system so you can see what happened each morning (`logs/2026-07-06.log`)

**Deliverable:** A clean, working GitHub repo you can link on LinkedIn/resume as "Built an autonomous AI news-to-stock intelligence agent."

---

## 5. Recommended Folder Structure (industry standard)

```
marketpulse-ai/
│
├── .env                     # API keys (never pushed to GitHub)
├── .gitignore                # tells git to ignore .env, cache files
├── README.md                  # project explanation
├── requirements.txt            # list of Python libraries needed
│
├── src/
│   ├── news_collector.py       # Phase 1
│   ├── ai_analyzer.py           # Phase 2
│   ├── sector_stock_mapper.py    # Phase 3
│   ├── message_sender.py          # Phase 4
│   └── main.py                     # runs everything in order
│
├── data/
│   └── sector_stock_map.json       # Phase 3A static mapping
│
├── logs/
│   └── (daily run logs go here)
│
└── .github/
    └── workflows/
        └── daily_run.yml            # Phase 5 GitHub Actions schedule
```

**Beginner lesson:** This structure — `src/`, `data/`, `logs/` — is exactly how professional Python projects are organized. Following this now builds the right habit for every future project, including your job at Trianz.

---

## 6. Tech Stack Summary (why each tool was picked)

| Layer | Tool | Why |
|---|---|---|
| News | `feedparser` + RSS | Free, no API key, reliable |
| AI | Gemini API (free tier) | You already have access, good enough for summarization |
| Stock mapping | Static JSON → later Dhan API | Ship fast now, upgrade later |
| Delivery | Twilio WhatsApp API *or* Gmail SMTP | WhatsApp = instant/mobile-first; Email = zero third-party signup, simplest to start |
| Scheduling | GitHub Actions | Free, cloud-based, doesn't need your laptop on |
| Code hosting | GitHub | Industry standard, builds your portfolio |

---

## 7. What You'll Actually Learn (beyond just "a working bot")

- Working with real-world APIs (RSS, Gemini, Twilio/Gmail, Dhan)
- Prompt engineering for structured AI output
- Modular code architecture (the "5 building blocks" mental model)
- Environment variables & API key security
- Cloud scheduling / CI-CD basics (GitHub Actions)
- Proper GitHub project structure and documentation

This is genuinely portfolio-worthy — the kind of project that stands out in interviews because it's a real, running system, not a tutorial copy.

---

## 8. Suggested Timeline

| Week | Focus |
|---|---|
| Week 1 | Phase 0 + Phase 1 (setup + news collector) |
| Week 2 | Phase 2 + Phase 3 (AI brain + sector mapping) |
| Week 3 | Phase 4 + Phase 5 (delivery + automation) |
| Week 4 | Phase 6 (polish + publish) + start using it daily |

---

## 9. Next Step

Once you're ready, we start **Phase 1** together — I'll write the actual `news_collector.py` code with you, explain every line, and you run it on your own machine. We build this piece by piece, test each one before moving to the next, exactly like the phases above.

Ready to start Phase 1?
