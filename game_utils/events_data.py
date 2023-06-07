import random

from game_utils.Events import Event, EventType
from utils.models import GameModel, PlayerModel


# Utils
def init_utils(**kwargs) -> tuple[GameModel, PlayerModel, Event]:
    """Initializes utils for the event callback function."""
    game: GameModel = kwargs.get("game")
    player: PlayerModel = kwargs.get("player")
    event: Event = kwargs.get("event")

    if not player or not game or not event:
        raise ValueError("Missing required arguments.")

    return game, player, event


# Base event


async def nothing(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    nothing_texts: list[str] = ["{} didn't do anything interesting today."]
    event._type = EventType.PASSIVE
    event.text = random.choice(nothing_texts).format(player)
    return event


async def wild_animals(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    wild_animals_texts: list[str] = ["{} got into a fight with a wild animal."]

    if player.is_armored:
        event._type = EventType.POSITIVE
        event.text = random.choice(wild_animals_texts).format(player)
        event.text += f" Luckily, {player} survived the fight due to their armor."
        player.is_armored = False

        return event
    else:
        event._type = EventType.NEGATIVE
        event.text = random.choice(wild_animals_texts).format(player)
        event.text += f" Sadly, {player} didn't survive."

        player.is_alive = False

    await player.save()
    return event


async def poisonous(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    poisonous_texts: list[str] = [
        "{} decided to eat some berries, but they were poisonous."
    ]

    if player.is_protected:
        event._type = EventType.POSITIVE
        event.text = random.choice(poisonous_texts).format(player)
        event.text += f" Luckily, {player} survived due to their medicines."

        player.is_protected = False

    else:
        event._type = EventType.NEGATIVE
        event.text = random.choice(poisonous_texts).format(player)

        if random.choice([True, False]):
            event.text += f" {player} don't feel so good."
            player.is_injured = True
        else:
            event.text += f" Sadly poison was too strong for {player}."
            player.is_alive = False

    await player.save()
    return event


# ...


# Event list
event_list: list[Event] = [
    Event(weight=1, callback=nothing),
    Event(weight=1, callback=wild_animals),
]
events_weights = [event.weight for event in event_list]


# Get random event for the game
async def get_random_event() -> Event:
    """Returns a random event from the event list."""
    return random.choices(event_list, weights=events_weights)[0]
