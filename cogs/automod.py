import discord
from discord.ext import commands

from database import get_setting, set_setting


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blocked = {"discord.gg/", "free nitro", "@everyone @everyone"}

    @commands.hybrid_command(name="automod")
    @commands.has_permissions(manage_guild=True)
    async def automod(self, ctx, enabled: bool):
        set_setting(ctx.guild.id, "automod_enabled", int(enabled))
        await ctx.send(f"AutoMod is now **{'enabled' if enabled else 'disabled'}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if not get_setting(message.guild.id, "automod_enabled"):
            return
        content = message.content.lower()
        if any(term in content for term in self.blocked):
            try:
                await message.delete()
                await message.channel.send(f"🛡️ {message.author.mention}, that message was blocked by LightCore AutoMod.", delete_after=5)
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
