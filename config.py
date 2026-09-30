"""All business settings in ONE place: industries, benchmarks and KBC services.

To add a new industry (e.g. "cars"), add one entry to INDUSTRIES.
No other code has to change: the classifier, scoring, recommender and UI
all loop over this dictionary.

The KBC services below are ILLUSTRATIVE for the hackathon, not real KBC products/tariffs.
"""

INDUSTRIES = {
    "baby_pregnancy": {
        "label": "Baby & pregnancy",
        "description": "Baby and children's clothing, baby gear, pregnancy and maternity shops",
        # Used by the rule-based fallback classifier and by the verification step
        "keywords": ["baby", "babies", "child", "kid", "toddler", "prenatal", "pregnan", "maternity", "newborn"],
        "avg_expense": 40,     # average € per visit in this industry (fake benchmark)
        "benchmark": 50,       # industry score needed before we show anything
        "services": [
            {
                "id": "kids_savings_account",
                "name": "KBC Kids Savings Account",
                "summary": "A savings account in your child's name, opened in 1 click.",
                "info": "Put money aside for your child's future from day one. You can set up a small "
                        "automatic monthly transfer, grandparents can contribute too, and your child "
                        "gets access when they turn 18.",
            },
            {
                "id": "family_insurance",
                "name": "KBC Family Insurance update",
                "summary": "Check that your family insurance covers a growing family.",
                "info": "Family (civil liability) insurance covers damage your family members cause to "
                        "others. When your family grows, you can add a new family member to your "
                        "policy in the app, without paperwork.",
            },
            {
                "id": "family_budget_coach",
                "name": "Family budget planner",
                "summary": "See what a growing family means for your monthly budget.",
                "info": "A simple planner in KBC Mobile that estimates new monthly costs (childcare, "
                        "clothing, health) and shows how much you could save each month.",
            },
        ],
    },
    "travel": {
        "label": "Travel",
        "description": "Airlines, airports, hotels, travel agencies, booking platforms, trains abroad",
        "keywords": ["airline", "airport", "flight", "hotel", "travel", "booking", "trip", "rail", "holiday"],
        "avg_expense": 250,
        "benchmark": 40,
        "services": [
            {
                "id": "travel_insurance",
                "name": "KBC Travel Insurance",
                "summary": "Cover medical costs, cancellation and lost luggage abroad.",
                "info": "Travel insurance covers medical assistance abroad, repatriation, cancellation of "
                        "your trip and lost or damaged luggage. You can take it out for a single trip "
                        "or for the whole year.",
            },
            {
                "id": "card_abroad",
                "name": "Use your card worldwide",
                "summary": "Unblock your debit card for use outside Europe with one tap.",
                "info": "For security, debit cards can be limited to Europe. In KBC Mobile you can "
                        "switch on worldwide use for the dates of your trip and switch it off again after.",
            },
            {
                "id": "currency_tips",
                "name": "Currency & card fee tips",
                "summary": "Pay smart abroad and avoid unnecessary fees.",
                "info": "When a card terminal abroad asks whether to pay in euros or in the local "
                        "currency, choosing the local currency is usually cheaper. See the exchange "
                        "rate and fees before you pay with the built-in currency converter.",
            },
        ],
    },
    "construction": {
        "label": "Construction & renovation",
        "description": "DIY and hardware stores, building materials, tiles, paint, contractors, renovation",
        "keywords": ["diy", "hardware", "brico", "build", "construction", "tile", "paint", "renovat", "timber"],
        "avg_expense": 80,
        "benchmark": 60,
        "services": [
            {
                "id": "renovation_loan",
                "name": "KBC Renovation Loan",
                "summary": "Finance your renovation works at a fixed rate.",
                "info": "A renovation loan spreads the cost of bigger works (roof, kitchen, insulation) "
                        "over several years with a fixed monthly amount. Energy-saving renovations can "
                        "qualify for better conditions.",
            },
            {
                "id": "home_insurance_update",
                "name": "Home insurance check-up",
                "summary": "Renovated? Make sure your home insurance reflects the new value.",
                "info": "After renovation works your home is often worth more. If your fire/home "
                        "insurance isn't updated, you might be under-insured. An advisor can check it "
                        "with you in 10 minutes.",
            },
            {
                "id": "energy_advice",
                "name": "Energy renovation advice",
                "summary": "Find out which works save the most energy and which grants exist.",
                "info": "Get an overview of insulation, heat pumps and solar panels, how much they could "
                        "save you per year, and which regional grants and premiums you may be entitled to.",
            },
        ],
    },
}

MAX_RELEVANCE = 10          # classifier scores each industry 0..10
MAX_SERVICES_PER_UPDATE = 3  # the For You page is essential info only, not a feed
