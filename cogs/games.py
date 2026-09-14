import asyncio
import random

import discord
from discord.ext import commands


class RPSView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.choices = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This game belongs to someone else.", ephemeral=True)
            return False
        return True

    async def finish(self, interaction, choice):
        bot_choice = random.choice(list(self.choices))
        if choice == bot_choice:
            result = "It's a draw!"
        elif (choice, bot_choice) in (("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")):
            result = "You win!"
        else:
            result = "I win!"
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"You chose {self.choices[choice]} **{choice}**. I chose {self.choices[bot_choice]} **{bot_choice}**.\n\n**{result}**", view=self)
        self.stop()

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction, button): await self.finish(interaction, "rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.primary)
    async def paper(self, interaction, button): await self.finish(interaction, "paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.success)
    async def scissors(self, interaction, button): await self.finish(interaction, "scissors")


class TicTacToeView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=180)
        self.author = author
        self.board = [" "] * 9
        self.turn = "X"
        self.message = None
        self._sync_labels()

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This game belongs to someone else.", ephemeral=True)
            return False
        if self.turn != "X":
            await interaction.response.send_message("Wait for my move.", ephemeral=True)
            return False
        return True

    def _sync_labels(self):
        for i, button in enumerate(self.children):
            if i < 9:
                button.label = self.board[i] if self.board[i] != " " else str(i + 1)

    def _winner(self):
        for a, b, c in ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)):
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]: return self.board[a]
        return "draw" if all(x != " " for x in self.board) else None

    def _bot_move(self):
        empty = [i for i, value in enumerate(self.board) if value == " "]
        if empty: self.board[random.choice(empty)] = "O"

    async def play(self, interaction, index):
        self.board[index] = "X"
        result = self._winner()
        if result is None:
            self._bot_move()
            result = self._winner()
        if result:
            text = "🎉 You win!" if result == "X" else "🤖 I win!" if result == "O" else "🤝 Draw!"
            for child in self.children: child.disabled = True
            self._sync_labels()
            await interaction.response.edit_message(content=text, view=self)
            self.stop()
        else:
            self._sync_labels()
            await interaction.response.edit_message(content="Your turn — **X**", view=self)

    @discord.ui.button(label="1", row=0, style=discord.ButtonStyle.secondary)
    async def b1(self, i, b): await self._cell(i, 0)
    @discord.ui.button(label="2", row=0, style=discord.ButtonStyle.secondary)
    async def b2(self, i, b): await self._cell(i, 1)
    @discord.ui.button(label="3", row=0, style=discord.ButtonStyle.secondary)
    async def b3(self, i, b): await self._cell(i, 2)
    @discord.ui.button(label="4", row=1, style=discord.ButtonStyle.secondary)
    async def b4(self, i, b): await self._cell(i, 3)
    @discord.ui.button(label="5", row=1, style=discord.ButtonStyle.secondary)
    async def b5(self, i, b): await self._cell(i, 4)
    @discord.ui.button(label="6", row=1, style=discord.ButtonStyle.secondary)
    async def b6(self, i, b): await self._cell(i, 5)
    @discord.ui.button(label="7", row=2, style=discord.ButtonStyle.secondary)
    async def b7(self, i, b): await self._cell(i, 6)
    @discord.ui.button(label="8", row=2, style=discord.ButtonStyle.secondary)
    async def b8(self, i, b): await self._cell(i, 7)
    @discord.ui.button(label="9", row=2, style=discord.ButtonStyle.secondary)
    async def b9(self, i, b): await self._cell(i, 8)

    async def _cell(self, interaction, index):
        if self.board[index] != " ":
            return await interaction.response.send_message("That square is already taken.", ephemeral=True)
        await self.play(interaction, index)


class Games(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="rps", description="Play rock-paper-scissors with LightCore.")
    async def rps(self, ctx):
        await ctx.send("Choose your move:", view=RPSView(ctx.author))

    @commands.hybrid_command(name="tictactoe", description="Play tic-tac-toe against LightCore.")
    async def tictactoe(self, ctx):
        await ctx.send("Your turn — **X**", view=TicTacToeView(ctx.author))

    @commands.hybrid_command(name="guess", description="Guess a number from 1 to 100.")
    async def guess(self, ctx):
        target = random.randint(1, 100)
        await ctx.send("🎯 I'm thinking of a number from **1–100**. You have 7 guesses; reply with a number.")
        def check(m): return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.isdigit()
        for attempt in range(1, 8):
            try:
                message = await self.bot.wait_for("message", timeout=30, check=check)
            except asyncio.TimeoutError:
                return await ctx.send("⌛ Game timed out.")
            number = int(message.content)
            if number == target: return await ctx.send(f"🎉 Correct! You got it in {attempt} guesses.")
            await ctx.send("⬆️ Higher!" if number < target else "⬇️ Lower!")
        await ctx.send(f"Game over! The number was **{target}**.")

    @commands.hybrid_command(name="trivia", description="Answer a quick trivia question.")
    async def trivia(self, ctx):
        questions = [("Which planet is known as the Red Planet?", ["Mars", "Venus", "Jupiter", "Mercury"], 0), ("How many sides does a hexagon have?", ["5", "6", "7", "8"], 1)]
        question, answers, correct = random.choice(questions)
        class Trivia(discord.ui.View):
            def __init__(self): super().__init__(timeout=30)
            async def choose(self, interaction, index):
                if interaction.user.id != ctx.author.id: return await interaction.response.send_message("This trivia belongs to someone else.", ephemeral=True)
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=("✅ Correct!" if index == correct else f"❌ Incorrect. The answer was **{answers[correct]}**."), view=self)
                self.stop()
        view = Trivia()
        for index, answer in enumerate(answers):
            button = discord.ui.Button(label=answer, style=discord.ButtonStyle.secondary)
            async def callback(interaction, idx=index): await view.choose(interaction, idx)
            button.callback = callback
            view.add_item(button)
        await ctx.send(f"🧠 **Trivia:** {question}", view=view)


async def setup(bot): await bot.add_cog(Games(bot))
