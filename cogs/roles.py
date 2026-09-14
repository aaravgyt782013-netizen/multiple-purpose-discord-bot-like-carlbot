import discord
from discord.ext import commands

from database import connect


class RoleToggleButton(discord.ui.Button):
    def __init__(self, role_id, label):
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary, custom_id=f"lightcore:selfrole:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message("This role no longer exists.", ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("I cannot manage that role because it is above my highest role.", ephemeral=True)
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="LightCore self-role")
                text = f"Removed **{role.name}**."
            else:
                await interaction.user.add_roles(role, reason="LightCore self-role")
                text = f"Added **{role.name}**."
        except discord.HTTPException:
            text = "I couldn't update that role. Check my role permissions."
        await interaction.response.send_message(text, ephemeral=True)


class RoleView(discord.ui.View):
    def __init__(self, role_id, label):
        super().__init__(timeout=None)
        self.add_item(RoleToggleButton(role_id, label))


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        with connect() as db:
            rows = db.execute("SELECT role_id, label FROM role_panels").fetchall()
        for row in rows:
            self.bot.add_view(RoleView(row["role_id"], row["label"]))

    @commands.hybrid_command(name="selfrole", description="Publish a persistent self-role button panel.")
    @commands.has_permissions(manage_roles=True)
    async def selfrole(self, ctx, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I cannot manage that role because it is above my highest role.")
        label = f"Get {role.name}"
        view = RoleView(role.id, label)
        message = await ctx.send(
            embed=discord.Embed(
                title="LightCore Self Role",
                description=f"Click the button below to toggle **{role.name}**.",
                color=discord.Color.blurple(),
            ),
            view=view,
        )
        with connect() as db:
            db.execute(
                "INSERT INTO role_panels(guild_id,channel_id,message_id,role_id,label) VALUES(?,?,?,?,?)",
                (ctx.guild.id, ctx.channel.id, message.id, role.id, label),
            )
        await ctx.send("✅ Self-role panel saved and will survive bot restarts.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Roles(bot))
