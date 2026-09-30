"""The AI agents of the Context Engine (Google Gemini via LangChain).

  1. Classification agent  - which industries is this company in? (0-10 per industry)
  2. Verification agent    - independent reviewer + rule check of that classification
  3. Advisor agent         - builds the For You page: picks widgets, writes texts + notification

Each agent uses "structured output": we give Gemini a Pydantic class and it MUST answer with
exactly those fields, so our code gets clean data instead of free text.
Each agent also has a no-LLM fallback, so the app keeps working without a key or without Wi-Fi.
"""
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from config import INDUSTRIES, INTENTS, MAX_RELEVANCE, MAX_WIDGETS_PER_INTENT, WIDGETS

load_dotenv()

DEFAULT_MODEL = "google_genai:gemini-2.5-flash"
LANGUAGES = {"nl": "Dutch", "fr": "French", "en": "English"}


# --- Connecting to Gemini ------------------------------------------------------------------
def get_api_key() -> str | None:
    """Key from .env (local) or from Streamlit secrets (when the app is deployed online)."""
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            key = None
    if key:
        os.environ["GOOGLE_API_KEY"] = key  # langchain-google-genai reads it from here
    return key


def get_llm():
    """The Gemini chat model, or None when no key is configured (→ fallbacks are used)."""
    if not get_api_key():
        return None
    from langchain.chat_models import init_chat_model
    return init_chat_model(os.getenv("MODEL", DEFAULT_MODEL), temperature=0)


# --- Output schemas ----------------------------------------------------------------------------
class IndustryRelevance(BaseModel):
    industry: str = Field(description="One of the given industry keys")
    relevance: int = Field(description=f"0 = unrelated, {MAX_RELEVANCE} = core business")


class Classification(BaseModel):
    scores: list[IndustryRelevance]
    reason: str = Field(description="One short sentence explaining the scores")


class Verdict(BaseModel):
    plausible: bool = Field(description="Is the proposed classification correct?")
    corrected: list[IndustryRelevance] = Field(description="Your own score for every industry")
    comment: str


class Card(BaseModel):
    widget_id: str = Field(description="Exactly one of the given widget ids")
    title: str = Field(description="Short title, max 6 words")
    message: str = Field(description="1-2 friendly, personal sentences")
    more_info: str = Field(description="3-4 sentences explaining the service and why it can help now")


class Section(BaseModel):
    intent: str = Field(description="Exactly one of the given intent keys")
    headline: str = Field(description="Short, warm section headline")
    cards: list[Card]


class ForYouUpdate(BaseModel):
    sections: list[Section]
    notification: str = Field(description="Max 90 characters: tells the customer their For You page has an update")


def _industry_list() -> str:
    return "\n".join(f"- {k}: {c['description']}" for k, c in INDUSTRIES.items())


def _to_dict(scores: list[IndustryRelevance]) -> dict[str, int]:
    """Guardrail on LLM output: only known industries, values clamped to 0..10."""
    out = {k: 0 for k in INDUSTRIES}
    for s in scores:
        if s.industry in out:
            out[s.industry] = max(0, min(MAX_RELEVANCE, int(s.relevance)))
    return out


def _top(scores: dict[str, int]) -> str | None:
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


# --- 1. Classification agent ----------------------------------------------------------------
def keyword_classify(merchant: str, description: str) -> dict[str, int]:
    """Fallback AND rule check: count industry keywords in the name/description."""
    text = f"{merchant} {description}".lower()
    out = {}
    for key, cfg in INDUSTRIES.items():
        hits = sum(1 for kw in cfg["keywords"] if kw in text)
        out[key] = min(MAX_RELEVANCE, 3 + 3 * hits) if hits else 0
    return out


def classify_merchant(merchant: str, description: str, llm=None) -> dict:
    if llm:
        try:
            r = llm.with_structured_output(Classification).invoke(
                "You classify companies for a bank. For EACH industry below, rate from 0 to "
                f"{MAX_RELEVANCE} how much this company belongs to it (0 = not at all, "
                f"{MAX_RELEVANCE} = its core business).\n"
                f"Industries:\n{_industry_list()}\n\nCompany: {merchant}\nDescription: {description}")
            return {"scores": _to_dict(r.scores), "reason": r.reason, "method": "gemini"}
        except Exception as e:
            print(f"[classify] Gemini failed for {merchant}, using keywords: {e}")
    return {"scores": keyword_classify(merchant, description),
            "reason": "Keyword match on name and description", "method": "keyword fallback"}


# --- 2. Verification agent ------------------------------------------------------------------
def verify(merchant: str, description: str, draft: dict, llm=None) -> dict:
    """Rule check + independent Gemini reviewer. Retry once on disagreement, else flag for a human."""
    rule_scores = keyword_classify(merchant, description)
    rule_ok = _top(rule_scores) in (None, _top(draft["scores"]))

    if draft["method"] != "gemini" or not llm:
        return {**draft, "status": "verified" if rule_ok else "needs_review"}

    try:
        v = llm.with_structured_output(Verdict).invoke(
            "You are a strict reviewer at a bank. Check this industry classification of a company.\n"
            f"Industries:\n{_industry_list()}\n\nCompany: {merchant}\nDescription: {description}\n"
            f"Proposed scores (0-{MAX_RELEVANCE}): {draft['scores']}\n"
            "Is it plausible? Also give your own score for every industry.")
        judge = _to_dict(v.corrected)
        judge_ok = v.plausible and _top(judge) == _top(draft["scores"])
    except Exception as e:
        print(f"[verify] reviewer failed for {merchant}: {e}")
        judge, judge_ok = draft["scores"], True

    if rule_ok and judge_ok:
        return {**draft, "status": "verified"}

    retry = classify_merchant(merchant, description, llm)
    if _top(retry["scores"]) == _top(judge) and _top(rule_scores) in (None, _top(retry["scores"])):
        return {**retry, "status": "verified", "reason": retry["reason"] + " (verified after retry)"}

    conservative = {k: min(draft["scores"][k], judge[k], retry["scores"][k]) for k in INDUSTRIES}
    return {"scores": conservative, "method": "gemini", "status": "needs_review",
            "reason": "Classifier and reviewer disagree - lowest scores kept, needs human review"}


# --- 3. Advisor agent (For You page) -------------------------------------------------------
def fallback_page(intents: list[str]) -> dict:
    sections = [{"intent": i, "headline": INTENTS[i]["headline"],
                 "cards": [{"widget_id": w, "title": WIDGETS[w]["name"], "message": WIDGETS[w]["summary"],
                            "more_info": WIDGETS[w]["info"]} for w in INTENTS[i]["widgets"][:MAX_WIDGETS_PER_INTENT]]}
                for i in intents]
    return {"sections": sections,
            "notification": f"Your For You page has an update — {INTENTS[intents[0]]['headline']}"[:120],
            "method": "template fallback"}


def build_for_you_page(customer: dict, intents: list[str], scores: dict, industries: dict, llm=None) -> dict:
    if not llm:
        return fallback_page(intents)

    blocks = []
    for i in intents:
        ev = "; ".join(f"{e['signal']} ({e['detail']})" for e in scores[i]["evidence"] if e["strength"] > 0)
        widgets = "\n".join(f"    - {w}: {WIDGETS[w]['name']} — {WIDGETS[w]['info']}" for w in INTENTS[i]["widgets"])
        blocks.append(f"* intent={i} ({INTENTS[i]['label']}, {INTENTS[i]['type']}, score {scores[i]['score']:.0%})\n"
                      f"  customer-facing headline style: '{INTENTS[i]['headline']}' (the internal label is NOT shown)\n"
                      f"  evidence: {ev}\n  available widgets:\n{widgets}")
    top_industry = max(industries, key=lambda k: industries[k]["score"])
    try:
        r = llm.with_structured_output(ForYouUpdate).invoke(
            "You are the advisor agent of the KBC banking app. You build the customer's 'For You' page: "
            "essential, helpful information only — no advertising tone, not pushy.\n"
            f"Write everything in {LANGUAGES.get(customer['language'], 'English')}.\n"
            f"For EACH intent below make one section and choose 1 to {MAX_WIDGETS_PER_INTENT} of its widgets, "
            "most useful first. Only use the given intent keys and widget ids.\n"
            "Rules:\n"
            "- Personalise with age, occupation, number of children and what they spend money on "
            f"(their strongest industry is '{INDUSTRIES[top_industry]['label']}').\n"
            "- NEVER use gender to choose products or tone.\n"
            "- NEVER state sensitive guesses directly (say 'planning for your family?', "
            "never 'congratulations on your pregnancy').\n"
            "- Do not invent prices, rates or numbers.\n\n"
            f"Customer: {customer['name'].split()[0]}, {customer['age']} years, {customer['occupation']}, "
            f"{customer['children']} children, lives in {customer['city']}.\n\n"
            "Validated intents:\n" + "\n".join(blocks))
    except Exception as e:
        print(f"[advisor] Gemini failed, using templates: {e}")
        return fallback_page(intents)

    # Guardrail on LLM output: keep only known intents/widgets that belong to that intent
    sections = []
    for s in r.sections:
        if s.intent in intents and s.intent not in [x["intent"] for x in sections]:
            cards = [c.model_dump() for c in s.cards if c.widget_id in INTENTS[s.intent]["widgets"]]
            if cards:
                sections.append({"intent": s.intent, "headline": s.headline, "cards": cards[:MAX_WIDGETS_PER_INTENT]})
    missing = [i for i in intents if i not in [s["intent"] for s in sections]]
    sections += fallback_page(missing)["sections"] if missing else []
    return {"sections": sections, "notification": r.notification[:120], "method": "gemini"}
