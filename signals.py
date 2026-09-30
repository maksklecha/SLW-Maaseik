"""Rule-based part of the pipeline: signals, offers, moment and channel.

Why rules and not the LLM here?  Rules are fast, free, predictable and easy
to explain to a bank, so they can run on all 2.3M customers every night.
The LLM is only used at the very end, to write the personal message.
"""
import json
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "customers.json"

# Assumed fee on card payments in a foreign currency (illustrative, not KBC's real tariff).
FX_FEE_RATE = 0.0175


def load_customers() -> tuple[date, list[dict]]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return date.fromisoformat(data["as_of"]), data["customers"]


# ---------------------------------------------------------------------------
# 1. SIGNALS: what is going on in this customer's life?
# ---------------------------------------------------------------------------
def detect_signals(customer: dict, today: date) -> list[dict]:
    txs = customer["transactions"]
    signals = []

    foreign = [t for t in txs if t["currency"] != "EUR"]
    if foreign:
        total = sum(t["amount_eur"] for t in foreign)
        currencies = sorted({t["currency"] for t in foreign})
        signals.append({
            "type": "foreign_currency_spending",
            "evidence": f"{len(foreign)} payments in {', '.join(currencies)} (≈ €{total:.0f})",
            "value_eur": round(total * FX_FEE_RATE, 2),
            "urgent": customer["location_now"] != "BE",  # they are abroad right now
        })

    for t in txs:
        if t.get("trip_start"):
            days = (date.fromisoformat(t["trip_start"]) - today).days
            if 0 < days <= 60:
                signals.append({
                    "type": "upcoming_trip",
                    "evidence": f"Flight booked with {t['merchant']} to {t['destination']}, leaving in {days} days",
                    "trip_start": t["trip_start"],
                    "urgent": False,
                })

    buffer = customer["balance_eur"] - 3 * customer["monthly_expenses_eur"]
    if buffer > 10_000:
        signals.append({
            "type": "idle_cash",
            "evidence": f"€{buffer:,.0f} more than 3 months of expenses on the current account",
            "urgent": False,
        })

    baby = [t for t in txs if t["category"] == "baby"]
    if len(baby) >= 2:
        signals.append({
            "type": "new_baby",
            "evidence": f"{len(baby)} purchases at baby stores ({', '.join(t['merchant'] for t in baby)})",
            "urgent": False,
        })

    if any(t.get("first_time") and t["category"] == "salary" for t in txs):
        signals.append({"type": "first_salary", "evidence": "First salary payment received", "urgent": False})

    subs = [t for t in txs if t["category"] == "subscription"]
    if len(subs) >= 4:
        monthly = sum(t["amount_eur"] for t in subs)
        signals.append({
            "type": "subscription_stack",
            "evidence": f"{len(subs)} subscriptions costing €{monthly:.2f}/month",
            "value_eur": round(monthly, 2),
            "urgent": False,
        })

    return signals


# ---------------------------------------------------------------------------
# 2. OFFERS: which KBC service helps with each signal? (illustrative catalogue)
# ---------------------------------------------------------------------------
CATALOG = {
    "foreign_currency_spending": {
        "service": "KBC Travel & FX advice",
        "benefit": "Cut foreign-currency card fees and always choose to pay in the local currency on card terminals",
        "category": "Save money",
    },
    "upcoming_trip": {
        "service": "KBC Travel Insurance",
        "benefit": "Cover medical costs, cancellation and lost luggage before you leave",
        "category": "Be protected",
    },
    "idle_cash": {
        "service": "Financial advisory appointment",
        "benefit": "Put money you don't need day-to-day to work in savings or investments",
        "category": "Grow your money",
    },
    "new_baby": {
        "service": "Family pack: child savings account + family insurance",
        "benefit": "Start saving for your child and check your family is covered",
        "category": "Life moment",
    },
    "first_salary": {
        "service": "Automatic savings plan",
        "benefit": "Put aside a small fixed amount every payday without thinking about it",
        "category": "Grow your money",
    },
    "subscription_stack": {
        "service": "Subscription overview in KBC Mobile",
        "benefit": "See all subscriptions in one place and cancel the ones you don't use",
        "category": "Save money",
    },
}


# ---------------------------------------------------------------------------
# 3. RIGHT MOMENT + RIGHT CHANNEL, based on the customer's profile
# ---------------------------------------------------------------------------
def pick_channel(customer: dict, signal: dict) -> str:
    if signal["urgent"] and customer["preferred_channel"] == "app":
        return "Push notification"
    if customer["age"] >= 65:
        # Older customers: email, plus a personal advisor for bigger decisions
        return "Advisor call" if signal["type"] == "idle_cash" else "Email"
    return {"app": "In-app For You card", "email": "Email"}[customer["preferred_channel"]]


def pick_moment(customer: dict, signal: dict, today: date) -> str:
    start, end = customer["active_hours"]
    window = f"{start:02d}:00–{end:02d}:00"
    if signal["urgent"]:
        return f"Today, {window} local time (while abroad, when they usually check their phone)"
    if signal["type"] == "upcoming_trip":
        send = date.fromisoformat(signal["trip_start"]) - timedelta(days=14)
        send = max(send, today + timedelta(days=1))
        return f"{send:%a %d %b}, {window} (2 weeks before departure)"
    if signal["type"] in ("first_salary", "idle_cash"):
        return f"Right after the next income arrives, {window}"
    return f"Tomorrow, {window} (their usual active hours)"


def build_offers(customer: dict, signals: list[dict], today: date) -> list[dict]:
    offers = []
    for s in signals:
        offer = {
            **CATALOG[s["type"]],
            "signal": s,
            "channel": pick_channel(customer, s),
            "moment": pick_moment(customer, s, today),
        }
        offers.append(offer)
    # Urgent first, then the ones with a concrete money value
    offers.sort(key=lambda o: (not o["signal"]["urgent"], -o["signal"].get("value_eur", 0)))
    return offers
