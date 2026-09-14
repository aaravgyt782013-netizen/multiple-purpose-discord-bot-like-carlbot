import logging
import os

import discord
from discord.ext import commands

try:
    import wavelink
except ImportError:  # pragma: no cover
    wavelink = None

log = logging.getLogger(__name__)


class Music(commands.Cog):
    """Lavalink-backed music. The bot process never creates raw FFmpeg audio sources."""

    def __init__(self, bot):
        self.bot = bot

    @property
    def node(self):
        if wavelink is None:
            return None
        try:
            return wavelink.Pool.get_node()
        except Exception:
            return None

    def node_error(self):
        if wavelink is None:
            return "Music is unavailable because Wavelink is not installed."
        return "No Lavalink node is connected. Set LAVALINK_URI and LAVALINK_PASSWORD on the host and make sure the node is online."

    async def _player(self, ctx):
        if not ctx.guild:
            await ctx.send("Music commands can only be used in a server.")
            return None
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("🎧 Join a voice channel first.")
            return None
        if self.node is None:
            await ctx.send(f"❌ {self.node_error()}")
            return None

        channel = ctx.author.voice.channel
        player = ctx.voice_client
        if player is None:
            try:
                player = await channel.connect(cls=wavelink.Player, self_deaf=True)
            except discord.Forbidden:
                await ctx.send("❌ I cannot join that voice channel. Give me **Connect** and **Speak** permissions.")
                return None
            except discord.ClientException as exc:
                await ctx.send(f"❌ Discord voice connection failed: `{exc}`. Check channel permissions and the server voice region.")
                return None
            except Exception as exc:
                log.exception("Lavalink voice connection failed")
                await ctx.send(f"❌ Voice connection failed: `{type(exc).__name__}: {exc}`. The Lavalink node may be offline or unable to reach Discord voice.")
                return None
        elif isinstance(player, wavelink.Player) and player.channel != channel:
            try:
                await player.move_to(channel)
            except Exception as exc:
                await ctx.send(f"❌ I could not move to your voice channel: `{exc}`")
                return None
        return player

    @commands.hybrid_command(name="join", description="Join your voice channel using Lavalink.")
    @commands.cooldown(2, 10, commands.BucketType.guild)
    async def join(self, ctx):
        player = await self._player(ctx)
        if player:
            await ctx.send("🎵 Connected through Lavalink.")

    @commands.hybrid_command(name="play", aliases=["p"], description="Search and play audio through Lavalink.")
    @commands.cooldown(3, 20, commands.BucketType.member)
    async def play(self, ctx, *, query: str):
        player = await self._player(ctx)
        if not player:
            return
        await ctx.defer()
        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as exc:
            log.exception("Lavalink search failed for %r", query)
            await ctx.send(f"❌ Lavalink could not search that request: `{type(exc).__name__}`. The music node may be offline or its source/plugin may be unavailable.")
            return
        if not tracks:
            await ctx.send("🔎 No playable track was found. Try a song title, artist + title, or a supported URL.")
            return
        track = tracks[0]
        try:
            await player.play(track)
        except Exception as exc:
            log.exception("Lavalink playback failed")
            await ctx.send(f"❌ Lavalink found the track but could not start playback: `{type(exc).__name__}: {exc}`")
            return
        await ctx.send(f"▶️ Playing **{track.title}** — `{track.author}`")

    @commands.hybrid_command(name="pause", description="Pause or resume the current Lavalink player.")
    async def pause(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await player.pause(not player.paused)
        await ctx.send("⏸️ Paused." if player.paused else "▶️ Resumed.")

    @commands.hybrid_command(name="skip", description="Skip the current track.")
    async def skip(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await player.skip()
        await ctx.send("⏭️ Skipped.")

    @commands.hybrid_command(name="stop", description="Stop playback and clear the Lavalink player.")
    async def stop(self, ctx):
        player = ctx.voice_client
        if isinstance(player, wavelink.Player):
            await player.stop()
        await ctx.send("⏹️ Playback stopped.")

    @commands.hybrid_command(name="volume", description="Set music volume from 0 to 100.")
    async def volume(self, ctx, value: int):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        value = max(0, min(100, value))
        await player.set_volume(value)
        await ctx.send(f"🔊 Volume set to **{value}%**.")

    @commands.hybrid_command(name="nowplaying", description="Show the current Lavalink track.")
    async def nowplaying(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await ctx.send(f"🎶 **{player.current.title}** — `{player.current.author}`")

    @commands.hybrid_command(name="leave", description="Disconnect the Lavalink player.")
    async def leave(self, ctx):
        player = ctx.voice_client
        if isinstance(player, wavelink.Player):
            await player.disconnect()
            return await ctx.send("👋 Left the voice channel.")
        await ctx.send("I am not connected to voice.")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload):
        log.info("Lavalink node READY: %s", payload.node.identifier)

    @commands.Cog.listener()
    async def on_wavelink_node_disconnected(self, payload):
        log.error("Lavalink node DISCONNECTED: %s", payload.node.identifier)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload):
        log.error("Lavalink track exception: %s", payload.exception)

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload):
        log.error("Lavalink track stuck: %s", payload.threshold)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload):
        if payload.player and payload.track:
            log.info("Track started in guild %s: %s", payload.player.guild.id, payload.track.title)


async def setup(bot):
    await bot.add_cog(Music(bot))
