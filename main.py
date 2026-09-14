import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from config import BOT_TOKEN, PREFIX, BRAND
from database import init_db

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
    "core", "moderation", "automod", "logging", "leveling", "tickets",
    "roles", "currency", "music", "embeds", "panels", "welcome",
    "giveaways", "custom_commands",
]


@bot.event
async def on_ready():
    logging.info("%s online as %s (%s)", BRAND, bot.user, bot.user.id)
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
