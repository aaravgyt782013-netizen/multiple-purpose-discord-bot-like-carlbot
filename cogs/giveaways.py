import discord
from discord.ext import commands

from database import connect


class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        with connect() as db:
            row = db.execute(
                "SELECT status, winner_id FROM giveaways WHERE id=?",
                (self.giveaway_id,),
            ).fetchone()
            if not row or row["status"] != "active":
                return await interaction.response.send_message("This giveaway is no longer active.", ephemeral=True)
            try:
                db.execute(
                    "INSERT INTO giveaway_entries(giveaway_id,user_id) VALUES(?,?)",
                    (self.giveaway_id, interaction.user.id),
                )
            except Exception:
                return await interaction.response.send_message("You already claimed this giveaway.", ephemeral=True)
            db.execute(
                "UPDATE giveaways SET status='ended', winner_id=?, ended_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'",
                (interaction.user.id, self.giveaway_id),
            )
            updated = db.execute("SELECT status,winner_id FROM giveaways WHERE id=?", (self.giveaway_id,)).fetchone()

        if updated["winner_id"] != interaction.user.id:
            return await interaction.response.send_message("Someone else claimed this giveaway first.", ephemeral=True)
        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("🎉 You won the giveaway! Please follow the organizer's instructions.")


class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        with connect() as db:
            rows = db.execute(
                "SELECT id, channel_id, message_id FROM giveaways WHERE status='active'"
            ).fetchall()
        for row in rows:
            self.bot.add_view(GiveawayView(row["id"]), message_id=row["message_id"])

    @commands.hybrid_command(name="giveaway", description="Create a persistent claim-based giveaway.")
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx, *, prize: str):
        embed = discord.Embed(
            title="🎉 LightCore Giveaway",
            description=f"**Prize:** {prize}\n\nBe the first eligible member to claim it.",
            color=discord.Color.gold(),
        )
        embed.set_footer(text="LightCore • Persistent giveaway")
        message = await ctx.send(embed=embed, view=GiveawayView(0))
        with connect() as db:
            cursor = db.execute(
                "INSERT INTO giveaways(guild_id,channel_id,message_id,prize,status) VALUES(?,?,?,?,'active')",
                (ctx.guild.id, ctx.channel.id, message.id, prize),
            )
            giveaway_id = cursor.lastrowid
        view = GiveawayView(giveaway_id)
        await message.edit(view=view)
        self.bot.add_view(view, message_id=message.id)
        await ctx.send(f"✅ Giveaway #{giveaway_id} created.")


async def setup(bot):
    await bot.add_cog(Giveaways(bot))
