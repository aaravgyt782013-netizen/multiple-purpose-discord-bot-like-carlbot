import discord
from discord.ext import commands

from database import connect, get_setting, set_setting


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="lightcore:ticket_create")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category_id = get_setting(guild.id, "ticket_category")
        category = guild.get_channel(category_id) if category_id else None
        existing = None
        with connect() as db:
            row = db.execute(
                "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND status='open'",
                (guild.id, interaction.user.id),
            ).fetchone()
        if row:
            existing = guild.get_channel(row["channel_id"])
        if existing:
            return await interaction.response.send_message(f"You already have an open ticket: {existing.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}", category=category, overwrites=overwrites
        )
        with connect() as db:
            db.execute(
                "INSERT INTO tickets(guild_id,channel_id,user_id,status) VALUES(?,?,?,'open')",
                (guild.id, channel.id, interaction.user.id),
            )
        await channel.send(f"{interaction.user.mention} welcome to your LightCore ticket. Use **.close** when finished.")
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanel())

    @commands.hybrid_command(name="ticketpanel", description="Publish the LightCore ticket panel.")
    @commands.has_permissions(manage_channels=True)
    async def ticketpanel(self, ctx):
        await ctx.send(
            embed=discord.Embed(
                title="LightCore Support",
                description="Press the button to create a private support ticket.",
                color=discord.Color.blurple(),
            ),
            view=TicketPanel(),
        )

    @commands.hybrid_command(name="setticketcategory", description="Set the category used for new tickets.")
    @commands.has_permissions(manage_guild=True)
    async def setticketcategory(self, ctx, category: discord.CategoryChannel):
        set_setting(ctx.guild.id, "ticket_category", category.id)
        await ctx.send(f"Ticket category set to **{category.name}**.")

    @commands.hybrid_command(name="setticketlog", description="Set the ticket transcript log channel.")
    @commands.has_permissions(manage_guild=True)
    async def setticketlog(self, ctx, channel: discord.TextChannel):
        set_setting(ctx.guild.id, "ticket_log_channel", channel.id)
        await ctx.send(f"Ticket transcript channel set to {channel.mention}.")

    @commands.hybrid_command(name="close", description="Close the current LightCore ticket and save its transcript.")
    async def close(self, ctx):
        with connect() as db:
            row = db.execute(
                "SELECT id FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'",
                (ctx.guild.id, ctx.channel.id),
            ).fetchone()
        if not row:
            return await ctx.send("This is not an open LightCore ticket channel.")

        lines = []
        try:
            async for message in ctx.channel.history(limit=500, oldest_first=True):
                stamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                content = message.content.replace("\n", " ")
                lines.append(f"[{stamp}] {message.author} ({message.author.id}): {content}")
        except discord.HTTPException:
            pass
        transcript = "\n".join(lines) or "No messages captured."
        with connect() as db:
            db.execute("UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
            db.execute("INSERT INTO ticket_transcripts(ticket_id,transcript) VALUES(?,?)", (row["id"], transcript[:50000]))

        log_id = get_setting(ctx.guild.id, "ticket_log_channel")
        log_channel = ctx.guild.get_channel(log_id) if log_id else None
        if log_channel:
            preview = transcript[:3800]
            await log_channel.send(
                embed=discord.Embed(
                    title=f"LightCore Ticket #{row['id']} Closed",
                    description=f"```text\n{preview}\n```",
                    color=discord.Color.blurple(),
                )
            )
        await ctx.send("Closing ticket and saving its transcript…")
        await ctx.channel.delete(reason=f"LightCore ticket closed by {ctx.author}")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
