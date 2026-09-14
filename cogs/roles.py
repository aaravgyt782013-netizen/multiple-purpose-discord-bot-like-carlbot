import discord
from discord.ext import commands


class RoleView(discord.ui.View):
    def __init__(self, role: discord.Role):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Toggle Role", style=discord.ButtonStyle.secondary, custom_id="lightcore:role_toggle")
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.role in interaction.user.roles:
            await interaction.user.remove_roles(self.role)
            await interaction.response.send_message(f"Removed **{self.role.name}**.", ephemeral=True)
        else:
            await interaction.user.add_roles(self.role)
            await interaction.response.send_message(f"Added **{self.role.name}**.", ephemeral=True)


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="selfrole")
    @commands.has_permissions(manage_roles=True)
    async def selfrole(self, ctx, role: discord.Role):
        await ctx.send(embed=discord.Embed(title="LightCore Self Role", description=f"Toggle **{role.name}** with the button below.", color=discord.Color.blurple()), view=RoleView(role))


async def setup(bot):
    await bot.add_cog(Roles(bot))
