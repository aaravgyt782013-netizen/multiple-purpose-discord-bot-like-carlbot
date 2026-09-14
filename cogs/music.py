import logging
import random
from collections import defaultdict, deque

import discord
from discord.ext import commands
try:
    import wavelink
except ImportError:
    wavelink = None
from database import connect

log = logging.getLogger(__name__)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(deque)
        self.requesters = {}
        self.track_requesters = {}
        self.loop_modes = defaultdict(lambda: "off")
        # The latest panel is retained only so controls can target the active
        # player state. New tracks always create a NEW message; panels are
        # never edited in place to announce a new song.
        self.panel_messages = {}
        self.panel_channels = {}
        self.announced_tracks = defaultdict(set)
        self.autoplay = defaultdict(bool)

    async def cog_load(self):
        with connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS music_settings (guild_id INTEGER PRIMARY KEY, autoplay INTEGER NOT NULL DEFAULT 0)")
            for row in db.execute("SELECT guild_id, autoplay FROM music_settings").fetchall():
                self.autoplay[row["guild_id"]] = bool(row["autoplay"])

    def _save_autoplay(self, guild_id, enabled):
        self.autoplay[guild_id] = enabled
        with connect() as db:
            db.execute("INSERT INTO music_settings(guild_id,autoplay) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET autoplay=excluded.autoplay", (guild_id, int(enabled)))

    def _set_player_autoplay(self, player, enabled):
        if wavelink is None or not isinstance(player, wavelink.Player):
            return
        player.autoplay = wavelink.AutoPlayMode.enabled if enabled else wavelink.AutoPlayMode.disabled
        if not enabled:
            try:
                player.auto_queue.clear()
            except Exception:
                pass

    @property
    def node(self):
        if wavelink is None:
            return None
        try:
            node = wavelink.Pool.get_node()
            return node if node.status is wavelink.NodeStatus.CONNECTED else None
        except Exception:
            return None

    def node_error(self):
        if wavelink is None:
            return "Wavelink is not installed."
        try:
            node = wavelink.Pool.get_node()
            return f"No Lavalink node is connected (current node status: `{getattr(node, 'status', 'unknown')}`)."
        except Exception:
            return "No Lavalink node is connected."

    async def _player(self, ctx):
        if not ctx.guild:
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
                self._set_player_autoplay(player, self.autoplay[ctx.guild.id])
            except discord.Forbidden:
                await ctx.send("❌ I need View Channel, Connect and Speak permissions.")
                return None
            except Exception as exc:
                log.exception("Voice connection failed")
                await ctx.send(f"❌ Voice connection failed: `{type(exc).__name__}`.")
                return None
        elif isinstance(player, wavelink.Player) and player.channel != channel:
            try:
                await player.move_to(channel)
            except Exception as exc:
                await ctx.send(f"❌ I could not move to your voice channel: `{type(exc).__name__}`.")
                return None
        return player

    @staticmethod
    def _duration(ms):
        seconds = max(0, int(ms or 0) // 1000)
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _embed(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        player = guild.voice_client if guild else None
        if not isinstance(player, wavelink.Player) or not player.current:
            return discord.Embed(title="🎵 Now Playing", description="Nothing is playing right now.", color=discord.Color.blurple())
        track = player.current
        requester = self.requesters.get(guild_id)
        url = getattr(track, "uri", None) or "#"
        by = f"<@{requester}>" if requester else "Unknown"
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"[{track.title}]({url})\n\nDuration: {self._duration(track.length)} • Requested By: {by}",
            color=discord.Color.blurple(),
        )
        artwork = getattr(track, "artwork", None)
        if artwork:
            embed.set_thumbnail(url=artwork)
        return embed

    async def _send_new_panel(self, guild_id, channel):
        """Send a fresh Now Playing message; never edit an older song announcement."""
        if channel is None:
            return None
        try:
            message = await channel.send(embed=self._embed(guild_id), view=MusicPanel(self, guild_id))
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Could not send Now Playing panel in channel %s", getattr(channel, "id", None))
            return None
        self.panel_channels[guild_id] = channel.id
        self.panel_messages[guild_id] = message
        return message

    async def _announce_current_track(self, guild_id, force=False):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        player = guild.voice_client
        track = player.current if isinstance(player, wavelink.Player) else None
        if not track:
            return None
        track_id = id(track)
        if not force and track_id in self.announced_tracks[guild_id]:
            return self.panel_messages.get(guild_id)
        channel_id = self.panel_channels.get(guild_id)
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None:
            return None
        self.announced_tracks[guild_id].add(track_id)
        return await self._send_new_panel(guild_id, channel)

    @commands.hybrid_command(name="join", description="Join your voice channel.")
    async def join(self, ctx):
        if await self._player(ctx):
            await ctx.send("🎵 Connected through Lavalink.")

    @commands.hybrid_command(name="play", aliases=["p"], description="Search and play audio.")
    async def play(self, ctx, *, query: str):
        player = await self._player(ctx)
        if not player:
            return
        await ctx.defer()
        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as exc:
            log.exception("Search failed")
            return await ctx.send(f"❌ Search failed: `{type(exc).__name__}`.")
        if not tracks:
            return await ctx.send("🔎 No playable track was found.")
        track = tracks[0]
        self.track_requesters[id(track)] = ctx.author.id
        self.panel_channels[ctx.guild.id] = ctx.channel.id
        if self.autoplay[ctx.guild.id]:
            self._save_autoplay(ctx.guild.id, False)
            self._set_player_autoplay(player, False)
        if player.current:
            self.queues[ctx.guild.id].append(track)
            embed = discord.Embed(title="✅ Added to Queue", description=f"[{track.title}]({getattr(track, 'uri', None) or '#'})", color=discord.Color.green())
            artwork = getattr(track, "artwork", None)
            if artwork:
                embed.set_thumbnail(url=artwork)
            await ctx.send(embed=embed)
        else:
            self.requesters[ctx.guild.id] = ctx.author.id
            await player.play(track, populate=False)
            # The command invocation channel is the source of the fresh panel.
            await self._announce_current_track(ctx.guild.id, force=True)

    @commands.hybrid_command(name="autoplay", description="Toggle server autoplay.")
    async def autoplay_command(self, ctx):
        enabled = not self.autoplay[ctx.guild.id]
        self._save_autoplay(ctx.guild.id, enabled)
        player = ctx.voice_client
        if isinstance(player, wavelink.Player):
            self._set_player_autoplay(player, enabled)
        await ctx.send(f"🔁 Autoplay is now **{'On' if enabled else 'Off'}**.")

    @commands.hybrid_command(name="pause", description="Pause or resume music.")
    async def pause(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await player.pause(not player.paused)

    @commands.hybrid_command(name="skip", aliases=["s"], description="Skip the current track.")
    async def skip(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await player.skip()

    @commands.hybrid_command(name="stop", description="Stop music and clear the queue.")
    async def stop(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        self.queues[ctx.guild.id].clear()
        self.loop_modes[ctx.guild.id] = "off"
        self._save_autoplay(ctx.guild.id, False)
        self._set_player_autoplay(player, False)
        await player.stop()
        await ctx.send("⏹️ Music stopped and queue cleared.")

    @commands.hybrid_command(name="volume", aliases=["vol"], description="Set music volume.")
    async def volume(self, ctx, value: commands.Range[int, 0, 100]):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        await player.set_volume(value)
        await ctx.send(f"🔊 Volume set to **{value}%**.")

    @commands.hybrid_command(name="nowplaying", aliases=["np"], description="Show the current track.")
    async def nowplaying(self, ctx):
        if not isinstance(ctx.voice_client, wavelink.Player) or not ctx.voice_client.current:
            return await ctx.send("❌ Nothing is currently playing.")
        self.panel_channels[ctx.guild.id] = ctx.channel.id
        await self._announce_current_track(ctx.guild.id, force=True)

    @commands.hybrid_command(name="queue", aliases=["q"], description="Show the music queue.")
    async def queue(self, ctx):
        q = self.queues[ctx.guild.id]
        if not q:
            return await ctx.send("📜 The music queue is empty.")
        text = "\n".join(f"**{i}.** {t.title} — `{self._duration(t.length)}`" for i, t in enumerate(list(q)[:15], 1))
        await ctx.send(embed=discord.Embed(title="📜 Music Queue", description=text, color=discord.Color.blurple()))

    @commands.hybrid_command(name="leave", description="Leave the voice channel.")
    async def leave(self, ctx):
        player = ctx.voice_client
        if isinstance(player, wavelink.Player):
            self.queues[ctx.guild.id].clear()
            self.panel_messages.pop(ctx.guild.id, None)
            self.panel_channels.pop(ctx.guild.id, None)
            self.announced_tracks.pop(ctx.guild.id, None)
            await player.disconnect()
            await ctx.send("👋 Left the voice channel.")
        else:
            await ctx.send("I am not connected to voice.")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload):
        if payload.player and payload.track:
            gid = payload.player.guild.id
            self.requesters[gid] = self.track_requesters.get(id(payload.track), self.requesters.get(gid))
            await self._announce_current_track(gid)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if not player or not player.guild:
            return
        gid = player.guild.id
        if self.loop_modes[gid] == "queue" and payload.track:
            self.queues[gid].append(payload.track)
        if self.queues[gid]:
            track = self.queues[gid].popleft()
            self.requesters[gid] = self.track_requesters.get(id(track), self.requesters.get(gid))
            await player.play(track, populate=self.autoplay[gid], max_populate=5)
        await self._announce_current_track(gid)


class MusicPanel(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        controls = [
            ("Pause", "⏸️", "pause", discord.ButtonStyle.primary, 0),
            ("Skip", "⏭️", "skip", discord.ButtonStyle.primary, 0),
            ("Stop", "⏹️", "stop", discord.ButtonStyle.danger, 0),
            ("Shuffle", "🔀", "shuffle", discord.ButtonStyle.secondary, 0),
            ("Queue", "📜", "queue", discord.ButtonStyle.secondary, 1),
            ("Loop", "🔁", "loop", discord.ButtonStyle.primary, 1),
        ]
        for label, emoji, action, style, row in controls:
            b = discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"lightcore:music:{guild_id}:{action}", row=row)
            b.callback = self._callback(action)
            self.add_item(b)

    def _callback(self, action):
        async def callback(interaction):
            guild = interaction.guild
            player = guild.voice_client if guild else None
            if not isinstance(player, wavelink.Player):
                return await interaction.response.send_message("❌ Music is not connected.", ephemeral=True)
            if action == "pause":
                await player.pause(not player.paused)
            elif action == "skip":
                await player.skip()
            elif action == "stop":
                self.cog.queues[self.guild_id].clear()
                self.cog.loop_modes[self.guild_id] = "off"
                self.cog._save_autoplay(self.guild_id, False)
                self.cog._set_player_autoplay(player, False)
                await player.stop()
            elif action == "shuffle":
                random.shuffle(self.cog.queues[self.guild_id])
            elif action == "loop":
                modes = ["off", "track", "queue"]
                self.cog.loop_modes[self.guild_id] = modes[(modes.index(self.cog.loop_modes[self.guild_id]) + 1) % len(modes)]
            elif action == "queue":
                q = self.cog.queues[self.guild_id]
                if not q:
                    return await interaction.response.send_message("📜 Queue is empty.", ephemeral=True)
                text = "\n".join(f"**{i}.** {t.title} — `{self.cog._duration(t.length)}`" for i, t in enumerate(list(q)[:15], 1))
                return await interaction.response.send_message(embed=discord.Embed(title="📜 Music Queue", description=text, color=discord.Color.blurple()), ephemeral=True)
            await interaction.response.edit_message(embed=self.cog._embed(self.guild_id), view=MusicPanel(self.cog, self.guild_id))
        return callback


async def setup(bot):
    await bot.add_cog(Music(bot))
