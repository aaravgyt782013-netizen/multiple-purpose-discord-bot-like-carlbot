import discord
from discord.ext import commands
from database import get_setting, set_setting


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="lightcore:ticket")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category_id = get_setting(guild.id, "ticket_category")
        category = guild.get_channel(category_id) if category_id else None
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        await channel.send(f"{interaction.user.mention} welcome to your LightCore ticket. Use **.close** when finished.")
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticketpanel")
    @commands.has_permissions(manage_channels=True)
    async def ticketpanel(self, ctx):
        await ctx.send(embed=discord.Embed(title="LightCore Support", description="Press the button to create a private support ticket.", color=discord.Color.blurple()), view=TicketPanel())

    @commands.hybrid_command(name="setticketcategory")
    @commands.has_permissions(manage_guild=True)
    async def setticketcategory(self, ctx, category: discord.CategoryChannel):
        set_setting(ctx.guild.id, "ticket_category", category.id)
        await ctx.send(f"Ticket category set to **{category.name}**.")

    @commands.hybrid_command(name="close")
    async def close(self, ctx):
        if ctx.channel.name.startswith("ticket-"):
            await ctx.send("Closing ticket and preparing its transcript…")
            await ctx.channel.delete(reason=f"LightCore ticket closed by {ctx.author}")
        else:
            await ctx.send("This is not a LightCore ticket channel.")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
