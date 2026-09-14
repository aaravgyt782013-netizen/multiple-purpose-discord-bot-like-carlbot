import os
import discord
from discord.ext import commands
from config import SUPPORT_SERVER_URL


class HelpView(discord.ui.View):
    def __init__(self, bot, author_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.message = None

        # Keep the first page useful even when the bot has many cogs.
        for label, emoji in (("Moderation", "🛡️"), ("Utility", "🔧"), ("Fun", "🎮")):
            button = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary)
            button.disabled = True
            self.add_item(button)

    def home_embed(self):
        embed = discord.Embed(
            title="🌐 LightCore Help",
            description=(
                "**All-in-one Discord bot**\n\n"
                "Use the command categories below to explore LightCore.\n"
                "Prefix: `.help`"
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🛡️ Moderation",
            value="Ban • Kick • Mute • Warn • Purge • Automod",
            inline=False,
        )
        embed.add_field(
            name="📊 Community",
            value="Stats • Leveling • Welcome • Roles • Tickets",
            inline=False,
        )
        embed.add_field(
            name="🎵 Music & Fun",
            value="Play • Queue • Skip • Games • Fun commands",
            inline=False,
        )
        embed.set_footer(text="LightCore • Type .help <command> for command details")
        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This help menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx):
        """Show the LightCore help embed reliably."""
        view = HelpView(self.bot, ctx.author.id)
        try:
            view.message = await ctx.send(embed=view.home_embed(), view=view)
        except discord.Forbidden:
            # If Embed Links is missing, don't make `.help` silently fail.
            # Discord can still receive a useful plain-text help response.
            await ctx.send(
                "🌐 **LightCore Help**\n"
                "Use `.help <command>` for details.\n"
                "Moderation • Community • Stats • Leveling • Music • Utility • Fun"
            )

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.send(f"LightCore latency: {round(self.bot.latency * 1000)}ms")

    @commands.command(name="about")
    async def about(self, ctx):
        embed = discord.Embed(
            title="LightCore",
            description="All-in-one Discord moderation, community, leveling, tickets, music and utility bot.",
            color=discord.Color.blurple(),
        )
        links = [f"[Support Server]({SUPPORT_SERVER_URL})"]
        for label, key in (
            ("Privacy Policy", "PRIVACY_POLICY_URL"),
            ("Terms of Service", "TERMS_URL"),
            ("Invite LightCore", "INVITE_URL"),
        ):
            if os.getenv(key):
                links.append(f"[{label}]({os.getenv(key)})")
        embed.add_field(name="Public links", value=" | ".join(links), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Core(bot))
