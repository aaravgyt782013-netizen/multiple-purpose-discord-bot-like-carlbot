import asyncio
import discord
from discord.ext import commands
import yt_dlp

YTDL = yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True})


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="join")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        if ctx.voice_client:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect()
        await ctx.send("🎵 LightCore joined the voice channel.")

    @commands.hybrid_command(name="play")
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        await ctx.send("🔎 Preparing audio…")
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, lambda: YTDL.extract_info(query, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        source = discord.FFmpegPCMAudio(data['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        ctx.voice_client.play(source)
        await ctx.send(f"▶️ Playing **{data.get('title', 'audio')}**")

    @commands.hybrid_command(name="stop")
    async def stop(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.send("⏹️ Playback stopped.")

    @commands.hybrid_command(name="leave")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")


async def setup(bot):
    await bot.add_cog(Music(bot))
