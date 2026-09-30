"""The demo UI (what the jury sees). Run with:

    streamlit run app.py
"""
import streamlit as st

import signals as sig
from graph import graph

st.set_page_config(page_title="KBC For You", page_icon="💙", layout="wide")

today, customers = sig.load_customers()
by_name = {c["name"]: c for c in customers}

st.title("💙 KBC For You")
st.caption("The right message, at the right moment, through the right channel — for every one of 2.3M customers. "
           "Demo with 100% fake customers.")

tab_feed, tab_scale = st.tabs(["For You page", "At scale"])


@st.cache_data(show_spinner=False)
def run_feed(customer_id: str) -> dict:
    """Run the graph once per customer and cache it (so the LLM isn't called on every click)."""
    customer = next(c for c in customers if c["id"] == customer_id)
    return graph.invoke({"customer": customer, "today": today})


with tab_feed:
    left, right = st.columns([1, 2])

    with left:
        name = st.selectbox("Customer (demo)", list(by_name))
        c = by_name[name]
        with st.container(border=True):
            st.subheader(c["name"])
            st.write(f"**{c['age']}** · {c['gender']} · {c['occupation']}")
            st.write(f"📍 {c['city']} · now in **{c['location_now']}**")
            st.write(f"🗣️ Language: {c['language'].upper()} · prefers **{c['preferred_channel']}**")
            st.write(f"🕒 Usually active {c['active_hours'][0]:02d}:00–{c['active_hours'][1]:02d}:00")
        with st.expander("Recent transactions"):
            st.dataframe(
                [{k: t[k] for k in ("date", "merchant", "amount", "currency", "country")} for t in c["transactions"]],
                hide_index=True,
            )

    with right:
        with st.spinner("Building the For You page..."):
            result = run_feed(c["id"])
        feed = result["feed"]

        if not feed:
            st.info("Nothing relevant right now — and that's fine. No spam.")
        for item in feed:
            with st.container(border=True):
                top = st.columns([3, 1])
                top[0].markdown(f"#### {item['title']}")
                top[1].markdown(f"`{item['category']}`")
                st.write(item["message"])
                if item["signal"].get("value_eur"):
                    st.metric("Estimated value for you", f"€{item['signal']['value_eur']:.2f}")
                meta = st.columns(3)
                meta[0].markdown(f"📨 **Channel**  \n{item['channel']}")
                meta[1].markdown(f"⏰ **Moment**  \n{item['moment']}")
                meta[2].markdown(f"🏦 **Service**  \n{item['service']}")
                st.caption(f"🔔 Notification preview: “{item['notification']}”")
                with st.expander("Why am I seeing this?"):
                    st.write(item["signal"]["evidence"])
                b1, b2 = st.columns(2)
                b1.button("Interested", key=f"yes-{c['id']}-{item['signal']['type']}")
                b2.button("Not for me", key=f"no-{c['id']}-{item['signal']['type']}")

with tab_scale:
    st.subheader("Same engine, every customer")
    st.write("Signals, moment and channel are simple rules → cheap to run nightly on millions of customers. "
             "Only the final message is written by the LLM.")
    rows = []
    for cust in customers:
        for o in sig.build_offers(cust, sig.detect_signals(cust, today), today):
            rows.append({"customer": cust["name"], "age": cust["age"], "signal": o["signal"]["type"],
                         "service": o["service"], "channel": o["channel"], "moment": o["moment"]})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    m = st.columns(3)
    m[0].metric("Customers in demo", len(customers))
    m[1].metric("Personal messages", len(rows))
    m[2].metric("Channels used", len({r["channel"] for r in rows}))
