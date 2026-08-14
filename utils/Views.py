import discord

from utils.client import HungerGamesBot
from utils.models import GameModel, PlayerModel


class JoinGameView(discord.ui.View):
    def __init__(self, game_id: int):
        super().__init__(timeout=0)

        button = discord.ui.Button(
            label="🎮 Join",
            style=discord.ButtonStyle.gray,
            custom_id=f"join_game_{game_id}",
        )
        self.add_item(button)

        button = discord.ui.Button(
            label="🚀 Start",
            style=discord.ButtonStyle.gray,
            custom_id=f"start_game_{game_id}",
        )
        self.add_item(button)


class InviteView(discord.ui.View):
    def __init__(self, client: HungerGamesBot):
        invite_url = "https://canary.discord.com/api/oauth2/authorize?client_id={}&permissions=8&scope=bot%20applications.commands".format(
            client.application_id
        )
        server_url = "https://dc.yoggies.dev/"

        invite = discord.ui.Button(
            label="Invite HungerGames", style=discord.ButtonStyle.url, url=invite_url
        )
        server = discord.ui.Button(
            label="Support server", style=discord.ButtonStyle.url, url=server_url
        )

        super().__init__(invite, server, timeout=0)
