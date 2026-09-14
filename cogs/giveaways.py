import discord
from discord.ext import commands


class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed = False

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="lightcore:giveaway_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            return await interaction.response.send_message("This giveaway has already been claimed.", ephemeral=True)
        self.claimed = True
        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("🎉 You claimed the giveaway! Please follow the organizer's instructions.")


class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="giveaway")
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx, *, prize: str):
        embed = discord.Embed(title="🎉 LightCore Giveaway", description=f"**Prize:** {prize}\n\nBe the first eligible member to claim it.", color=discord.Color.gold())
        embed.set_footer(text="LightCore • Organizer-selected/claim-based giveaway")
        await ctx.send(embed=embed, view=GiveawayView())


async def setup(bot):
    await bot.add_cog(Giveaways(bot))
