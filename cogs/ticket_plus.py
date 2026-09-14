import discord
from discord.ext import commands
from database import connect


class TicketPlus(commands.Cog):
    @commands.hybrid_command(name="ticketcategory", description="Set the category label for the current ticket.")
    @commands.has_permissions(manage_channels=True)
    async def ticketcategory(self, ctx, category: str):
        category = category.strip().lower()[:32]
        with connect() as db:
            row = db.execute("SELECT id FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'", (ctx.guild.id, ctx.channel.id)).fetchone()
            if not row:
                return await ctx.send("❌ This is not an open LightCore ticket.")
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row['id'],))
            db.execute("UPDATE ticket_meta SET category=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (category, row['id']))
        await ctx.send(f"🎫 Ticket category set to **{category}**.")


async def setup(bot):
    await bot.add_cog(TicketPlus(bot))
