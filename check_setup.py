"""Run this FIRST to check that your API key and model work.

    python check_setup.py
"""
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
import os

load_dotenv()  # reads the .env file and puts its values in os.environ

model_name = os.getenv("MODEL", "google_genai:gemini-2.5-flash")
print(f"Testing model: {model_name} ...")

llm = init_chat_model(model_name)
reply = llm.invoke("Say 'setup works!' and nothing else.")
print("Model replied:", reply.content)
