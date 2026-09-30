"""The demo UI (what the jury sees). Run with:

    streamlit run app.py
"""
import streamlit as st

from graph import graph

st.set_page_config(page_title="SLW Maaseik - Hackathon", page_icon="🚀")
st.title("🚀 SLW Maaseik - Hackathon demo")
st.caption("TODO: one sentence explaining what problem this solves.")

# Streamlit re-runs this whole file on every click, so we keep the chat
# history in st.session_state (it survives those re-runs).
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show the conversation so far
for role, text in st.session_state.messages:
    st.chat_message(role).write(text)

# Chat input box at the bottom of the page
if user_input := st.chat_input("Ask something..."):
    st.session_state.messages.append(("user", user_input))
    st.chat_message("user").write(user_input)

    with st.spinner("Thinking..."):
        result = graph.invoke({"messages": st.session_state.messages})
    answer = result["messages"][-1].content

    st.session_state.messages.append(("assistant", answer))
    st.chat_message("assistant").write(answer)
