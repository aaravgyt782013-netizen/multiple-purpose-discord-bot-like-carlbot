import discord
from discord.ext import commands
from database import connect


class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def ensure(self, guild_id, user_id):
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (guild_id, user_id))

    @commands.hybrid_command(name="balance")
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        self.ensure(ctx.guild.id, member.id)
        with connect() as db:
            row = db.execute("SELECT balance FROM balances WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()
        await ctx.send(f"💰 **{member.display_name}** has **{row['balance']}** LightCoins.")

    @commands.hybrid_command(name="daily")
    async def daily(self, ctx):
        self.ensure(ctx.guild.id, ctx.author.id)
        with connect() as db:
            db.execute("UPDATE balances SET balance=balance+100 WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id))
        await ctx.send("💰 You received 100 LightCoins.")

    @commands.hybrid_command(name="pay")
    async def pay(self, ctx, member: discord.Member, amount: int):
        if member.bot or member.id == ctx.author.id or amount <= 0:
            return await ctx.send("Choose another member and a positive amount.")
        self.ensure(ctx.guild.id, ctx.author.id); self.ensure(ctx.guild.id, member.id)
        with connect() as db:
            sender = db.execute("SELECT balance FROM balances WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()['balance']
            if sender < amount:
                return await ctx.send("You don't have enough LightCoins.")
            db.execute("UPDATE balances SET balance=balance-? WHERE guild_id=? AND user_id=?", (amount, ctx.guild.id, ctx.author.id))
            db.execute("UPDATE balances SET balance=balance+? WHERE guild_id=? AND user_id=?", (amount, ctx.guild.id, member.id))
        await ctx.send(f"💸 Sent **{amount}** LightCoins to {member.mention}.")

    @commands.hybrid_command(name="rich")
    async def rich(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT user_id,balance FROM balances WHERE guild_id=? ORDER BY balance DESC LIMIT 10", (ctx.guild.id,)).fetchall()
        text = "\n".join(f"**{i}.** <@{r['user_id']}> — {r['balance']} LightCoins" for i, r in enumerate(rows, 1)) or "No balances yet."
        await ctx.send(embed=discord.Embed(title="LightCore Wealth Leaderboard", description=text, color=discord.Color.gold()))

    @commands.hybrid_command(name="shop")
    async def shop(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT name,price,description FROM shop_items WHERE guild_id=?", (ctx.guild.id,)).fetchall()
        text = "\n".join(f"**{r['name']}** — {r['price']} LightCoins — {r['description'] or ''}" for r in rows) or "The shop is empty. Admins can add items through the GUI panel."
        await ctx.send(embed=discord.Embed(title="LightCore Shop", description=text, color=discord.Color.blurple()))


async def setup(bot):
    await bot.add_cog(Currency(bot))
