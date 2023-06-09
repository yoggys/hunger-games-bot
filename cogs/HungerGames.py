import asyncio

import discord
from discord.ext import commands

from game_utils.GamesManager import GamesManager
from utils.client import HungerGamesBot
from utils.models import GameModel, PlayerModel
from utils.Paginator import Paginator


class HungerGames(commands.Cog):
    def __init__(self, client):
        self.client: HungerGamesBot = client
        self.GamesManager: GamesManager = GamesManager(client=self.client)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.GamesManager.run_games()

    @commands.slash_command(description="Create a Hunger Games game.")
    @discord.default_permissions(moderate_members=True)
    async def hgcreate(
        self,
        ctx: discord.ApplicationContext,
        private: discord.Option(bool, "Should the game be private?") = False,
        day_length: discord.Option(int, "Length of each day in minutes.") = 60,
        max_players: discord.Option(int, "Maximum number of players.") = 24,
        channel: discord.Option(
            discord.TextChannel, "Channel to create the game in."
        ) = None,
    ) -> None:
        if max_players < 2 or max_players > 24:
            return await ctx.respond(
                "❌ Maximum players must be between 2 and 24.", ephemeral=True
            )

        channel = channel or ctx.channel
        game = await GameModel.create(
            guild_id=ctx.guild.id,
            channel_id=channel.id,
            owner_id=ctx.author.id,
            max_players=max_players,
            is_invite_only=private,
            day_length=day_length,
        )

        description = f"To join the game type `/hgjoin game_id:{game.id}`"
        if private:
            description += (
                "\nThis game is private, so only the owner can invite players."
            )

        embed = discord.Embed(
            title="✅ Game created!",
            description=description,
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Game ID", value=game.id)
        embed.add_field(name="Max players", value=game.max_players)
        embed.add_field(name="Private", value=game.is_invite_only)
        embed.add_field(name="Channel", value=channel.mention)

        await ctx.respond(embed=embed)

    @commands.slash_command(description="Invite someone to a Hunger Games game.")
    async def hginvite(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to invite to."),
        member: discord.Option(discord.Member, "Member to invite."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if not game.is_invite_only:
            return await ctx.respond("❌ This game is not private.", ephemeral=True)

        if game.owner_id != ctx.author.id:
            return await ctx.respond(
                "❌ You are not the owner of this game.", ephemeral=True
            )

        if game.is_started:
            return await ctx.respond("❌ This game has already started.", ephemeral=True)

        if member.bot:
            return await ctx.respond(
                "❌ You cannot invite bots to a game.", ephemeral=True
            )

        if member.id in game.invited_users:
            return await ctx.respond(
                "❌ This player has already been invited.", ephemeral=True
            )

        await game.fetch_related("players")
        if member.id in [player.user_id for player in game.players]:
            return await ctx.respond(
                "❌ This player is already in the game.", ephemeral=True
            )

        if len(game.players) >= game.max_players:
            return await ctx.respond("❌ This game is full.", ephemeral=True)

        game.invited_users.append(member.id)
        await game.save()

        await ctx.respond(
            f"✅ {member.mention} has been invited to the game **{game}**."
        )

    @commands.slash_command(description="Join a Hunger Games game.")
    async def hgjoin(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to join."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if game.is_started:
            return await ctx.respond("❌ This game has already started.", ephemeral=True)

        if (
            game.is_invite_only
            and ctx.author.id not in game.invited_users
            and game.owner_id != ctx.author.id
        ):
            return await ctx.respond(
                "❌ You are not invited to this game.", ephemeral=True
            )

        await game.fetch_related("players")
        if ctx.author.id in [player.user_id for player in game.players]:
            return await ctx.respond("❌ You are already in this game.", ephemeral=True)

        current_players = len(game.players)
        if current_players >= game.max_players:
            return await ctx.respond("❌ This game is full.", ephemeral=True)

        await PlayerModel.create(game=game, user_id=ctx.author.id)
        await ctx.respond(
            f"✅ {ctx.author.mention} have joined the game **{game}** ({current_players + 1}/{game.max_players})."
        )

    @commands.slash_command(description="Create a Hunger Games game.")
    @discord.default_permissions(moderate_members=True)
    async def hgstart(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to invite to."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if game.owner_id != ctx.author.id:
            return await ctx.respond(
                "❌ You are not the owner of this game.", ephemeral=True
            )

        if game.is_started:
            return await ctx.respond("❌ This game has already started.", ephemeral=True)

        await game.fetch_related("players")
        if len(game.players) < 2:
            return await ctx.respond(
                "❌ This game does not have enough players.", ephemeral=True
            )

        game.is_started = True
        await game.save()

        await ctx.respond(f"✅ The game **{game}** has started.")
        asyncio.ensure_future(self.GamesManager.run_game(game=game))

    @commands.slash_command(description="Create and start a Hunger Games game.")
    @commands.is_owner()
    async def hgdebug(
        self,
        ctx: discord.ApplicationContext,
        players: discord.Option(int, "Number of players to create.") = 2,
        instant: discord.Option(bool, "Instantly end days of the game.") = False,
    ) -> None:
        game = await GameModel.create(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            owner_id=ctx.author.id,
            day_length=0 if instant else 1,
            is_invite_only=True,
            is_started=True,
        )

        for index in range(players):
            await PlayerModel.create(game=game, user_id=index)

        await ctx.respond(f"✅ Done - **{game}** with **{players}** players.")
        await self.GamesManager.run_game(game=game)

        await PlayerModel.filter(game=game).delete()
        await game.delete()

    def format_player(self, player: PlayerModel, winner: int) -> str:
        if not player.is_alive:
            return f"~~{player}~~ 💀\n> ` Died by {player.death_by}. `"

        badges = []
        if player.is_injured:
            badges.append("`[ 🤕 Injured ]`")
        if player.is_armored:
            badges.append("`[ 🛡️ Armored ]`")
        if player.is_protected:
            badges.append("`[ 💉 Meds ]`")

        return "{} {}{}".format(
            player,
            "👑" if player.user_id == winner else "❤️",
            ("\n> " + " ".join(badges)) if badges else "",
        )

    def format_entry(self, index: int, player: PlayerModel, winner: int) -> str:
        return f"{index + 1}. {self.format_player(player, winner)}"

    @commands.slash_command(description="Get more info about Hunger Game game.")
    async def hginfo(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to get more info."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        players = await PlayerModel.filter(game=game).order_by(
            "-is_alive", "-current_day", "is_injured"
        )

        if not game.is_started:
            return await ctx.respond(
                f"❌ This game has not started yet ({len(players)}/{game.max_players}).",
                ephemeral=True,
            )

        if len(players) == 0:
            return await ctx.respond("❌ This game has no players.", ephemeral=True)

        alive_count = len([player for player in players if player.is_alive])
        dead_count = len(players) - alive_count

        game_embed = discord.Embed(
            title=f"Hunger Games #{game_id}", color=discord.Color.gold()
        )
        game_embed.add_field(name="Day", value=f"` {game.current_day} `", inline=True)
        game_embed.add_field(name="Alive", value=f"` {alive_count} `", inline=True)
        game_embed.add_field(name="Dead", value=f"` {dead_count} `", inline=True)
        game_embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/704387250351243425/1116424425722613790/logo-hgb.png"
        )

        if game.winner:
            game_embed.add_field(name="Winner", value=f"<@{game.winner}>")

        max_day = max([player.current_day for player in players])
        embeds = [game_embed]
        current_day = None
        description = ""

        for i in range(0, len(players), 10):
            for player in players[i : i + 10]:
                player_day = max_day if player.is_alive else player.current_day
                if player_day != current_day:
                    current_day = player_day
                    description += f"\n## Day {current_day}\n"

                description += (
                    f"{self.format_entry(players.index(player), player, game.winner)}\n"
                )
            embed = discord.Embed(description=description, color=discord.Color.gold())
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.respond(embeds=embeds[0], ephemeral=True)
        else:
            pages = Paginator(pages=embeds)
            await pages.respond(ctx.interaction, ephemeral=True)

    @commands.slash_command(description="Fill game with bots.")
    @commands.is_owner()
    async def hgbots(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID."),
        count: discord.Option(int, "Number of bots to create.") = 1,
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)
        
        if game.is_started:
            await ctx.respond("❌ Game has already started.", ephemeral=True)
        
        await ctx.defer(ephemeral=True)
            
        for index in range(count):
            await PlayerModel.create(game=game, user_id=index)
            
        await ctx.respond(f"✅ Added **{count}** bots to **{game}**.", ephemeral=True)
def setup(client):
    client.add_cog(HungerGames(client))
