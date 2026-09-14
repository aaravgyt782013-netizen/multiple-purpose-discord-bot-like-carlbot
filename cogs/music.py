import logging
import random
from collections import defaultdict, deque

import discord
from discord.ext import commands

try:
    import wavelink
except ImportError:  # pragma: no cover
    wavelink = None

from database import connect

log = logging.getLogger(__name__)


class Music(commands.Cog):
    """Lavalink-backed music with persistent per-server autoplay."""

    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(deque)
        self.requesters = {}
        self.track_requesters = {}
        self.loop_modes = defaultdict(lambda: "off")
        self.panel_messages = {}
        self.autoplay = defaultdict(bool)

    async def cog_load(self):
        # Keep autoplay persistent without coupling music settings to the general
        # guild_settings schema. Existing databases migrate automatically.
        with connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS music_settings ("
                "guild_id INTEGER PRIMARY KEY, autoplay INTEGER NOT NULL DEFAULT 0)"
            )
            rows = db.execute("SELECT guild_id, autoplay FROM music_settings").fetchall()
        for row in rows:
            self.autoplay[row["guild_id"]] = bool(row["autoplay"])

    def _save_autoplay(self, guild_id, enabled):
        self.autoplay[guild_id] = enabled
        with connect() as db:
            db.execute(
                "INSERT INTO music_settings(guild_id, autoplay) VALUES(?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET autoplay=excluded.autoplay",
                (guild_id, int(enabled)),
            )

    def _autoplay_enabled(self, guild_id):
        return bool(self.autoplay[guild_id])

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
            if node.status is not wavelink.NodeStatus.CONNECTED:
                return None
            return node
        except Exception:
            return None

    def node_error(self):
        if wavelink is None:
            return "Wavelink is not installed."
        try:
            node = wavelink.Pool.get_node()
            status = getattr(node, "status", "unknown")
            return f"No Lavalink node is connected (current node status: `{status}`). Check the Render Lavalink env vars and node availability."
        except Exception:
            return "No Lavalink node is connected. Check the Render Lavalink env vars and node availability."

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
                self._set_player_autoplay(player, self._autoplay_enabled(ctx.guild.id))
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

    def _embed(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        player = guild.voice_client if guild else None
        autoplay = self._autoplay_enabled(guild_id)
        if not isinstance(player, wavelink.Player) or not player.current:
            embed = discord.Embed(title="🎵 Now Playing", description="Nothing is playing right now.", color=discord.Color.blurple())
            embed.add_field(name="🔁 Autoplay", value="**On**" if autoplay else "**Off**", inline=True)
            return embed
        track = player.current
        requester = self.requesters.get(guild_id)
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{track.title}]({getattr(track, 'uri', None) or '#'})**",
            color=discord.Color.blurple(),
        )
        artwork = getattr(track, "artwork", None)
        if artwork:
            embed.set_thumbnail(url=artwork)
        embed.add_field(name="Duration", value=f"`{self._duration(track.length)}`", inline=True)
        embed.add_field(name="Requested by", value=f"<@{requester}>" if requester else "Unknown", inline=True)
        embed.add_field(name="🔁 Autoplay", value="**On**" if autoplay else "**Off**", inline=True)
        embed.set_footer(text=f"Queue: {len(self.queues[guild_id])} • Loop: {self.loop_modes[guild_id]}")
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
            self.requesters[guild_id] = self.track_requesters.get(id(track), self.requesters.get(guild_id))
            await player.play(track, populate=self._autoplay_enabled(guild_id), max_populate=5)
            await self._update_panel(guild_id)
            return
        if queue:
            # A manually queued track always has priority over Lavalink's auto queue.
            track = queue.popleft()
            self.requesters[guild_id] = self.track_requesters.get(id(track), self.requesters.get(guild_id))
            await player.play(track, populate=self._autoplay_enabled(guild_id), max_populate=5)
            await self._update_panel(guild_id)
            return
        # With no manual queue, Wavelink's native AutoPlay/auto_queue takes over.
        # We deliberately do not call player.stop()/disconnect here.
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
            # A manual play request explicitly ends autoplay so it does not
            # unexpectedly resume a recommendation chain after this request.
            if self._autoplay_enabled(ctx.guild.id):
                self._save_autoplay(ctx.guild.id, False)
                self._set_player_autoplay(player, False)

            if player.current:
                self.queues[ctx.guild.id].append(track)
                embed = discord.Embed(
                    title="✅ Added to Queue",
                    description=f"**[{track.title}]({getattr(track, 'uri', None) or '#'})**",
                    color=discord.Color.green(),
                )
                artwork = getattr(track, "artwork", None)
                if artwork:
                    embed.set_thumbnail(url=artwork)
                embed.add_field(name="Duration", value=f"`{self._duration(track.length)}`", inline=True)
                embed.set_footer(text="Autoplay stopped because a song was manually queued.")
                await ctx.send(embed=embed)
            else:
                self.requesters[ctx.guild.id] = ctx.author.id
                await player.play(track, populate=self._autoplay_enabled(ctx.guild.id), max_populate=5)
            await self._send_or_update_panel(ctx)
        except Exception as exc:
            log.exception("Lavalink playback failed")
            await ctx.send(f"❌ Lavalink found the track but could not start playback: `{type(exc).__name__}: {exc}`")

    @commands.hybrid_command(name="autoplay", description="Toggle persistent server autoplay on or off.")
    async def autoplay_command(self, ctx):
        player = ctx.voice_client
        enabled = not self._autoplay_enabled(ctx.guild.id)
        self._save_autoplay(ctx.guild.id, enabled)
        if isinstance(player, wavelink.Player):
            if enabled:
                self._set_player_autoplay(player, True)
                if player.current:
                    # Populate recommendations from the current track while
                    # preserving the current playback position.
                    position = max(0, int(getattr(player, "position", 0) or 0))
                    try:
                        await player.play(player.current, start=position, populate=True, max_populate=5)
                    except Exception:
                        log.exception("Failed to populate autoplay recommendations")
            else:
                self._set_player_autoplay(player, False)
        await self._update_panel(ctx.guild.id)
        await ctx.send(f"🔁 Autoplay is now **{'On' if enabled else 'Off'}** for this server.")

    @commands.hybrid_command(name="pause", description="Pause or resume the current player.")
    async def pause(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        await player.pause(not player.paused)
        await self._update_panel(ctx.guild.id)

    @commands.hybrid_command(name="skip", aliases=["s"], description="Skip the current track.")
    async def skip(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        await player.skip()

    @commands.hybrid_command(name="stop", description="Stop playback, clear the queue, and disable autoplay.")
    async def stop(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        self.queues[ctx.guild.id].clear()
        self.loop_modes[ctx.guild.id] = "off"
        self._save_autoplay(ctx.guild.id, False)
        self._set_player_autoplay(player, False)
        await player.stop()
        await self._update_panel(ctx.guild.id)

    @commands.hybrid_command(name="volume", aliases=["vol"], description="Set music volume from 0 to 100.")
    async def volume(self, ctx, value: int):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player):
            return await ctx.send("❌ Music is not connected.")
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await ctx.send("❌ Join the same voice channel as LightCore to control music.")
        await player.set_volume(max(0, min(100, value)))
        await self._update_panel(ctx.guild.id)

    @commands.hybrid_command(name="nowplaying", aliases=["np"], description="Show the current Lavalink track.")
    async def nowplaying(self, ctx):
        player = ctx.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await ctx.send("❌ Nothing is currently playing.")
        await self._send_or_update_panel(ctx)

    @commands.hybrid_command(name="queue", aliases=["q"], description="Show the current music queue.")
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
            self._set_player_autoplay(player, False)
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
            guild_id = payload.player.guild.id
            self.requesters[guild_id] = self.track_requesters.get(id(payload.track), self.requesters.get(guild_id))
            log.info("Track started in guild %s: %s", guild_id, payload.track.title)
            await self._update_panel(guild_id)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if not player or not player.guild:
            return
        guild_id = player.guild.id
        # Wavelink's native AutoPlay owns its auto_queue. Only our manual
        # queue/loop needs explicit advancement here.
        if self.loop_modes[guild_id] == "queue" and payload.track:
            self.queues[guild_id].append(payload.track)
        try:
            if self.queues[guild_id]:
                await self._play_next(guild_id, player)
            else:
                await self._update_panel(guild_id)
        except Exception:
            log.exception("Failed to advance music queue in guild %s", guild_id)


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
            ("Autoplay", "🔁", "autoplay", discord.ButtonStyle.primary, 1),
        ]
        for label, emoji, action, style, row in controls:
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=style,
                custom_id=f"lightcore:music:{guild_id}:{action}",
                row=row,
            )
            if action == "autoplay":
                button.label = "Autoplay On" if cog._autoplay_enabled(guild_id) else "Autoplay Off"
            if action == "loop" and cog.loop_modes[guild_id] != "off":
                button.label = f"Loop {cog.loop_modes[guild_id].title()}"
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
                self.cog._save_autoplay(self.guild_id, False)
                self.cog._set_player_autoplay(player, False)
                await player.stop()
            elif action == "shuffle":
                random.shuffle(self.cog.queues[self.guild_id])
            elif action == "loop":
                modes = ["off", "track", "queue"]
                current = modes.index(self.cog.loop_modes[self.guild_id])
                self.cog.loop_modes[self.guild_id] = modes[(current + 1) % len(modes)]
            elif action == "autoplay":
                enabled = not self.cog._autoplay_enabled(self.guild_id)
                self.cog._save_autoplay(self.guild_id, enabled)
                if enabled:
                    self.cog._set_player_autoplay(player, True)
                    if player.current:
                        position = max(0, int(getattr(player, "position", 0) or 0))
                        try:
                            await player.play(player.current, start=position, populate=True, max_populate=5)
                        except Exception:
                            log.exception("Failed to populate autoplay recommendations from panel")
                else:
                    self.cog._set_player_autoplay(player, False)
            elif action == "queue":
                queue = self.cog.queues[self.guild_id]
                if not queue:
                    return await interaction.response.send_message("📜 Queue is empty.", ephemeral=True)
                text = "\n".join(f"**{i}.** {t.title} — `{self.cog._duration(t.length)}`" for i, t in enumerate(list(queue)[:15], 1))
                return await interaction.response.send_message(
                    embed=discord.Embed(title="📜 Music Queue", description=text, color=discord.Color.blurple()),
                    ephemeral=True,
                )
            await interaction.response.edit_message(embed=self.cog._embed(self.guild_id), view=MusicPanel(self.cog, self.guild_id))
        return callback


async def setup(bot):
    await bot.add_cog(Music(bot))
