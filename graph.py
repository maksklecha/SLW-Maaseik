"""The Context Engine as a LangGraph pipeline (run once per customer, e.g. when new transactions arrive).

 START → load_data → classify_merchants → verify_classification → score_industries
                                                                        │
                                   below every benchmark ──► END (nothing to show = no spam)
                                   above a benchmark ↓
                                recommend → notify → END

- Node  = one step (a Python function that gets the state and returns what it changes).
- Edge  = the arrow to the next step. A *conditional* edge picks the next step with a function.
- State = the dictionary (EngineState) that travels through all nodes.
"""
from typing import TypedDict

import agents
import db
import scoring
import signals
from langgraph.graph import END, START, StateGraph


class EngineState(TypedDict, total=False):
    customer_id: str
    customer: dict
    transactions: list[dict]
    drafts: dict           # merchant -> classification before verification
    classifications: dict  # merchant -> verified classification
    breakdown: dict        # industry -> score details
    triggered: list[str]   # industries above their benchmark
    updates: list[dict]    # For You page content
    notifications: list[dict]


def load_data(state: EngineState) -> dict:
    return {"customer": db.get_customer(state["customer_id"]),
            "transactions": db.get_transactions(state["customer_id"])}


def classify_merchants(state: EngineState) -> dict:
    """Agent step. Only NEW merchants are classified; known ones come from the cache table."""
    llm = agents.get_llm()
    drafts = {}
    for t in state["transactions"]:
        m = t["merchant"]
        if m not in drafts and db.get_classification(m) is None:
            drafts[m] = {**agents.classify_merchant(m, t["description"], llm), "description": t["description"]}
    return {"drafts": drafts}


def verify_classification(state: EngineState) -> dict:
    llm = agents.get_llm()
    for m, draft in state["drafts"].items():
        final = agents.verify(m, draft["description"], draft, llm)
        db.save_classification(m, final["scores"], final["reason"], final["status"], final["method"])
    merchants = {t["merchant"] for t in state["transactions"]}
    return {"classifications": {m: db.get_classification(m) for m in merchants}}


def score_industries(state: EngineState) -> dict:
    breakdown = scoring.industry_breakdown(state["transactions"], state["classifications"])
    db.save_scores(state["customer_id"], {ind: b["score"] for ind, b in breakdown.items()})
    return {"breakdown": breakdown, "triggered": scoring.above_benchmark(breakdown)}


def route_after_scoring(state: EngineState) -> str:
    return "recommend" if state["triggered"] else END


def recommend(state: EngineState) -> dict:
    llm = agents.get_llm()
    updates = [{"industry": ind, **agents.recommend(state["customer"], ind, state["breakdown"][ind], llm)}
               for ind in state["triggered"]]
    db.replace_recommendations(state["customer_id"], updates)
    return {"updates": updates}


def notify(state: EngineState) -> dict:
    """One notification per newly triggered industry — never twice for the same thing."""
    c = state["customer"]
    sent = []
    for u in state["updates"]:
        if not db.already_notified(c["id"], u["industry"]):
            n = {"industry": u["industry"], "channel": signals.pick_channel(c),
                 "moment": signals.pick_moment(c), "text": u["notification"]}
            db.save_notification(c["id"], **n)
            sent.append(n)
    return {"notifications": sent}


def build_graph():
    g = StateGraph(EngineState)
    for name, fn in [("load_data", load_data), ("classify_merchants", classify_merchants),
                     ("verify_classification", verify_classification), ("score_industries", score_industries),
                     ("recommend", recommend), ("notify", notify)]:
        g.add_node(name, fn)
    g.add_edge(START, "load_data")
    g.add_edge("load_data", "classify_merchants")
    g.add_edge("classify_merchants", "verify_classification")
    g.add_edge("verify_classification", "score_industries")
    g.add_conditional_edges("score_industries", route_after_scoring, ["recommend", END])
    g.add_edge("recommend", "notify")
    g.add_edge("notify", END)
    return g.compile()


graph = build_graph()


def run(customer_id: str) -> EngineState:
    db.ensure_db()
    return graph.invoke({"customer_id": customer_id})
