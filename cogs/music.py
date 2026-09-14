import logging
import random
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord.ext import commands

try:
    import wavelink
except ImportError:  # pragma: no cover
    wavelink = None

log = logging.getLogger(__name__)


class Music(commands.Cog):
    """Lavalink-backed music with a live-in-place control panel."""

    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(deque)
        self.requesters = {}
        self.track_requesters = {}
        self.loop_modes = defaultdict(lambda: "off")
        self.panel_messages = {}

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
            return "Wavelink is not installed."
        return "No Lavalink node is connected. Check LAVALINK_URI/LAVALINK_PASSWORD and the node status."

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
                await ctx.send("❌ I cannot join/speak in that voice channel. Give LightCore **View Channel, Connect, and Speak** permissions.")
                return None
            except discord.ClientException as exc:
                await ctx.send(f"❌ Discord voice connection failed: `{exc}`. Check channel permissions and the voice server.")
                return None
            except Exception as exc:
                log.exception("Lavalink voice connection failed")
                await ctx.send(f"❌ Voice connection failed: `{type(exc).__name__}: {exc}`. The Lavalink node may be offline.")
                return None
        elif isinstance(player, wavelink.Player) and player.channel != channel:
            try:
                await player.move_to(channel)
            except Exception as exc:
                await ctx.send(f"❌ I could not move to your voice channel: `{exc}`")
                return None
        return player

    @staticmethod
    def _duration(ms):
        seconds = max(0, int(ms or 0) // 1000)
        return f"{seconds // 60}:{seconds % 60:02d}"

    @staticmethod
    def _bar(position_ms, length_ms, size=16):
        if not length_ms:
            return "░" * size
        ratio = max(0, min(1, position_ms / length_ms))
        point = min(size - 1, int(ratio * size))
        return "".join("🔘" if i == point else "▬" for i in range(size))

    def _progress(self, player):
        current = player.current
        position = getattr(player, "position", timedelta(0))
        position_ms = int(position.total_seconds() * 1000) if isinstance(position, timedelta) else int(position or 0)
        length = int(getattr(current, "length", 0) or 0)
        return f"`{self._duration(position_ms)}` {self._bar(position_ms, length)} `{self._duration(length)}`"

    def _embed(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        player = guild.voice_client if guild else None
        if not isinstance(player, wavelink.Player) or not player.current:
            return discord.Embed(title="🎵 LightCore Music", description="Nothing is playing right now.", color=discord.Color.blurple())
        track = player.current
        requester = self.requesters.get(guild_id, "Unknown")
        embed = discord.Embed(title="🎵 Now Playing", description=f"**{track.title}**\nby `{track.author}`", color=discord.Color.blurple())
        artwork = getattr(track, "artwork", None)
        if artwork:
            embed.set_thumbnail(url=artwork)
        embed.add_field(name="Progress", value=self._progress(player), inline=False)
        embed.add_field(name="Requester", value=f"<@{requester}>" if isinstance(requester, int) else str(requester), inline=True)
        embed.add_field(name="Loop", value=self.loop_modes[guild_id], inline=True)
        embed.add_field(name="Queue", value=f"{len(self.queues[guild_id])} track(s)", inline=True)
        embed.set_footer(text="Only members in the bot's voice channel can use these controls.")
        return embed

    async def _update_panel(self, guild_id, message=None):
        message = message or self.panel_messages.get(guild_id)
        if not message:
            return
        try:
            await message.edit(embed=self._embed(guild_id), view=MusicPanel(self, guild_id))
            self.panel_messages[guild_id] = message
        except (discord.NotFound, discord.HTTPException):
            self.panel_messages.pop(guild_id, None)

    async def _send_or_update_panel(self, ctx):
        existing = self.panel_messages.get(ctx.guild.id)
        if existing:
            await self._update_panel(ctx.guild.id, existing)
            return
        message = await ctx.send(embed=self._embed(ctx.guild.id), view=MusicPanel(self, ctx.guild.id))
        self.panel_messages[ctx.guild.id] = message

    async def _play_next(self, guild_id, player):
        queue = self.queues[guild_id]
        if self.loop_modes[guild_id] == "track" and player.current:
            track = player.current
            self.requesters[guild_id] = self.track_requesters.get(id(track), self.requesters.get(guild_id, "Unknown"))
            await player.play(track)
            await self._update_panel(guild_id)
            return
        if queue:
            track = queue.popleft()
            self.requesters[guild_id] = self.track_requesters.get(id(track), self.requesters.get(guild_id, "Unknown"))
            await player.play(track)
            await self._update_panel(guild_id)
            return
        await self._update_panel(guild_id)

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
            await ctx.send(f"❌ Lavalink could not search that request: `{type(exc).__name__}`. The node/source plugin may be unavailable.")
            return
        if not tracks:
            await ctx.send("🔎 No playable track was found. Try a title, artist + title, or supported URL.")
            return
        track = tracks[0]
        self.track_requesters[id(track)] = ctx.author.id
        try:
            if player.current:
                self.queues[ctx.guild.id].append(track)
                await ctx.send(f"➕ Queued **{track.title}** — `{self._duration(track.length)}`")
            else:
                self.requesters[ctx.guild.id] = ctx.author.id
                await player.play(track)
                await ctx.send(f"▶️ Playing **{track.title}** — `{track.author}`")
            await self._send_or_update_panel(ctx)
        except Exception as exc:
            log.exception("Lavalink playback failed")
            await ctx.send(f"❌ Lavalink found the track but could not start playback: `{type(exc).__name__}: {exc}`")

    @commands.hybrid_command(name="pause", description="Pause or resume the current player.")
    async def pause(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        await player.pause(not player.paused)
        await self._update_panel(ctx.guild.id)

    @commands.hybrid_command(name="skip", description="Skip the current track.")
    async def skip(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        await player.skip()

    @commands.hybrid_command(name="stop", description="Stop playback and clear the queue.")
    async def stop(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        self.queues[ctx.guild.id].clear()
        self.loop_modes[ctx.guild.id] = "off"
        await player.stop()
        await self._update_panel(ctx.guild.id)

    @commands.hybrid_command(name="volume", description="Set music volume from 0 to 100.")
    async def volume(self, ctx, value: int):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        await player.set_volume(max(0, min(100, value)))
        await self._update_panel(ctx.guild.id)

    @commands.hybrid_command(name="nowplaying", description="Show the current Lavalink track.")
    async def nowplaying(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await self._send_or_update_panel(ctx)

    @commands.hybrid_command(name="queue", description="Show the current music queue.")
    async def queue(self, ctx):
        queue = self.queues[ctx.guild.id]
        if not queue:
            return await ctx.send("📜 The music queue is empty.")
        lines = [f"**{i}.** {t.title} — `{self._duration(t.length)}`" for i, t in enumerate(list(queue)[:15], 1)]
        await ctx.send(embed=discord.Embed(title="📜 Music Queue", description="\n".join(lines), color=discord.Color.blurple()))

    @commands.hybrid_command(name="leave", description="Disconnect the Lavalink player.")
    async def leave(self, ctx):
        player = ctx.voice_client
        if isinstance(player, wavelink.Player):
            self.queues[ctx.guild.id].clear()
            await player.disconnect()
            self.panel_messages.pop(ctx.guild.id, None)
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
            await self._update_panel(payload.player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if not player or not player.guild:
            return
        guild_id = player.guild.id
        if self.loop_modes[guild_id] == "queue" and payload.track:
            self.queues[guild_id].append(payload.track)
        try:
            await self._play_next(guild_id, player)
        except Exception:
            log.exception("Failed to advance music queue in guild %s", guild_id)


class MusicPanel(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        controls = [
            ("Pause/Resume", "⏯️", "pause"), ("Skip", "⏭️", "skip"), ("Stop", "⏹️", "stop"),
            ("Shuffle", "🔀", "shuffle"), ("Loop", "🔁", "loop"), ("Vol -", "🔉", "voldown"),
            ("Vol +", "🔊", "volup"), ("Queue", "📜", "queue"),
        ]
        for label, emoji, action in controls:
            button = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=f"lightcore:music:{guild_id}:{action}")
            button.callback = self._callback(action)
            self.add_item(button)

    def _callback(self, action):
        async def callback(interaction):
            guild = interaction.guild
            player = guild.voice_client if guild else None
            if not isinstance(player, wavelink.Player):
                return await interaction.response.send_message("❌ Music is not connected.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel != player.channel:
                return await interaction.response.send_message("❌ Join the same voice channel as LightCore to use the music controls.", ephemeral=True)
            if action == "pause":
                await player.pause(not player.paused)
            elif action == "skip":
                await player.skip()
            elif action == "stop":
                self.cog.queues[self.guild_id].clear()
                self.cog.loop_modes[self.guild_id] = "off"
                await player.stop()
            elif action == "shuffle":
                random.shuffle(self.cog.queues[self.guild_id])
            elif action == "loop":
                modes = ["off", "track", "queue"]
                current = modes.index(self.cog.loop_modes[self.guild_id])
                self.cog.loop_modes[self.guild_id] = modes[(current + 1) % len(modes)]
            elif action == "voldown":
                await player.set_volume(max(0, int(getattr(player, "volume", 100)) - 10))
            elif action == "volup":
                await player.set_volume(min(100, int(getattr(player, "volume", 100)) + 10))
            elif action == "queue":
                queue = self.cog.queues[self.guild_id]
                if not queue:
                    return await interaction.response.send_message("📜 Queue is empty.", ephemeral=True)
                text = "\n".join(f"**{i}.** {t.title} — `{self.cog._duration(t.length)}`" for i, t in enumerate(list(queue)[:15], 1))
                return await interaction.response.send_message(embed=discord.Embed(title="📜 Music Queue", description=text, color=discord.Color.blurple()), ephemeral=True)
            await interaction.response.edit_message(embed=self.cog._embed(self.guild_id), view=MusicPanel(self.cog, self.guild_id))
        return callback


async def setup(bot):
    await bot.add_cog(Music(bot))
