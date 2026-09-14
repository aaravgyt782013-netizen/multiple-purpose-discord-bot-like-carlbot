import discord
from discord.ext import commands
from database import get_setting, set_setting


class ToggleView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    async def interaction_check(self, interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server to use this panel.", ephemeral=True)
            return False
        return True

    async def toggle(self, interaction, key, label):
        value = int(not bool(get_setting(self.guild_id, key)))
        set_setting(self.guild_id, key, value)
        await interaction.response.send_message(f"**{label}** is now **{'enabled' if value else 'disabled'}**.", ephemeral=True)

    @discord.ui.button(label="Leveling", style=discord.ButtonStyle.primary, row=0)
    async def leveling(self, interaction, button): await self.toggle(interaction, "level_enabled", "Leveling")

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.primary, row=0)
    async def economy(self, interaction, button): await self.toggle(interaction, "currency_enabled", "Economy")

    @discord.ui.button(label="AutoMod", style=discord.ButtonStyle.secondary, row=0)
    async def automod(self, interaction, button): await self.toggle(interaction, "automod_enabled", "AutoMod")

    @discord.ui.button(label="Member Stats", style=discord.ButtonStyle.secondary, row=0)
    async def stats(self, interaction, button): await self.toggle(interaction, "memberstats_enabled", "Member Stats")


class ChannelModal(discord.ui.Modal, title="LightCore Channel Settings"):
    channel = discord.ui.TextInput(label="Log channel ID (blank to clear)", required=False, max_length=20)
    welcome = discord.ui.TextInput(label="Welcome channel ID (blank to clear)", required=False, max_length=20)
    goodbye = discord.ui.TextInput(label="Goodbye channel ID (blank to clear)", required=False, max_length=20)
    review = discord.ui.TextInput(label="Application review channel ID", required=False, max_length=20)

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
        self.channel.default = str(get_setting(guild_id, "log_channel") or "")
        self.welcome.default = str(get_setting(guild_id, "welcome_channel") or "")
        self.goodbye.default = str(get_setting(guild_id, "goodbye_channel") or "")
        self.review.default = str(get_setting(guild_id, "application_review_channel") or "")

    async def on_submit(self, interaction):
        values = (("log_channel", self.channel.value), ("welcome_channel", self.welcome.value), ("goodbye_channel", self.goodbye.value), ("application_review_channel", self.review.value))
        for key, value in values:
            set_setting(self.guild_id, key, int(value) if value.isdigit() else None)
        await interaction.response.send_message("Channel settings saved.", ephemeral=True)


class AdminSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Core feature toggles", value="toggles", emoji="⚙️"),
            discord.SelectOption(label="Channel settings", value="channels", emoji="📣"),
            discord.SelectOption(label="Leveling settings", value="leveling", emoji="🏆"),
            discord.SelectOption(label="Welcome / Goodbye", value="welcome", emoji="👋"),
            discord.SelectOption(label="Tickets / Roles / Temp Voice", value="community", emoji="🧩"),
            discord.SelectOption(label="Applications", value="applications", emoji="📝"),
        ]
        super().__init__(placeholder="Choose a LightCore settings area…", options=options)

    async def callback(self, interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server.", ephemeral=True)
        if self.values[0] == "toggles":
            return await interaction.response.send_message("Use the buttons below to toggle the major systems.", view=ToggleView(interaction.guild.id), ephemeral=True)
        if self.values[0] == "channels":
            return await interaction.response.send_modal(ChannelModal(interaction.guild.id))
        await interaction.response.send_message(f"**{self.values[0].title()}** settings are managed by their feature panel/commands. This central panel is the single entry point for LightCore configuration.", ephemeral=True)


class AdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(AdminSelect())


class Admin(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="adminpanel", description="Open the central LightCore server settings panel.")
    @commands.has_permissions(manage_guild=True)
    async def adminpanel(self, ctx):
        embed = discord.Embed(title="LightCore • Admin Center", description="Central GUI for server-wide LightCore configuration. Select a category to manage feature settings without editing files.", color=discord.Color.blurple())
        embed.add_field(name="Enabled systems", value="Leveling • Economy • AutoMod • Member Stats")
        embed.add_field(name="Configuration", value="Channels • Welcome/Goodbye • Tickets • Roles • Temp Voice • Applications", inline=False)
        embed.set_footer(text="LightCore • Manage Server required")
        await ctx.send(embed=embed, view=AdminView())


async def setup(bot): await bot.add_cog(Admin(bot))
