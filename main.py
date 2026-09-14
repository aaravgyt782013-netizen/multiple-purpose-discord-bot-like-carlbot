import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db
from health_server import start_health_server

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
PREFIX = "."
BRAND = "LightCore"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from .env")
if not CLIENT_ID:
    raise RuntimeError("CLIENT_ID is missing from .env")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
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
    "admin", "memberstats", "applications", "core",
]


async def load_extensions():
    for name in COGS:
        await bot.load_extension(f"cogs.{name}")
        logging.info("Loaded cog: %s", name)


def validate_command_names():
    prefix_names = {}
    for command in bot.walk_commands():
        if isinstance(command, commands.Group):
            continue
        name = command.qualified_name.lower()
        prefix_names.setdefault(name, []).append(command.cog_name or "unknown")

    duplicates = {name: owners for name, owners in prefix_names.items() if len(owners) > 1}
    if duplicates:
        formatted = ", ".join(f"{name}: {owners}" for name, owners in duplicates.items())
        raise RuntimeError(f"Command name collision detected: {formatted}")

    slash_names = {}
    for command in bot.tree.walk_commands():
        name = command.qualified_name.lower()
        slash_names.setdefault(name, []).append(type(command).__name__)
    slash_duplicates = {name: owners for name, owners in slash_names.items() if len(owners) > 1}
    if slash_duplicates:
        formatted = ", ".join(f"{name}: {owners}" for name, owners in slash_duplicates.items())
        raise RuntimeError(f"Slash command collision detected: {formatted}")

    logging.info(
        "Integration validation passed: %d prefix commands and %d slash commands registered without collisions.",
        len(prefix_names),
        len(slash_names),
    )


@bot.event
async def on_ready():
    logging.info("%s online as %s (%s) • Client ID %s", BRAND, bot.user, bot.user.id, CLIENT_ID)
    if getattr(bot, "_slash_synced", False):
        return
    try:
        synced = await bot.tree.sync()
        bot._slash_synced = True
        logging.info("Synced %d slash commands", len(synced))
    except Exception:
        logging.exception("Slash command sync failed")


async def runner():
    init_db()
    await load_extensions()
    validate_command_names()
    logging.info("Startup dry-run validation passed; connecting to Discord.")
    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    start_health_server()
    asyncio.run(runner())
