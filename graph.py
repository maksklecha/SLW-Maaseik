"""The "brain" of the app: a LangGraph graph.

Right now the graph has ONE node (the chatbot). During the hackathon you
can add more nodes (e.g. "retrieve documents", "classify request",
"call a tool") and connect them with edges.

    START --> chatbot --> END
"""
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, MessagesState, StateGraph

load_dotenv()

llm = init_chat_model(os.getenv("MODEL", "anthropic:claude-sonnet-5-5"))

# TODO at the hackathon: rewrite this for the challenge you pick.
SYSTEM_PROMPT = (
    "You are a helpful assistant built for the Tectonic Hackathon. "
    "Answer clearly and concisely."
)


def chatbot(state: MessagesState) -> dict:
    """Node: send the conversation to the LLM and return its answer."""
    messages = [("system", SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    # Returning {"messages": [...]} APPENDS to the state (it does not replace it).
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile()


graph = build_graph()
