"""The Intent Score formula (the team's definition). Pure maths, no LLM -> cheap for 2.3M customers.

    merchant_score = (relevance / 10) × visits² × (total_spent / avg_expense_of_industry)
    industry_score = sum of merchant_score over all merchants the customer paid

Change the formula here, in score_merchant(), and the whole app follows.
"""
from collections import defaultdict

from config import INDUSTRIES, MAX_RELEVANCE


def score_merchant(relevance: int, visits: int, total_spent: float, avg_expense: float) -> float:
    return (relevance / MAX_RELEVANCE) * visits ** 2 * (total_spent / avg_expense)


def industry_breakdown(transactions: list[dict], classifications: dict[str, dict]) -> dict[str, dict]:
    """Returns per industry: total score + the numbers behind it (for "Why am I seeing this?")."""
    # 1. Group the transactions per merchant: how often and how much?
    per_merchant = defaultdict(lambda: {"visits": 0, "spent": 0.0})
    for t in transactions:
        per_merchant[t["merchant"]]["visits"] += 1
        per_merchant[t["merchant"]]["spent"] += t["amount_eur"]

    # 2. Apply the formula for every (industry, merchant) pair
    result = {}
    for ind, cfg in INDUSTRIES.items():
        parts = []
        for merchant, agg in per_merchant.items():
            relevance = classifications.get(merchant, {}).get("scores", {}).get(ind, 0)
            if relevance == 0:
                continue
            parts.append({
                "merchant": merchant,
                "relevance": relevance,
                "visits": agg["visits"],
                "spent": round(agg["spent"], 2),
                "score": round(score_merchant(relevance, agg["visits"], agg["spent"], cfg["avg_expense"]), 2),
            })
        parts.sort(key=lambda p: -p["score"])
        result[ind] = {"score": round(sum(p["score"] for p in parts), 2),
                       "benchmark": cfg["benchmark"], "merchants": parts}
    return result


def above_benchmark(breakdown: dict[str, dict]) -> list[str]:
    """Industries that crossed their benchmark, strongest first (score relative to its benchmark)."""
    hits = [ind for ind, b in breakdown.items() if b["score"] >= b["benchmark"]]
    return sorted(hits, key=lambda ind: -breakdown[ind]["score"] / breakdown[ind]["benchmark"])
