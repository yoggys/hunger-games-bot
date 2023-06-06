import asyncio
import random
from datetime import datetime
from typing import Union

import discord
from tortoise.queryset import Q

from game_utils.events_data import get_random_event
from utils.models import GameModel, PlayerModel


class GamesManager:
    def __init__(self, client):
        self.client = client

    async def get_alive_players(
        self, model: Union[GameModel, PlayerModel], count: bool = False
    ) -> Union[list[PlayerModel], int]:
        model = model if isinstance(model, GameModel) else model.game
        queryset = PlayerModel.filter(
            Q(game=model) & Q(is_alive=True) & ~Q(current_day=model.current_day)
        )
        return await queryset.count() if count else await queryset

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

        players = await self.get_alive_players(model=game)

        if len(players) < 2:
            return await self.check_game_end(game=game, skip_check=True)

        while len(players) > 1:
            random.shuffle(players)
            if await self.run_day(
                game=game, players=players, remaining_minutes=remaining_minutes
            ):
                break
            remaining_minutes = game.day_length
            players = await self.get_alive_players(model=game)

    async def run_day(
        self, game: GameModel, players: list[PlayerModel], remaining_minutes: int
    ) -> Union[bool, None]:
        if await self.run_players(
            game=game, players=players, remaining_minutes=remaining_minutes
        ):
            return True
        game.current_day += 1
        game.current_day_choices.clear()
        await game.save()

    async def run_players(
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
        event = await get_random_event()
        event = await event.execute(game=game, player=player, event=event)

        embed = discord.Embed(
            title=f"Hunger Games {game}",
            description=event.text,
            color=event._type.value,
        )

        if user := self.client.get_user(player.user_id):
            embed.set_thumbnail(url=user.display_avatar)

        channel = self.client.get_channel(game.channel_id)
        await channel.send(player, embed=embed)

    async def check_game_end(
        self, game: GameModel, skip_check=False
    ) -> Union[discord.Message, None]:
        if skip_check or await self.get_alive_players(model=game, count=True) < 2:
            return await self.end_game(game=game)

    async def end_game(self, game: GameModel) -> discord.Message:
        game.is_ended = True
        await game.save()

        winner = await game.players.filter(is_alive=True).first()

        channel = self.client.get_channel(game.channel_id)
        return await channel.send(f"🎉 {winner} won the **{game}** Hunger Games!")
