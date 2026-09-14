import math

import discord
from discord.ext import commands


CATEGORIES = [
    ("Moderation", "🛡️", {"Moderation", "AutoMod"}),
    ("Levels", "⭐", {"Leveling"}),
    ("Tickets", "🎫", {"Tickets"}),
    ("Roles", "🏷️", {"Roles"}),
    ("Economy", "🪙", {"Currency"}),
    ("Music", "🎵", {"Music"}),
    ("Fun", "🎉", {"Fun"}),
    ("Games", "🎮", {"Games"}),
    ("Server", "🖥️", {"ServerInfo", "MemberStats", "Welcome", "Logging"}),
    ("Giveaways", "🎁", {"Giveaways"}),
    ("Applications", "📝", {"ApplicationCog"}),
    ("Custom Commands", "⚙️", {"CustomCommands"}),
    ("Configuration", "🔧", {"Admin", "Panels", "Embeds"}),
    ("Temp Voice", "🔊", {"TempVoice"}),
    ("Core", "💠", {"Core"}),
]

CATEGORY_MAP = {name: (emoji, cogs) for name, emoji, cogs in CATEGORIES}


class HelpView(discord.ui.View):
    def __init__(self, bot, author_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.category = None
        self.page = 0
        self.message = None
        self._rebuild_components()

    def _rebuild_components(self):
        self.clear_items()
        options = [discord.SelectOption(label="Home", value="__home__", emoji="🏠", description="Return to the LightCore home")]
        options += [
            discord.SelectOption(label=name, value=name, emoji=emoji, description=f"View {name} commands")
            for name, emoji, _ in CATEGORIES
        ]
        select = discord.ui.Select(placeholder="Choose a help category…", min_values=1, max_values=1, options=options, row=0)
        select.callback = self._select_callback
        self.add_item(select)

        home = discord.ui.Button(label="Home", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)
        home.callback = self._home_callback
        self.add_item(home)

        if self.category:
            pages = max(1, math.ceil(len(self._entries()) / 8))
            if pages > 1:
                back = discord.ui.Button(label="Back", emoji="◀️", style=discord.ButtonStyle.primary, row=1, disabled=self.page <= 0)
                nxt = discord.ui.Button(label="Next", emoji="▶️", style=discord.ButtonStyle.primary, row=1, disabled=self.page >= pages - 1)
                back.callback = self._back_callback
                nxt.callback = self._next_callback
                self.add_item(back)
                self.add_item(nxt)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This help menu belongs to the user who opened it.", ephemeral=True)
            return False
        return True

    def _commands(self):
        return [c for c in self.bot.walk_commands() if not c.hidden]

    def _entries(self):
        if not self.category:
            return []
        _, cog_names = CATEGORY_MAP[self.category]
        entries = [c for c in self._commands() if (c.cog_name or "Core") in cog_names]
        return sorted(entries, key=lambda c: c.qualified_name.lower())

    @staticmethod
    def _syntax(command):
        signature = command.signature.strip()
        return f".{command.qualified_name}{(' ' + signature) if signature else ''}"

    @staticmethod
    def _description(command):
        return (command.description or "No description provided.").strip().replace("\n", " ")

    def home_embed(self):
        embed = discord.Embed(
            title="LightCore • Help",
            description="Welcome to LightCore! Select a category below to browse commands, syntax, and descriptions.",
            color=discord.Color.blurple(),
        )
        if self.bot.user:
            embed.set_author(name="LightCore", icon_url=self.bot.user.display_avatar.url)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="📖 How to use", value="Use the dropdown to explore commands. Every command works with `.` or its Discord slash-command equivalent.", inline=False)
        for name, emoji, _ in CATEGORIES:
            embed.add_field(name=f"{emoji} {name}", value="Select from the menu below.", inline=True)
        embed.set_footer(text="LightCore • Interactive Help • Expires after 3 minutes")
        return embed

    def category_embed(self):
        emoji, _ = CATEGORY_MAP[self.category]
        entries = self._entries()
        pages = max(1, math.ceil(len(entries) / 8))
        self.page = max(0, min(self.page, pages - 1))
        current = entries[self.page * 8:(self.page + 1) * 8]
        embed = discord.Embed(title=f"{emoji} LightCore • {self.category}", description="Commands in this category:", color=discord.Color.blurple())
        if self.bot.user:
            embed.set_author(name="LightCore", icon_url=self.bot.user.display_avatar.url)
        if current:
            for command in current:
                embed.add_field(name=f"`{self._syntax(command)}`", value=self._description(command), inline=False)
        else:
            embed.description = "No commands are currently registered in this category."
        embed.set_footer(text=f"Page {self.page + 1}/{pages} • LightCore")
        return embed

    async def _select_callback(self, interaction: discord.Interaction):
        value = interaction.data.get("values", ["__home__"])[0]
        self.category = None if value == "__home__" else value
        self.page = 0
        self._rebuild_components()
        await interaction.response.edit_message(embed=self.home_embed() if not self.category else self.category_embed(), view=self)

    async def _home_callback(self, interaction: discord.Interaction):
        self.category = None
        self.page = 0
        self._rebuild_components()
        await interaction.response.edit_message(embed=self.home_embed(), view=self)

    async def _back_callback(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        self._rebuild_components()
        await interaction.response.edit_message(embed=self.category_embed(), view=self)

    async def _next_callback(self, interaction: discord.Interaction):
        pages = max(1, math.ceil(len(self._entries()) / 8))
        self.page = min(pages - 1, self.page + 1)
        self._rebuild_components()
        await interaction.response.edit_message(embed=self.category_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Open the interactive LightCore help menu.")
    async def help(self, ctx: commands.Context):
        view = HelpView(self.bot, ctx.author.id)
        view.message = await ctx.send(embed=view.home_embed(), view=view)

    @commands.hybrid_command(name="ping", description="Show LightCore latency.")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"🏓 LightCore latency: {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="about", description="Show LightCore version and configuration basics.")
    async def about(self, ctx: commands.Context):
        await ctx.send("**LightCore** • prefix `.`, Python + discord.py 2.7.1")


async def setup(bot):
    await bot.add_cog(Core(bot))
