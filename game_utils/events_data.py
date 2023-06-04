import random

from game_utils.events import Event, EventType
from utils.models import GameModel, PlayerModel


# Utils
def init_utils(**kwargs) -> tuple[GameModel, PlayerModel, Event]:
    game: GameModel = kwargs.get("game")
    player: PlayerModel = kwargs.get("player")
    event: Event = kwargs.get("event")

    if not player or not game or not event:
        raise ValueError("Missing required arguments.")

    return game, player, event


# Base event
basic_texts: list[str] = ["{} didn't do anything interesting today."]


async def basic(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event._type = EventType.PASSIVE
    event.text = random.choice(basic_texts).format(player)
    return event


# ...


# Event list
event_list: list[Event] = [Event(weight=1, callback=basic)]
