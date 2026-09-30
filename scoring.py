"""The two scoring formulas of the Context Engine. Pure maths, no LLM -> cheap for 2.3M customers.

1) Industry score (the team's formula), per customer and industry:
       merchant_score = (relevance / 10) × visits² × (total_spent / avg_expense_of_industry)
       industry_score = sum of merchant_score over the merchants the customer paid

2) Intent Score, per intent (life event / micro-moment), fusing all signal types:
       intent = 1 - Π (1 - weight × strength)          ("noisy-OR")
   Each signal can only ADD evidence; two strong signals together give a very high score.
   Example: flight bookings (0.8) + app opened at a foreign airport (0.75) → 1 - 0.2 × 0.25 = 95%.
"""
from collections import Counter, defaultdict

from config import INDUSTRIES, INTENT_THRESHOLD, INTENTS, MAX_RELEVANCE


# --- 1. Industry score -------------------------------------------------------------------
def score_merchant(relevance: int, visits: int, total_spent: float, avg_expense: float) -> float:
    return (relevance / MAX_RELEVANCE) * visits ** 2 * (total_spent / avg_expense)


def industry_breakdown(transactions: list[dict], classifications: dict[str, dict]) -> dict[str, dict]:
    per_merchant = defaultdict(lambda: {"visits": 0, "spent": 0.0})
    for t in transactions:
        per_merchant[t["merchant"]]["visits"] += 1
        per_merchant[t["merchant"]]["spent"] += t["amount_eur"]

    result = {}
    for ind, cfg in INDUSTRIES.items():
        parts = []
        for merchant, agg in per_merchant.items():
            relevance = (classifications.get(merchant) or {}).get("scores", {}).get(ind, 0)
            if relevance:
                parts.append({"merchant": merchant, "relevance": relevance, "visits": agg["visits"],
                              "spent": round(agg["spent"], 2),
                              "score": round(score_merchant(relevance, agg["visits"], agg["spent"],
                                                            cfg["avg_expense"]), 2)})
        parts.sort(key=lambda p: -p["score"])
        result[ind] = {"score": round(sum(p["score"] for p in parts), 2),
                       "benchmark": cfg["benchmark"], "merchants": parts}
    return result


# --- 2. Intent score -----------------------------------------------------------------------
def _signal_strength(sig: dict, customer: dict, industries: dict, transactions: list[dict],
                     app_counts: Counter, contexts: list[dict]) -> tuple[float, str]:
    """Returns (strength 0..1, human-readable evidence)."""
    kind = sig["kind"]
    if kind == "industry":
        b = industries[sig["industry"]]
        return min(1.0, b["score"] / b["benchmark"]), f"industry score {b['score']} / benchmark {b['benchmark']}"
    if kind == "foreign_currency":
        foreign = [t for t in transactions if t["currency"] != "EUR"]
        cur = ", ".join(sorted({t["currency"] for t in foreign}))
        return min(1.0, len(foreign) / 3), f"{len(foreign)} payments in {cur}" if foreign else "none"
    if kind == "spending_ratio":
        spent = sum(t["amount_eur"] for t in transactions)
        ratio = spent / customer["monthly_income"]
        return max(0.0, min(1.0, (ratio - 0.5) / 0.5)), f"spent €{spent:.0f} = {ratio:.0%} of monthly income"
    if kind == "app_event":
        n = app_counts[sig["event"]]
        return min(1.0, n / sig["min_count"]), f"seen {n}×"
    if kind == "context":
        hits = [c for c in contexts if c["event"] == sig["event"]]
        return (1.0, hits[-1]["detail"]) if hits else (0.0, "not observed")
    raise ValueError(f"Unknown signal kind: {kind}")


def intent_scores(customer: dict, industries: dict, transactions: list[dict],
                  app_events: list[dict], contexts: list[dict]) -> dict[str, dict]:
    app_counts = Counter(e["event"] for e in app_events)
    result = {}
    for key, cfg in INTENTS.items():
        remaining, evidence = 1.0, []
        for sig in cfg["signals"]:
            strength, detail = _signal_strength(sig, customer, industries, transactions, app_counts, contexts)
            remaining *= 1 - sig["weight"] * strength
            evidence.append({"signal": sig["label"], "kind": sig["kind"], "weight": sig["weight"],
                             "strength": round(strength, 2), "detail": detail})
        score = 1 - remaining
        mult = cfg.get("profile_multiplier")
        if mult and customer[mult["field"]] != mult["equals"]:
            score *= mult["otherwise"]
            evidence.append({"signal": f"Profile: {mult['field']} = {customer[mult['field']]}", "kind": "profile",
                             "weight": mult["otherwise"], "strength": 1.0, "detail": f"score × {mult['otherwise']}"})
        result[key] = {"score": round(score, 3), "validated": score >= INTENT_THRESHOLD, "evidence": evidence}
    return result


def validated_intents(scores: dict[str, dict]) -> list[str]:
    """Intents above the threshold, strongest first."""
    return sorted([k for k, v in scores.items() if v["validated"]], key=lambda k: -scores[k]["score"])
