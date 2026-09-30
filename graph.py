"""The "brain" of the app: a LangGraph graph that builds a personal For You feed.

    START --> detect_signals --> match_offers --> write_messages --> END
              (rules)            (rules: service,   (LLM: personal text
                                  moment, channel)   in the customer's language)
"""
import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

import signals as sig

load_dotenv()

LANGUAGES = {"nl": "Dutch", "fr": "French", "en": "English"}


class FeedState(TypedDict, total=False):
    customer: dict
    today: object  # datetime.date
    signals: list[dict]
    offers: list[dict]
    feed: list[dict]


class Card(BaseModel):
    """What the LLM must return for one offer (structured output)."""
    title: str = Field(description="Short, catchy card title, max 6 words")
    message: str = Field(description="2 sentences, personal, friendly, no jargon")
    notification: str = Field(description="Push/email subject line, max 90 characters")


# --- Nodes ------------------------------------------------------------------
def detect_signals(state: FeedState) -> dict:
    return {"signals": sig.detect_signals(state["customer"], state["today"])}


def match_offers(state: FeedState) -> dict:
    return {"offers": sig.build_offers(state["customer"], state["signals"], state["today"])}


def _fallback_card(offer: dict) -> Card:
    """Used when there is no API key or the LLM call fails, so the demo never breaks."""
    return Card(title=offer["service"], message=offer["benefit"] + ".",
                notification=f"{offer['service']}: {offer['benefit']}"[:90])


def write_messages(state: FeedState) -> dict:
    c = state["customer"]
    feed = []
    llm = None
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"):
        llm = init_chat_model(os.getenv("MODEL", "anthropic:claude-sonnet-5-5")).with_structured_output(Card)

    for offer in state["offers"]:
        card = None
        if llm:
            prompt = (
                "You write personalised messages for the 'For You' page of KBC, a Belgian bank.\n"
                f"Write in {LANGUAGES.get(c['language'], 'English')}. Channel: {offer['channel']}.\n"
                "Adapt tone to the customer (age, occupation). Be helpful, not pushy. "
                "Do not invent numbers other than the ones given.\n\n"
                f"Customer: {c['name'].split()[0]}, {c['age']} years old, {c['occupation']}, lives in {c['city']}.\n"
                f"What we noticed: {offer['signal']['evidence']}.\n"
                f"KBC service to suggest: {offer['service']} — {offer['benefit']}.\n"
                + (f"Estimated saving/value: €{offer['signal']['value_eur']}.\n" if offer["signal"].get("value_eur") else "")
            )
            try:
                card = llm.invoke(prompt)
            except Exception as e:  # network down, bad key, ... -> keep the demo alive
                print(f"LLM failed, using fallback text: {e}")
        feed.append({**offer, **(card or _fallback_card(offer)).model_dump()})
    return {"feed": feed}


# --- Graph ------------------------------------------------------------------
def build_graph():
    builder = StateGraph(FeedState)
    builder.add_node("detect_signals", detect_signals)
    builder.add_node("match_offers", match_offers)
    builder.add_node("write_messages", write_messages)
    builder.add_edge(START, "detect_signals")
    builder.add_edge("detect_signals", "match_offers")
    builder.add_edge("match_offers", "write_messages")
    builder.add_edge("write_messages", END)
    return builder.compile()


graph = build_graph()
