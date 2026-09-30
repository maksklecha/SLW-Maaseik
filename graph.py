"""The Context Engine as a LangGraph pipeline: Understand → Recognize → Adapt → (notify).

 START → load_data → classify_merchants → verify_classification → score_industries → score_intents
         UNDERSTAND   (classification agent)  (verification agent)   (team formula)     RECOGNIZE
                                                                                           │
                                   no intent above threshold ──► clear page → END (no spam)
                                   intent(s) validated ↓
                          advisor (For You page, ADAPT) → notify (right channel + moment) → END

- Node  = one step: a Python function that receives the state and returns what it changes.
- Edge  = the arrow to the next step. A *conditional* edge picks the next step with a function.
- State = the dictionary (EngineState) that travels through all nodes.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

import agents
import db
import scoring
import signals


class EngineState(TypedDict, total=False):
    customer_id: str
    customer: dict
    transactions: list[dict]
    app_events: list[dict]
    contexts: list[dict]
    drafts: dict            # merchant -> classification before verification
    classifications: dict   # merchant -> verified classification
    industries: dict        # industry -> score details
    intents: dict           # intent -> score + evidence
    validated: list[str]    # intents above the threshold
    page: dict              # For You page content
    notification: dict | None


# --- UNDERSTAND ---------------------------------------------------------------------------
def load_data(state: EngineState) -> dict:
    cid = state["customer_id"]
    return {"customer": db.get_customer(cid), "transactions": db.get_transactions(cid),
            "app_events": db.get_app_events(cid), "contexts": db.get_context_events(cid)}


def classify_merchants(state: EngineState) -> dict:
    """Classification agent. Only NEW merchants; known ones come from the cache table."""
    llm = agents.get_llm()
    drafts = {}
    for t in state["transactions"]:
        m = t["merchant"]
        if m not in drafts and db.get_classification(m) is None:
            drafts[m] = {**agents.classify_merchant(m, t["description"], llm), "description": t["description"]}
    return {"drafts": drafts}


def verify_classification(state: EngineState) -> dict:
    """Verification agent + rule check, then store in the cache."""
    llm = agents.get_llm()
    for m, draft in state["drafts"].items():
        final = agents.verify(m, draft["description"], draft, llm)
        db.save_classification(m, final["scores"], final["reason"], final["status"], final["method"])
    return {"classifications": {t["merchant"]: db.get_classification(t["merchant"]) for t in state["transactions"]}}


def score_industries(state: EngineState) -> dict:
    return {"industries": scoring.industry_breakdown(state["transactions"], state["classifications"])}


# --- RECOGNIZE ---------------------------------------------------------------------------
def score_intents(state: EngineState) -> dict:
    intents = scoring.intent_scores(state["customer"], state["industries"], state["transactions"],
                                    state["app_events"], state["contexts"])
    db.save_intent_scores(state["customer_id"], {k: v["score"] for k, v in intents.items()},
                          db.data_version(state["customer_id"]))
    return {"intents": intents, "validated": scoring.validated_intents(intents)}


def route_after_intents(state: EngineState) -> str:
    return "advisor" if state["validated"] else "no_update"


def no_update(state: EngineState) -> dict:
    db.clear_for_you_page(state["customer_id"])
    return {"page": None, "notification": None}


# --- ADAPT --------------------------------------------------------------------------------
def advisor(state: EngineState) -> dict:
    """Advisor agent builds the For You page. Only calls Gemini when the situation changed."""
    signature = ",".join(state["validated"])
    existing = db.get_for_you_page(state["customer_id"])
    if existing and existing["signature"] == signature:
        return {"page": existing}
    page = agents.build_for_you_page(state["customer"], state["validated"], state["intents"],
                                     state["industries"], agents.get_llm())
    db.save_for_you_page(state["customer_id"], signature, page)
    return {"page": {"signature": signature, "content": page}}


def notify(state: EngineState) -> dict:
    """One notification for NEW intents only (never twice for the same thing), right channel + moment."""
    c = state["customer"]
    new = [i for i in state["validated"] if i not in db.notified_intents(c["id"])]
    if not new:
        return {"notification": None}
    page = state["page"]["content"]
    n = {"intents": new, "channel": signals.pick_channel(c),
         "moment": signals.pick_moment(c, state["contexts"], new), "text": page["notification"]}
    db.save_notification(c["id"], **n)
    return {"notification": n}


def build_graph():
    g = StateGraph(EngineState)
    for name, fn in [("load_data", load_data), ("classify_merchants", classify_merchants),
                     ("verify_classification", verify_classification), ("score_industries", score_industries),
                     ("score_intents", score_intents), ("no_update", no_update),
                     ("advisor", advisor), ("notify", notify)]:
        g.add_node(name, fn)
    g.add_edge(START, "load_data")
    g.add_edge("load_data", "classify_merchants")
    g.add_edge("classify_merchants", "verify_classification")
    g.add_edge("verify_classification", "score_industries")
    g.add_edge("score_industries", "score_intents")
    g.add_conditional_edges("score_intents", route_after_intents, ["advisor", "no_update"])
    g.add_edge("no_update", END)
    g.add_edge("advisor", "notify")
    g.add_edge("notify", END)
    return g.compile()


graph = build_graph()


def run(customer_id: str) -> EngineState:
    db.ensure_db()
    return graph.invoke({"customer_id": customer_id})
