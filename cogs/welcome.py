import discord
from discord.ext import commands
from database import get_setting, set_setting


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_message(self, guild, member, setting_channel, setting_message, default):
        channel_id = get_setting(guild.id, setting_channel)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel:
            template = get_setting(guild.id, setting_message) or default
            await channel.send(template.replace('{user}', member.mention).replace('{server}', guild.name))

    @commands.hybrid_command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel, *, message="Welcome {user} to {server}!"):
        set_setting(ctx.guild.id, "welcome_channel", channel.id)
        set_setting(ctx.guild.id, "welcome_message", message)
        await ctx.send(f"Welcome messages enabled in {channel.mention}.")

    @commands.hybrid_command(name="setgoodbye")
    @commands.has_permissions(manage_guild=True)
    async def setgoodbye(self, ctx, channel: discord.TextChannel, *, message="Goodbye {user}!"):
        set_setting(ctx.guild.id, "goodbye_channel", channel.id)
        set_setting(ctx.guild.id, "goodbye_message", message)
        await ctx.send(f"Goodbye messages enabled in {channel.mention}.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_message(member.guild, member, "welcome_channel", "welcome_message", "Welcome {user} to {server}!")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.send_message(member.guild, member, "goodbye_channel", "goodbye_message", "Goodbye {user}!")


async def setup(bot):
    await bot.add_cog(Welcome(bot))
