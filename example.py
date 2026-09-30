"""One-command demo, no Streamlit needed:

    python example.py

Runs Yusuf through the Context Engine twice (before and after new data arrives)
and prints every step as a story. Resets the demo database first.
"""
import agents
import db
from config import INDUSTRIES, INTENTS
from graph import run

CUSTOMER = "C001"  # Yusuf


def show(title: str, s: dict) -> None:
    c = s["customer"]
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    print(f"👤 {c['name']}, {c['age']}, {c['occupation']}, {c['children']} children, prefers {c['preferred_channel']}")
    print(f"📥 Data received: {len(s['transactions'])} transactions, {len(s['app_events'])} app actions, "
          f"{len(s['contexts'])} context signals")

    print("\n1) Classification agent (+ verification):")
    for m, cl in sorted(s["classifications"].items()):
        top = {INDUSTRIES[k]["label"]: v for k, v in cl["scores"].items() if v}
        print(f"   {m:<24} {top or 'no relevant industry'}  [{cl['status']}, {cl['method']}]")

    print("\n2) Industry score vs benchmark (team formula):")
    for ind, b in s["industries"].items():
        if b["merchants"]:
            parts = " + ".join(f"{m['relevance'] / 10}×{m['visits']}²×({m['spent']:g}/{INDUSTRIES[ind]['avg_expense']})"
                               for m in b["merchants"])
            print(f"   {INDUSTRIES[ind]['label']}: {parts} = {b['score']}  (benchmark {b['benchmark']})")

    print("\n3) Intent Scores (threshold 70%):")
    for key, v in s["intents"].items():
        if v["score"] > 0:
            print(f"   {INTENTS[key]['label']:<30} {v['score']:.0%}  {'✅ validated' if v['validated'] else '⚪ below threshold'}")

    n = s.get("notification")
    print("\n4) Notification: " + (f"{n['channel']} · {n['moment']}\n   🔔 “{n['text']}”" if n
                                  else "none — nothing important to tell (no spam)"))

    print("\n5) For You page:")
    if not s.get("page"):
        print("   the normal KBC home screen")
        return
    for section in s["page"]["content"]["sections"]:
        print(f"   ## {section['headline']}")
        for card in section["cards"]:
            print(f"   • {card['title']}: {card['message']}\n     More info: {card['more_info']}")
    print(f"   (texts written by: {s['page']['content']['method']})")


if __name__ == "__main__":
    db.reset_db()
    print("LLM:", "Gemini" if agents.get_api_key() else "no API key → keyword classifier + template texts")
    show("BEFORE — Yusuf's history (one visit to a childwear shop)", run(CUSTOMER))
    db.release_next_batch(CUSTOMER)
    show("AFTER — new data arrives (more childwear visits, maternity shop, app actions)", run(CUSTOMER))
