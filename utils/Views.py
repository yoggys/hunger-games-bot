import discord

from utils.client import HungerGamesBot


class InviteView(discord.ui.View):
    def __init__(self, client: HungerGamesBot):
        invite_url = "https://canary.discord.com/api/oauth2/authorize?client_id={}&permissions=8&scope=bot%20applications.commands".format(
            client.application_id
        )
        server_url = "https://discord.gg/yoggies"

        invite = discord.ui.Button(
            label="Invite HungerGames", style=discord.ButtonStyle.url, url=invite_url
        )
        server = discord.ui.Button(
            label="Support server", style=discord.ButtonStyle.url, url=server_url
        )

        super().__init__(invite, server, timeout=0)
