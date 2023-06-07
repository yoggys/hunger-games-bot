import asyncio
import random
from datetime import datetime
from typing import Union

import discord
from tortoise.queryset import Q

from game_utils.events_data import get_random_event
from utils.client import HungerGamesBot
from utils.models import GameModel, PlayerModel


class GamesManager:
    def __init__(self, client: HungerGamesBot):
        self.client = client

    async def get_alive_players(
        self,
        model: Union[GameModel, PlayerModel],
        restart: bool = False,
        count: bool = False,
    ) -> Union[list[PlayerModel], int]:
        """Returns a list of alive players in the game."""
        model = model if isinstance(model, GameModel) else model.game
        queryset = PlayerModel.filter(Q(game=model) & Q(is_alive=True))
        if restart:
            queryset = queryset.filter(~Q(current_day=model.current_day))
        return await queryset.count() if count else await queryset

    async def run_games(self):
        """Runs all games in the database."""
        for game in await GameModel.filter(is_started=True, is_ended=False):
            await game.fetch_related("players")
            asyncio.ensure_future(self.run_game(game=game))

    async def run_game(self, game: GameModel):
        """Run a specific game."""
        loop_length = game.day_length * 60
        last_loop = game.updated_at or game.created_at

        remaining_time = int(
            (loop_length - (datetime.now(last_loop.tzinfo) - last_loop).total_seconds())
        )

        players = await self.get_alive_players(model=game)
        if len(players) < 2:
            return await self.check_game_end(game=game, skip_check=True)

        if any([player.current_day < game.current_day for player in players]):
            players = await self.get_alive_players(model=game, restart=True)

        while len(players) > 1:
            random.shuffle(players)
            if await self.run_day(
                game=game, players=players, remaining_time=remaining_time
            ):
                break

            remaining_time = loop_length

            game.current_day += 1
            game.current_day_choices.clear()
            await game.save()

            players = await self.get_alive_players(model=game)

    async def run_day(
        self, game: GameModel, players: list[PlayerModel], remaining_time: int
    ) -> Union[bool, None]:
        """Run a day in the game."""
        if await self.run_players_events(
            game=game, players=players, remaining_time=remaining_time
        ):
            return True
        await self.day_summary(game=game)

    async def day_summary(self, game: GameModel) -> None:
        deaths_today = await PlayerModel.filter(
            game=game, is_alive=False, current_day=game.current_day
        )

        channel = self.client.get_channel(game.channel_id)
        if len(deaths_today) == 0:
            embeds = [
                discord.Embed(
                    title="There were no shots fired this night...",
                    description="No one died. Is it luck, or some kind of tactic?",
                    color=discord.Color.gold(),
                )
            ]
        else:
            embeds = [
                discord.Embed(
                    title="Cannon shots go off in the distance...",
                    description=f"The following tributes have died today:",
                    color=discord.Color.gold(),
                ),
                discord.Embed(
                    description="\n".join([str(player) for player in deaths_today]),
                    color=discord.Color.gold(),
                ).set_footer(test="We'll see what the next day brings..."),
            ]

        await channel.send(f"Hunger Games **{game}**.", embeds=embeds)

    async def run_players_events(
        self, game: GameModel, players: list[PlayerModel], remaining_time: int
    ) -> Union[bool, None]:
        """Run all alive players events."""
        player_offset = 0 if remaining_time <= 0 else int(remaining_time / len(players))
        remaining_offset = 0

        for player in players:
            if player_offset > 0:
                offset = random.randint(0, player_offset)
                remaining_offset = player_offset - offset
                await asyncio.sleep(offset)

            player = await PlayerModel.get(id=player.id)
            if player.is_alive:
                await self.player_event(game=game, player=player)
                player.current_day = game.current_day
                await player.save()
                if await self.check_game_end(game=game):
                    return True

            await asyncio.sleep(remaining_offset)

    async def player_event(self, game: GameModel, player: PlayerModel) -> None:
        """Run a player event."""
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
        """Check if the game has ended."""
        if skip_check or await self.get_alive_players(model=game, count=True) < 2:
            return await self.end_game(game=game)

    async def end_game(self, game: GameModel) -> discord.Message:
        """End the game."""
        game.is_ended = True
        await game.save()

        winner = await game.players.filter(is_alive=True).first()

        channel = self.client.get_channel(game.channel_id)
        return await channel.send(f"🎉 {winner} won the **{game}** Hunger Games!")
