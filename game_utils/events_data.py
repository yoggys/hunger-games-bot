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

    nothing_descriptions = [
        "{} spent the day without any noteworthy events.",
        "The day passed uneventfully for {} as they went about their routine.",
        "No significant incidents occurred in {}'s day, leaving them to reflect on their strategies.",
        "A quiet day unfolded for {}, devoid of any remarkable occurrences.",
        "{} found themselves in a state of idleness as the hours slipped away without event.",
        "The arena remained undisturbed for {}, granting them a day of respite from the chaos.",
        "As the sun set on another day, {} found themselves caught in the monotony of survival.",
    ]

    event._type = EventType.PASSIVE
    event.text = random.choice(nothing_descriptions).format(player)
    return event


async def wild_animals(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    wild_animals_descriptions = [
        "{} encountered a fierce wild animal and engaged in a brutal fight.",
        "A terrifying encounter with a wild animal left {} in a life-or-death struggle.",
        "{} found themselves face to face with a ferocious beast, resulting in a violent confrontation.",
        "The tranquility of the arena was shattered for {} as they became entangled in a deadly battle with a wild animal.",
        "In a harrowing turn of events, {} crossed paths with a dangerous creature, leading to a desperate fight for survival.",
        "The serenity of the day was shattered when {} faced off against a savage wild animal, their skills put to the ultimate test.",
    ]

    event.text = random.choice(wild_animals_descriptions).format(player)
    if player.is_armored:
        event._type = EventType.POSITIVE
        event.text += f"\nLuckily, {player} survived the fight due to their armor."
        player.is_armored = False
    else:
        event._type = EventType.NEGATIVE
        event.text += (
            f"\nSadly, {player} couldn't overcome the ferocity of the wild animal."
        )
        player.death_by = "wild animals"
        player.is_alive = False

    await player.save()
    return event


async def poisonous(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    poisonous_descriptions = [
        "{} made the unfortunate choice of consuming poisonous berries, leading to dire consequences.",
        "In a moment of hunger, {} ingested toxic plants, suffering the effects of their poisonous nature.",
        "{} fell victim to the deadly allure of seemingly harmless berries, only to be poisoned by their toxicity.",
        "The tempting appearance of berries led {} astray, as the poison within took a toll on their body.",
        "Unbeknownst to {}, the seemingly edible vegetation they consumed turned out to be lethal, poisoning their system.",
        "A fatal mistake was made by {}, who unknowingly consumed a lethal dose of poisonous substance.",
    ]

    event.text = random.choice(poisonous_descriptions).format(player)
    if player.is_protected:
        event._type = EventType.POSITIVE
        event.text += f"\nLuckily, {player} survived due to their medicines."
        player.is_protected = False
    else:
        event._type = EventType.NEGATIVE
        if not player.is_injured and random.randint(0, 1):
            event.text += f"\n{player} starts feeling unwell, experiencing the effects of the poison."
            player.is_injured = True
        else:
            event.text += (
                f"\nSadly, the poison overwhelms {player} and claims their life."
            )
            player.death_by = "poison"
            player.is_alive = False

    await player.save()
    return event


async def chest(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    if random.randint(0, 1):
        good_loot_texts = [
            "{} found a chest containing medicine that healed them.",
            "{} discovered a chest and acquired armor.",
            "{} obtained medicine from a chest, boosting their chances of survival.",
        ]

        event._type = EventType.POSITIVE
        if player.is_injured:
            player.is_injured = False
            event.text = good_loot_texts[0].format(player)
        else:
            loot = random.randint(1, 2)
            event.text = good_loot_texts[loot].format(player)

            if loot == 1 and not player.is_armored:
                player.is_armored = True
            elif loot == 2 and not player.is_protected:
                player.is_protected = True
            else:
                event._type = EventType.PASSIVE
                event.text += (
                    f"\nHowever, {player} already had it, so nothing has changed."
                )

    else:
        bad_loot_texts = [
            "{} opened a chest that turned out to be an exploding trap.",
            "A treacherous chest caught {} off guard, triggering an explosive trap.",
            "The excitement of finding a chest quickly turned into danger for {} as it detonated.",
        ]

        event._type = EventType.NEGATIVE
        event.text = random.choice(bad_loot_texts).format(player)
        if player.is_armored:
            event._type = EventType.PASSIVE
            event.text += f"\nFortunately, the armor saved {player}'s life."
            player.is_armored = False
        else:
            player.death_by = "explosion"
            player.is_alive = False

    await player.save()

    return event


# ...


# Event list
event_list: list[Event] = [
    Event(weight=2, callback=nothing),
    Event(weight=1, callback=wild_animals),
    Event(weight=1, callback=poisonous),
    Event(weight=1, callback=chest),
]
events_weights = [event.weight for event in event_list]


# Get random event for the game
async def get_random_event() -> Event:
    """Returns a random event from the event list."""
    return random.choices(event_list, weights=events_weights)[0]
