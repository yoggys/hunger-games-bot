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


async def sponsors(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    event._type = EventType.POSITIVE

    if player.is_injured:
        sponsors_heal_descriptions = [
            "{} receives a sponsor package containing medicine that miraculously heals their injuries.",
            "In a stroke of luck, sponsors send {} a healing potion, mending their wounds.",
            "{} is blessed by sponsors with medicine that quickly mends their injuries.",
        ]

        player.is_injured = False

        event.text = random.choice(sponsors_heal_descriptions).format(player)

    else:
        if not player.is_armored:
            sponsors_armor_descriptions = [
                "Thanks to the generosity of sponsors, a set of armor materializes before {}, offering formidable protection against enemy attacks.",
                "In recognition of {}, sponsors send a special suit of armor, enhancing their chances of survival.",
                "{} is granted a gift from sponsors: a sturdy shield that provides unparalleled defense in the arena.",
            ]
            event.text = random.choice(sponsors_armor_descriptions).format(player)

            player.is_armored = True
        elif not player.is_protected:
            sponsors_meds_descriptions = [
                "Sponsors send {} a first aid kit, equipping them with life-saving supplies in dangerous situations.",
                "The district sends {} a set of potent pills, ensuring they have the means to overcome adversity.",
                "{} receives a medical package from sponsors, containing essential supplies for survival in the harsh arena.",
            ]
            event.text = random.choice(sponsors_meds_descriptions).format(player)

            player.is_protected = True
        else:
            sponsors_passive_descriptions = [
                "A generous sponsor delivers a package of nourishing food to {}, preventing hunger from becoming a threat.",
                "Accompanying the sponsor package, {} receives a detailed map that enhances their navigation skills in the treacherous arena.",
                "Sponsors provide {} with essential supplies, including clean water and additional resources for an extended stay in the arena.",
            ]
            event._type = EventType.PASSIVE
            event.text = random.choice(sponsors_passive_descriptions).format(player)

    await player.save()

    return event


async def fight_player(**kwargs) -> Event:
    def player_weigth(player: PlayerModel) -> int:
        positive = 5 * int(player.is_armored) + int(player.is_protected)
        negative = -6 * int(player.is_injured)
        return 10 + positive + negative  # 10 is the base weight

    game, player, event = init_utils(**kwargs)

    event._type = EventType.NEGATIVE

    players = await game.players.filter(is_alive=True).exclude(id=player.id)
    player2 = random.choice(players)

    choice = random.choices(
        [player, player2], [player_weigth(player), player_weigth(player2)]
    )[0]
    winner = player if choice == player else player2
    loser = player2 if choice == player else player

    if random.random() < 0.2:
        fight_injured_texts = [
            "{} engages in a fierce battle with {} but emerges victorious, leaving their opponent injured.",
            "{} skillfully defeats {} in a grueling fight, inflicting injuries upon them.",
            "In a brutal clash, {} overpowers {} and inflicts injuries, securing their triumph.",
        ]

        event.text = random.choice(fight_injured_texts).format(winner, loser)
        loser.is_injured = True
        await loser.save()
    else:
        fight_death_texts = [
            "{} engages in a deadly fight with {} and emerges as the victor, ending their opponent's life.",
            "In a brutal confrontation, {} manages to overpower {} and delivers a fatal blow.",
            "A fierce battle unfolds between {} and {}, but ultimately, first one emerges triumphant, leaving their opponent lifeless.",
        ]

        event.text = random.choice(fight_death_texts).format(winner, loser)
        loser.death_by = f"fight with {winner}"
        loser.is_alive = False
        await loser.save()

    if random.random() < 0.15:
        winner_injured_texts = [
            "{} sustains injuries despite their victory in the intense fight.",
            "Even after winning the fight, {}, unfortunately, ends up injured.",
        ]

        event.text += f"\n{random.choice(winner_injured_texts).format(winner)}"
        player.is_injured = True

    if not loser.is_alive:
        player.kills.append(str(loser))

    await player.save()

    return event


# ...


# Event list
event_list: list[Event] = [
    Event(weight=200, callback=nothing),
    Event(weight=70, callback=wild_animals),
    Event(weight=50, callback=poisonous),
    Event(weight=60, callback=chest),
    Event(weight=50, callback=sponsors),
    Event(weight=90, callback=fight_player),
]
events_weights = [event.weight for event in event_list]


# Get random event for the game
async def get_random_event() -> Event:
    """Returns a random event from the event list."""
    return random.choices(event_list, weights=events_weights)[0]
