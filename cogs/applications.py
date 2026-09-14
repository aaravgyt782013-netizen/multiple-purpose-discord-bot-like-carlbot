import json

import discord
from discord.ext import commands
from database import connect, get_setting, set_setting


class ApplicationModal(discord.ui.Modal):
    def __init__(self, application_id, form_name, questions):
        super().__init__(title=form_name[:45])
        self.application_id = application_id
        self.form_name = form_name
        self.questions = questions
        for index, question in enumerate(questions[:5]):
            self.add_item(discord.ui.TextInput(label=question[:45], style=discord.TextStyle.paragraph, required=True, max_length=1000, custom_id=f"q{index}"))

    async def on_submit(self, interaction):
        answers = {question: self.children[index].value for index, question in enumerate(self.questions[:5])}
        with connect() as db:
            cursor = db.execute("INSERT INTO application_submissions (application_id,guild_id,user_id,answers) VALUES (?,?,?,?)", (self.application_id, interaction.guild.id, interaction.user.id, json.dumps(answers)))
            submission_id = cursor.lastrowid
        review_id = get_setting(interaction.guild.id, "application_review_channel")
        channel = interaction.guild.get_channel(review_id) if review_id else None
        if channel is None:
            with connect() as db:
                row = db.execute("SELECT review_channel FROM applications WHERE id=?", (self.application_id,)).fetchone()
            channel = interaction.guild.get_channel(row[0]) if row and row[0] else None
        if channel is None:
            return await interaction.response.send_message("Your application was saved, but the review channel is not configured. Tell server staff.", ephemeral=True)
        embed = discord.Embed(title=f"New Application • {self.form_name}", description=f"Applicant: {interaction.user.mention}\nSubmission ID: `{submission_id}`", color=discord.Color.blurple())
        for question, answer in answers.items(): embed.add_field(name=question, value=answer[:1024], inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await channel.send(embed=embed, view=ReviewView(submission_id, interaction.user.id))
        await interaction.response.send_message("✅ Your application has been submitted for review.", ephemeral=True)


class ReviewView(discord.ui.View):
    def __init__(self, submission_id, applicant_id):
        super().__init__(timeout=None)
        self.submission_id = submission_id
        self.applicant_id = applicant_id

    async def review(self, interaction, status):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Only server staff can review applications.", ephemeral=True)
        with connect() as db:
            row = db.execute("SELECT status FROM application_submissions WHERE id=?", (self.submission_id,)).fetchone()
            if not row or row[0] != "pending":
                return await interaction.response.send_message("This application has already been reviewed.", ephemeral=True)
            db.execute("UPDATE application_submissions SET status=?, reviewer_id=? WHERE id=?", (status, interaction.user.id, self.submission_id))
        for child in self.children: child.disabled = True
        label = "Accepted" if status == "accepted" else "Denied"
        await interaction.response.edit_message(content=f"**{label}** by {interaction.user.mention}", view=self)
        member = interaction.guild.get_member(self.applicant_id)
        if member:
            try: await member.send(f"Your **LightCore application** (#{self.submission_id}) was **{status}** in {interaction.guild.name}.")
            except discord.HTTPException: pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button): await self.review(interaction, "accepted")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction, button): await self.review(interaction, "denied")


class ApplicationCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="applicationcreate", description="Create an application form. Questions are separated by |.")
    @commands.has_permissions(manage_guild=True)
    async def applicationcreate(self, ctx, name: str, *, questions: str):
        items = [q.strip() for q in questions.split("|") if q.strip()][:5]
        if not items: return await ctx.send("Add at least one question.")
        review = get_setting(ctx.guild.id, "application_review_channel")
        with connect() as db:
            cursor = db.execute("INSERT INTO applications (guild_id,form_name,questions,review_channel) VALUES (?,?,?,?)", (ctx.guild.id, name[:80], json.dumps(items), review))
            app_id = cursor.lastrowid
        await ctx.send(f"✅ Created application **{name}** (ID `{app_id}`). Use `.applicationpanel {app_id}` to publish it.")

    @commands.hybrid_command(name="applicationpanel", description="Publish an application form button.")
    @commands.has_permissions(manage_guild=True)
    async def applicationpanel(self, ctx, application_id: int):
        with connect() as db:
            row = db.execute("SELECT form_name,questions,enabled FROM applications WHERE id=? AND guild_id=?", (application_id, ctx.guild.id)).fetchone()
        if not row: return await ctx.send("Application not found.")
        if not row[2]: return await ctx.send("That application is disabled.")
        questions = json.loads(row[1])
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(label=f"Apply • {row[0][:70]}", style=discord.ButtonStyle.primary)
        async def callback(interaction):
            await interaction.response.send_modal(ApplicationModal(application_id, row[0], questions))
        button.callback = callback
        view.add_item(button)
        embed = discord.Embed(title=f"📝 {row[0]}", description="Click the button below to open the application form.", color=discord.Color.blurple())
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="applicationreviewchannel", description="Set the application review channel by ID.")
    @commands.has_permissions(manage_guild=True)
    async def applicationreviewchannel(self, ctx, channel: discord.TextChannel):
        set_setting(ctx.guild.id, "application_review_channel", channel.id)
        await ctx.send(f"Application review channel set to {channel.mention}.")

    @commands.hybrid_command(name="applications", description="List configured application forms.")
    @commands.has_permissions(manage_guild=True)
    async def applications(self, ctx):
        with connect() as db: rows = db.execute("SELECT id,form_name,enabled FROM applications WHERE guild_id=? ORDER BY id DESC", (ctx.guild.id,)).fetchall()
        text = "\n".join(f"`{r[0]}` • {r[1]} • {'enabled' if r[2] else 'disabled'}" for r in rows) or "No applications configured."
        await ctx.send(embed=discord.Embed(title="LightCore Applications", description=text, color=discord.Color.blurple()))


async def setup(bot): await bot.add_cog(ApplicationCog(bot))
