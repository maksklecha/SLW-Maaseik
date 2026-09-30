"""Unit tests for the scoring logic. Run with:

    pytest

A unit test is a small function that checks that one piece of code gives the expected
answer. scoring.py is a plain formula (no LLM), so the answers are always the same.
"""
import pytest

import db
import graph
import scoring
from config import INDUSTRIES


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Use a temporary database and no LLM, so the tests never touch kbc.db or the internet."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(graph.agents, "get_llm", lambda: None)
    db.reset_db()


def test_formula_worked_example():
    # relevance 9/10, 4 visits, €240 in total, industry average €40 → 0.9 × 16 × 6
    assert scoring.score_merchant(9, 4, 240, 40) == pytest.approx(86.4)


def test_single_gift_purchase_stays_below_benchmark():
    # Emma's example: one childwear purchase of €35 as a gift
    score = scoring.score_merchant(9, 1, 35, INDUSTRIES["baby_pregnancy"]["avg_expense"])
    assert score == pytest.approx(0.79, abs=0.01)
    assert score < INDUSTRIES["baby_pregnancy"]["benchmark"]


def test_unrelated_merchant_adds_nothing():
    transactions = [{"merchant": "Colruyt", "amount_eur": 500}] * 10
    result = scoring.industry_breakdown(transactions, {"Colruyt": {"scores": {"baby_pregnancy": 0}}})
    assert result["baby_pregnancy"]["score"] == 0


def test_yusuf_before_below_and_after_above_benchmark(fresh_db):
    before = graph.run("C001")["industries"]["baby_pregnancy"]
    assert before["score"] == pytest.approx(1.24, abs=0.01)
    assert before["score"] < before["benchmark"]

    db.release_next_batch("C001")
    after = graph.run("C001")["industries"]["baby_pregnancy"]
    assert after["score"] == pytest.approx(88.4, abs=0.01)
    assert after["score"] >= after["benchmark"]


def test_intent_score_flight_plus_airport_is_95_percent():
    customer = {"children": 0, "monthly_income": 3000}
    industries = {k: {"score": 0, "benchmark": v["benchmark"]} for k, v in INDUSTRIES.items()}
    industries["travel"]["score"] = INDUSTRIES["travel"]["benchmark"]         # flight bookings at full strength
    contexts = [{"event": "airport_abroad", "detail": "Opened the app at a foreign airport"}]
    scores = scoring.intent_scores(customer, industries, [], [], contexts)
    assert scores["international_travel"]["score"] == pytest.approx(0.95)
    assert scores["international_travel"]["validated"]


def test_having_children_lowers_expecting_child_intent(fresh_db):
    db.release_next_batch("C001")
    s = graph.run("C001")
    no_kids = s["intents"]["expecting_child"]["score"]
    with_kids = scoring.intent_scores({**s["customer"], "children": 2}, s["industries"],
                                      s["transactions"], s["app_events"], s["contexts"])
    assert no_kids >= 0.70
    assert with_kids["expecting_child"]["score"] == pytest.approx(no_kids * 0.5, abs=0.001)  # scores are rounded to 3 decimals
    assert not with_kids["expecting_child"]["validated"]
