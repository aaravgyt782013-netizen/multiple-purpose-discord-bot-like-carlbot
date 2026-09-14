import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
PREFIX = "."
BRAND = "LightCore"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from .env")
if not CLIENT_ID:
    raise RuntimeError("CLIENT_ID is missing from .env")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    case_insensitive=True,
    help_command=None,
    activity=discord.Game(name=".help | LightCore"),
)

COGS = [
    "moderation", "automod", "logging", "leveling", "tickets", "roles",
    "currency", "music", "embeds", "panels", "welcome", "giveaways",
    "custom_commands", "temp_voice", "fun", "games", "serverinfo",
    "admin", "memberstats", "applications",
]


@bot.event
async def on_ready():
    logging.info("%s online as %s (%s) • Client ID %s", BRAND, bot.user, bot.user.id, CLIENT_ID)
    try:
        synced = await bot.tree.sync()
        logging.info("Synced %d slash commands", len(synced))
    except Exception:
        logging.exception("Slash command sync failed")


async def load_extensions():
    for name in COGS:
        await bot.load_extension(f"cogs.{name}")
        logging.info("Loaded cog: %s", name)


async def runner():
    init_db()
    await load_extensions()
    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(runner())
