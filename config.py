"""
Configurations for the Telegram Bot.
"""
import os
from dotenv import load_dotenv


load_dotenv()

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured in environment variables.")


NESTJS_API_BASE_URL = "http://localhost:3000/api" 


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not configured in environment variables.")


# Similarity threshold for fuzzy matching (0-100). Adjust based on how strict you want to be.
FUZZY_MATCH_THRESHOLD = 82