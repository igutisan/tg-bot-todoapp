"""
Configurations for the Telegram Bot.
"""
import os
from dotenv import load_dotenv


load_dotenv()

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno.")


NESTJS_API_BASE_URL = "http://localhost:3000/api" 


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN no está configurado en las variables de entorno.")


# Umbral de similitud para fuzzy matching (0-100). Ajusta según qué tan estricto quieres ser.
FUZZY_MATCH_THRESHOLD = 82
