"""The demo UI (what the jury sees in the video). Run with:

    streamlit run app.py

Streamlit re-runs this whole file on every click. All state lives in the
SQLite database, so nothing is lost between re-runs.
"""
import pandas as pd
import streamlit as st

import agents
import db
from config import INDUSTRIES
from graph import run

st.set_page_config(page_title="KBC For You", page_icon="💙", layout="wide")
db.ensure_db()

st.title("💙 KBC For You — Context Engine")
st.caption("Proof of concept with 100% fake customers. "
           + ("LLM: **Gemini connected**" if agents.get_llm() else "LLM: **no API key → rule/template fallback**"))

with st.sidebar:
    customers = db.get_customers()
    labels = {f"{c['name']} ({c['age']}, {c['occupation']})": c["id"] for c in customers}
    customer_id = labels[st.selectbox("Customer (demo)", list(labels))]
    c = db.get_customer(customer_id)
    st.markdown(f"**{c['name']}** · {c['age']} · {c['gender']}  \n{c['occupation']}  \n📍 {c['city']}  \n"
                f"👶 Children: {c['children']}  \n🗣️ Language: {c['language'].upper()}  \n"
                f"📨 Prefers: {c['preferred_channel']}  \n🕒 Active {c['active_hour_start']:02d}–{c['active_hour_end']:02d}h")
    st.divider()
    if st.button("💳 New transactions arrive", type="primary", disabled=not db.has_unreleased(customer_id),
                 use_container_width=True):
        db.release_next_batch(customer_id)
    if st.button("↺ Reset demo data", use_container_width=True):
        db.reset_db()
        st.rerun()

# Run the Context Engine on the transactions the bank has received so far
with st.spinner("Context Engine is analysing transactions..."):
    state = run(customer_id)

tab_fyp, tab_engine, tab_scale = st.tabs(["📱 For You page", "⚙️ Context Engine", "🌍 At scale"])

# --- For You page -----------------------------------------------------------------
with tab_fyp:
    for n in db.get_notifications(customer_id):
        st.success(f"**{n['channel']}** · {n['moment']}  \n🔔 “{n['text']}”")

    updates = db.get_recommendations(customer_id)
    if not updates:
        st.info("Nothing new for you right now. (No benchmark crossed → no message, no spam.)")
    for u in updates:
        b = state["breakdown"][u["industry"]]
        st.subheader(f"For you: {INDUSTRIES[u['industry']]['label']}")
        for card in u["cards"]:
            with st.container(border=True):
                st.markdown(f"#### {card['title']}")
                st.write(card["message"])
                with st.expander("More info"):
                    st.write(card["more_info"])
                cols = st.columns(2)
                cols[0].button("I'm interested", key=f"y-{customer_id}-{card['service_id']}")
                cols[1].button("Not for me", key=f"n-{customer_id}-{card['service_id']}")
        with st.expander("Why am I seeing this?"):
            for m in b["merchants"]:
                st.write(f"{m['visits']}× at **{m['merchant']}** (€{m['spent']:.2f} in total)")
        st.caption(f"Text written by: {u['method']}")

# --- Context Engine (the logic behind it) ---------------------------------------------
with tab_engine:
    st.markdown("#### 1. Transactions received")
    st.dataframe(pd.DataFrame(state["transactions"]), hide_index=True, use_container_width=True)

    st.markdown("#### 2. Merchant → industry classification (agent) + verification")
    rows = []
    for m, cl in sorted(state["classifications"].items()):
        rows.append({"merchant": m, **{INDUSTRIES[k]["label"]: v for k, v in cl["scores"].items()},
                     "status": "✅ verified" if cl["status"] == "verified" else "⚠️ needs review",
                     "method": cl["method"], "reason": cl["reason"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("#### 3. Industry score vs benchmark")
    st.latex(r"\text{score} = \sum_{\text{merchants}} \frac{\text{relevance}}{10}\times\text{visits}^2"
             r"\times\frac{\text{total spent}}{\text{avg. expense in industry}}")
    for ind, b in state["breakdown"].items():
        crossed = b["score"] >= b["benchmark"]
        st.markdown(f"**{INDUSTRIES[ind]['label']}**: {b['score']} / benchmark {b['benchmark']} "
                    + ("🟢 **triggered**" if crossed else "⚪ below benchmark"))
        st.progress(min(1.0, b["score"] / b["benchmark"]))
        if b["merchants"]:
            st.dataframe(pd.DataFrame(b["merchants"]), hide_index=True, use_container_width=True)

    history = db.get_score_history(customer_id)
    if history:
        st.markdown("#### 4. Living profile: score history")
        df = pd.DataFrame(history)
        df["run"] = df.groupby("industry").cumcount() + 1
        st.line_chart(df.pivot(index="run", columns="industry", values="score"))

# --- At scale --------------------------------------------------------------------------
with tab_scale:
    st.markdown(
        "- **Merchants are classified once** and cached → cost grows with the number of *companies*, "
        "not with 2.3M customers × transactions.\n"
        "- **Scoring is a formula** (no LLM) → runs on every customer every night for almost nothing.\n"
        "- **The LLM only writes** for customers who crossed a benchmark.\n"
        "- **New industry** = one new entry in `config.py`."
    )
    classified = db.get_all_classifications()
    m = st.columns(3)
    m[0].metric("Customers", len(customers))
    m[1].metric("Merchants classified (cache)", len(classified))
    m[2].metric("Needing human review", sum(1 for x in classified if x["status"] != "verified"))
