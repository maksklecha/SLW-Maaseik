"""The demo UI (what the jury sees in the video). Run with:

    streamlit run app.py

Streamlit re-runs this whole file on every click. All state lives in the SQLite
database, so nothing is lost between re-runs, and Gemini is only called when new data arrives.
"""
import pandas as pd
import streamlit as st

import agents
import db
from config import DEMO_FX_RATES, DEMO_LOAN_RATE, INDUSTRIES, INTENT_THRESHOLD, INTENTS, WIDGETS
from graph import run

st.set_page_config(page_title="KBC For You", page_icon="💙", layout="wide")
db.ensure_db()

st.title("💙 KBC For You — Context Engine")
st.caption("Proof of concept with 100% fake customers · "
           + ("🟢 **Gemini connected**" if agents.get_api_key() else "⚪ **No Gemini key → rule/template fallback**"))

# --- Sidebar: pick a customer + simulate new data --------------------------------------------
with st.sidebar:
    customers = db.get_customers()
    labels = {f"{c['name']} ({c['age']})": c["id"] for c in customers}
    customer_id = labels[st.selectbox("Customer (demo)", list(labels))]
    c = db.get_customer(customer_id)
    st.markdown(f"**{c['name']}** · {c['age']} · {c['occupation']}  \n📍 {c['city']} · 👶 children: {c['children']}  \n"
                f"🗣️ {c['language'].upper()} · 📨 prefers {c['preferred_channel']} · "
                f"🕒 {c['active_hour_start']:02d}–{c['active_hour_end']:02d}h")
    st.divider()
    if st.button("⚡ New data arrives", type="primary", disabled=not db.has_unreleased(customer_id),
                 use_container_width=True, help="Releases the next batch of transactions, app actions and context signals"):
        db.release_next_batch(customer_id)
    if st.button("↺ Reset demo", use_container_width=True):
        db.reset_db()
        st.rerun()

with st.spinner("Context Engine is analysing..."):
    state = run(customer_id)

tab_fyp, tab_engine, tab_scale = st.tabs(["📱 For You page", "⚙️ Context Engine", "🌍 At scale"])


# --- Interactive widgets (the modular widget library) ---------------------------------------
def draw_widget(widget_id: str) -> None:
    w, key = WIDGETS[widget_id], f"{customer_id}-{widget_id}"
    if w["type"] == "converter":
        foreign = [t["currency"] for t in state["transactions"] if t["currency"] != "EUR"]
        cur = foreign[-1] if foreign else "USD"
        amount = st.number_input(f"Amount in {cur}", min_value=0.0, value=5000.0, step=500.0, key=key)
        st.write(f"≈ **€{amount / DEMO_FX_RATES.get(cur, 1):,.2f}** (demo rate 1 EUR = {DEMO_FX_RATES.get(cur, 1)} {cur})")
    elif w["type"] == "toggle":
        if st.toggle("Card active worldwide", key=key):
            st.success("Your debit card now works worldwide (demo).")
    elif w["type"] == "action":
        if st.button(w["action"], key=key):
            db.save_feedback(customer_id, widget_id, "used")
            st.success("Done! (demo)")
    elif w["type"] == "loan_simulator":
        amount = st.slider("Amount (€)", 5_000, 60_000, 20_000, 1_000, key=key + "-a")
        years = st.slider("Years", 2, 15, 7, key=key + "-y")
        r, n = DEMO_LOAN_RATE / 12, years * 12
        st.write(f"Monthly payment ≈ **€{amount * r / (1 - (1 + r) ** -n):,.2f}** (demo rate {DEMO_LOAN_RATE:.1%})")
    elif w["type"] == "budget":
        spent = sum(t["amount_eur"] for t in state["transactions"])
        st.write(f"Income: **€{c['monthly_income']:,.0f}** · Spent: **€{spent:,.0f}**")
        st.progress(min(1.0, spent / c["monthly_income"]))


# --- For You page ------------------------------------------------------------------------------
with tab_fyp:
    for n in db.get_notifications(customer_id):
        st.success(f"**{n['channel']}** · {n['moment']}  \n🔔 “{n['text']}”")

    page = state.get("page")
    if not page:
        st.info("Your usual KBC home screen. Nothing needs your attention right now "
                "(no intent above the threshold → no message, no spam).")
    else:
        dismissed = db.dismissed_widgets(customer_id)
        for section in page["content"]["sections"]:
            intent = INTENTS[section["intent"]]
            st.subheader(section["headline"])
            st.caption(f"{intent['type']} · Intent Score {state['intents'][section['intent']]['score']:.0%}")
            for card in section["cards"]:
                if card["widget_id"] in dismissed:
                    continue
                with st.container(border=True):
                    st.markdown(f"#### {card['title']}")
                    st.write(card["message"])
                    draw_widget(card["widget_id"])
                    with st.expander("More info"):
                        st.write(card["more_info"])
                    cols = st.columns(2)
                    if cols[0].button("👍 Interested", key=f"y-{customer_id}-{card['widget_id']}"):
                        db.save_feedback(customer_id, card["widget_id"], "interested")
                        st.toast("Thanks! An advisor can follow up.")
                    if cols[1].button("Not for me", key=f"n-{customer_id}-{card['widget_id']}"):
                        db.save_feedback(customer_id, card["widget_id"], "not_for_me")
                        st.rerun()
            with st.expander("Why am I seeing this?"):
                for e in state["intents"][section["intent"]]["evidence"]:
                    if e["strength"] > 0:
                        st.write(f"• {e['signal']}: {e['detail']}")
        st.caption(f"Texts written by: {page['content']['method']}")

# --- Context Engine: the logic behind it ------------------------------------------------------
with tab_engine:
    st.markdown("### 1 · Understand — data received")
    t1, t2, t3 = st.columns(3)
    t1.markdown("**Transactional**")
    t1.dataframe(pd.DataFrame(state["transactions"])[["ts", "merchant", "amount", "currency", "amount_eur"]],
                 hide_index=True, use_container_width=True)
    t2.markdown("**Behavioral (in-app)**")
    t2.dataframe(pd.DataFrame(state["app_events"] or [{"ts": "-", "event": "-"}])[["ts", "event"]],
                 hide_index=True, use_container_width=True)
    t3.markdown("**Contextual**")
    t3.dataframe(pd.DataFrame(state["contexts"] or [{"ts": "-", "detail": "-"}])[["ts", "detail"]],
                 hide_index=True, use_container_width=True)

    st.markdown("### 2 · Classification agent + verification")
    rows = [{"merchant": m, **{INDUSTRIES[k]["label"]: v for k, v in cl["scores"].items()},
             "status": "✅ verified" if cl["status"] == "verified" else "⚠️ needs review",
             "method": cl["method"], "reason": cl["reason"]}
            for m, cl in sorted(state["classifications"].items())]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("### 3 · Industry score (team formula)")
    st.latex(r"\text{score} = \sum_{\text{merchants}} \frac{\text{relevance}}{10}\times\text{visits}^2"
             r"\times\frac{\text{total spent}}{\text{avg. expense in industry}}")
    cols = st.columns(len(INDUSTRIES))
    for col, (ind, b) in zip(cols, state["industries"].items()):
        col.metric(INDUSTRIES[ind]["label"], b["score"], f"benchmark {b['benchmark']}", delta_color="off")
        col.progress(min(1.0, b["score"] / b["benchmark"]))
        if b["merchants"]:
            col.dataframe(pd.DataFrame(b["merchants"]), hide_index=True, use_container_width=True)

    st.markdown(f"### 4 · Recognize — Intent Scores (threshold {INTENT_THRESHOLD:.0%})")
    st.latex(r"\text{Intent} = 1 - \prod_{\text{signals}} (1 - \text{weight} \times \text{strength})")
    for key, v in state["intents"].items():
        st.markdown(f"**{INTENTS[key]['label']}** ({INTENTS[key]['type']}): **{v['score']:.0%}** "
                    + ("🟢 validated" if v["validated"] else "⚪ below threshold"))
        st.progress(v["score"])
        with st.expander("Signals"):
            st.dataframe(pd.DataFrame(v["evidence"]), hide_index=True, use_container_width=True)

    history = db.get_intent_history(customer_id)
    if history:
        st.markdown("### 5 · Living profile — Intent Score history")
        df = pd.DataFrame(history).pivot_table(index="data_version", columns="intent", values="score")
        st.line_chart(df)

# --- At scale ------------------------------------------------------------------------------------
with tab_scale:
    st.markdown(
        "- **Companies are classified once** (cached) → cost grows with the number of companies, "
        "not with 2.3M customers × transactions.\n"
        "- **Both scores are formulas** (no LLM) → run on every customer, every night, for almost nothing.\n"
        "- **Gemini only writes** the For You page for customers whose situation changed.\n"
        "- **New industry, intent or widget** = one entry in `config.py`; no human work per customer.")
    classified = db.get_all_classifications()
    m = st.columns(4)
    m[0].metric("Customers", len(customers))
    m[1].metric("Companies classified", len(classified))
    m[2].metric("Needing human review", sum(1 for x in classified if x["status"] != "verified"))
    m[3].metric("Widgets in library", len(WIDGETS))
