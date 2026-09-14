import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
PREFIX = "."
BRAND = "LightCore"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from .env")
if not CLIENT_ID:
    raise RuntimeError("CLIENT_ID is missing from .env")
