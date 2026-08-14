import discord

from utils.client import HungerGamesBot
from utils.models import GameModel, PlayerModel


class JoinGameView(discord.ui.View):
    def __init__(self, game_id: int):
        super().__init__(timeout=None)
        self.game_id = game_id

    @discord.ui.button(
        label="🎮 Join Game", style=discord.ButtonStyle.gray, custom_id="join_game"
    )
    async def join_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        game = await GameModel.get_or_none(id=self.game_id)
        if not game:
            return await interaction.response.send_message(
                "❌ Game not found.", ephemeral=True
            )

        if game.is_started:
            return await interaction.response.send_message(
                "❌ This game has already started.", ephemeral=True
            )

        if (
            game.is_invite_only
            and interaction.user.id not in game.invited_users
            and game.owner_id != interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ You are not invited to this game.", ephemeral=True
            )

        await game.fetch_related("players")
        if interaction.user.id in [player.user_id for player in game.players]:
            return await interaction.response.send_message(
                "❌ You are already in this game.", ephemeral=True
            )

        if len(game.players) >= game.max_players:
            return await interaction.response.send_message(
                "❌ This game is full.", ephemeral=True
            )

        await PlayerModel.create(game=game, user_id=interaction.user.id)
        current_players = len(game.players) + 1

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} has joined the game **{game}** ({current_players}/{game.max_players}).",
            ephemeral=True,
        )


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
