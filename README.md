# KBC For You — SLW Maaseik
Tectonic Hackathon ronde 1 · KBC challenge

**Time is worth more than money.** Customers don't want to hunt for the right bank product:
KBC should notice what's going on in their life and offer the right help,
**at the right moment, through the right channel**.

**KBC For You** is a personalised feed + notification engine:

1. **Signals** from (fake) customer data: profile (age, gender, occupation, language) + transactions.
   Example: Lotte (27) is paying in **JPY** in Tokyo → foreign-currency fees.
2. **Offer matching**: each signal maps to a KBC service (e.g. *Travel & FX advice*).
3. **Right moment & channel**: based on the profile. Lotte is abroad and uses the app → push
   notification tonight during her usual active hours. Marc (68) → email / advisor call.
4. **Personal message**: an LLM writes the card in the customer's own language and tone.

```
START → detect_signals → match_offers → write_messages → END
        (rules)          (rules)         (LLM, with fallback text)
```

**Why it scales to 2.3M customers:** steps 1–3 are cheap rules that can run nightly on every
customer; the LLM is only used for the final wording, and the demo still works without it.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional: add an API key for LLM-written messages
streamlit run app.py
```

| File | What it is |
|---|---|
| `data/customers.json` | 5 **fake** customers (profile + transactions) |
| `signals.py` | Rules: signals, KBC service catalogue, moment & channel |
| `graph.py` | LangGraph pipeline + LLM message writer |
| `app.py` | Streamlit demo: For You page + "At scale" view |

## Unfinished / next steps
- Real KBC data & product catalogue (fees and services here are illustrative).
- Learn from "Interested / Not for me" clicks to improve ranking.
- Real delivery via push/email/voice (e.g. ElevenLabs for a voice channel).
- Authentication: the demo lets you pick any fake customer; a real app would only show the logged-in customer's own feed.

## Security
No real customer data, no secrets in the repo (`.env` is git-ignored), LLM output is rendered as plain text.
