import discord
from discord.ext import commands
from tortoise import Tortoise


class HungerGamesBot(commands.Bot):
    def __init__(self, sync: bool = False):
        super().__init__(intents=discord.Intents.default(), help_command=None)
        self.sync = sync

        self.load_extension("cogs.System")
        self.load_extension("cogs.HungerGames")

    async def on_connect(self):
        await self.init_db()

        if self.sync:
            await self.sync_commands()

    async def init_db(self):
        await Tortoise.init(
            db_url="sqlite://main.db", modules={"models": ["utils.models"]}
        )
        await Tortoise.generate_schemas()

    async def on_ready(self):
        print("Running as {} (ID: {})".format(self.user, self.user.id))
