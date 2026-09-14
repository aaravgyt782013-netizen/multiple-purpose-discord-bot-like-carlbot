import random

import discord
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="8ball", description="Ask the magic 8-ball a question.")
    async def eight_ball(self, ctx, *, question: str):
        answers = [
            "It is certain.", "Without a doubt.", "Most likely.", "Ask again later.",
            "Cannot predict that yet.", "Probably not.", "My sources say no.", "Very doubtful."
        ]
        await ctx.send(f"🎱 **Question:** {question}\n**Answer:** {random.choice(answers)}")

    @commands.hybrid_command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, ctx):
        await ctx.send(f"🪙 **{random.choice(('Heads', 'Tails'))}!**")

    @commands.hybrid_command(name="dice", description="Roll a die.")
    async def dice(self, ctx, sides: commands.Range[int, 2, 100] = 6):
        await ctx.send(f"🎲 You rolled **{random.randint(1, sides)}** / {sides}.")

    @commands.hybrid_command(name="choose", description="Choose randomly between options separated by |.")
    async def choose(self, ctx, *, options: str):
        choices = [x.strip() for x in options.split("|") if x.strip()]
        if len(choices) < 2:
            return await ctx.send("Give me at least two options separated by `|`.")
        await ctx.send(f"🎯 I choose **{random.choice(choices)}**!")

    @commands.hybrid_command(name="randomnumber", description="Generate a random number.")
    async def randomnumber(self, ctx, minimum: int = 1, maximum: int = 100):
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        await ctx.send(f"🔢 Random number: **{random.randint(minimum, maximum)}**")

    @commands.hybrid_command(name="meme", description="Fetch a random meme from Reddit's public JSON endpoint.")
    async def meme(self, ctx):
        await ctx.defer()
        import urllib.request
        import json
        request = urllib.request.Request(
            "https://www.reddit.com/r/memes/random.json",
            headers={"User-Agent": "LightCore/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            post = payload[0]["data"]["children"][0]["data"]
            if post.get("over_18"):
                return await ctx.send("I skipped an age-restricted meme.")
            embed = discord.Embed(title=post.get("title", "Random meme"), url="https://www.reddit.com" + post.get("permalink", ""))
            embed.set_image(url=post.get("url"))
            embed.set_footer(text="LightCore • Random Meme")
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send("I couldn't fetch a meme right now. Try again in a moment.")


async def setup(bot):
    await bot.add_cog(Fun(bot))
