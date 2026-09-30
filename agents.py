"""The LLM parts of the Context Engine (Google Gemini via LangChain).

1. classify_merchant()  - agent: which industries is this company in? (0-10 each)
2. verify()             - verification step: rule check + independent Gemini "judge"
3. recommend()          - writes the For You update (services + more info + notification)

Every function has a no-LLM fallback, so the demo works without an API key
or when the Wi-Fi drops. The UI shows which method was used.
"""
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from config import INDUSTRIES, MAX_RELEVANCE, MAX_SERVICES_PER_UPDATE

load_dotenv()

LANGUAGES = {"nl": "Dutch", "fr": "French", "en": "English"}


def get_llm():
    """Returns the chat model, or None when no API key is configured."""
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        return None
    from langchain.chat_models import init_chat_model  # imported here so the app runs without it
    return init_chat_model(os.getenv("MODEL", "google_genai:gemini-2.5-flash"), temperature=0)


# --- Output schemas (structured output = the LLM must fill in exactly these fields) ------
class IndustryRelevance(BaseModel):
    industry: str = Field(description="One of the given industry keys")
    relevance: int = Field(ge=0, le=MAX_RELEVANCE, description="0 = unrelated, 10 = core business")


class Classification(BaseModel):
    scores: list[IndustryRelevance]
    reason: str = Field(description="One short sentence explaining the scores")


class Verdict(BaseModel):
    plausible: bool = Field(description="Is the classification correct?")
    corrected: list[IndustryRelevance] = Field(description="Your own scores for every industry")
    comment: str


class ServiceCard(BaseModel):
    service_id: str = Field(description="Exactly one of the given service ids")
    title: str = Field(description="Short title, max 6 words")
    message: str = Field(description="1-2 friendly, personal sentences")
    more_info: str = Field(description="3-4 sentences explaining the service and why it may help")


class ForYouUpdate(BaseModel):
    cards: list[ServiceCard]
    notification: str = Field(description="Max 90 characters: tells the customer their For You page has an update")


def _industry_list() -> str:
    return "\n".join(f"- {key}: {cfg['description']}" for key, cfg in INDUSTRIES.items())


def _to_dict(scores: list[IndustryRelevance]) -> dict[str, int]:
    """Keep only known industries (the LLM could invent one) and clamp to 0..10."""
    out = {key: 0 for key in INDUSTRIES}
    for s in scores:
        if s.industry in out:
            out[s.industry] = max(0, min(MAX_RELEVANCE, s.relevance))
    return out


def _top(scores: dict[str, int]) -> str | None:
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


# --- 1. Classification agent -------------------------------------------------
def keyword_classify(merchant: str, description: str) -> dict[str, int]:
    """Fallback + rule check: count how many industry keywords appear in the name/description."""
    text = f"{merchant} {description}".lower()
    scores = {}
    for key, cfg in INDUSTRIES.items():
        hits = sum(1 for kw in cfg["keywords"] if kw in text)
        scores[key] = min(MAX_RELEVANCE, 3 + 3 * hits) if hits else 0
    return scores


def classify_merchant(merchant: str, description: str, llm=None) -> dict:
    if llm:
        try:
            result = llm.with_structured_output(Classification).invoke(
                "You classify companies for a bank. For EACH industry below, rate from 0 to 10 how much "
                "this company belongs to it (0 = not at all, 10 = its core business).\n"
                f"Industries:\n{_industry_list()}\n\n"
                f"Company: {merchant}\nDescription: {description}"
            )
            return {"scores": _to_dict(result.scores), "reason": result.reason, "method": "gemini"}
        except Exception as e:
            print(f"[classify] LLM failed for {merchant}, using keywords: {e}")
    return {"scores": keyword_classify(merchant, description),
            "reason": "Keyword match on name and description", "method": "keyword fallback"}


# --- 2. Verification step -------------------------------------------------------
def verify(merchant: str, description: str, draft: dict, llm=None) -> dict:
    """Two independent checks. Returns the final classification with a status."""
    rule_scores = keyword_classify(merchant, description)
    rule_ok = _top(rule_scores) == _top(draft["scores"]) or _top(rule_scores) is None

    if draft["method"] != "gemini" or not llm:
        # Keywords were used for the draft itself -> the rule check is all we have
        return {**draft, "status": "verified" if rule_ok else "needs_review"}

    try:
        verdict = llm.with_structured_output(Verdict).invoke(
            "You are a strict reviewer at a bank. Check this industry classification of a company.\n"
            f"Industries:\n{_industry_list()}\n\n"
            f"Company: {merchant}\nDescription: {description}\n"
            f"Proposed scores (0-10): {draft['scores']}\n"
            "Is it plausible? Also give your own scores for every industry."
        )
        judge_scores = _to_dict(verdict.corrected)
        judge_ok = verdict.plausible and _top(judge_scores) == _top(draft["scores"])
    except Exception as e:
        print(f"[verify] judge failed for {merchant}: {e}")
        judge_scores, judge_ok = draft["scores"], True

    if rule_ok and judge_ok:
        return {**draft, "status": "verified"}

    # Disagreement: classify once more, then check again
    retry = classify_merchant(merchant, description, llm)
    if _top(retry["scores"]) == _top(judge_scores) and (_top(rule_scores) in (None, _top(retry["scores"]))):
        return {**retry, "status": "verified", "reason": retry["reason"] + " (verified after retry)"}

    # Still no agreement: keep the most conservative (lowest) score per industry and flag it
    conservative = {k: min(draft["scores"][k], judge_scores[k], retry["scores"][k]) for k in INDUSTRIES}
    return {"scores": conservative, "reason": "Classifier and reviewer disagree - needs human review",
            "method": "gemini", "status": "needs_review"}


# --- 3. Recommender --------------------------------------------------------------
def _fallback_update(customer: dict, industry: str) -> dict:
    cfg = INDUSTRIES[industry]
    cards = [{"service_id": s["id"], "title": s["name"], "message": s["summary"], "more_info": s["info"]}
             for s in cfg["services"][:MAX_SERVICES_PER_UPDATE]]
    return {"cards": cards, "notification": f"New on your For You page: tips about {cfg['label'].lower()}",
            "method": "template fallback"}


def recommend(customer: dict, industry: str, breakdown: dict, llm=None) -> dict:
    cfg = INDUSTRIES[industry]
    if llm:
        services = "\n".join(f"- id={s['id']}: {s['name']} — {s['info']}" for s in cfg["services"])
        merchants = ", ".join(f"{m['merchant']} ({m['visits']} visits, €{m['spent']})" for m in breakdown["merchants"])
        try:
            result = llm.with_structured_output(ForYouUpdate).invoke(
                "You write the 'For You' page of the KBC banking app: short, essential, helpful info — "
                "not advertising, not pushy.\n"
                f"Write in {LANGUAGES.get(customer['language'], 'English')}.\n"
                f"Choose 1 to {MAX_SERVICES_PER_UPDATE} of the KBC services below that fit this customer best, "
                "most relevant first. Only use the given service ids.\n"
                "Rules: base the choice on the industry, age, occupation, number of children and spending. "
                "NEVER use gender to choose products. NEVER state sensitive guesses directly "
                "(e.g. do not say 'congratulations on your baby'; say 'planning for your family?'). "
                "Do not invent prices or numbers.\n\n"
                f"Customer: {customer['name'].split()[0]}, {customer['age']} years, {customer['occupation']}, "
                f"{customer['children']} children, lives in {customer['city']}.\n"
                f"Detected industry: {cfg['label']} (score {breakdown['score']}, benchmark {breakdown['benchmark']}).\n"
                f"Recent spending there: {merchants}.\n\n"
                f"Available KBC services:\n{services}"
            )
            valid_ids = {s["id"] for s in cfg["services"]}
            cards = [c.model_dump() for c in result.cards if c.service_id in valid_ids][:MAX_SERVICES_PER_UPDATE]
            if cards:
                return {"cards": cards, "notification": result.notification[:120], "method": "gemini"}
        except Exception as e:
            print(f"[recommend] LLM failed, using template: {e}")
    return _fallback_update(customer, industry)
