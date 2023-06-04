import discord
from discord.ext import commands
from tortoise import Tortoise


class HungerGamesBot(commands.Bot):
    def __init__(self):
        super().__init__(intents=discord.Intents.default(), help_command=None)

        self.load_extension("cogs.System")
        self.load_extension("cogs.HungerGames")

    async def on_connect(self):
        await Tortoise.init(
            db_url="sqlite://main.db", modules={"models": ["utils.models"]}
        )
        await Tortoise.generate_schemas()
        await super().on_connect()

    async def on_ready(self):
        print("Running as {} (ID: {})".format(self.user, self.user.id))
