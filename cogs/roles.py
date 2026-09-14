import discord
from discord.ext import commands
from database import connect

class RoleToggleButton(discord.ui.Button):
    def __init__(self, role_id, label):
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary, custom_id=f"lightcore:selfrole:{role_id}"); self.role_id=role_id
    async def callback(self,interaction):
        role=interaction.guild.get_role(self.role_id)
        if role is None:return await interaction.response.send_message("This role no longer exists.",ephemeral=True)
        if role>=interaction.guild.me.top_role:return await interaction.response.send_message("I cannot manage that role because it is above my highest role.",ephemeral=True)
        try:
            if role in interaction.user.roles:await interaction.user.remove_roles(role,reason="LightCore self-role"); text=f"Removed **{role.name}**."
            else:await interaction.user.add_roles(role,reason="LightCore self-role"); text=f"Added **{role.name}**."
        except discord.HTTPException:text="I couldn't update that role. Check my role permissions."
        await interaction.response.send_message(text,ephemeral=True)
class RoleView(discord.ui.View):
    def __init__(self,role_id,label):super().__init__(timeout=None);self.add_item(RoleToggleButton(role_id,label))

class Roles(commands.Cog):
    def __init__(self,bot):self.bot=bot
    async def cog_load(self):
        with connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS autorole_settings (guild_id INTEGER PRIMARY KEY, role_id INTEGER)")
            rows=db.execute("SELECT role_id,label FROM role_panels").fetchall()
        for row in rows:self.bot.add_view(RoleView(row["role_id"],row["label"]))
    @commands.hybrid_command(name="selfrole",description="Publish a persistent self-role button panel.")
    @commands.has_permissions(manage_roles=True)
    async def selfrole(self,ctx,role:discord.Role):
        if role>=ctx.guild.me.top_role:return await ctx.send("I cannot manage that role because it is above my highest role.")
        label=f"Get {role.name}"; message=await ctx.send(embed=discord.Embed(title="LightCore Self Role",description=f"Click the button below to toggle **{role.name}**.",color=discord.Color.blurple()),view=RoleView(role.id,label))
        with connect() as db:db.execute("INSERT INTO role_panels(guild_id,channel_id,message_id,role_id,label) VALUES(?,?,?,?,?)",(ctx.guild.id,ctx.channel.id,message.id,role.id,label))
        await ctx.send("✅ Self-role panel saved and will survive bot restarts.",ephemeral=True)
    @commands.hybrid_group(name="role",invoke_without_command=True,description="Manage server member roles.")
    async def role(self,ctx):
        if ctx.invoked_subcommand is None:await ctx.send("Use `.role add <user> <role>` or `.role remove <user> <role>`. ")
    @role.command(name="add",description="Add a role to a member.")
    @commands.has_permissions(manage_roles=True)
    async def role_add(self,ctx,member:discord.Member,role:discord.Role):
        if role>=ctx.guild.me.top_role:return await ctx.send("❌ I cannot manage that role because it is at or above my highest role.")
        if role>=ctx.author.top_role and ctx.author != ctx.guild.owner:return await ctx.send("❌ You cannot manage a role at or above your highest role.")
        await member.add_roles(role,reason=f"Manual role add by {ctx.author}"); await ctx.send(f"✅ Added {role.mention} to {member.mention}.")
    @role.command(name="remove",description="Remove a role from a member.")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self,ctx,member:discord.Member,role:discord.Role):
        if role>=ctx.guild.me.top_role:return await ctx.send("❌ I cannot manage that role because it is at or above my highest role.")
        if role>=ctx.author.top_role and ctx.author != ctx.guild.owner:return await ctx.send("❌ You cannot manage a role at or above your highest role.")
        await member.remove_roles(role,reason=f"Manual role removal by {ctx.author}"); await ctx.send(f"✅ Removed {role.mention} from {member.mention}.")
    @commands.hybrid_command(name="autorole",description="Set the role automatically assigned to new members.")
    @commands.has_permissions(manage_guild=True)
    async def autorole(self,ctx,role:discord.Role):
        if role>=ctx.guild.me.top_role:return await ctx.send("❌ I cannot assign that role because it is at or above my highest role.")
        with connect() as db:db.execute("INSERT INTO autorole_settings(guild_id,role_id) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET role_id=excluded.role_id",(ctx.guild.id,role.id))
        await ctx.send(f"✅ Autorole enabled: new members will receive {role.mention} when I can manage it.")
    @commands.Cog.listener()
    async def on_member_join(self,member):
        try:
            with connect() as db:row=db.execute("SELECT role_id FROM autorole_settings WHERE guild_id=?",(member.guild.id,)).fetchone()
            if row:
                role=member.guild.get_role(row["role_id"])
                if role and role<member.guild.me.top_role:await member.add_roles(role,reason="LightCore autorole")
        except Exception:self.bot.logger.exception("Autorole failed for guild %s",member.guild.id) if hasattr(self.bot,"logger") else None

async def setup(bot):await bot.add_cog(Roles(bot))
