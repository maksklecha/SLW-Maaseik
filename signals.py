"""Right channel + right moment, decided by simple rules on the customer profile.

Rules (not the LLM) so that it is predictable, explainable and free at scale.
"""


def pick_channel(customer: dict) -> str:
    if customer["age"] >= 65:
        return "📞 Phone call by a KBC advisor"   # a personal call instead of a text for elderly customers
    if customer["preferred_channel"] == "app":
        return "📱 Push notification"
    return "✉️ Email"


def pick_moment(customer: dict) -> str:
    start, end = customer["active_hour_start"], customer["active_hour_end"]
    if customer["age"] >= 65:
        return f"Next weekday between {start:02d}:00 and {end:02d}:00 (when they are usually available)"
    return f"Today between {start:02d}:00 and {end:02d}:00 (when they usually use their phone)"
