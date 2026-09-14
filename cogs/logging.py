import discord
from discord.ext import commands

from database import get_setting, set_setting


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, guild, title, description):
        channel_id = get_setting(guild.id, "log_channel")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
            embed.set_footer(text="LightCore")
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    @commands.hybrid_command(name="setlog")
    @commands.has_permissions(manage_guild=True)
    async def setlog(self, ctx, channel: discord.TextChannel):
        set_setting(ctx.guild.id, "log_channel", channel.id)
        await ctx.send(f"Logging channel set to {channel.mention}.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot:
            await self.send_log(message.guild, "Message deleted", f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:1500] or '[empty]'}")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild and not before.author.bot and before.content != after.content:
            await self.send_log(before.guild, "Message edited", f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content[:700]}\n**After:** {after.content[:700]}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_log(member.guild, "Member joined", f"{member.mention} joined the server.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.send_log(member.guild, "Member left", f"**User:** {member} ({member.id})")


async def setup(bot):
    await bot.add_cog(Logging(bot))
