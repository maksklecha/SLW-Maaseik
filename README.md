# KBC For You — Context Engine · SLW Maaseik
Tectonic Hackathon round 1 · KBC challenge

KBC Mobile has hundreds of great features, but the customer has to go looking for them.
**KBC For You** flips this: a Context Engine behind the app watches (fake) transactions, recognises
what is changing in a customer's life, and puts only the **essential, relevant** KBC services on a
personal **For You page**, with a notification at the **right moment** through the **right channel**.

## How it works

```
 START → load_data → classify_merchants → verify_classification → score_industries
                     (Gemini agent: which     (rule check + Gemini      (formula, no LLM)
                      industries, 0-10)        judge; retry or flag)          │
                                                     below benchmark ──► END (no spam)
                                                     above benchmark ↓
                                           recommend (Gemini) → notify (right channel/moment) → END
```

1. **Classify.** An agent rates every company on a 0–10 scale per industry: *travel*, *construction*, *baby & pregnancy*. Each company is classified **once** and cached.
2. **Verify.** A keyword rule check plus an independent Gemini "judge". If they disagree, the agent classifies again once. If they still disagree, the company is flagged `needs_review`.
3. **Score** each industry per customer:

   `score = Σ (relevance/10) × visits² × (total spent / average expense in that industry)`

4. **Benchmark.** Only above an industry's benchmark does Gemini choose the services and write the For You cards (with a "More info" section). The texts are in the customer's language, adapted to their age, occupation and number of children. **Gender is never used to choose products.**
5. **Notify.** "There's an update on your For You page" is sent through the right channel and at the right moment. Customers aged 65+ get a **phone call**, app users get a **push notification**, others get an **email**, always during the customer's usual active hours. Each notification is sent only once per topic.

### Demo scenarios (press "New transactions arrive")

| Customer | What happens | Result |
|---|---|---|
| Yusuf, 31, **0 children** | Repeated visits to a childwear shop | Push notification → kids' savings account + family insurance |
| Lotte, 27 | Flights + hotel bookings | Push notification → travel insurance, card for use abroad, currency tips |
| Marc, **68** | Repeated visits to a DIY store + a tile shop | **Phone call** → renovation loan, home insurance check |
| Emma, 21 | One gift bought at the childwear shop | Stays below the benchmark → **nothing** (no spam) |

### Why it scales to 2.3M customers
- Companies are classified once. The number of companies is far smaller than customers × transactions.
- Scoring is a simple formula that can run every night for every customer.
- The LLM only writes for customers who crossed a benchmark.
- Adding an industry = one entry in `config.py`.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional: add a free Gemini key (aistudio.google.com)
python check_setup.py              # only if you added a key
streamlit run app.py
```

Without a key, everything still runs: a keyword classifier replaces the classification agent and template texts replace the Gemini texts. The app shows which method was used.

| File | What it is |
|---|---|
| `config.py` | Industries, keywords, average expense, benchmarks, KBC services + info |
| `data/seed.json` | **Fake** customers, merchants and transactions (batch 0 = history, batch 1 = new) |
| `db.py` | SQLite schema, seed data, parameterised queries |
| `agents.py` | Gemini classifier, verifier and recommender (+ fallbacks) |
| `scoring.py` | The scoring formula and benchmark check |
| `signals.py` | Rules for the right channel and moment |
| `graph.py` | The LangGraph pipeline |
| `app.py` | Streamlit demo: For You page, Context Engine view, At scale |

## Unfinished / next steps
- Behavioural signals (in-app actions) and context signals (location, e.g. arriving at an airport) as extra inputs to the score.
- The "Interested / Not for me" buttons don't store feedback yet. That feedback should adjust future scores.
- Real KBC data, services and tariffs (everything here is illustrative).
- Real delivery of push, email and phone calls.
- Authentication: the customer picker is for the demo only. A real app shows only the logged-in customer's own data.

## Security & privacy
- Fake data only. No secrets in the repo (`.env` and `kbc.db` are git-ignored).
- All SQL uses parameterised queries.
- LLM output is checked: only known industries and known service IDs are accepted, and scores are clamped to 0–10.
- LLM output is rendered as plain text, never as HTML.
- Sensitive guesses are never stated directly ("planning for your family?", not "congratulations on your baby").
- Gender is not used to decide which products are offered.
