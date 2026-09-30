"""All business settings in ONE place: industries, intents (life events / micro-moments) and widgets.

Nothing here is code logic - it is configuration. To add a new industry, intent or widget,
add an entry below; the engine, the agents and the UI all loop over these dictionaries.
All KBC services, rates and texts are ILLUSTRATIVE for the hackathon (not real KBC products/tariffs).
"""

MAX_RELEVANCE = 10          # the classification agent scores each industry 0..10
INTENT_THRESHOLD = 0.70     # Intent Score needed before the For You page changes
MAX_WIDGETS_PER_INTENT = 3  # the For You page is essential info only, not a feed

# ---------------------------------------------------------------------------
# 1. INDUSTRIES — used by the classification agent + the team's scoring formula
# ---------------------------------------------------------------------------
INDUSTRIES = {
    "baby_pregnancy": {
        "label": "Baby & pregnancy",
        "description": "Baby and children's clothing, baby gear, pregnancy and maternity shops",
        "keywords": ["baby", "babies", "child", "kid", "toddler", "prenatal", "pregnan", "maternity", "newborn"],
        "avg_expense": 40,   # average € per visit in this industry (fake benchmark data)
        "benchmark": 50,     # industry score at which the transactional signal is at full strength
    },
    "travel": {
        "label": "Travel",
        "description": "Airlines, airports, hotels, travel agencies, booking platforms, trains",
        "keywords": ["airline", "airport", "flight", "hotel", "travel", "booking", "trip", "rail", "holiday"],
        "avg_expense": 250,
        "benchmark": 40,
    },
    "construction": {
        "label": "Construction & renovation",
        "description": "DIY and hardware stores, building materials, tiles, paint, contractors, renovation",
        "keywords": ["diy", "hardware", "brico", "build", "construction", "tile", "paint", "renovat", "timber"],
        "avg_expense": 80,
        "benchmark": 60,
    },
}

# ---------------------------------------------------------------------------
# 2. INTENTS — the Intent Scoring Algorithm fuses several signals into one %.
#
#    Signal kinds:
#      industry          strength = min(1, industry_score / benchmark)          (transactional)
#      foreign_currency  strength = min(1, payments_in_foreign_currency / 3)    (transactional)
#      spending_ratio    strength = (spent / monthly income - 0.5) / 0.5        (transactional)
#      app_event         strength = min(1, times_seen / min_count)              (behavioral)
#      context           strength = 1 if the context event happened, else 0    (contextual)
#
#    Intent Score = 1 - Π (1 - weight × strength)      ("noisy-OR": every signal adds evidence)
#    Example: flight tickets (0.8) + app opened at a foreign airport (0.75) → 1 - 0.2×0.25 = 95%
# ---------------------------------------------------------------------------
INTENTS = {
    "international_travel": {
        "label": "International travel",
        "type": "Micro-moment",
        "signals": [
            {"kind": "industry", "industry": "travel", "weight": 0.80, "label": "Flight / hotel bookings"},
            {"kind": "context", "event": "airport_abroad", "weight": 0.75, "label": "Opened the app at a foreign airport"},
            {"kind": "foreign_currency", "weight": 0.50, "label": "Payments in a foreign currency"},
            {"kind": "app_event", "event": "viewed_travel_insurance", "min_count": 1, "weight": 0.30,
             "label": "Looked at travel insurance in the app"},
        ],
        "widgets": ["currency_converter", "card_abroad", "luggage_insurance", "currency_tips", "travel_insurance"],
    },
    "expecting_child": {
        "label": "Expecting / planning a child",
        "type": "Life event",
        "signals": [
            {"kind": "industry", "industry": "baby_pregnancy", "weight": 0.85, "label": "Repeated baby & pregnancy purchases"},
            {"kind": "app_event", "event": "viewed_child_savings", "min_count": 1, "weight": 0.40,
             "label": "Looked at child savings in the app"},
            {"kind": "app_event", "event": "viewed_family_insurance", "min_count": 1, "weight": 0.30,
             "label": "Looked at family insurance in the app"},
        ],
        # Profile check: buying baby things WITHOUT having children is the strong signal.
        # Customers who already have kids are probably shopping for them -> score × 0.5
        "profile_multiplier": {"field": "children", "equals": 0, "otherwise": 0.5},
        "widgets": ["child_savings", "family_insurance", "family_budget"],
    },
    "home_renovation": {
        "label": "Home renovation",
        "type": "Life event",
        "signals": [
            {"kind": "industry", "industry": "construction", "weight": 0.85, "label": "Repeated DIY / building purchases"},
            {"kind": "app_event", "event": "renovation_simulator_abandoned", "min_count": 1, "weight": 0.50,
             "label": "Started the renovation loan simulator but did not finish"},
        ],
        "widgets": ["renovation_loan", "home_insurance_check", "energy_advice"],
    },
    "budget_stress": {
        "label": "Budget stress",
        "type": "Micro-moment",
        "signals": [
            {"kind": "app_event", "event": "balance_check_month_end", "min_count": 5, "weight": 0.65,
             "label": "Checks the balance often near the end of the month"},
            {"kind": "spending_ratio", "weight": 0.50, "label": "Spending is high compared to monthly income"},
        ],
        "widgets": ["budget_overview", "advisor_call"],
    },
}

# ---------------------------------------------------------------------------
# 3. WIDGET LIBRARY — modular UI blocks for the For You page.
#    "type" tells app.py which interactive element to draw.
# ---------------------------------------------------------------------------
WIDGETS = {
    # Travel
    "currency_converter": {"type": "converter", "name": "Currency converter",
        "summary": "See what things cost in euros while you travel.",
        "info": "Convert prices to euros instantly with today's rate, so you always know what you pay."},
    "card_abroad": {"type": "toggle", "name": "Use your debit card worldwide",
        "summary": "Unblock your card for use outside Europe with one tap.",
        "info": "For your safety, debit cards can be limited to Europe. Switch on worldwide use for your "
                "trip and switch it off again when you are back."},
    "luggage_insurance": {"type": "action", "action": "Add luggage cover for this trip", "name": "Luggage micro-insurance",
        "summary": "Cover your luggage for just this trip.",
        "info": "A small, short-term insurance for lost, stolen or damaged luggage, only for the days you travel."},
    "currency_tips": {"type": "info", "name": "Pay smart abroad",
        "summary": "Avoid unnecessary card fees abroad.",
        "info": "When a card terminal abroad asks whether to pay in euros or in the local currency, choosing "
                "the LOCAL currency is usually cheaper (paying in euros often includes a worse exchange rate)."},
    "travel_insurance": {"type": "action", "action": "Get travel insurance", "name": "KBC Travel Insurance",
        "summary": "Medical costs, cancellation and assistance abroad.",
        "info": "Covers medical assistance and repatriation abroad, trip cancellation and luggage, "
                "for one trip or for the whole year."},
    # Expecting a child
    "child_savings": {"type": "action", "action": "Open a child savings account (1 click)", "name": "KBC Kids Savings Account",
        "summary": "Start saving for your child's future from day one.",
        "info": "A savings account in your child's name. Set up a small automatic monthly transfer; family "
                "can contribute too. Your child gets access at 18."},
    "family_insurance": {"type": "action", "action": "Update my family insurance", "name": "Family insurance update",
        "summary": "Make sure your family insurance fits a growing family.",
        "info": "Family (civil liability) insurance covers damage caused to others by members of your family. "
                "Add a new family member in the app, without paperwork."},
    "family_budget": {"type": "info", "name": "Family budget planner",
        "summary": "See what a growing family means for your budget.",
        "info": "Estimate new monthly costs such as childcare, clothing and health, and how much you can save."},
    # Home renovation
    "renovation_loan": {"type": "loan_simulator", "name": "Renovation loan simulator",
        "summary": "Finish your simulation: see your monthly payment in seconds.",
        "info": "A renovation loan spreads the cost of bigger works over several years with a fixed monthly "
                "amount. Energy-saving renovations can get better conditions."},
    "home_insurance_check": {"type": "action", "action": "Plan a 10-minute insurance check", "name": "Home insurance check-up",
        "summary": "Renovated? Make sure your home insurance matches the new value.",
        "info": "After renovation works your home is often worth more. Without an update you may be under-insured."},
    "energy_advice": {"type": "info", "name": "Energy renovation advice",
        "summary": "Which works save the most energy, and which grants exist?",
        "info": "An overview of insulation, heat pumps and solar panels, what they could save you per year, "
                "and which regional grants you may be entitled to."},
    # Budget stress
    "budget_overview": {"type": "budget", "name": "Your month at a glance",
        "summary": "A calm overview of what came in and what went out.",
        "info": "See your income and spending this month side by side, and which categories are the largest."},
    "advisor_call": {"type": "action", "action": "Book a free call with an advisor", "name": "Talk to an advisor",
        "summary": "Plan the coming months together with a KBC advisor.",
        "info": "A free, no-obligation conversation about your budget, bigger expenses and savings buffer."},
}

# Demo values for the interactive widgets (illustrative)
DEMO_FX_RATES = {"JPY": 162.0, "USD": 1.10, "GBP": 0.85}   # 1 EUR = x
DEMO_LOAN_RATE = 0.045                                       # yearly rate for the loan simulator
