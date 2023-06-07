import discord
from discord.ext import commands

from utils.client import HungerGamesBot
from utils.Views import InviteView


class System(commands.Cog):
    def __init__(self, client):
        self.client: HungerGamesBot = client

    @commands.Cog.listener()
    async def on_ready(self):
        await self.change_presence()

    async def change_presence(self):
        activity = discord.Activity(
            type=discord.ActivityType.streaming,
            name="Begin your adventure!",
        )
        await self.client.change_presence(
            status=discord.Status.streaming, activity=activity
        )

    @commands.slash_command(description="Shows bot invite link.")
    async def invite(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            description="To add {} to your server click the invitation below!".format(
                self.client.user.mention
            ),
            color=discord.Color.blurple(),
        )
        await ctx.respond(embed=embed, view=InviteView(self.client))

    @commands.slash_command(description="Shows bot latency.")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            f"Pong! {round(self.client.latency * 1000)}ms", ephemeral=True
        )

    @commands.slash_command(description="Shows bot help.")
    async def help(self, ctx: discord.ApplicationContext):
        desc = "> Check more commands by typing `/hg` in chat!\n\n"
        desc += "`/invite` - displays invite link\n"
        desc += "`/ping` - displays bot latency\n"
        embed = discord.Embed(description=desc, color=discord.Color.blurple())
        await ctx.respond(embed=embed, ephemeral=True)


def setup(client):
    client.add_cog(System(client))
