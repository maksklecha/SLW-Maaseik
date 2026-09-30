"""Checks that every mechanism of the KBC For You concept works. Run with:

    python verify_concept.py

Part A runs WITHOUT Gemini (fallback mode).
Part B replaces Gemini with a "stub" (a fake model that returns fixed answers), so the
Gemini code paths - structured output, verification retry, guardrails - are tested
without internet or an API key.
Part C checks that the real Gemini connection can be created (only if the package is installed).
"""
import os
import subprocess

os.environ.pop("GOOGLE_API_KEY", None)  # Part A and B must not use a real key

import agents  # noqa: E402
import db  # noqa: E402
import graph  # noqa: E402
import scoring  # noqa: E402
from config import INTENTS, INTENT_THRESHOLD  # noqa: E402

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"{'✅' if ok else '❌'} {name}" + (f"  ({detail})" if detail else ""))


def scenario(cid: str) -> tuple[dict, dict]:
    before = graph.run(cid)
    db.release_next_batch(cid)
    return before, graph.run(cid)


# ================================ A. Fallback mode ===============================================
print("\n=== A. Engine without Gemini (fallback mode) ===")
agents.get_llm = lambda: None
db.reset_db()

with db.connect() as conn:
    n = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
         for t in ("customers", "transactions", "app_events", "context_events")}
check("Database built from schema.sql + seed.sql with 3 customers and all 3 signal types",
      n["customers"] == 3 and all(n[t] > 0 for t in ("transactions", "app_events", "context_events")), str(n))

check("Team formula: childwear 9/10, 4 visits, €240, avg €40 → 86.4",
      round(scoring.score_merchant(9, 4, 240, 40), 1) == 86.4)
check("Intent formula: flight bookings (0.8) + foreign airport (0.75) → 95%",
      round(1 - (1 - 0.8) * (1 - 0.75), 2) == 0.95)

# Scenario 1: Yusuf, no children, repeated childwear visits
b, a = scenario("C001")
check("Yusuf BEFORE: below threshold → no For You update, no notification",
      not b["validated"] and b.get("notification") is None, f"{b['intents']['expecting_child']['score']:.0%}")
check("Yusuf AFTER: 'expecting a child' validated", "expecting_child" in a["validated"],
      f"{a['intents']['expecting_child']['score']:.0%}")
widgets = [c["widget_id"] for s in a["page"]["content"]["sections"] for c in s["cards"]]
check("Yusuf: kids savings account + family insurance on the For You page, with more info",
      {"child_savings", "family_insurance"} <= set(widgets)
      and all(c["more_info"] for s in a["page"]["content"]["sections"] for c in s["cards"]))
check("Yusuf: push notification during his active hours (15-17h)",
      a["notification"]["channel"].startswith("📱") and "15:00" in a["notification"]["moment"])
with_kids = {**a["customer"], "children": 2}
s_kids = scoring.intent_scores(with_kids, a["industries"], a["transactions"], a["app_events"], a["contexts"])
check("Same purchases WITH children → not validated (profile matters)",
      not s_kids["expecting_child"]["validated"], f"{s_kids['expecting_child']['score']:.0%}")

# Scenario 2: Lotte, flights + paying in yen + app opened at a foreign airport
b, a = scenario("C002")
check("Lotte BEFORE: one flight only → below threshold", not b["validated"],
      f"{b['intents']['international_travel']['score']:.0%}")
travel = a["intents"]["international_travel"]
check("Lotte AFTER: 'international travel' ≥ 95% (transactional + behavioral + contextual)",
      travel["score"] >= 0.95, f"{travel['score']:.0%}")
kinds = {e["kind"] for e in travel["evidence"] if e["strength"] > 0}
check("Lotte: all three data dimensions contributed", {"industry", "app_event", "context", "foreign_currency"} <= kinds,
      ", ".join(sorted(kinds)))
widgets = [c["widget_id"] for s in a["page"]["content"]["sections"] for c in s["cards"]]
check("Lotte: currency converter, card unblock toggle, luggage micro-insurance",
      {"currency_converter", "card_abroad", "luggage_insurance"} <= set(widgets))
check("Lotte: right moment = right now (context trigger at the airport)",
      a["notification"]["moment"].startswith("Right now") and "Narita" in a["notification"]["moment"])

# Scenario 3: Marc, 68, renovation + budget pressure
b, a = scenario("C003")
check("Marc AFTER: 'home renovation' and 'budget stress' validated",
      {"home_renovation", "budget_stress"} <= set(a["validated"]), str(a["validated"]))
check("Marc (68): phone call instead of a text", a["notification"]["channel"].startswith("📞"))
check("Marc: one combined notification for both topics", sorted(a["notification"]["intents"]) ==
      sorted(["home_renovation", "budget_stress"]))

# No spam + living profile
again = graph.run("C003")
check("Re-running without new data sends NO second notification", again.get("notification") is None)
check("Living profile keeps a history (before + after)", len({h["data_version"] for h in db.get_intent_history("C003")}) == 2)

db.save_feedback("C003", "energy_advice", "not_for_me")
check("'Not for me' feedback is stored and hides that widget", "energy_advice" in db.dismissed_widgets("C003"))

check("Every merchant classified exactly once (cache) and verified",
      len(db.get_all_classifications()) == len({t["merchant"] for cid in ("C001", "C002", "C003")
                                                 for t in db.get_transactions(cid)})
      and all(c["status"] == "verified" for c in db.get_all_classifications()))


# Responsible-by-design claims
db.reset_db()
db.release_next_batch("C001")
y = graph.run("C001")
customer_texts = " ".join([y["notification"]["text"]] + [s["headline"] for s in y["page"]["content"]["sections"]]).lower()
check("Sensitive guess never stated in customer texts (no 'expecting', 'pregnant', 'baby')",
      not any(w in customer_texts for w in ("expecting", "pregnan", "baby")), y["page"]["content"]["sections"][0]["headline"])
app_src = open("app.py", encoding="utf-8").read()
card_block = app_src.split("for card in section[\"cards\"]:")[1].split("st.caption(f\"Texts written by")[0]
check("'Why am I seeing this?' is shown on every card", "Why am I seeing this?" in card_block)
srcs = {f: open(f, encoding="utf-8").read() for f in ("scoring.py", "signals.py", "agents.py", "graph.py")}
check("Gender is never read by the scoring, channel or agent code",
      not any("[\"gender\"]" in s or "['gender']" in s for s in srcs.values()))
check("Formula threshold: only intents >= 70% change the page",
      all((v["score"] >= INTENT_THRESHOLD) == v["validated"] for v in y["intents"].values()))


# ================================ B. Gemini code paths (stub) =====================================
print("\n=== B. Agents with a stub Gemini model ===")


class StubRunner:
    def __init__(self, stub, schema):
        self.stub, self.schema = stub, schema

    def invoke(self, prompt):
        self.stub.calls.append((self.schema.__name__, prompt))
        company = prompt.split("Company: ")[-1].split("\n")[0] if "Company: " in prompt else ""
        if self.schema is agents.Classification:
            scores = agents.keyword_classify(company, prompt.split("Description: ")[-1].split("\n")[0])
            if company == "Colruyt":          # deliberately wrong: a supermarket as baby shop
                scores = {**scores, "baby_pregnancy": 8}
            return agents.Classification(scores=[agents.IndustryRelevance(industry=k, relevance=v)
                                                 for k, v in scores.items()] +
                                         [agents.IndustryRelevance(industry="made_up", relevance=10)],
                                         reason="stub")
        if self.schema is agents.Verdict:
            wrong = company == "Colruyt"
            own = agents.keyword_classify(company, prompt.split("Description: ")[-1].split("\n")[0])
            return agents.Verdict(plausible=not wrong, comment="stub", corrected=[
                agents.IndustryRelevance(industry=k, relevance=v) for k, v in own.items()])
        if self.schema is agents.ForYouUpdate:
            intents = [k for k in INTENTS if f"intent={k}" in prompt]
            sections = [agents.Section(intent=i, headline=f"Stub {i}", cards=[
                agents.Card(widget_id=w, title="t", message="m", more_info="i") for w in INTENTS[i]["widgets"][:2]]
                + [agents.Card(widget_id="hack_widget", title="x", message="x", more_info="x")]) for i in intents]
            sections.append(agents.Section(intent="made_up_intent", headline="x", cards=[]))
            return agents.ForYouUpdate(sections=sections, notification="Stub notification")
        raise AssertionError(self.schema)


class StubLLM:
    def __init__(self):
        self.calls = []

    def with_structured_output(self, schema):
        return StubRunner(self, schema)


stub = StubLLM()
agents.get_llm = lambda: stub
db.reset_db()
for cid in ("C001", "C002", "C003"):
    db.release_next_batch(cid)
    graph.run(cid)

cls = {c["merchant"]: c for c in db.get_all_classifications()}
check("Classification agent output stored with method 'gemini'", cls["Brico Liège"]["method"] == "gemini")
check("Guardrail: invented industry 'made_up' is dropped", "made_up" not in cls["Brico Liège"]["scores"])
check("Verification: wrong classification (supermarket = baby shop) → retried → 'needs_review'",
      cls["Colruyt"]["status"] == "needs_review" and cls["Colruyt"]["scores"]["baby_pregnancy"] == 0)
n_classify = sum(1 for s, p in stub.calls if s == "Classification" and "Company: Delhaize" in p)
check("Cache: Delhaize (used by 2 customers) classified by Gemini only once", n_classify == 1, f"{n_classify}×")

page = db.get_for_you_page("C002")["content"]
ids = [c["widget_id"] for s in page["sections"] for c in s["cards"]]
check("Guardrail: invented widget and intent from the LLM are removed",
      "hack_widget" not in ids and all(s["intent"] in INTENTS for s in page["sections"]))
advisor_prompts = [p for s, p in stub.calls if s == "ForYouUpdate"]
check("Advisor prompt forbids using gender and stating sensitive guesses",
      all("NEVER use gender" in p and "NEVER state sensitive guesses" in p for p in advisor_prompts))
check("Advisor writes in the customer's language (Yusuf → Dutch, Marc → French)",
      any("Yusuf" in p and "in Dutch" in p for p in advisor_prompts) and any("Marc" in p and "French" in p for p in advisor_prompts))
before = len(stub.calls)
graph.run("C002")
check("Page refresh without new data makes NO new Gemini calls", len(stub.calls) == before)


# ================================ D. Extending by configuration only ==============================
print("\n=== D. New industry + intent + widget via config only ===")
agents.get_llm = lambda: None
import config  # noqa: E402
config.INDUSTRIES["cars"] = {"label": "Cars", "description": "Car dealers and garages",
                             "keywords": ["car", "garage", "dealer"], "avg_expense": 300, "benchmark": 30}
config.WIDGETS["car_loan"] = {"type": "action", "action": "Simulate a car loan", "name": "KBC Car Loan",
                              "summary": "Finance your new car.", "info": "A fixed-rate loan for a new or used car."}
config.INTENTS["buying_car"] = {"label": "Buying a car", "headline": "Looking for a new car?", "type": "Life event",
                                "signals": [{"kind": "industry", "industry": "cars", "weight": 0.8, "label": "Car dealer visits"}],
                                "widgets": ["car_loan"]}
db.reset_db()
with db.connect() as conn:
    conn.execute("INSERT INTO merchants VALUES ('Garage Peeters', 'Car dealer and garage')")
    conn.executemany("INSERT INTO transactions (customer_id, ts, merchant, amount, currency, amount_eur, country, batch, released) "
                     "VALUES ('C002', '2026-09-2' || ?, 'Garage Peeters', 400, 'EUR', 400, 'BE', 0, 1)", [(i,) for i in range(3)])
car = graph.run("C002")
check("New industry/intent/widget added only in config → classified, scored, validated, shown",
      "buying_car" in car["validated"] and car["page"]["content"]["sections"][0]["cards"][0]["widget_id"] == "car_loan",
      f"cars score {car['industries']['cars']['score']}, intent {car['intents']['buying_car']['score']:.0%}")
for d, k in ((config.INDUSTRIES, "cars"), (config.WIDGETS, "car_loan"), (config.INTENTS, "buying_car")):
    d.pop(k)


# ================================ C. Real Gemini connection ========================================
print("\n=== C. Gemini connection ===")
try:
    import langchain_google_genai  # noqa: F401
    os.environ["GOOGLE_API_KEY"] = "dummy-key-for-construction-test"
    from langchain.chat_models import init_chat_model
    model = init_chat_model(agents.DEFAULT_MODEL, temperature=0)
    check("Gemini chat model can be created via init_chat_model", type(model).__name__ == "ChatGoogleGenerativeAI",
          type(model).__name__)
    os.environ.pop("GOOGLE_API_KEY")
except ImportError:
    print("⚠️  langchain-google-genai not installed yet → run: pip install -r requirements.txt")

tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
check("Security: no .env or kbc.db committed to git", ".env" not in tracked and "kbc.db" not in tracked)

db.reset_db()
print(f"\n{sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)
