import discord
from discord.ext import commands


CATEGORIES = {
    "Moderation": {"Moderation", "AutoMod"},
    "Levels": {"Leveling"},
    "Tickets": {"Tickets"},
    "Roles": {"Roles"},
    "Economy": {"Currency"},
    "Music": {"Music"},
    "Fun": {"Fun"},
    "Games": {"Games"},
    "Server": {"ServerInfo", "MemberStats", "Welcome", "Logging"},
    "Giveaways": {"Giveaways"},
    "Applications": {"ApplicationCog"},
    "Custom Commands": {"CustomCommands"},
    "Configuration": {"Admin", "Panels", "Embeds"},
    "Temp Voice": {"TempVoice"},
    "Core": {"Core"},
}


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show all LightCore commands grouped by category.")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="LightCore • Help",
            description="All LightCore commands. Prefix: `.` • Slash commands are also available.",
            color=discord.Color.blurple(),
        )
        grouped = {name: [] for name in CATEGORIES}
        assigned = set()

        for command in self.bot.walk_commands():
            if command.hidden:
                continue
            if isinstance(command, commands.Group) and command.commands:
                # Subcommands are listed separately below.
                continue
            cog_name = command.cog_name or "Core"
            category = next((name for name, cogs in CATEGORIES.items() if cog_name in cogs), "Other")
            grouped.setdefault(category, []).append(command.qualified_name)
            assigned.add(command.qualified_name)

        for category, names in grouped.items():
            if names:
                names.sort()
                embed.add_field(name=category, value="`" + "` • `".join(names) + "`", inline=False)

        other = sorted(
            command.qualified_name
            for command in self.bot.walk_commands()
            if not command.hidden and not isinstance(command, commands.Group) and command.qualified_name not in assigned
        )
        if other:
            embed.add_field(name="Other", value="`" + "` • `".join(other) + "`", inline=False)
        embed.set_footer(text="LightCore • Use /help or .help")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Show LightCore latency.")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"🏓 LightCore latency: {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="about", description="Show LightCore version and configuration basics.")
    async def about(self, ctx: commands.Context):
        await ctx.send("**LightCore** • prefix `.`, Python + discord.py 2.7.1")


async def setup(bot):
    await bot.add_cog(Core(bot))
