import discord
from discord.ext import commands
from database import set_setting


class ConfigSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Enable Leveling", value="level_on"),
            discord.SelectOption(label="Disable Leveling", value="level_off"),
            discord.SelectOption(label="Enable Currency", value="currency_on"),
            discord.SelectOption(label="Disable Currency", value="currency_off"),
        ]
        super().__init__(placeholder="Choose a LightCore setting…", options=options)

    async def callback(self, interaction: discord.Interaction):
        mapping = {
            "level_on": ("level_enabled", 1), "level_off": ("level_enabled", 0),
            "currency_on": ("currency_enabled", 1), "currency_off": ("currency_enabled", 0),
        }
        key, value = mapping[self.values[0]]
        set_setting(interaction.guild.id, key, value)
        await interaction.response.send_message(f"Updated **{key}** → **{bool(value)}**.", ephemeral=True)


class ConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ConfigSelect())


class Panels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="panel")
    @commands.has_permissions(manage_guild=True)
    async def panel(self, ctx):
        embed = discord.Embed(title="LightCore Control Panel", description="Configure major server systems using the menu. More controls are added per cog.", color=discord.Color.blurple())
        embed.set_footer(text="LightCore • GUI Configuration")
        await ctx.send(embed=embed, view=ConfigView())


async def setup(bot):
    await bot.add_cog(Panels(bot))
