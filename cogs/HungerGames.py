import asyncio
import random
from datetime import datetime
from typing import Union

import discord
from discord.ext import commands
from tortoise.queryset import Q

from utils.client import HungerGamesBot
from game_utils.events import Event
from game_utils.events_data import event_list
from utils.models import GameModel, PlayerModel


class HungerGames(commands.Cog):
    def __init__(self, client):
        self.client: HungerGamesBot = client

        self.events: list[Event] = []
        self.events_weights: list[int] = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.register_events()
        await self.run_games()

    def register_events(self):
        self.events = event_list
        self.events_weights = [event.weight for event in event_list]

    async def run_games(self, game: GameModel = None):
        for game in await GameModel.filter(is_started=True, is_ended=False):
            await game.fetch_related("players")
            asyncio.ensure_future(self.run_game(game=game))

    async def run_game(self, game: GameModel):
        loop_minutes = game.day_length
        last_loop = game.updated_at or game.created_at

        remaining_minutes = int(
            loop_minutes
            - (datetime.now(last_loop.tzinfo) - last_loop).total_seconds() / 60
        )

        players = await self.get_day_alive_players(game=game)

        if len(players) < 2:
            await self.check_game_end(game=game, skip_check=True)

        while len(players) > 1:
            random.shuffle(players)
            if await self.run_day(
                game=game, players=players, remaining_minutes=remaining_minutes
            ):
                break
            remaining_minutes = game.day_length
            players = await self.get_day_alive_players(game=game)

    async def get_day_alive_players(self, game: GameModel) -> list[PlayerModel]:
        return await PlayerModel.filter(
            Q(game=game) & Q(is_alive=True) & ~Q(current_day=game.current_day)
        )

    async def run_day(
        self, game: GameModel, players: list[PlayerModel], remaining_minutes: int
    ) -> Union[bool, None]:
        if await self.execute_events(
            game=game, players=players, remaining_minutes=remaining_minutes
        ):
            return True
        game.current_day += 1
        game.current_day_choices.clear()
        await game.save()

    async def execute_events(
        self, game: GameModel, players: list[PlayerModel], remaining_minutes: int
    ) -> Union[bool, None]:
        player_offset = (
            0 if remaining_minutes <= 0 else int(remaining_minutes * 60 / len(players))
        )
        remaining_offset = 0

        for player in players:
            if player_offset > 0:
                offset = random.randint(0, player_offset)
                remaining_offset = player_offset - offset
                await asyncio.sleep(offset)

            player = await PlayerModel.get(id=player.id)
            if player.is_alive:
                await self.player_event(game=game, player=player)
                if await self.check_game_end(game=game):
                    return True

            await asyncio.sleep(remaining_offset)

    async def player_event(self, game: GameModel, player: PlayerModel) -> None:
        event = await self.get_random_event()
        event = await event.execute(game=game, player=player, event=event)

        embed = discord.Embed(
            title="Hunger Games",
            description=event.text,
            color=event._type.value,
        )

        user = self.client.get_user(player.user_id) or await self.client.fetch_user(
            player.user_id
        )
        embed.set_thumbnail(url=user.display_avatar)

        channel = self.client.get_channel(game.channel_id)
        await channel.send(user.mention, embed=embed)

    async def check_game_end(
        self, game: GameModel, skip_check=False
    ) -> Union[discord.Message, None]:
        if not skip_check:
            if await game.players.filter(is_alive=True).count() > 1:
                return

        game.is_ended = True
        await game.save()

        winner = await game.players.filter(is_alive=True).first()

        channel = self.client.get_channel(game.channel_id)
        return await channel.send(f"🎉 {winner} won the **#{game.id}** Hunger Games!")

    async def get_random_event(self) -> Event:
        return random.choices(self.events, weights=self.events_weights)[0]

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
            return await ctx.respond("❌ Maximum players must be between 2 and 24.")

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
    @discord.default_permissions(moderate_members=True)
    async def hginvite(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to invite to."),
        member: discord.Option(discord.Member, "Member to invite."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.")

        if not game.is_invite_only:
            return await ctx.respond("❌ This game is not private.")

        if game.owner_id != ctx.author.id:
            return await ctx.respond("❌ You are not the owner of this game.")

        if member.bot:
            return await ctx.respond("❌ You cannot invite bots to a game.")

        if member.id in game.invited_users:
            return await ctx.respond("❌ This player has already been invited.")

        await game.fetch_related("players")
        if member.id in [player.user_id for player in game.players]:
            return await ctx.respond("❌ This player is already in the game.")

        if len(game.players) >= game.max_players:
            return await ctx.respond("❌ This game is full.")

        game.invited_users.append(member.id)
        await game.save()

        await ctx.respond(f"✅ {member.mention} has been invited to the game.")

    @commands.slash_command(description="Join a Hunger Games game.")
    @discord.default_permissions(moderate_members=True)
    async def hgjoin(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to join."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.")

        if (
            game.is_invite_only
            and ctx.author.id not in game.invited_users
            and game.owner_id != ctx.author.id
        ):
            return await ctx.respond("❌ You are not invited to this game.")

        await game.fetch_related("players")
        if ctx.author.id in [player.user_id for player in game.players]:
            return await ctx.respond("❌ You are already in this game.")

        if len(game.players) >= game.max_players:
            return await ctx.respond("❌ This game is full.")

        await PlayerModel.create(game=game, user_id=ctx.author.id)
        await ctx.respond("✅ You have joined the game.")

    @commands.slash_command(description="Create a Hunger Games game.")
    @discord.default_permissions(moderate_members=True)
    async def hgstart(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to invite to."),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.")

        if game.owner_id != ctx.author.id:
            return await ctx.respond("❌ You are not the owner of this game.")

        if game.is_started:
            return await ctx.respond("❌ This game has already started.")

        await game.fetch_related("players")
        if len(game.players) < 0:
            return await ctx.respond("❌ This game does not have enough players.")

        game.is_started = True
        await game.save()

        await ctx.respond("✅ The game has started.")
        asyncio.ensure_future(self.run_game(game=game))

    @commands.slash_command(description="Create a Hunger Games game.")
    @commands.is_owner()
    async def debug(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID"),
    ) -> None:
        game = await GameModel.get_or_none(id=game_id)
        if not game:
            return await ctx.respond("❌ Game not found.")

        await game.fetch_related("players")
        for player in game.players:
            print(player.user_id)

        await ctx.respond("✅ Done.")


def setup(client):
    client.add_cog(HungerGames(client))
