# HANDOFF — Tectonic Hackathon (KBC challenge) · Team SLW Maaseik

> **UPDATE (latest decisions, these override §3–§4 below):** the repo now implements the
> **Context Engine** described in `README.md`:
> - **LLM:** Google Gemini, via `langchain-google-genai` and `GOOGLE_API_KEY`.
> - **3 industries** in `config.py`: travel, construction, baby & pregnancy.
> - **Industry classification agent** (0–10 per industry, cached per merchant) + a **verification step** (rule check + Gemini judge, one retry, else `needs_review`).
> - **Formula:** `score = Σ (relevance/10) × visits² × (total_spent / avg_expense)` (`scoring.py`).
> - **Per-industry benchmark** → Gemini recommender writes the For You cards with "more info" → notification via the right channel (65+ → phone call) and moment (`signals.py`).
> - **Pipeline:** `graph.py`. **Data:** `data/seed.json` → SQLite `kbc.db` (`db.py`). **UI:** `app.py`.
> - Behavioural and context signals are listed as next steps.

> **For Claude Code:** read this whole file before doing anything. It is the full context
> of an earlier planning session. The team are **3 Python beginners** who just finished a
> LangChain/LangGraph course. Explain what you do in plain language, define framework terms
> (node, edge, state, tool, agent, structured output...), flag beginner pitfalls, and keep the
> code simple, well-commented and readable. Prefer a working small thing over an ambitious broken one.

---

## 1. The hackathon (facts from the official Participants Guide)

- **Event:** Tectonic Hackathon, round 1 (preselection), 30 Sep 2026, 18:00–23:00. Finals 20 Oct in Ghent (€10,000 prize). 32 teams qualify (16 per track).
- **Our track:** **KBC** only (ignore SD Worx).
- **KBC challenge (paraphrased):** Imagine a KBC that perfectly understands what customers need and
  responds at exactly the right moment. First think without constraints about the ideal customer
  experience, then show how it could be delivered to **2.3 million customers** in a scalable way.
  They want **not "just another feature"**, but a **vision + proof of concept** for a *scalable
  personalisation approach* that changes how KBC understands, supports and guides customers.
- **KBC's guiding questions** (our solution must answer each one):
  1. What **signals** help understand what customers need?
  2. How can customers be recognised by **situation, behaviour and intent**?
  3. How can personalised experiences **adapt automatically** to each customer?
  4. How can it work **across products, services and channels**?
  5. How to create impact for **millions of customers at the same time**?
- **Extra framing given to us by KBC on the day:** *time is more valuable than money today* —
  people have a common frustration (wasting time on admin/searching), the solution must adapt to
  each customer and be able to scale.

### Judging criteria
1. **Creativity** – how original is the idea?
2. **Technical ability** – does it work?
3. **Fit** – did we solve the challenge?
4. **Security** – how secure is it? (**Aikido** security audit = **10%** of the score)

### What to submit (on the Builderbase platform, one team member submits)
- [ ] Short description of the project
- [ ] **Demo video < 3 minutes** (team decided: a video explaining the idea + code; a short live run is strongly recommended, see §9)
- [ ] **Public GitHub repo** link: https://github.com/maksklecha/SLW-Maaseik
- [ ] **Aikido screenshots, before and after** fixing issues
- [ ] **README**: explain the project, how to run it, and what is unfinished

### Rules that matter
- Built within the time slot. One submission per team. **Final means final** — no edits after submitting.
- Repo must stay **public** until judging is complete.
- **Never upload passwords, API keys or confidential data.** Use **fake data only**.

### Technical partners (from the guide)
- **Aikido** (required): sign up via https://app.aikido.dev/ai-pentests/discounts/hackathon-tectonic-aikido
  with "Continue with GitHub", connect the repo, run the **AI Code Audit** (baseline), fix issues,
  mark resolved, screenshot before/after. It checks: business-logic flaws, **IDOR** (accessing other
  users' data by changing an ID), authentication, authorization.
- **Google Cloud**: free credits via the team link on Builderbase (valid 1 week) → possible free LLM (Gemini).
- **ElevenLabs** (text-to-speech) and **Cursor** credits via the hackathon Discord — optional.

---

## 2. Our idea — "KBC For You" with a living customer profile

**One-liner:** *KBC doesn't just know who you are — it notices what is changing in your life and
helps at the right moment, through the right channel.*

- KBC already has a **static profile** per customer (age, gender, occupation, city, language,
  preferred channel...).
- We add a **living profile**: an **LLM agent** continuously reads **new transactions** and
  **predicts life changes** (new baby, moving house, new job/first salary, retirement, new car,
  travelling abroad...). Each prediction has a **confidence score (0–1)** and the **evidence** behind it.
- From the living profile, KBC recommends the right **KBC service** (child savings account, family
  insurance, travel insurance, financial advice, savings plan...) on a personal **For You page**,
  delivered at the **right moment** (the customer's usual active hours / relevant timing) through the
  **right channel** (push notification, in-app card, email, advisor call) based on their profile.

### Example stories (use these in data + video)
| Customer | Signal in transactions | Predicted change | KBC service | Channel / moment |
|---|---|---|---|---|
| Yusuf, 34, night-shift nurse | Several purchases at baby stores | Expecting / new child | Child savings account + family insurance | In-app card, 15–17h (he works nights) |
| Lotte, 27, developer | Many payments in **JPY**, now in Japan | Travelling abroad | Travel & FX advice (cut foreign-currency fees) | **Push now**, during her evening phone time |
| Marc, 68, retired | Large idle balance on current account | Money not working for him | Financial advisory appointment | **Advisor call / email**, mornings |
| Emma, 21, student | First salary + 5 subscriptions | Financial independence | Automatic savings plan + subscription overview | In-app card, late evening |
| Sofie, 45, freelancer | Flight to US booked in 14 days | Upcoming trip | Travel insurance | Email, 2 weeks before departure |

> ⚠️ **Accuracy note (keep it):** the team's first idea said "paying in euros instead of yen saves
> money". That is usually **false** — accepting "pay in euros?" on a foreign card terminal
> (*dynamic currency conversion*) is typically **more** expensive. Phrase the advice as
> **"cut foreign-currency fees / choose the local currency"** with a KBC travel/advice service.

### How it answers KBC's 5 questions (pitch material)
1. **Signals** → transactions (merchant category, currency, country, recurring amounts, first-time income) + static profile.
2. **Situation / behaviour / intent** → the living profile: predicted life events with confidence + evidence.
3. **Adapts automatically** → the profile updates with every new batch of transactions; messages adapt tone/language/channel to the person.
4. **Across products & channels** → one life event triggers several services (savings + insurance + advice) and picks the channel per customer.
5. **Millions at once** → cheap **rules/SQL pre-filter** runs on everyone; the **LLM only runs for customers where something changed**, and only for interpretation + wording (see §4-C).

---

## 3. Current state of the repo (at hand-over)

```
SLW-Maaseik/
├── README.md            # project README (rules require it) — update at the end
├── HANDOFF.md           # this file
├── requirements.txt     # langchain, langchain-anthropic, langchain-openai, langgraph, streamlit, python-dotenv, pandas
├── .env.example         # template: ANTHROPIC_API_KEY / OPENAI_API_KEY / MODEL=provider:model
├── .gitignore           # ignores .env, .venv, __pycache__, .DS_Store, editor folders
├── check_setup.py       # tests that the API key + model work
├── data/customers.json  # 5 FAKE customers (profile + transactions) — the stories above
├── signals.py           # RULES: detect_signals(), CATALOG of KBC services, pick_channel(), pick_moment(), build_offers()
├── graph.py             # LangGraph: START → detect_signals → match_offers → write_messages → END
└── app.py               # Streamlit UI: "For You page" tab + "At scale" tab
```

- **Working prototype (tested):** rule-based signals → service matching → moment & channel →
  LLM writes each card (title, message, notification) in the customer's language via
  `with_structured_output(Card)`. **If there is no API key or the LLM call fails, it falls back to
  template text**, so the app never crashes. Cards show "Why am I seeing this?" (evidence).
- **Not yet tested:** the LLM-written messages (no API key was available).
- **Not yet built:** the **SQL database**, the **agents**, the **continuous/living profile** (§4–§5).
- Model is chosen by `MODEL` in `.env` via LangChain's `init_chat_model("provider:model")`, e.g.
  `anthropic:claude-sonnet-5-5`, `openai:gpt-4o-mini`, or a Google Gemini model via `google_genai:...`
  (would need `langchain-google-genai` added to requirements).
- **Git:** latest commit `b54ee1a` (the prototype) might **not be pushed** yet — the original laptop's
  network blocked GitHub. Run `git status` / `git log origin/main..` and push if needed.
- **Collaboration:** Live Share was **dropped**. Each teammate works on their own laptop and
  collaborates through **GitHub** (pull/push every 20–30 min, work in separate files).
- **Env notes:** the original venv used Python 3.12 via `uv` (`uv venv --python 3.12 .venv`);
  Python 3.14 is the system default and some packages may lack wheels for it — prefer 3.11/3.12.

---

## 4. Target architecture (the plan to build)

### 4.1 Database: SQLite (proof of concept)
SQLite = a full SQL database stored in **one file** (`kbc.db`), built into Python (`import sqlite3`),
no server. Same SQL moves to PostgreSQL later ("scales to a real bank database" in the pitch).

**Design principle:** keep **facts** (static profile, transactions) **separate from predictions**
(living profile). A prediction is never "true", only "likely" → always store confidence + evidence + status.

Proposed schema (adapt as needed):

```sql
CREATE TABLE customers (
    id TEXT PRIMARY KEY,               -- e.g. 'C001'
    name TEXT, age INTEGER, gender TEXT, occupation TEXT, city TEXT,
    language TEXT,                     -- 'nl' | 'fr' | 'en'
    preferred_channel TEXT,            -- 'app' | 'email'
    active_hour_start INTEGER, active_hour_end INTEGER,
    balance_eur REAL, monthly_expenses_eur REAL,
    location_now TEXT                  -- country code, e.g. 'BE', 'JP'
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT REFERENCES customers(id),
    date TEXT, merchant TEXT, category TEXT,  -- 'baby', 'travel', 'salary', 'subscription', ...
    amount REAL, currency TEXT, amount_eur REAL, country TEXT,
    batch INTEGER DEFAULT 0,           -- 0 = history, 1,2,... = "new transactions arrive" for the demo
    processed INTEGER DEFAULT 0        -- has the profiler already seen this row?
);

CREATE TABLE profile_insights (      -- THE LIVING PROFILE (written by the Profiler agent)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT REFERENCES customers(id),
    insight TEXT,                      -- e.g. 'expecting_child', 'moving_house', 'travelling_abroad'
    confidence REAL,                   -- 0..1
    evidence TEXT,                     -- human-readable reason
    status TEXT DEFAULT 'active',      -- 'active' | 'confirmed' | 'rejected' | 'expired'
    first_seen TEXT, last_updated TEXT
);

CREATE TABLE profile_summary (       -- readable text summary of the customer (approach E)
    customer_id TEXT PRIMARY KEY REFERENCES customers(id),
    summary TEXT, last_updated TEXT
);

CREATE TABLE kbc_services (          -- catalogue the Advisor may choose from (illustrative)
    id TEXT PRIMARY KEY, name TEXT, description TEXT,
    related_insights TEXT              -- comma-separated insight keys
);

CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT REFERENCES customers(id),
    insight_id INTEGER REFERENCES profile_insights(id),
    service_id TEXT REFERENCES kbc_services(id),
    channel TEXT, moment TEXT, title TEXT, message TEXT, notification TEXT,
    created_at TEXT
);

CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT REFERENCES customers(id),
    recommendation_id INTEGER REFERENCES recommendations(id),
    reaction TEXT,                     -- 'interested' | 'not_for_me'
    created_at TEXT
);
```

Seed it from `data/customers.json` (plus extra **batch 1/2** transactions for the demo, e.g. more
baby-store purchases for Yusuf so his confidence visibly rises).

### 4.2 Orchestration (LangGraph)

```
                    ┌──────────────── SQLite (kbc.db) ────────────────┐
                    │ customers · transactions · profile_insights      │
                    │ profile_summary · kbc_services · recommendations │
                    └──────▲──────────────▲────────────────▲───────────┘
                           │ tools         │ tools            │
new transactions ──► [0 Rules pre-filter] ──► [1 Profiler agent] ──► [2 Advisor agent] ──► [3 Guardrail check] ──► For You page
                     "did anything        "what changed in      "which service,       "creepy, pushy,
                      change?" (no LLM)     this person's life?"  channel, moment?"      sensitive?"
```

- **Agent** = an LLM in a loop with **tools** (Python functions it may call). In LangGraph:
  `from langgraph.prebuilt import create_react_agent` (ReAct = Reason + Act).
- **0. Rules pre-filter (no LLM):** reuse/extend `signals.py`. Only customers with unprocessed
  transactions that trigger a rule go to the LLM → this is the **scaling argument**.
- **1. Profiler agent** — tools (read-only except one narrow write):
  - `get_customer(customer_id)` → static profile
  - `get_current_profile(customer_id)` → active insights + summary
  - `get_new_transactions(customer_id)` → unprocessed rows
  - `upsert_insight(customer_id, insight, confidence, evidence)` → add/update one insight
  - `update_summary(customer_id, summary)`
  - Then mark the transactions `processed = 1`.
  - Rules for confidence: one weak hint ≈ 0.3 (could be a gift); repeated evidence raises it
    (e.g. 5 baby purchases in 2 months ≈ 0.85); insights without new evidence decay/expire.
- **2. Advisor agent** — for each insight with **confidence ≥ 0.7**: pick a service from
  `kbc_services`, pick **channel + moment** (reuse `pick_channel` / `pick_moment` logic from
  `signals.py`), write title/message/notification in the customer's **language and tone**
  (structured output), store in `recommendations`.
- **3. Guardrail check** — one LLM (or rule) pass that rejects/rewrites messages that reveal a
  sensitive prediction, are pushy, or touch sensitive categories (see §6).
- **Continuous in the demo:** a Streamlit button **"New transactions arrive"** loads the next batch
  and re-runs the pipeline → the profile and confidence bars visibly change.

**Agent pitfalls to avoid:** few tools per agent (3–5), a step limit (`recursion_limit`), tools that
only read what they need, and **never a "run any SQL" tool** (prompt injection could run
`DELETE FROM customers`; Aikido would flag it). Use **parameterised queries**
(`cursor.execute("... WHERE id = ?", (customer_id,))`), never f-strings in SQL (SQL injection).

### 4.3 Profile-building approaches (decided direction: **B + C + E**, a small D)
- **A. One-shot structured profile:** one LLM call on all data → fixed Pydantic schema. Simple, not continuous.
- **B. Incremental memory profile (chosen core):** LLM gets the **existing profile + only new
  transactions** and returns **changes** (add / raise / lower / expire insights). Truly "continuous"
  and cheap. Demo: watch confidence grow as batches arrive.
- **C. Rules first, LLM second (chosen):** cheap SQL/rules decide *who* needs the LLM → scales to 2.3M.
- **D. Multi-agent specialists:** supervisor + analyst/profiler/advisor/critic. Impressive but hard to
  debug — we do a **small version**: Profiler + Advisor + Guardrail.
- **E. Readable profile summary (chosen):** short plain-text description kept next to the structured
  insights; the Advisor uses it for more natural messages; nice to show on screen.

Suggested Pydantic output schema for the Profiler (if using structured output instead of tools):
```python
class InsightChange(BaseModel):
    insight: str          # e.g. "expecting_child"
    action: Literal["add", "increase", "decrease", "expire"]
    confidence: float     # new value 0..1
    evidence: str

class ProfileUpdate(BaseModel):
    changes: list[InsightChange]
    summary: str          # updated readable summary (approach E)
```

### 4.4 Proposed file layout (split so 3 people can work in parallel without merge conflicts)
```
db.py            # create schema, seed from JSON, small query helpers (parameterised!)   → person B
data/            # customers.json + demo transaction batches                          → person B
signals.py       # rules pre-filter + channel/moment rules (exists)                    → person A/B
agents.py        # tools + Profiler agent + Advisor agent + guardrail                  → person A
graph.py         # LangGraph wiring: prefilter → profiler → advisor → guardrail        → person A
app.py           # Streamlit: For You page, living profile view, "new transactions" button, At scale tab → person C
README.md        # final project README                                               → person C
```

---

## 5. UI plan (Streamlit, `app.py`)
- Select a (fake) customer → static profile card.
- **Living profile** panel: insights with **confidence bars** + evidence + summary text.
- **For You page**: recommendation cards (title, message, service, channel, moment, notification
  preview, "Why am I seeing this?", buttons **Interested / Not for me** → write to `feedback`,
  "Not for me" lowers the insight's confidence).
- Button **"New transactions arrive"** → next batch → rerun pipeline → profile changes live.
- **At scale** tab: table of all customers → insights → services → channels; explain rules-first scaling.
- Streamlit pitfall: the script re-runs top-to-bottom on every click → keep state in
  `st.session_state` / the database, and cache expensive LLM calls (`st.cache_data`).
- Render LLM output as plain text (`st.write`), **never** with `unsafe_allow_html=True`.

---

## 6. Privacy, ethics & security (judges will ask; also the Security score)
- Famous cautionary tale: a retailer (Target) predicted a pregnancy from purchases and sent baby
  coupons before the family knew. A bank must do better:
  - **Never state the prediction** ("Congrats on your baby!") → use soft wording
    ("Planning for your family's future? Discover the child savings account.").
  - **Confidence threshold** (≥ 0.7) before acting.
  - **Explainability:** always show "Why am I seeing this?".
  - **Customer control:** "Not for me" lowers confidence; the customer can see/delete their profile.
  - **Sensitive categories** (health, religion, financial distress...) → **no automatic marketing**,
    only human advisor or nothing (guardrail's job). Mention **GDPR**.
- **Security checklist (for Aikido):** no secrets in the repo (`.env` git-ignored, `.env.example`
  only placeholders); fake data only; parameterised SQL; no raw-SQL tool for agents; input
  validation on customer IDs; LLM output rendered as text; document in the README that the demo
  customer selector stands in for **authentication** (a real app shows only the logged-in
  customer's own data — this pre-empts an IDOR finding).

---

## 7. Accounts / keys (beginner guide)
- **LLM key is needed to actually run the agents** (a few cents per run). Options:
  1. **Free:** Google Cloud hackathon credits (Builderbase team link) or **Google AI Studio**
     (aistudio.google.com → "Get API key", free tier with rate limits).
  2. **~€5:** Anthropic (platform.claude.com → Billing → API Keys) or OpenAI (platform.openai.com).
  - API credit ≠ ChatGPT Plus / Claude Pro subscription. Set a **spending limit**. Key goes **only
    in `.env`**, shared privately between teammates, **never** committed or pasted in chat/screenshots.
    Revoke it after the hackathon (repo is public).
- **Free, no account needed:** Python, LangChain, LangGraph, Streamlit, SQLite.
- **Optional free:** LangSmith (smith.langchain.com) to trace agent steps (nice in the video).
- **Required:** Aikido (hackathon link above), GitHub (repo public).
- **Code must still run without a key** (fallback text) so nothing crashes; say clearly in the README
  which parts were tested with a real LLM.

---

## 8. Team workflow (no Live Share — GitHub only)
- Everyone: clone, `python3 -m venv .venv`, `source .venv/bin/activate`,
  `pip install -r requirements.txt`, `cp .env.example .env`, add the shared key, `streamlit run app.py`.
- Repo owner adds the other two as **collaborators** (GitHub → Settings → Collaborators).
- **Split by file** (§4.4). `git pull` → work → `git add <files>` → `git commit -m "..."` → `git pull` → `git push`,
  every 20–30 min. "Rejected" on push = pull first. Merge conflict = two people edited the same lines.

---

## 9. Video (< 3 min) — suggested script
1. **Problem (20 s):** time > money; people waste time finding the right bank help; banks message at the wrong moment/channel.
2. **Idea (30 s):** living profile that predicts life changes from transactions → For You page, right moment, right channel.
3. **Live run (60–80 s):** Yusuf → "new transactions arrive" → confidence "expecting child" rises
   0.3 → 0.85 → soft-worded child savings card in the app, 15–17h. Then Lotte in Japan → push notification.
   Show "Why am I seeing this?".
4. **Scale + architecture (30 s):** rules/SQL pre-filter on 2.3M customers, LLM only where something changed; diagram of §4.2.
5. **Trust & security (15 s):** confidence threshold, soft wording, customer control, GDPR, Aikido score.
- Even if the team only explains the code, **30 s of a real run** strongly helps "Technical ability: does it work?".

---

## 10. Priority order for building (time is short)
1. `db.py` + seed data (with batches) — the foundation.
2. Profiler agent updating `profile_insights` (approach B) — the core of the idea.
3. Advisor agent + reuse channel/moment rules → `recommendations`.
4. Streamlit: living profile + For You cards + "new transactions" button.
5. Guardrail check, feedback buttons, At scale tab.
6. README update, Aikido scan → fix → rescan (screenshots), make repo public, record video, **submit ≥ 15 min early**.

Keep the existing no-key fallback working at every step, so there is always something to show.
