# KBC For You — Context Engine · SLW Maaseik
Tectonic Hackathon round 1 · KBC challenge

KBC Mobile has hundreds of great features, but the customer has to go looking for them. **KBC For You**
flips that from reactive to proactive. A **Context Engine** understands the customer's situation and turns
the home screen into a **For You page**, built from modular widgets, with only the essential, relevant
banking, insurance and investment services. A notification tells them about it at the **right moment**,
through the **right channel**.

## How it works: Understand → Recognize → Adapt → Scale

```
 START → load_data → classify_merchants → verify_classification → score_industries → score_intents
         UNDERSTAND   (classification agent)  (verification agent)   (team formula)     RECOGNIZE
                                                                                           │
                                   no intent above 70% ──► normal home screen → END (no spam)
                                   intent(s) validated ↓
                        advisor agent: For You page (ADAPT) → notify: right channel + moment → END
```

1. **Understand.** The engine reads three kinds of data per customer, plus the KBC profile (age, occupation, children, language, preferred channel, active hours):
   - **Transactional:** payments, e.g. repeated childwear purchases, flights, paying in yen.
   - **Behavioral:** in-app actions, e.g. an unfinished renovation loan simulator, balance checks at month-end.
   - **Contextual:** micro-moments, e.g. opening the app at a foreign airport.
2. **Classification agent** (Gemini). Rates every company 0–10 per industry: travel, construction, baby & pregnancy. Each company is classified **once** and cached.
3. **Verification agent.** A keyword rule check plus an independent Gemini reviewer. If they disagree, the company is classified again. If they still disagree, the lowest scores are kept and it's flagged ⚠️ `needs_review`.
4. **Industry score** (team formula): `Σ (relevance/10) × visits² × (total spent / avg. expense in industry)`, compared to a benchmark per industry.
5. **Intent Score** (Recognize). Combines all signals into one percentage per Life Event or Micro-moment:
   `Intent = 1 − Π (1 − weight × strength)`. Flight bookings (0.8) plus a foreign airport (0.75) gives **95%**. Profile checks apply too: baby purchases *without* children count fully, with children the score is halved.
6. **Advisor agent** (Adapt). For intents of **70% or more**, Gemini picks widgets from the library and writes the texts in the customer's language, adapted to their age, occupation and children. **Gender is never used.** Sensitive guesses are never stated directly.
7. **Notify.** One notification per new situation, never repeated:
   - 65+ → 📞 phone call
   - app user → 📱 push
   - otherwise → ✉️ email

   The moment is **right now** when a context trigger fired (just landed abroad). Otherwise it's the customer's usual active hours.

### The 3 example customers (click "⚡ New data arrives")
| Customer | New data | Intent | For You page | Notification |
|---|---|---|---|---|
| **Yusuf**, 31, nurse, **0 children** | 3 more childwear visits, a maternity store, looked at child savings | Expecting a child **94%** | 1-click kids' savings account, family insurance update, budget planner | 📱 Push, 15–17h |
| **Lotte**, 27, developer | Hotel bookings, 2nd flight, **payments in JPY**, opened the app at **Narita airport** | International travel **98%** | Currency converter, unblock card worldwide, luggage micro-insurance | 📱 Push, **right now** |
| **Marc**, 68, retired homeowner | 4× DIY store, tile shop, unfinished loan simulator, balance checks at month-end | Home renovation **93%** + budget stress **74%** | Renovation loan simulator, home insurance check, month overview, advisor call | 📞 **Phone call**, weekday 9–11h |

Before the new data arrives, all three are below the threshold, so they see the normal home screen with no message.

## Walkthrough: Yusuf, before and after

Run `python example.py` to see this in your terminal. No Streamlit or API key is needed.
A saved run is in **[examples/yusuf_output.txt](examples/yusuf_output.txt)**. It was made without an API key, so it shows the keyword classifier and template texts.

| Step | Before (history) | After "new data arrives" |
|---|---|---|
| Raw data | 3 transactions, incl. 1× Little Stars Childwear €55 | +3× Little Stars Childwear (€60, €48, €77), 1× Prenatal Antwerpen €80, looked at child savings + family insurance in the app |
| Classification | Little Stars Childwear → Baby & pregnancy **9/10** ✅ verified | + Prenatal Antwerpen → Baby & pregnancy **10/10** ✅ verified |
| Industry score (benchmark 50) | **1.24**, below | **88.4**, above |
| Intent "expecting / planning a child" (threshold 70%) | **2%** | **94%** ✅ validated |
| Notification + For You page | none, normal home screen | 📱 Push, today 15:00–17:00 → kids' savings account, family insurance update, family budget planner |

### Worked example of the scoring formula (real numbers from the code)

`score = Σ (relevance/10) × visits² × (total spent / average expense in the industry)`

The average expense for Baby & pregnancy is **€40**, and the benchmark is **50** (both set in `config.py`).

- **Yusuf, after:**
  - Little Stars Childwear: 0.9 × 4² × (240 / 40) = 0.9 × 16 × 6 = **86.4**
  - Prenatal Antwerpen: 1.0 × 1² × (80 / 40) = 1.0 × 1 × 2 = **2.0**
  - Total: **88.4 ≥ 50**, so the transactional signal is at full strength.
- **Yusuf, before:** 0.9 × 1² × (55 / 40) = **1.24**, far below 50.
- **Emma (one gift):** one childwear purchase of €35, bought as a present: 0.9 × 1² × (35 / 40) = **0.79**, far below 50.

This is the "no spam" rule. Because visits are **squared**, one purchase barely counts and **repeated** visits add up very fast. A single gift never triggers a message.

**The Intent Score** then combines this with the other signals: `1 − (1 − 0.85×1.0) × (1 − 0.40×1) × (1 − 0.30×1) = 1 − 0.15 × 0.6 × 0.7 = 93.7%`. The three factors are the purchases, the child savings page and the family insurance page. If Yusuf already had children, the score would be halved to 47%, below the threshold.

These numbers are checked automatically in [test_scoring.py](test_scoring.py). Run it with `pytest`.

### What is tested, and what is not
- ✅ **Unit tests** (`pytest`): 6 tests of the formulas and scenarios.
- ✅ **`python verify_concept.py`**: 30 checks of every mechanism, including the Gemini code paths with a stub model (verification retry, output guardrails, no duplicate notifications, no repeated LLM calls).
- ⚠️ **Not yet run against the live Gemini API.** The Gemini client is created and wired up, but real Gemini answers haven't been checked. With a key, the texts are written by Gemini instead of the templates in the saved example.
- ⚠️ **Unfinished:** see the list below.

### Why it scales to 2.3M customers
- Companies are classified once; there are far fewer companies than customers × transactions.
- Both scores are formulas (no LLM), cheap enough to run every night for every customer.
- Gemini only runs when a customer's situation changes. A page refresh makes no new call.
- A new industry, intent or widget is one entry in `config.py`, with no human work per customer.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # paste your free Gemini key (https://aistudio.google.com → Get API key)
python check_setup.py              # tests the Gemini connection
streamlit run app.py
python example.py                  # one customer as a story in the terminal (no Streamlit)
pytest                             # 6 unit tests of the scoring logic
python verify_concept.py           # 30 automatic checks of every mechanism
```

**Without a key, everything still runs:** a keyword classifier and template texts replace Gemini, and the app shows which method was used.

**Share it online without sharing your key:**
1. Deploy the repo for free on [Streamlit Community Cloud](https://share.streamlit.io).
2. Paste `GOOGLE_API_KEY` in the app's **Secrets** settings (see `.streamlit/secrets.toml.example`).

Anyone with the link then uses Gemini. **Never commit a key to this repo.**

| File | What it is |
|---|---|
| `database/schema.sql` | The SQL database: KBC input tables + what the engine learns |
| `database/seed.sql` | The 3 **fake** customers with transactions, app events and context events |
| `config.py` | Industries, intents (signals + weights), widget library, thresholds |
| `db.py` | Builds `kbc.db` from the SQL files, parameterised queries |
| `agents.py` | Gemini classification, verification and advisor agents (+ fallbacks + output guardrails) |
| `scoring.py` | Industry formula + Intent Score |
| `signals.py` | Right channel + right moment rules |
| `graph.py` | The LangGraph pipeline |
| `app.py` | Streamlit demo: For You page, Context Engine view, At scale |
| `verify_concept.py` | Automatic checks of the whole concept |
| `example.py` | One-command demo for one customer, printed as a story |
| `examples/yusuf_output.txt` | Saved output of `example.py` (no API key) |
| `test_scoring.py` | Unit tests (pytest) |

## Unfinished / next steps
- Real KBC data, products and tariffs (everything here, including the rates, is illustrative).
- Learning from feedback: "Not for me" hides a widget, but doesn't yet lower future scores.
- Real delivery of push, email and phone calls, and real card or insurance actions.
- Authentication: the customer picker is for the demo only. A real app shows only the logged-in customer's own data.
- Not yet run against the live Gemini API (the Gemini paths are tested with a stub model in `verify_concept.py`).

## Security & privacy
- Fake data only. `.env`, `kbc.db` and Streamlit secrets are git-ignored.
- All SQL uses `?` placeholders (no SQL injection).
- LLM output guardrails: only known industries, intents and widget IDs are accepted, and scores are clamped to 0–10.
- LLM text is rendered as plain text, never as HTML.
- Gender is not used to choose products. Sensitive guesses are never stated ("planning for your family?").
- Every section has a "Why am I seeing this?" explanation.
