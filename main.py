import asyncio
import logging
import os
import shutil
import time

import discord
import wavelink
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db
from health_server import start_health_server

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
LAVALINK_URI = os.getenv("LAVALINK_URI", "").strip()
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "").strip()
LAVALINK_NAME = os.getenv("LAVALINK_NAME", "primary").strip() or "primary"
PREFIX = "."
BRAND = "LightCore"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from .env")
if not CLIENT_ID:
    raise RuntimeError("CLIENT_ID is missing from .env")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("lightcore")
intents = discord.Intents.all()


class LightCoreBot(commands.Bot):
    async def setup_hook(self):
        await load_extensions()
        await connect_lavalink(self)


bot = LightCoreBot(command_prefix=PREFIX, intents=intents, case_insensitive=True, help_command=None, activity=discord.Game(name=".help | LightCore"))
bot.started_at = time.monotonic()

COGS = [
    "moderation", "automod", "logging", "leveling", "tickets", "ticket_plus", "roles", "currency", "music", "embeds", "panels",
    "welcome", "giveaways", "giveaway_plus", "custom_commands", "temp_voice", "fun", "games", "serverinfo", "admin", "memberstats",
    "applications", "advanced_safe", "activitystats", "core",
]


async def load_extensions():
    for name in COGS:
        try:
            await bot.load_extension(f"cogs.{name}")
            log.info("Loaded cog: %s", name)
        except Exception:
            log.exception("Failed to load cog: %s", name)
            raise


def _lavalink_env_status():
    return bool(LAVALINK_URI), bool(LAVALINK_PASSWORD), bool(LAVALINK_NAME)


async def connect_lavalink(client):
    uri_ok, password_ok, name_ok = _lavalink_env_status()
    log.info(
        "Lavalink env check: LAVALINK_URI=%s LAVALINK_PASSWORD=%s LAVALINK_NAME=%s",
        "SET" if uri_ok else "MISSING",
        "SET" if password_ok else "MISSING",
        "SET" if name_ok else "MISSING",
    )
    if not uri_ok or not password_ok or not name_ok:
        log.error("Lavalink NOT configured: all three Lavalink env vars must be non-empty.")
        return

    delays = (2, 5, 10)
    for attempt in range(1, 4):
        try:
            node = wavelink.Node(
                identifier=LAVALINK_NAME,
                uri=LAVALINK_URI,
                password=LAVALINK_PASSWORD,
                retries=3,
            )
            await wavelink.Pool.connect(nodes=[node], client=client)
            log.info("Lavalink connection attempt %d/3 submitted: %s (%s)", attempt, LAVALINK_NAME, LAVALINK_URI)
            return
        except Exception as exc:
            log.exception("Lavalink connection attempt %d/3 failed: %s", attempt, exc)
            if attempt < 3:
                delay = delays[attempt - 1]
                log.warning("Retrying Lavalink connection in %ss...", delay)
                await asyncio.sleep(delay)
    log.error("Lavalink FAILED after 3 startup attempts. Music commands will report the node as unavailable.")


def validate_command_names():
    prefix_names = {}
    for command in bot.walk_commands():
        if isinstance(command, commands.Group):
            continue
        prefix_names.setdefault(command.qualified_name.lower(), []).append(command.cog_name or "unknown")
    duplicates = {n: o for n, o in prefix_names.items() if len(o) > 1}
    if duplicates:
        raise RuntimeError("Command name collision detected: " + ", ".join(f"{n}: {o}" for n, o in duplicates.items()))
    slash_names = {}
    for command in bot.tree.walk_commands():
        slash_names.setdefault(command.qualified_name.lower(), []).append(type(command).__name__)
    slash_duplicates = {n: o for n, o in slash_names.items() if len(o) > 1}
    if slash_duplicates:
        raise RuntimeError("Slash command name collision detected: " + ", ".join(f"{n}: {o}" for n, o in slash_duplicates.items()))
    log.info("Integration validation passed: %d prefix commands and %d slash commands.", len(prefix_names), len(slash_names))


@bot.event
async def on_ready():
    log.info("%s online as %s (%s) • Client ID %s", BRAND, bot.user, bot.user.id, CLIENT_ID)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        log.info("FFmpeg detected in PATH: %s (Lavalink playback does not use local FFmpeg)", ffmpeg)
    else:
        log.warning("FFmpeg is not in PATH. This does not block Lavalink playback because decoding runs on Lavalink.")
    if getattr(bot, "_slash_synced", False):
        return
    try:
        synced = await bot.tree.sync()
        bot._slash_synced = True
        log.info("Synced %d slash commands", len(synced))
    except Exception:
        log.exception("Slash command sync failed")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Slow down — try again in **{error.retry_after:.1f}s**.")
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌ You do not have the required permission for this command.")
    if isinstance(error, commands.BotMissingPermissions):
        return await ctx.send("❌ I am missing a Discord permission required for that action.")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"❌ Missing `{error.param.name}`. Use `.help {ctx.command.qualified_name}` for syntax.")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ One of the arguments could not be understood. Check the member/channel/number and try again.")
    if isinstance(error, commands.CheckFailure):
        return await ctx.send("❌ This command cannot be used here or you do not meet its requirements.")
    log.exception("Unhandled command error in %s", getattr(ctx.command, "qualified_name", "unknown"), exc_info=error)
    try:
        await ctx.send("⚠️ LightCore hit an internal error. The error was logged; please try again later.")
    except Exception:
        log.exception("Could not send global error response")


async def runner():
    init_db()
    validate_command_names()
    log.info("Startup validation passed; connecting to Discord.")
    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    start_health_server()
    asyncio.run(runner())
