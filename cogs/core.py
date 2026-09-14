import math
import os
import discord
from discord.ext import commands

# Human-friendly help categories. The cog names below are matched against the
# actual loaded cog names, so every registered command has a home in .help.
CATEGORIES = [
    ("Moderation", "🛡️", {"Moderation", "AutoMod"}),
    ("Levels", "⭐", {"Leveling"}),
    ("Tickets", "🎫", {"Tickets", "TicketPlus"}),
    ("Roles", "🏷️", {"Roles"}),
    ("Economy", "🪙", {"Currency"}),
    ("Music", "🎵", {"Music"}),
    ("Fun", "🎉", {"Fun"}),
    ("Games", "🎮", {"Games"}),
    ("Server", "🖥️", {"ServerInfo", "MemberStats", "Welcome", "Logging"}),
    ("Activity", "📊", {"ActivityStats", "Status"}),
    ("Giveaways", "🎁", {"Giveaways", "GiveawayPlus"}),
    ("Applications", "📝", {"ApplicationCog", "Applications"}),
    ("Custom Commands", "⚙️", {"CustomCommands"}),
    ("Configuration", "🔧", {"Admin", "Panels", "Embeds"}),
    ("Temp Voice", "🔊", {"TempVoice"}),
    ("Utility", "🧰", {"Utility"}),
    ("Core", "💠", {"Core"}),
]

COMMAND_PERMISSIONS = {
    "ban": "Ban Members", "kick": "Kick Members", "mute": "Moderate Members", "warn": "Moderate Members",
    "purge": "Manage Messages", "warnings": "Moderate Members", "automod": "Manage Server", "setlog": "Manage Server",
    "levelconfig": "Manage Server", "levelconfig rate": "Manage Server", "levelconfig cooldown": "Manage Server",
    "levelconfig message": "Manage Server", "levelconfig reward": "Manage Server", "levelconfig enable": "Manage Server",
    "ticketsetup": "Manage Channels", "ticketcategory": "Manage Channels", "ticketcategory list": "Manage Channels",
    "ticketcategory add": "Manage Channels", "ticketcategory delete": "Manage Channels",
    "selfrole": "Manage Roles", "shopadd": "Manage Server", "shopremove": "Manage Server",
    "giveaway": "Manage Server", "giveawaybonus": "Manage Server", "giveawaypick": "Manage Server",
    "customadd": "Manage Server", "customremove": "Manage Server", "embed": "Manage Messages", "announce": "Manage Messages",
    "panel": "Manage Server", "setwelcome": "Manage Server", "setgoodbye": "Manage Server", "tempvoice": "Manage Channels",
    "tempvoice setup": "Manage Channels", "tempvoice_disable": "Manage Channels", "adminpanel": "Manage Server",
    "memberstats": "Manage Server", "growth": "Manage Server", "retention": "Manage Server", "applicationcreate": "Manage Server",
    "applicationpanel": "Manage Server", "applicationreviewchannel": "Manage Server", "applications": "Manage Server",
}


def logo_url(bot):
    return os.getenv("LIGHTCORE_LOGO_URL") or (bot.user.display_avatar.url if bot.user else None)


def get_help_categories(bot):
    """Return configured categories plus a safe fallback for any new cog.

    This prevents newly added cogs/commands from silently disappearing from
    .help just because a developer forgot to update the category list.
    """
    loaded_cogs = {cog.__class__.__name__ for cog in bot.cogs.values()}
    categories = list(CATEGORIES)
    assigned = set()
    for _, _, cog_names in categories:
        assigned.update(cog_names)

    # Keep the normal UI stable, but automatically expose any future cog.
    unknown = sorted(loaded_cogs - assigned)
    if unknown:
        categories.append(("Other", "📦", set(unknown)))
    return categories


class HelpView(discord.ui.View):
    def __init__(self, bot, author_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.category = None
        self.page = 0
        self.message = None
        self.rebuild()

    @property
    def categories(self):
        return get_help_categories(self.bot)

    def category_map(self):
        return {name: (emoji, cogs) for name, emoji, cogs in self.categories}

    def rebuild(self):
        self.clear_items()
        options = [discord.SelectOption(label="Home", value="__home__", emoji="🏠", description="Return to LightCore home")]
        for name, emoji, _ in self.categories:
            options.append(discord.SelectOption(label=name, value=name, emoji=emoji, description=f"View {name} commands"))
        select = discord.ui.Select(placeholder="Choose a help category…", options=options[:25])
        select.callback = self.select_callback
        self.add_item(select)

        home = discord.ui.Button(label="Home", emoji="🏠", style=discord.ButtonStyle.secondary)
        home.callback = self.home_callback
        self.add_item(home)

        if self.category:
            pages = max(1, math.ceil(len(self.entries()) / 8))
            if pages > 1:
                back = discord.ui.Button(label="Back", emoji="◀️", style=discord.ButtonStyle.primary, disabled=self.page <= 0)
                nxt = discord.ui.Button(label="Next", emoji="▶️", style=discord.ButtonStyle.primary, disabled=self.page >= pages - 1)
                back.callback = self.back_callback
                nxt.callback = self.next_callback
                self.add_item(back)
                self.add_item(nxt)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This help menu belongs to the user who opened it.", ephemeral=True)
            return False
        return True

    def entries(self):
        if not self.category:
            return []
        category_map = self.category_map()
        if self.category not in category_map:
            return []
        cogs = category_map[self.category][1]
        return sorted(
            [
                command
                for command in self.bot.walk_commands()
                if not command.hidden and (command.cog_name or "Core") in cogs
            ],
            key=lambda command: command.qualified_name.lower(),
        )

    def total_visible_commands(self):
        return len([command for command in self.bot.walk_commands() if not command.hidden])

    @staticmethod
    def syntax(command):
        base = f".{command.qualified_name}"
        signature = command.signature.strip()
        if signature:
            base += f" {signature}"
        aliases = getattr(command, "aliases", [])
        if aliases:
            return f"{base}  •  aliases: {', '.join('.' + alias for alias in aliases)}"
        return base

    @staticmethod
    def permission_note(command):
        permission = COMMAND_PERMISSIONS.get(command.qualified_name.lower())
        return f" • Requires: **{permission}**" if permission else ""

    def brand(self, embed):
        url = logo_url(self.bot)
        if url:
            embed.set_author(name="LightCore", icon_url=url)
            embed.set_thumbnail(url=url)
        return embed

    def home_embed(self):
        embed = discord.Embed(
            title="LightCore • Help",
            description="Select a category to browse **every visible registered command**, with syntax, aliases, descriptions and permission notes.",
            color=discord.Color.blurple(),
        )
        self.brand(embed)
        embed.add_field(
            name="📖 Usage",
            value=(
                "Use `.help` to open this interactive menu. Commands are collected directly from the loaded bot registry, "
                "so newly added commands automatically appear in their matching category."
            ),
            inline=False,
        )
        embed.add_field(name="📊 Command Count", value=f"**{self.total_visible_commands()}** visible commands registered", inline=False)
        for name, emoji, cogs in self.categories:
            count = sum(
                1
                for command in self.bot.walk_commands()
                if not command.hidden and (command.cog_name or "Core") in cogs
            )
            embed.add_field(name=f"{emoji} {name}", value=f"**{count}** commands • use the dropdown", inline=True)
        embed.set_footer(text="LightCore • Interactive Help • Every visible command • Expires after 3 minutes")
        return embed

    def category_embed(self):
        category_map = self.category_map()
        emoji = category_map[self.category][0]
        entries = self.entries()
        pages = max(1, math.ceil(len(entries) / 8))
        self.page = max(0, min(self.page, pages - 1))
        current = entries[self.page * 8:(self.page + 1) * 8]
        embed = discord.Embed(title=f"{emoji} LightCore • {self.category}", color=discord.Color.blurple())
        self.brand(embed)
        for command in current:
            description = (command.description or "No description provided.").replace("\n", " ")
            embed.add_field(name=f"`{self.syntax(command)}`", value=description + self.permission_note(command), inline=False)
        if not current:
            embed.description = "No visible commands are registered in this category yet."
        embed.set_footer(text=f"Page {self.page + 1}/{pages} • {len(entries)} commands in this category • LightCore")
        return embed

    async def select_callback(self, interaction):
        value = interaction.data.get("values", ["__home__"])[0]
        self.category = None if value == "__home__" else value
        self.page = 0
        self.rebuild()
        await interaction.response.edit_message(embed=self.home_embed() if not self.category else self.category_embed(), view=self)

    async def home_callback(self, interaction):
        self.category = None
        self.page = 0
        self.rebuild()
        await interaction.response.edit_message(embed=self.home_embed(), view=self)

    async def back_callback(self, interaction):
        self.page = max(0, self.page - 1)
        self.rebuild()
        await interaction.response.edit_message(embed=self.category_embed(), view=self)

    async def next_callback(self, interaction):
        pages = max(1, math.ceil(len(self.entries()) / 8))
        self.page = min(pages - 1, self.page + 1)
        self.rebuild()
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

    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx):
        """Open the interactive LightCore help menu."""
        view = HelpView(self.bot, ctx.author.id)
        try:
            view.message = await ctx.send(embed=view.home_embed(), view=view)
        except discord.Forbidden:
            await ctx.send("🌐 **LightCore Help**\nUse `.help` to open the interactive help menu.\nIf the embed does not appear, give LightCore the **Embed Links** permission.")

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.send(f"LightCore latency: {round(self.bot.latency * 1000)}ms")

    @commands.command(name="about")
    async def about(self, ctx):
        embed = self.brand(discord.Embed(title="💠 LightCore", description="All-in-one Discord moderation, community, leveling, tickets, music and utility bot.", color=discord.Color.blurple()))
        links = []
        support_url = os.getenv("SUPPORT_SERVER_URL")
        if support_url:
            links.append(f"[Support Server]({support_url})")
        for label, key in (("Privacy Policy", "PRIVACY_POLICY_URL"), ("Terms of Service", "TERMS_URL"), ("Invite LightCore", "INVITE_URL")):
            if os.getenv(key):
                links.append(f"[{label}]({os.getenv(key)})")
        embed.add_field(name="🔗 Public links", value=" • ".join(links) if links else "Public links are not configured yet.", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Core(bot))
