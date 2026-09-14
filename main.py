import asyncio
import logging
import os
import shutil
import time
from urllib.parse import urlparse

import discord
import wavelink
from discord.ext import commands
from dotenv import load_dotenv
from database import init_db
from health_server import start_health_server

load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
CLIENT_ID=os.getenv("CLIENT_ID")
LAVALINK_URI=os.getenv("LAVALINK_URI","").strip()
LAVALINK_PASSWORD=os.getenv("LAVALINK_PASSWORD","").strip()
LAVALINK_NAME=os.getenv("LAVALINK_NAME","primary").strip() or "primary"
PREFIX="."
BRAND="LightCore"
if not BOT_TOKEN:raise RuntimeError("BOT_TOKEN is missing from .env")
if not CLIENT_ID:raise RuntimeError("CLIENT_ID is missing from .env")
logging.basicConfig(level=logging.INFO,format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
log=logging.getLogger("lightcore")
intents=discord.Intents.all()

class LightCoreBot(commands.Bot):
    async def setup_hook(self):
        await load_extensions()
        validate_command_names()
        await connect_lavalink(self)

    async def on_wavelink_node_ready(self,payload):
        node=getattr(payload,"node",None)
        log.info(
            "Lavalink NODE READY event fired: node=%r uri=%r connected=%s",
            getattr(node,"identifier",LAVALINK_NAME),
            getattr(node,"uri",LAVALINK_URI),
            getattr(node,"is_connected",None),
        )

    async def on_wavelink_node_closed(self,payload):
        node=getattr(payload,"node",None)
        log.warning(
            "Lavalink NODE CLOSED event fired: node=%r reason=%r code=%r",
            getattr(node,"identifier",LAVALINK_NAME),
            getattr(payload,"reason",None),
            getattr(payload,"code",None),
        )

bot=LightCoreBot(command_prefix=PREFIX,intents=intents,case_insensitive=True,help_command=None,activity=discord.Game(name=".help | LightCore"))
bot.started_at=time.monotonic()
bot.started_at_wall=discord.utils.utcnow()
COGS=["moderation","automod","logging","leveling","tickets","ticket_plus","roles","currency","music","embeds","panels","welcome","giveaways","giveaway_plus","custom_commands","temp_voice","fun","games","serverinfo","admin","memberstats","applications","activitystats","status","utility","core"]

async def load_extensions():
    for name in COGS:
        try:await bot.load_extension(f"cogs.{name}");log.info("Loaded cog: %s",name)
        except Exception:log.exception("Failed to load cog: %s",name);raise

def _lavalink_env_status():return bool(LAVALINK_URI),bool(LAVALINK_PASSWORD),bool(LAVALINK_NAME)

async def raw_lavalink_connectivity_check():
    """Check DNS/TCP reachability without performing Lavalink authentication."""
    parsed=urlparse(LAVALINK_URI)
    host=parsed.hostname
    port=parsed.port or (443 if parsed.scheme=="https" else 80)
    if not host:
        log.error("Lavalink RAW CONNECTIVITY: could not parse host from LAVALINK_URI=%r",LAVALINK_URI)
        return False
    started=time.monotonic()
    try:
        reader,writer=await asyncio.wait_for(asyncio.open_connection(host,port),timeout=10)
        elapsed=time.monotonic()-started
        log.info("Lavalink RAW TCP CONNECTIVITY OK: host=%r port=%d elapsed=%.2fs",host,port,elapsed)
        writer.close()
        await writer.wait_closed()
        return True
    except asyncio.TimeoutError:
        log.error("Lavalink RAW TCP CONNECTIVITY TIMED OUT after 10s: host=%r port=%d",host,port)
    except Exception as exc:
        log.error("Lavalink RAW TCP CONNECTIVITY FAILED: host=%r port=%d error=%s: %s",host,port,type(exc).__name__,exc,exc_info=True)
    return False

async def connect_lavalink(client):
    uri_ok,password_ok,name_ok=_lavalink_env_status()
    log.info("Lavalink config: LAVALINK_URI=%r (non-empty=%s); LAVALINK_PASSWORD=%s (non-empty); LAVALINK_NAME=%r (non-empty=%s)",LAVALINK_URI,uri_ok,"SET" if password_ok else "MISSING",LAVALINK_NAME,name_ok)
    if not uri_ok or not password_ok or not name_ok:
        log.error("Lavalink startup connection skipped: one or more required env vars are empty.")
        return

    await raw_lavalink_connectivity_check()

    for attempt,delay in enumerate((2,5,10),1):
        try:
            node=wavelink.Node(identifier=LAVALINK_NAME,uri=LAVALINK_URI,password=LAVALINK_PASSWORD,retries=3)
            log.info("Lavalink connection attempt %d/3: calling and awaiting wavelink.Pool.connect() with 15s hard timeout...",attempt)
            started=time.monotonic()
            await asyncio.wait_for(
                wavelink.Pool.connect(nodes=[node],client=client),
                timeout=15,
            )
            elapsed=time.monotonic()-started
            log.info("Lavalink Pool.connect() RETURNED on attempt %d/3 after %.2fs; node=%r uri=%r",attempt,elapsed,LAVALINK_NAME,LAVALINK_URI)
            log.info("Lavalink NODE READY is still required; waiting for Wavelink node-ready event asynchronously.")
            return
        except asyncio.TimeoutError:
            log.error("Lavalink connection TIMED OUT after 15s on attempt %d/3; wavelink.Pool.connect() did not return.",attempt)
        except Exception as exc:
            log.exception("Lavalink connection attempt %d/3 failed with %s: %s",attempt,type(exc).__name__,exc)
        if attempt<3:
            log.warning("Retrying Lavalink connection in %ss...",delay)
            await asyncio.sleep(delay)
    log.error("Lavalink FAILED after 3 startup attempts; /play will remain unavailable until a node connects.")

def validate_command_names():
    prefix_names={}
    for c in bot.walk_commands():
        if isinstance(c,commands.Group):continue
        prefix_names.setdefault(c.qualified_name.lower(),[]).append(c.cog_name or "unknown")
        for alias in getattr(c,"aliases",[]):prefix_names.setdefault(alias.lower(),[]).append(f"{c.cog_name or 'unknown'} (alias of {c.qualified_name})")
    dup={n:o for n,o in prefix_names.items() if len(o)>1}
    if dup:raise RuntimeError("Command name/alias collision detected: "+", ".join(f"{n}: {o}" for n,o in dup.items()))
    slash={}
    for c in bot.tree.walk_commands():slash.setdefault(c.qualified_name.lower(),[]).append(type(c).__name__)
    sdup={n:o for n,o in slash.items() if len(o)>1}
    if sdup:raise RuntimeError("Slash command name collision detected: "+", ".join(f"{n}: {o}" for n,o in sdup.items()))
    log.info("Integration validation passed: %d prefix commands and %d slash commands.",len(prefix_names),len(slash))

@bot.event
async def on_ready():
    log.info("%s online as %s (%s) • Client ID %s",BRAND,bot.user,bot.user.id,CLIENT_ID);ffmpeg=shutil.which("ffmpeg")
    log.info("FFmpeg detected in PATH: %s (local FFmpeg is not used for Lavalink playback).",ffmpeg) if ffmpeg else log.warning("FFmpeg is not in PATH; Lavalink playback can still work.")
    if getattr(bot,"_slash_synced",False):return
    try:synced=await bot.tree.sync();bot._slash_synced=True;log.info("Synced %d slash commands",len(synced))
    except Exception:log.exception("Slash command sync failed")

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.CommandNotFound):return
    if isinstance(error,commands.CommandOnCooldown):return await ctx.send(f"⏳ Slow down — try again in **{error.retry_after:.1f}s**.")
    if isinstance(error,commands.MissingPermissions):
        names=", ".join(p.replace("_"," ").title() for p in error.missing_permissions);e=discord.Embed(title="🚫 Permission Required",description=f"You need **{names}** permission to use this command.",color=discord.Color.red());return await ctx.send(embed=e)
    if isinstance(error,commands.BotMissingPermissions):
        names=", ".join(p.replace("_"," ").title() for p in error.missing_permissions);e=discord.Embed(title="⚠️ Bot Permission Missing",description=f"LightCore needs **{names}** permission to complete this action.",color=discord.Color.orange());return await ctx.send(embed=e)
    if isinstance(error,commands.MissingRequiredArgument):return await ctx.send(f"❌ Missing `{error.param.name}`. Use `.help {ctx.command.qualified_name}` for syntax.")
    if isinstance(error,commands.BadArgument):return await ctx.send("❌ One of the arguments could not be understood. Check the member/channel/number and try again.")
    if isinstance(error,commands.CheckFailure):return await ctx.send("❌ This command cannot be used here or you do not meet its requirements.")
    log.exception("Unhandled command error in %s",getattr(ctx.command,"qualified_name","unknown"),exc_info=error)
    try:await ctx.send("⚠️ LightCore hit an internal error. The error was logged; please try again later.")
    except Exception:log.exception("Could not send global error response")

async def runner():init_db();validate_command_names();log.info("Startup validation passed; connecting to Discord.");await bot.start(BOT_TOKEN)
if __name__=="__main__":start_health_server();asyncio.run(runner())
