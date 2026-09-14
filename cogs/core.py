import math
import os
import discord
from discord.ext import commands

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
    ("Giveaways", "🎁", {"Giveaways", "GiveawayPlus"}),
    ("Applications", "📝", {"ApplicationCog"}),
    ("Custom Commands", "⚙️", {"CustomCommands"}),
    ("Configuration", "🔧", {"Admin", "Panels", "Embeds"}),
    ("Temp Voice", "🔊", {"TempVoice"}),
    ("Core", "💠", {"Core"}),
]
CATEGORY_MAP = {name: (emoji, cogs) for name, emoji, cogs in CATEGORIES}


def logo_url(bot):
    return os.getenv("LIGHTCORE_LOGO_URL") or (bot.user.display_avatar.url if bot.user else None)


class HelpView(discord.ui.View):
    def __init__(self, bot, author_id):
        super().__init__(timeout=180)
        self.bot = bot; self.author_id = author_id; self.category = None; self.page = 0; self.message = None
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        options = [discord.SelectOption(label="Home", value="__home__", emoji="🏠", description="Return to LightCore home")]
        options += [discord.SelectOption(label=n, value=n, emoji=e, description=f"View {n} commands") for n, e, _ in CATEGORIES]
        select = discord.ui.Select(placeholder="Choose a help category…", options=options); select.callback = self.select_callback; self.add_item(select)
        home = discord.ui.Button(label="Home", emoji="🏠", style=discord.ButtonStyle.secondary); home.callback = self.home_callback; self.add_item(home)
        if self.category:
            pages = max(1, math.ceil(len(self.entries()) / 8))
            if pages > 1:
                back = discord.ui.Button(label="Back", emoji="◀️", style=discord.ButtonStyle.primary, disabled=self.page <= 0)
                nxt = discord.ui.Button(label="Next", emoji="▶️", style=discord.ButtonStyle.primary, disabled=self.page >= pages - 1)
                back.callback = self.back_callback; nxt.callback = self.next_callback; self.add_item(back); self.add_item(nxt)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This help menu belongs to the user who opened it.", ephemeral=True); return False
        return True

    def entries(self):
        if not self.category: return []
        cogs = CATEGORY_MAP[self.category][1]
        return sorted([c for c in self.bot.walk_commands() if not c.hidden and (c.cog_name or "Core") in cogs], key=lambda c: c.qualified_name.lower())

    @staticmethod
    def syntax(command):
        base = f".{command.qualified_name}{(' ' + command.signature.strip()) if command.signature.strip() else ''}"
        aliases = getattr(command, "aliases", [])
        return f"{base}  •  aliases: {', '.join('.' + a for a in aliases)}" if aliases else base

    def brand(self, embed):
        url = logo_url(self.bot)
        if url:
            embed.set_author(name="LightCore", icon_url=url)
            embed.set_thumbnail(url=url)
        return embed

    def home_embed(self):
        embed = discord.Embed(title="LightCore • Help", description="Select a category to browse commands, syntax, descriptions and short aliases.", color=discord.Color.blurple())
        self.brand(embed)
        embed.add_field(name="📖 Usage", value="Every hybrid command works with `.` and its Discord slash-command equivalent. Short aliases are listed next to commands where available.", inline=False)
        for n, e, _ in CATEGORIES: embed.add_field(name=f"{e} {n}", value="Use the dropdown below.", inline=True)
        embed.set_footer(text="LightCore • Interactive Help • Expires after 3 minutes")
        return embed

    def category_embed(self):
        emoji = CATEGORY_MAP[self.category][0]; entries = self.entries(); pages = max(1, math.ceil(len(entries) / 8)); self.page = max(0, min(self.page, pages - 1))
        current = entries[self.page * 8:(self.page + 1) * 8]
        embed = discord.Embed(title=f"{emoji} LightCore • {self.category}", color=discord.Color.blurple()); self.brand(embed)
        for command in current: embed.add_field(name=f"`{self.syntax(command)}`", value=(command.description or "No description provided.").replace("\n", " "), inline=False)
        if not current: embed.description = "No commands are registered in this category yet."
        embed.set_footer(text=f"Page {self.page + 1}/{pages} • LightCore")
        return embed

    async def select_callback(self, interaction):
        value = interaction.data.get("values", ["__home__"])[0]; self.category = None if value == "__home__" else value; self.page = 0; self.rebuild()
        await interaction.response.edit_message(embed=self.home_embed() if not self.category else self.category_embed(), view=self)

    async def home_callback(self, interaction):
        self.category = None; self.page = 0; self.rebuild(); await interaction.response.edit_message(embed=self.home_embed(), view=self)

    async def back_callback(self, interaction):
        self.page = max(0, self.page - 1); self.rebuild(); await interaction.response.edit_message(embed=self.category_embed(), view=self)

    async def next_callback(self, interaction):
        pages = max(1, math.ceil(len(self.entries()) / 8)); self.page = min(pages - 1, self.page + 1); self.rebuild(); await interaction.response.edit_message(embed=self.category_embed(), view=self)

    async def on_timeout(self):
        for item in self.children: item.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except discord.HTTPException: pass


class Core(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="help", description="Open the interactive LightCore help menu.")
    async def help(self, ctx):
        view = HelpView(self.bot, ctx.author.id); view.message = await ctx.send(embed=view.home_embed(), view=view)

    @commands.hybrid_command(name="ping", description="Show LightCore latency.")
    async def ping(self, ctx): await ctx.send(f"🏓 LightCore latency: {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="about", description="Show LightCore public information and policy links.")
    async def about(self, ctx):
        embed = self.brand(discord.Embed(title="💠 LightCore", description="All-in-one Discord moderation, community, leveling, tickets, music and utility bot.", color=discord.Color.blurple())); links = []
        for label, key in (("Support Server", "SUPPORT_SERVER_URL"), ("Privacy Policy", "PRIVACY_POLICY_URL"), ("Terms of Service", "TERMS_URL"), ("Invite LightCore", "INVITE_URL")):
            if os.getenv(key): links.append(f"[{label}]({os.getenv(key)})")
        embed.add_field(name="🔗 Public links", value=" • ".join(links) if links else "Public links are not configured yet.", inline=False); await ctx.send(embed=embed)

async def setup(bot): await bot.add_cog(Core(bot))
