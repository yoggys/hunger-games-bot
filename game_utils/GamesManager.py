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
        queryset = PlayerModel.filter(Q(game=model, is_alive=True))
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

        await game.fetch_related("players")
        if len(game.players) == len(players):
            await self.send_start_info(game=game)

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

    async def send_start_info(self, game: GameModel) -> None:
        channel = self.client.get_channel(game.channel_id)

        embed = discord.Embed(
            title=f"The {game} Hunger Games has started!",
            description="\n".join([str(player) for player in game.players]),
        )
        await channel.send(embed=embed)

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
        color = {"color": discord.Color.from_rgb(0, 0, 0)}
        if len(deaths_today) == 0:
            alive_descriptions = [
                "A quiet night enveloped the arena as the moonlight danced upon the motionless bodies. No lives were claimed, leaving the tributes to ponder their next move.",
                "Silence echoes through the arena as the night passes without any bloodshed. The tributes remain locked in a tense stalemate, testing the limits of their strategies.",
                "In a surprising turn of events, the night remains peaceful as no one falls victim to the darkness. The tributes cautiously navigate the arena, each waiting for the perfect opportunity.",
                "The absence of gunfire heralds a night of reprieve for the tributes. They lie in wait, each contemplating their survival strategies amidst the uncertainty.",
                "A night of eerie stillness descends upon the arena. No lives are claimed, leaving the tributes to question whether this is a moment of respite or a calm before the storm.",
                "As dawn breaks, it becomes clear that the night passed without a single casualty. The tributes must reevaluate their plans, searching for weaknesses or hidden alliances.",
                "The arena remains untouched by the grim hand of death. The tributes, uncertain of the reasons behind this tranquility, grow increasingly cautious in their actions.",
                "The night brings no loss of life, confounding both the tributes and the spectators. The tension mounts as they wonder if this is a testament to their ingenuity or simply an anomaly.",
            ]
            embeds = [
                discord.Embed(
                    title="There were no shots fired this night...",
                    description=random.choice(alive_descriptions),
                    **color,
                )
            ]
        else:
            death_descriptions = [
                "Another tribute has fallen, their fate sealed by a merciless force.",
                "The arena claims yet another life, leaving the remaining tributes in a state of heightened vigilance.",
                "A life is extinguished, a reminder of the cruel reality that engulfs the Hunger Games.",
                "The echoes of a fallen tribute reverberate through the arena, a haunting testament to the brutality of this deadly game.",
                "A tribute's journey comes to a tragic end, leaving a void that cannot be filled.",
                "In the face of relentless odds, a tribute succumbs to the ruthless forces at play.",
                "The Games claim another victim, their memory forever etched in the minds of those who remain.",
                "A tribute's light is extinguished, their story left unfinished in the annals of the Hunger Games.",
            ]
            day_data = [
                f"{player} died by {player.death_by}." for player in deaths_today
            ]
            embeds = [
                discord.Embed(
                    title="Cannon shots go off in the distance...",
                    description=f"The following tributes have died today:",
                    **color,
                ),
                discord.Embed(description="\n".join(day_data), **color).set_footer(
                    text=random.choice(death_descriptions)
                ),
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
        winner = await PlayerModel.get(game=game, is_alive=True)

        if winner.current_day != game.current_day:
            winner.current_day = game.current_day
            await winner.save()

        game.is_ended = True
        game.winner = winner.user_id

        await game.save()

        embed = discord.Embed(
            title=f"Hunger Games {game}",
            description=f"🎉 {winner} won the **{game}** Hunger Games!",
            color=discord.Color.gold(),
        )
        channel = self.client.get_channel(game.channel_id)
        return await channel.send(str(winner), embed=embed)
