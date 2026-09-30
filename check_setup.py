"""Run this to check that your Gemini API key and model work:

    python check_setup.py
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads the .env file and puts its values in os.environ

if not os.getenv("GOOGLE_API_KEY"):
    raise SystemExit(
        "No GOOGLE_API_KEY found.\n"
        "1. Get a free key at https://aistudio.google.com  →  'Get API key'\n"
        "2. Paste it in the .env file:  GOOGLE_API_KEY=your-key\n"
        "(The app also works WITHOUT a key, using the keyword classifier and template texts.)"
    )

from langchain.chat_models import init_chat_model  # noqa: E402

model_name = os.getenv("MODEL", "google_genai:gemini-2.5-flash")
print(f"Testing model: {model_name} ...")

llm = init_chat_model(model_name)
reply = llm.invoke("Say 'setup works!' and nothing else.")
print("Model replied:", reply.content)
