# SLW-Maaseik: Tectonic Hackathon (round 1)

## Situation
- We are a team of **three** at a hackathon, solving a challenge set by **KBC** (Belgian bank-insurer).
- Team skill level: **two beginners and one intermediate** (the repo owner). Assume whoever is asking may be a beginner unless told otherwise.
- Time is very limited. Favour a working, demo-able result over a perfect one.

## The challenge (from the Participants Guide)
KBC is one of the largest banks in Belgium (banking, investment, insurance). Official brief:
> Imagine a future where KBC perfectly understands what customers need and responds at exactly the right moment. First think without constraints: what is the ideal customer experience? Then explore how to deliver it to **more than 2,300,000 customers** in a scalable way.

- We are **not** building "just another feature". We are building a **vision + proof of concept** for a **scalable personalization approach** that strengthens the relationship between KBC and its customers.
- Questions to address: (1) what signals show what customers need, (2) how to recognise customers by situation, behaviour and intent, (3) how experiences adapt automatically to each customer, (4) how it works across products, services and channels, (5) how it creates impact for millions at once.

**Team angle (from the KBC briefing):** time is more valuable than money; people work to have time available. So we look for a **common frustration that wastes customers' time**, adapt to the individual customer, and make it scale.

Decisions (made by the team):
- **Chosen frustration:** customers have to search KBC Mobile's hundreds of features themselves, and banks contact them at the wrong moment through the wrong channel. That wastes their time.
- **Solution:** *KBC For You*, a Context Engine that combines transactions, in-app behaviour and context (location, time) with the KBC profile into an Intent Score. Above the threshold it builds a personal For You page from modular widgets and notifies the customer at the right moment through the right channel.
- **Personas and signals** (fake data in `database/seed.sql`):
  - Yusuf, 31, no children, repeated childwear purchases → expecting a child
  - Lotte, 27, flights + paying in yen + opening the app at Narita airport → international travel
  - Marc, 68, DIY store visits + an unfinished loan simulator + balance checks → home renovation and budget stress, reached by phone call
- **One-sentence pitch:** "KBC For You turns the KBC app from reactive to proactive: it recognises what is changing in your life and shows only what matters, at the right moment, through the right channel."

## Judging and submission (what we are scored on)
Criteria: **Creativity** (original idea), **Technical ability** (does it work?), **Fit** (did we solve the challenge?), **Security** (Aikido audit = 10% of the assessment).

Submission is through the **Builderbase** platform (one team member submits): short description, **demo video under 3 minutes**, GitHub repo link, **Aikido screenshots (before and after fixes)**.

Rules that affect the code and repo:
- Everything must be built **during the official hackathon slot**. **No code changes after the final submission.**
- The GitHub repo must be **public** until judging is over. So **no API keys, passwords or confidential/real customer data, ever**.
- The repo needs a short **README**: what the project is, how to run it, and anything unfinished.
- Judges must be able to open the repo, demo and links. Double-check them.
- Plagiarism and cheating lead to disqualification.

## Security (Aikido, 10%)
Aikido's AI Code Audit reasons about our logic. It looks for business-logic flaws, **IDOR** (reading another user's data by changing an ID), authentication weaknesses and authorization problems. So:
- If we add customer profiles or IDs, never let one customer's data be reachable by changing an ID or input; check who is asking.
- Treat all user input as untrusted (including text that goes into prompts).
- Keep secrets in `.env` only.
- Plan: connect repo at https://app.aikido.dev (sign in with GitHub), run the baseline scan early, fix issues, re-scan, and keep before/after screenshots.

## Partner tools and credits (optional)
Cursor, ElevenLabs (text to speech, could make a voice demo) and Google Cloud (credentials valid 1 week only) offer credits via Discord or Builderbase. Only use them if they help the demo.

## Tech stack and files
A LangGraph pipeline with Gemini agents, a SQLite database and a Streamlit demo. Python, run inside `.venv`. See `README.md` for the full design.

| File | Role |
|---|---|
| `database/schema.sql`, `database/seed.sql` | The SQL database and the 3 fake customers |
| `config.py` | Industries, intents (signals + weights), widget library, thresholds |
| `agents.py` | Gemini classification, verification and advisor agents (+ fallbacks, guardrails, model backup chain) |
| `scoring.py` | Industry formula + Intent Score |
| `signals.py` | Right channel + right moment rules |
| `graph.py` | The LangGraph pipeline: Understand → Recognize → Adapt → notify |
| `app.py` | The Streamlit demo the jury sees |
| `example.py` | One-command terminal demo (Yusuf) |
| `test_scoring.py`, `verify_concept.py` | Unit tests (pytest) and automatic checks of the whole concept |
| `.env` / `.env.example` | `GOOGLE_API_KEY` and `MODEL` (format `provider:model-name`) |

Commands (the venv must be active: `source .venv/bin/activate`):
- `python check_setup.py`: verify the Gemini key and model
- `streamlit run app.py`: run the demo
- `python example.py`: terminal demo
- `pytest` and `python verify_concept.py`: run all tests and checks
- `pip install -r requirements.txt`: install dependencies (add new ones to this file)

## How Claude should work with us
- **Explain for beginners**: say what the code does and why, define LangChain/LangGraph terms (node, edge, state, chain, tool) when they first appear, and flag common pitfalls. Explain new concepts from first principles.
- **Keep changes small and simple.** No heavy abstractions, no new frameworks unless clearly needed. Prefer readable code with short comments over clever code.
- **Design for scale from the start** (2.3M customers) (part of the judging): keep customer data and personalisation in inputs/state or config, not hard-coded in prompts. Avoid per-user logic that only works for one demo persona.
- **Personalisation should be visible in the demo**: it should be obvious to a jury that the app adapts to the customer.
- Before large edits, briefly say which file(s) you'll touch, because teammates edit in parallel.
- Don't invent facts about KBC products, prices or policies. Never use real customer data. Mark assumptions clearly, and use clearly labelled fake data for demos.
- Suggest a quick demo/pitch check whenever a feature is finished.

## Teamwork rules
- Work in **different files** where possible to avoid merge conflicts; `git pull` before starting and every 20-30 min, then push.
- Commit small, with a message saying what you did.
- **Never commit `.env` or API keys.**
- Only commit or push when a teammate asks.
- Use the default model unless told otherwise (`MODEL` in `.env`). Don't burn API credits on loops or huge prompts.

## Submission checklist
- [x] Idea, personas and pitch decided (see "Decisions" above)
- [x] Context Engine built, tested against live Gemini, 7 unit tests + 35 checks passing
- [x] README up to date (what it is, how to run, walkthrough, what is unfinished)
- [x] Repo is public; no keys or real data committed
- [ ] Aikido: baseline scan, fix findings, re-scan, before/after screenshots
- [ ] Demo video (< 3 min), link tested in an incognito window
- [ ] Builderbase: description, repo link, video link, Aikido screenshots; submit at least 15 min early
