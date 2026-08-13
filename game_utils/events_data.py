import random

from game_utils.Events import Event, EventType
from utils.models import GameModel, PlayerModel


def normalize_inventory(player: PlayerModel) -> list[str]:
    inventory = player.inventory or []
    return [str(item).strip().lower() for item in inventory if str(item).strip()]


def has_item(player: PlayerModel, item_name: str) -> bool:
    return str(item_name).strip().lower() in normalize_inventory(player)


def add_item(player: PlayerModel, item_name: str) -> None:
    item_key = str(item_name).strip().lower()
    if not item_key:
        return
    inventory = normalize_inventory(player)
    if item_key not in inventory:
        inventory.append(item_key)
        player.inventory = inventory
        player.sync_gear_from_inventory()


def remove_item(player: PlayerModel, item_name: str) -> None:
    item_key = str(item_name).strip().lower()
    if not item_key:
        return
    inventory = normalize_inventory(player)
    player.inventory = [item for item in inventory if item != item_key]
    player.sync_gear_from_inventory()


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
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\nLuckily, {player} survived the fight due to their armor."
        remove_item(player, "armor")
        remove_item(player, "shield")
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
    if (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        event._type = EventType.POSITIVE
        event.text += f"\nLuckily, {player} survived due to their medicines."
        remove_item(player, "medkit")
        remove_item(player, "medicine")
        remove_item(player, "potion")
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
            add_item(player, "medkit")
        else:
            loot = random.randint(1, 2)
            event.text = good_loot_texts[loot].format(player)

            if loot == 1 and not (
                has_item(player, "armor") or has_item(player, "shield")
            ):
                add_item(player, "armor")
            elif loot == 2 and not (
                has_item(player, "medkit")
                or has_item(player, "medicine")
                or has_item(player, "potion")
            ):
                add_item(player, "medkit")
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

        if has_item(player, "armor") or has_item(player, "shield"):
            event._type = EventType.PASSIVE
            event.text += f"\nFortunately, the armor saved {player}'s life."

            remove_item(player, "armor")
            remove_item(player, "shield")
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
        add_item(player, "medicine")
        event.text = random.choice(sponsors_heal_descriptions).format(player)

    else:
        if not (has_item(player, "armor") or has_item(player, "shield")):
            sponsors_armor_descriptions = [
                "Thanks to the generosity of sponsors, a set of armor materializes before {}, offering formidable protection against enemy attacks.",
                "In recognition of {}, sponsors send a special suit of armor, enhancing their chances of survival.",
                "{} is granted a gift from sponsors: a sturdy shield that provides unparalleled defense in the arena.",
            ]
            event.text = random.choice(sponsors_armor_descriptions).format(player)
            add_item(player, "armor")
        elif not (
            has_item(player, "medkit")
            or has_item(player, "medicine")
            or has_item(player, "potion")
        ):
            sponsors_meds_descriptions = [
                "Sponsors send {} a first aid kit, equipping them with life-saving supplies in dangerous situations.",
                "The district sends {} a set of potent pills, ensuring they have the means to overcome adversity.",
                "{} receives a medical package from sponsors, containing essential supplies for survival in the harsh arena.",
            ]
            event.text = random.choice(sponsors_meds_descriptions).format(player)
            add_item(player, "medkit")
        else:
            sponsors_passive_descriptions = [
                "A generous sponsor delivers a package of nourishing food to {}, preventing hunger from becoming a threat.",
                "Accompanying the sponsor package, {} receives a detailed map that enhances their navigation skills in the treacherous arena.",
                "Sponsors provide {} with essential supplies, including clean water and additional resources for an extended stay in the arena.",
            ]
            event._type = EventType.PASSIVE
            event.text = random.choice(sponsors_passive_descriptions).format(player)
            add_item(player, "food")

    await player.save()

    return event


async def fight_player(**kwargs) -> Event:
    def player_weight(p: PlayerModel) -> int:
        armor_bonus = 5 if has_item(p, "armor") or has_item(p, "shield") else 0
        med_bonus = (
            1
            if has_item(p, "medkit") or has_item(p, "medicine") or has_item(p, "potion")
            else 0
        )
        negative = -6 * int(p.is_injured)
        return 10 + armor_bonus + med_bonus + negative  # 10 is the base weight

    game, player, event = init_utils(**kwargs)

    event._type = EventType.NEGATIVE

    players = await game.players.filter(is_alive=True).exclude(id=player.id)
    player2 = random.choice(players)

    choice = random.choices(
        [player, player2], [player_weight(player), player_weight(player2)]
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
        loser.death_by = "fight with {}".format(
            str(winner).replace("`", "") if winner.is_bot else winner
        )
        loser.is_alive = False
        await loser.save()

    if random.random() < 0.15:
        winner_injured_texts = [
            "{} sustains injuries despite their victory in the intense fight.",
            "Even after winning the fight, {}, unfortunately, ends up injured.",
        ]

        event.text += f"\n{random.choice(winner_injured_texts).format(winner)}"
        winner.is_injured = True

    if not loser.is_alive:
        await winner.killed_players.add(player)
        await loser.save()

    await player.save()

    return event


async def storm(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    storm_descriptions = [
        "A violent thunderstorm tears across the arena, forcing {} to sprint for cover as lightning strikes the ground around them.",
        "Dark clouds swallow the sky and a torrential storm crashes down on {}, leaving them soaked and disoriented.",
        "The arena turns into a battlefield of wind and rain as {} gets caught in a brutal lightning storm.",
        "A sudden supercell rolls through the arena, hurling debris toward {} and threatening to end their game in an instant.",
    ]

    event.text = random.choice(storm_descriptions).format(player)
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\nThe armor absorbs most of the damage, and {player} survives with only a scare."
        remove_item(player, "armor")
        remove_item(player, "shield")
    elif (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        event._type = EventType.POSITIVE
        event.text += f"\nA first aid kit and careful planning keep {player} alive through the storm."
        remove_item(player, "medkit")
        remove_item(player, "medicine")
        remove_item(player, "potion")
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.5 and not player.is_injured:
            event.text += f"\n{player} is struck by flying debris and leaves the storm badly injured."
            player.is_injured = True
        else:
            event.text += f"\nThe storm claims {player} before they can reach shelter."
            player.death_by = "storm"
            player.is_alive = False

    await player.save()
    return event


async def hidden_cache(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    cache_descriptions = [
        "{} stumbles upon a hidden cache buried beneath the roots of a massive tree.",
        "In a forgotten corner of the arena, {} discovers a sealed supply crate left behind by the Capitol.",
        "A cunning search reveals a concealed stash near a broken watchtower, and {} claims it before anyone else can.",
        "The ground gives way under {}'s boots, exposing a well-hidden cache of life-saving gear.",
    ]

    event.text = random.choice(cache_descriptions).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        event.text += (
            f"\nInside is medicine, and {player} manages to patch themselves up."
        )
        player.is_injured = False
        add_item(player, "medkit")
    else:
        loot = random.choice(["armor", "medicine"])
        if loot == "armor" and not (
            has_item(player, "armor") or has_item(player, "shield")
        ):
            add_item(player, "armor")
            event.text += f"\nA reinforced chestplate is tucked inside, giving {player} solid protection."
        elif loot == "medicine" and not (
            has_item(player, "medkit")
            or has_item(player, "medicine")
            or has_item(player, "potion")
        ):
            add_item(player, "medkit")
            event.text += (
                f"\nA medical kit is found, and {player} stores it carefully for later."
            )
        else:
            event._type = EventType.PASSIVE
            event.text += f"\nThe cache is useful, but {player} already has the best gear it can offer."

    await player.save()
    return event


async def river_crossing(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    river_descriptions = [
        "{} attempts to cross a fast, black river and nearly loses everything in the current.",
        "A sudden river surge sweeps through the arena, forcing {} to fight the water just to stay alive.",
        "The river is colder and stronger than expected, and {} takes a terrifying plunge while searching for a way across.",
    ]

    event.text = random.choice(river_descriptions).format(player)
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\nThe armor keeps {player} afloat long enough to reach shore, though it is ruined in the process."
        remove_item(player, "armor")
        remove_item(player, "shield")
    elif (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        event._type = EventType.POSITIVE
        event.text += f"\n{player} manages to stay alive with a medical kit and a lucky grip on a rock."
        remove_item(player, "medkit")
        remove_item(player, "medicine")
        remove_item(player, "potion")
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.55:
            event.text += f"\nAs the river drags them under, {player} is left injured and exhausted."
            player.is_injured = True
        else:
            event.text += f"\nThe river drags {player} beneath the surface, and they do not resurface."
            player.death_by = "river"
            player.is_alive = False

    await player.save()
    return event


async def alliance_offer(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    alliance_texts = [
        "A nearby tribute offers {} a fragile alliance, promising safety for a few dangerous hours.",
        "Suddenly, {} is approached by a nervous alliance partner who whispers of shared survival.",
        "In the midst of chaos, {} is offered a temporary truce that could keep both of them alive for a while.",
    ]

    event.text = random.choice(alliance_texts).format(player)
    event._type = EventType.PASSIVE

    if player.is_injured:
        event.text += f"\nThe alliance is fleeting, but it gives {player} the chance to recover enough to keep moving."
        player.is_injured = False
    elif random.random() < 0.5:
        event.text += (
            f"\nThe gesture is kind, though {player} knows it could just be a trap."
        )
    else:
        event.text += f"\nThe pact is brief and surprisingly useful, giving {player} a much-needed calm moment."

    await player.save()
    return event


async def food_cache(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    food_texts = [
        "{} finds a stockpile of dry rations nestled under a fallen shelter.",
        "A hidden food cache appears near a quiet grove, and {} takes the chance to recover strength.",
        "The ground opens around {} just enough to reveal a stash of food, medicine, and clean water.",
    ]

    event.text = random.choice(food_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        event.text += f"\nThe supplies help {player} recover enough to move through the arena again."
        player.is_injured = False
    else:
        event.text += (
            f"\nThe cache gives {player} a rare, comforting sense of security."
        )

    await player.save()
    return event


async def ritual_site(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    ritual_texts = [
        "{} comes across a forgotten ritual site covered in old carvings and strange symbols.",
        "An eerie shrine sits in the middle of the arena, and {} cannot help but investigate it.",
        "The silence around a ruined altar is unsettling, but {} finds a sudden burst of luck there.",
    ]

    event.text = random.choice(ritual_texts).format(player)
    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThey find a charm that fortifies their resolve and keeps them moving."
        )
        add_item(player, "charm")
    else:
        event._type = EventType.NEGATIVE
        event.text += (
            f"\nA cursed omen grips {player}, and the site leaves them shaken and weak."
        )
        player.is_injured = True

    await player.save()
    return event


async def supply_drop(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    drop_texts = [
        "A supply drop from the Capitol crashes into the arena near {}, bringing a burst of hope.",
        "A parachute drifts down and lands beside {}, showering them with survival gear.",
        "The sky suddenly fills with cargo from a sponsor flight, and {} is lucky enough to reach it first.",
    ]

    event.text = random.choice(drop_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        event.text += f"\nInside the crate is medicine, and {player} recovers quickly."
        player.is_injured = False
        add_item(player, "medkit")
    else:
        if not (has_item(player, "armor") or has_item(player, "shield")):
            add_item(player, "shield")
            event.text += f"\nA reinforced shield is pulled from the cargo, hardening {player}'s protection."
        elif not (
            has_item(player, "medkit")
            or has_item(player, "medicine")
            or has_item(player, "potion")
        ):
            add_item(player, "medkit")
            event.text += (
                f"\nA medical pack is included, giving {player} a new layer of safety."
            )
        else:
            event._type = EventType.PASSIVE
            event.text += f"\nThe drop contains great supplies, but {player} already has enough gear to last."

    await player.save()
    return event


async def bird_omen(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    omen_texts = [
        "A flock of black birds circles overhead as if warning {} of approaching danger.",
        "A sudden burst of wings sends the arena into a panic, and {} spots a disturbing omen in the sky.",
        "The birds are too quiet, too still, and their sudden swirl above {} feels like a sign of fate.",
    ]

    event.text = random.choice(omen_texts).format(player)
    event._type = EventType.PASSIVE
    if random.random() < 0.35:
        event._type = EventType.NEGATIVE
        event.text += f"\nThe omen turns out to be a real warning; the chaos that follows leaves {player} injured."
        player.is_injured = True
    else:
        event.text += f"\nThe omen passes, but the unsettling feeling remains in the back of {player}'s mind."

    await player.save()
    return event


async def hunter_lair(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    lair_texts = [
        "{} discovers an abandoned hunter's den stocked with crude weapons and sharp tools.",
        "A hidden hunter's lair is uncovered by {}, and the loot inside is far more useful than expected.",
        "The arena reveals a forgotten hunting camp, and {} claims the remaining supplies before anyone else does.",
    ]

    event.text = random.choice(lair_texts).format(player)
    event._type = EventType.POSITIVE

    if not (has_item(player, "armor") or has_item(player, "shield")):
        add_item(player, "armor")
        event.text += f"\nA reinforced leather rig is found, and {player} straps it on immediately."
    elif not (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        add_item(player, "medkit")
        event.text += f"\nA field kit is tucked beside the gear, giving {player} a second chance in a bad fight."
    else:
        event._type = EventType.PASSIVE
        event.text += f"\nThe den is packed with useful gear, but {player} already has what they need."

    await player.save()
    return event


async def arena_fire(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    fire_texts = [
        "A ring of fire erupts across a patch of the arena, forcing {} to run through the heat to survive.",
        "The ground suddenly ignites around {}, and the panic spreads faster than the flames.",
        "An accidental blaze races through the arena and cuts {} off from safer ground.",
    ]

    event.text = random.choice(fire_texts).format(player)
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe armor shields {player} long enough to escape the worst of it."
        )
        remove_item(player, "armor")
        remove_item(player, "shield")
    elif (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        event._type = EventType.POSITIVE
        event.text += f"\n{player} reaches a water source and survives the fire with a few painful burns."
        remove_item(player, "medkit")
        remove_item(player, "medicine")
        remove_item(player, "potion")
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.5:
            event.text += (
                f"\nThe flames leave {player} badly injured and barely breathing."
            )
            player.is_injured = True
        else:
            event.text += (
                f"\nThe blaze consumes {player} before anyone can do anything."
            )
            player.death_by = "fire"
            player.is_alive = False

    await player.save()
    return event


async def fog_mystery(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    fog_texts = [
        "A heavy fog rolls over the arena, swallowing every sound except the breathing of {}.",
        "The mist thickens until the world disappears, and {} must move carefully through the unknown.",
        "A silent fog creeps through the arena, hiding movement and twisting the senses of {}.",
    ]

    event.text = random.choice(fog_texts).format(player)
    event._type = EventType.PASSIVE

    if player.is_injured:
        event.text += f"\nThe eerie silence gives {player} time to recover a little."
        player.is_injured = False
    elif random.random() < 0.6:
        event.text += f"\nThe fog offers a brief moment of cover, allowing {player} to slip away unseen."
    else:
        event.text += (
            f"\nThe fog is unsettling, but it only deepens the tension of the hunt."
        )

    await player.save()
    return event


async def old_map(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    map_texts = [
        "{} spots an old map half-buried in the mud, and the routes marked on it look promising.",
        "A weathered map leads {} toward a safer path through the arena's dead zones.",
        "A torn map appears beneath a broken shelter and reveals a hidden route to fresh water.",
    ]

    event.text = random.choice(map_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        event.text += (
            f"\nThe route lets {player} avoid danger and recover enough to keep moving."
        )
        player.is_injured = False
    elif not (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        add_item(player, "medkit")
        event.text += f"\nThe map points toward a hidden stash, and {player} gathers a medical kit before moving on."
    else:
        event.text += f"\nThe map is valuable, but {player} has already secured enough survival tools."

    await player.save()
    return event


async def snare_trap(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    trap_texts = [
        "A crude snare hidden in the grass lashes out at {} as they pass by.",
        "A trap set by another tribute snaps shut near {}, leaving them tangled and exposed.",
        "An unseen snare catches {} by the ankle, dragging them into a frantic struggle for freedom.",
    ]

    event.text = random.choice(trap_texts).format(player)
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\nThe armor takes the force of the trap, and {player} escapes with only bruises."
        remove_item(player, "armor")
        remove_item(player, "shield")
    elif (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nA quick wound pack keeps {player} alive long enough to break free."
        )
        remove_item(player, "medkit")
        remove_item(player, "medicine")
        remove_item(player, "potion")
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.55:
            event.text += (
                f"\nThe trap leaves {player} injured and exhausted, but still alive."
            )
            player.is_injured = True
        else:
            event.text += (
                f"\nThe snare tightens around {player} until there is no way out."
            )
            player.death_by = "trap"
            player.is_alive = False

    await player.save()
    return event


async def stolen_signal(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    signal_texts = [
        "A cracked radio signal blares through the arena, and {} is stunned by the sudden Capitol transmission.",
        "The warning signal cuts through the trees, startling {} and everyone nearby.",
        "A strange transmission carries through the air, and {} has a split-second to react before the panic spreads.",
    ]

    event.text = random.choice(signal_texts).format(player)
    event._type = EventType.PASSIVE

    if random.random() < 0.5:
        event.text += (
            f"\nThe broadcast gives {player} a moment to think and move more carefully."
        )
    else:
        event.text += f"\nThe signal is unsettling, and {player} loses precious time in a world of uncertainty."

    await player.save()
    return event


async def ecology_bloom(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    bloom_texts = [
        "A rare bloom opens in the arena, and {} realizes it may provide more than beauty.",
        "Unexpected flowers spread across a ruined clearing, and {} sees an opportunity for rest and recovery.",
        "A bright patch of wildflowers appears around {}, filling the air with color and just a little hope.",
    ]

    event.text = random.choice(bloom_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        event.text += (
            f"\nThe flowers and nearby herbs help {player} recover from their injuries."
        )
        player.is_injured = False
        add_item(player, "herbs")
    else:
        event.text += f"\nThe moment of calm and beauty gives {player} a rare reprieve."

    await player.save()
    return event


async def black_market(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    market_texts = [
        "At the edge of the arena, {} finds a shadowy black market hidden beneath a toppled stall.",
        "A bargain is struck in a clandestine market, and {} is offered a risky deal for survival gear.",
        "Under moonlight, {} stumbles into a secret trading hub where desperate tributes barter for anything useful.",
    ]

    event.text = random.choice(market_texts).format(player)
    event._type = EventType.PASSIVE

    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        pick = random.choice(["knife", "potion", "shield"])
        add_item(player, pick)
        event.text += f"\nThe deal pays off: {player} gains a {pick}."
    else:
        event.text += f"\nThe trader is slick, but {player} leaves with only a story and a lesson."

    await player.save()
    return event


async def graveyard_search(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    grave_texts = [
        "{} searches the ruined graves of previous battles and finds something the arena forgot to bury.",
        "An old cemetery sits in the dark, and {} discovers a weathered survival stash hidden among the stones.",
        "The past haunts this place, but {} finds a handful of useful items among the broken memorials.",
    ]

    event.text = random.choice(grave_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        player.is_injured = False
        event.text += (
            f"\nA forgotten healer's kit restores {player} enough to keep moving."
        )
        add_item(player, "medkit")
    else:
        item = random.choice(["armor", "food", "potion"])
        add_item(player, item)
        event.text += (
            f"\nThe search turns up a {item}, and {player} pockets it quickly."
        )

    await player.save()
    return event


async def moonlit_ritual(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    ritual_texts = [
        "By moonlight, {} stumbles into a silent ritual circle etched into the earth.",
        "The arena's silver glow reveals an old shrine, and {} cannot help but kneel beside it.",
        "A lunar ritual site hums with energy as {} passes through it under a cold night sky.",
    ]

    event.text = random.choice(ritual_texts).format(player)
    if random.random() < 0.6:
        event._type = EventType.POSITIVE
        event.text += f"\nThe ritual grants {player} a brief surge of strength and a charm of protection."
        add_item(player, "charm")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\nThe ritual unsettles {player}, and the eerie energy leaves them shaken and weak."
        player.is_injured = True

    await player.save()
    return event


async def scavenger_hunt(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    hunt_texts = [
        "{} turns the arena into a scavenger hunt and finds a hidden survival bundle in plain sight.",
        "A desperate search through wreckage reveals a stash of useful supplies for {}.",
        "The arena is full of signs, and {} follows them to a secret cache nobody else noticed.",
    ]

    event.text = random.choice(hunt_texts).format(player)
    event._type = EventType.POSITIVE

    loot = random.choice(["food", "medkit", "armor", "potion"])
    add_item(player, loot)
    event.text += f"\nA careful scavenger run yields a {loot}."

    await player.save()
    return event


async def broken_tower(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    tower_texts = [
        "{} climbs a broken tower and finds a precarious lookout point above the arena.",
        "A ruined watchtower drops an old supply box into the hands of {} when the wind finally settles.",
        "The tower offers a view of the arena, and from its cracked ruin {} spies a hidden stash below.",
    ]

    event.text = random.choice(tower_texts).format(player)
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe high ground helps {player} stay safe and spot a quick escape route."
        )
    else:
        event._type = EventType.NEGATIVE
        event.text += (
            f"\nThe climb is treacherous, and {player} slips, twisting an ankle badly."
        )
        player.is_injured = True

    await player.save()
    return event


async def failing_sponsor(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    sponsor_texts = [
        "A sponsor drone crashes near {}, scattering its payload across the mud.",
        "A broken delivery drone drops a strange package beside {}, but not everyone is happy about it.",
        "A sponsor signal flickers, and then a damaged crate lands in front of {} with a strange, ominous label.",
    ]

    event.text = random.choice(sponsor_texts).format(player)
    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        gift = random.choice(["food", "medicine", "shield"])
        add_item(player, gift)
        event.text += f"\nThe damaged gear still contains a useful {gift}."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\nThe cargo explodes in a spray of sparks, leaving {player} injured and furious."
        player.is_injured = True

    await player.save()
    return event


# LEGENDARY EVENTS (Rare, High Impact)


async def legendary_discovery(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    legend_texts = [
        "In a place where no one dared venture, {} discovers an ancient weapon of unimaginable power.",
        "A golden artifact gleams in the ruins, and {} realizes they have found something truly legendary.",
        "The ground opens to reveal the remains of a champion from ages past, and {} claims their legendary gear.",
    ]

    event.text = random.choice(legend_texts).format(player)
    event._type = EventType.POSITIVE

    add_item(player, "legendary_sword")
    event.text += f"\n{player} now wields a legendary weapon that changes everything in the arena."

    await player.save()
    return event


async def arena_collapse(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    collapse_texts = [
        "The arena itself begins to crumble, and massive sections of ground collapse around {}.",
        "An earthquake shakes the arena to its core, and {} is caught in the chaos of collapsing structures.",
        "The walls of the arena start to fail, and {} must flee as everything comes down around them.",
    ]

    event.text = random.choice(collapse_texts).format(player)
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe armor and quick reflexes save {player} from the falling debris."
        )
    elif has_item(player, "legendary_sword"):
        event._type = EventType.POSITIVE
        event.text += f"\nWith their legendary weapon, {player} cuts through the danger with ease."
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.6:
            event.text += (
                f"\nThe collapse leaves {player} badly injured and trapped in rubble."
            )
            player.is_injured = True
        else:
            event.text += (
                f"\nThe collapsing arena claims {player} in a shower of stone and dust."
            )
            player.death_by = "arena collapse"
            player.is_alive = False

    await player.save()
    return event


async def forbidden_vault(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    vault_texts = [
        "{} discovers a sealed vault beneath the arena, and inside is everything needed to win.",
        "A forbidden chamber opens before {}, revealing treasures beyond imagination.",
        "In the deepest part of the arena, {} finds a vault of ancient wealth and power.",
    ]

    event.text = random.choice(vault_texts).format(player)
    event._type = EventType.POSITIVE

    add_item(player, "crown")
    add_item(player, "legendary_sword")
    add_item(player, "potion")
    event.text += (
        f"\n{player} claims the treasures inside, gaining power beyond measure."
    )

    await player.save()
    return event


async def celestial_intervention(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    intervention_texts = [
        "The sky opens and a gift from the heavens falls before {}.",
        "A mysterious divine force grants {} a blessing of immense power.",
        "The arena seems to pause as {} receives an otherworldly gift.",
    ]

    event.text = random.choice(intervention_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        player.is_injured = False
        event.text += f"\n{player} is fully healed by the intervention."

    add_item(player, "divine_favor")
    event.text += (
        f"\n{player} now carries divine favor, granting protection beyond mortal means."
    )

    await player.save()
    return event


async def betrayal_cascade(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    betrayal_texts = [
        "Allies turn on {} in a sudden, vicious betrayal.",
        "{} is surrounded by former allies who have decided to end the games.",
        "In a shocking moment, everyone {} trusted reveals their true intentions.",
    ]

    event.text = random.choice(betrayal_texts).format(player)
    event._type = EventType.NEGATIVE

    if has_item(player, "legendary_sword") or has_item(player, "divine_favor"):
        event._type = EventType.PASSIVE
        event.text += f"\nBut {player}'s power is too great, and the betrayal fails."
    elif has_item(player, "armor") and has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\nFortunately, {player}'s gear is strong enough to survive."
        remove_item(player, "armor")
    else:
        if random.random() < 0.7:
            event.text += f"\n{player} is left injured and alone."
            player.is_injured = True
        else:
            event.text += f"\n{player} falls to the overwhelming numbers."
            player.death_by = "betrayal"
            player.is_alive = False

    await player.save()
    return event


async def final_horizon(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    horizon_texts = [
        "As {} reaches the edge of the arena, they see a way out—a final path to freedom.",
        "{} glimpses the end of the games and feels the weight of hope.",
        "The horizon shifts, and {} realizes they are close to ending this nightmare.",
    ]

    event.text = random.choice(horizon_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        player.is_injured = False
        event.text += f"\nThe promise of escape heals {player}'s spirit and body."

    add_item(player, "hope")
    event.text += f"\n{player} carries the momentum toward the final battle."

    await player.save()
    return event


# CHALLENGE EVENTS (Test player skills and loadouts)


async def cliff_climb(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    climb_texts = [
        "{} faces a treacherous cliff that blocks the safest route through the arena.",
        "A sheer cliff rises before {}, offering a shortcut or a deadly obstacle.",
        "{} must decide whether to risk the dangerous climb or find another way.",
    ]

    event.text = random.choice(climb_texts).format(player)

    if has_item(player, "rope") or has_item(player, "charm"):
        event._type = EventType.POSITIVE
        event.text += f"\n{player} uses their gear to safely climb and gain time on the competition."
        add_item(player, "rope")
    elif has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\nThe armor provides grip and protection; {player} scales the cliff successfully."
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.65:
            event.text += f"\n{player} slips halfway up and falls hard, suffering serious injuries."
            player.is_injured = True
        else:
            event.text += (
                f"\n{player} loses their grip and plummets to the rocks below."
            )
            player.death_by = "cliff fall"
            player.is_alive = False

    await player.save()
    return event


async def poison_swamp(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    swamp_texts = [
        "{} trudges through a sickly green swamp filled with noxious fumes.",
        "A fetid bog stretches across the arena, and {} must cross it to survive.",
        "The ground becomes soft and poisonous as {} ventures into a toxic marsh.",
    ]

    event.text = random.choice(swamp_texts).format(player)

    if has_item(player, "potion") or has_item(player, "medicine"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nWith medicine, {player} resists the poison and emerges unharmed."
        )
        remove_item(player, "potion")
        remove_item(player, "medicine")
    elif has_item(player, "armor"):
        event._type = EventType.POSITIVE
        event.text += f"\nThe armor seals out most toxins; {player} crosses with difficulty but survives."
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.5:
            event.text += (
                f"\nThe poison burns {player}'s lungs and leaves them weakened."
            )
            player.is_injured = True
        else:
            event.text += f"\nThe toxic marsh overwhelms {player}, and they sink beneath the surface."
            player.death_by = "poison swamp"
            player.is_alive = False

    await player.save()
    return event


async def ice_lake(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    ice_texts = [
        "{} encounters a frozen lake that might be the fastest crossing—or a death trap.",
        "A sheet of ice stretches across a chasm, and {} must decide whether to risk it.",
        "The treacherous ice creaks beneath {}'s feet as they attempt a dangerous crossing.",
    ]

    event.text = random.choice(ice_texts).format(player)

    if has_item(player, "charm") or has_item(player, "rope"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\n{player} carefully uses their equipment to cross the ice safely."
        )
        add_item(player, "rope")
    elif has_item(player, "armor"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe armor's weight helps {player} stay grounded; they cross with care."
        )
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.6:
            event.text += f"\nThe ice cracks beneath {player}, and the freezing water leaves them badly hurt."
            player.is_injured = True
        else:
            event.text += f"\nThe ice breaks completely, and {player} is pulled under by the current."
            player.death_by = "ice lake"
            player.is_alive = False

    await player.save()
    return event


async def abandoned_bunker(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    bunker_texts = [
        "{} discovers an abandoned military bunker filled with pre-games equipment.",
        "An old reinforced shelter sits hidden beneath the arena, and {} claims its contents.",
        "Inside a buried bunker, {} finds enough supplies to last for days.",
    ]

    event.text = random.choice(bunker_texts).format(player)
    event._type = EventType.POSITIVE

    loot = random.choice(["armor", "medkit", "rope", "knife"])
    add_item(player, loot)
    event.text += f"\nAmong the dust and rust, {player} finds a valuable {loot}."

    if random.random() < 0.2:
        event.text += f"\nBut the bunker isn't empty—something stirs in the darkness."
        player.is_injured = True

    await player.save()
    return event


async def ambush(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    game, player, event = init_utils(**kwargs)

    players = await game.players.filter(is_alive=True).exclude(id=player.id)
    if not players:
        event._type = EventType.PASSIVE
        event.text = f"{player} finds nothing but the sound of their own footsteps."
        await player.save()
        return event

    attacker = random.choice(players)

    ambush_texts = [
        "{} is suddenly ambushed by {} in a surprise attack!",
        "Out of nowhere, {} leaps from hiding and attacks {} with ferocity.",
        "{} is caught off-guard as {} springs a carefully planned trap.",
    ]

    event.text = random.choice(ambush_texts).format(attacker, player)
    event._type = EventType.NEGATIVE

    # Ambushed players have disadvantage
    defender_weight = 5 if has_item(player, "armor") else 2
    attacker_weight = 10 + (5 if has_item(attacker, "armor") else 0)

    choice = random.choices([player, attacker], [defender_weight, attacker_weight])[0]
    winner = attacker if choice == attacker else player
    loser = player if choice == attacker else attacker

    if loser.is_alive:
        if random.random() < 0.4:
            event.text += f"\n{loser} manages to survive but is left gravely wounded."
            loser.is_injured = True
            await loser.save()
        else:
            event.text += (
                f"\n{loser} does not survive the sudden onslaught of {winner}."
            )
            loser.death_by = f"ambush by {str(winner).replace(chr(96), '')}"
            loser.is_alive = False
            await loser.save()
            await winner.killed_players.add(player)

    await player.save()
    return event


async def endurance_trial(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    trial_texts = [
        "{} faces a brutal physical trial that tests the very limits of endurance.",
        "The arena presents an obstacle course that {} must navigate to continue.",
        "A grueling marathon of terrain challenges tests {}'s will to survive.",
    ]

    event.text = random.choice(trial_texts).format(player)

    food_items = sum(
        1
        for item in (player.inventory or [])
        if str(item).strip().lower() in ["food", "medkit", "medicine", "potion"]
    )

    if food_items >= 2:
        event._type = EventType.POSITIVE
        event.text += f"\nWith proper supplies, {player} powers through and gains significant ground."
        add_item(player, "stamina")
    elif has_item(player, "charm"):
        event._type = EventType.POSITIVE
        event.text += f"\n{player}'s inner strength carries them through the trial."
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.6:
            event.text += f"\n{player} is exhausted and injured after barely completing the trial."
            player.is_injured = True
        else:
            event.text += (
                f"\n{player} collapses before the trial ends, too weakened to continue."
            )
            player.death_by = "exhaustion"
            player.is_alive = False

    await player.save()
    return event


async def treasure_maze(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    maze_texts = [
        "{} stumbles into an ancient maze filled with treasures and traps.",
        "A labyrinth of corridors appears, and {} navigates through seeking riches.",
        "{} enters a twisting maze with the promise of great rewards—and great danger.",
    ]

    event.text = random.choice(maze_texts).format(player)

    trap_chance = 0.6
    if has_item(player, "map") or has_item(player, "charm"):
        trap_chance = 0.25

    if random.random() > trap_chance:
        event._type = EventType.POSITIVE
        treasure = random.choice(["crown", "legendary_sword", "shield", "medkit"])
        add_item(player, treasure)
        event.text += (
            f"\nAfter navigating the maze, {player} claims a valuable {treasure}."
        )
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\nA hidden trap activates, and {player} is caught in the maze's defense system."
        if has_item(player, "armor"):
            event.text += (
                f"\nThe armor absorbs most of the damage, but {player} is still hurt."
            )
            remove_item(player, "armor")
            player.is_injured = False
        else:
            player.is_injured = True

    await player.save()
    return event


async def hidden_city(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    city_texts = [
        "{} discovers the ruins of a hidden city buried beneath the arena.",
        "An ancient civilization's remains surface, revealing {}'s path to power.",
        "Crumbling structures of a lost city appear before {}, filled with forgotten knowledge.",
    ]

    event.text = random.choice(city_texts).format(player)
    event._type = EventType.POSITIVE

    add_item(player, "ancient_relic")
    event.text += f"\n{player} claims an ancient relic that resonates with old power."

    if not player.is_injured and random.random() < 0.3:
        add_item(player, "map")
        event.text += f"\nAlongside the relic, a map of the arena itself is discovered."

    await player.save()
    return event


async def avalanche(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    avalanche_texts = [
        "A massive avalanche tears through the arena, and {} runs for their life.",
        "The mountain cannot hold, and tons of snow and rock descend toward {}.",
        "Without warning, the peak of the arena collapses in a catastrophic avalanche.",
    ]

    event.text = random.choice(avalanche_texts).format(player)

    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe armor shields {player} from the worst of the crushing snow."
        )
        remove_item(player, "armor")
        remove_item(player, "shield")
    elif has_item(player, "charm") or has_item(player, "divine_favor"):
        event._type = EventType.POSITIVE
        event.text += f"\nBy luck or fate, {player} finds shelter just in time."
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.5:
            event.text += f"\n{player} is buried under snow and ice, severely injured."
            player.is_injured = True
        else:
            event.text += (
                f"\nThe avalanche sweeps {player} away, and they are never found."
            )
            player.death_by = "avalanche"
            player.is_alive = False

    await player.save()
    return event


# DISASTER EVENTS (Arena-wide catastrophes)


async def earthquake(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    quake_texts = [
        "The earth beneath {} trembles violently as a massive earthquake shakes the arena.",
        "Sudden violent tremors throw {} to the ground and split the terrain wide open.",
        "The arena heaves and buckles as {} struggles to stay upright during an earthquake.",
    ]

    event.text = random.choice(quake_texts).format(player)

    if has_item(player, "armor"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe armor keeps {player} protected as the ground shifts beneath them."
        )
    elif has_item(player, "charm"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\n{player} finds stable ground just before a massive chasm opens."
        )
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.55:
            event.text += f"\n{player} tumbles into a crevasse and is badly injured by falling rocks."
            player.is_injured = True
        else:
            event.text += (
                f"\nThe ground swallows {player} entirely before any help can arrive."
            )
            player.death_by = "earthquake"
            player.is_alive = False

    await player.save()
    return event


async def flooding(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    flood_texts = [
        "A sudden flash flood tears through the arena, and {} is caught in the rushing water.",
        "Heavy rain causes a massive surge of water to sweep across the battlefield toward {}.",
        "An enormous wall of water crashes through the arena, and {} is swept into the current.",
    ]

    event.text = random.choice(flood_texts).format(player)

    if has_item(player, "rope") or has_item(player, "charm"):
        event._type = EventType.POSITIVE
        event.text += f"\nUsing quick thinking and their gear, {player} reaches higher ground safely."
    elif has_item(player, "armor"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe armor's weight keeps {player} grounded long enough to escape."
        )
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.5:
            event.text += f"\n{player} is swept downstream but manages to reach shore, badly bruised."
            player.is_injured = True
        else:
            event.text += (
                f"\nThe torrent is too strong, and {player} is lost to the flood."
            )
            player.death_by = "flooding"
            player.is_alive = False

    await player.save()
    return event


async def meteor_strike(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    meteor_texts = [
        "The sky lights up as a meteor streaks overhead and crashes into the arena near {}.",
        "A fireball descends from above, and {} watches as it impacts the ground with catastrophic force.",
        "Without warning, a massive celestial object plummets toward the arena, narrowly missing {}.",
    ]

    event.text = random.choice(meteor_texts).format(player)

    if has_item(player, "divine_favor") or has_item(player, "charm"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nFate protects {player}, and they emerge unharmed from the chaos."
        )
    elif has_item(player, "armor"):
        event._type = EventType.POSITIVE
        event.text += (
            f"\nThe impact throws {player} back, but the armor saves their life."
        )
    else:
        event._type = EventType.NEGATIVE
        if random.random() < 0.6:
            event.text += (
                f"\nThe shockwave slams into {player}, leaving them severely wounded."
            )
            player.is_injured = True
        else:
            event.text += f"\nThe meteor's impact kills {player} instantly."
            player.death_by = "meteor strike"
            player.is_alive = False

    await player.save()
    return event


# SOCIAL EVENTS (Alliance and player interaction)


async def rivalry_ignite(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    game, player, event = init_utils(**kwargs)
    players = await game.players.filter(is_alive=True).exclude(id=player.id)
    if not players:
        event._type = EventType.PASSIVE
        event.text = f"{player} stands alone, with no one left to challenge."
        await player.save()
        return event

    rival = random.choice(players)

    rivalry_texts = [
        "{} spots {} across the arena, and old rivalries are reignited.",
        "The sight of {} stirs something dangerous in {}'s heart—ancient rivalry awakens.",
        "{} and {} lock eyes, and the air crackles with tension and old hatred.",
    ]

    event.text = random.choice(rivalry_texts).format(player, rival)
    event._type = EventType.PASSIVE

    add_item(player, "rivalry_marker")
    event.text += f"\n{player} becomes obsessed with confronting {rival}, willing to take any risk."

    await player.save()
    return event


async def healing_circle(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    circle_texts = [
        "{} discovers a group of tributes who are willing to share medicine and food.",
        "A peaceful gathering of players offers {} shelter and healing supplies.",
        "In a rare moment of compassion, tributes band together to help {}.",
    ]

    event.text = random.choice(circle_texts).format(player)
    event._type = EventType.POSITIVE

    if player.is_injured:
        player.is_injured = False
        event.text += f"\n{player} is fully healed by the collective care of the group."

    add_item(player, "medkit")
    add_item(player, "food")
    event.text += f"\n{player} gains supplies and a temporary sense of peace."

    await player.save()
    return event


async def betrayal_warning(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    warning_texts = [
        "A fellow tribute warns {} of an impending ambush, risking their own safety.",
        "{} overhears a plot against their life and barely escapes with time to spare.",
        "An unlikely ally secretly tips {} off to a deadly trap in their path.",
    ]

    event.text = random.choice(warning_texts).format(player)
    event._type = EventType.POSITIVE

    add_item(player, "warning_gift")
    event.text += (
        f"\nThanks to the warning, {player} survives with new resolve and gratitude."
    )

    await player.save()
    return event


# MYSTERY EVENTS (Supernatural and unknown)


async def ghost_encounter(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    ghost_texts = [
        "{} is haunted by the specter of a fallen tribute, reaching out from beyond death.",
        "A ghostly apparition appears before {}, whispering ancient secrets of the arena.",
        "{} sees the phantom of a past victor, watching them with hollow eyes.",
    ]

    event.text = random.choice(ghost_texts).format(player)
    event._type = EventType.PASSIVE

    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        event.text += f"\nThe ghost grants {player} a vision of hidden treasure."
        add_item(player, "spirit_gift")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\nThe phantom's touch leaves {player} shaken and injured."
        player.is_injured = True

    await player.save()
    return event


async def time_distortion(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    time_texts = [
        "{} experiences a strange moment where time seems to slow around them.",
        "Reality bends, and {} finds themselves moving at impossible speed.",
        "{} watches helplessly as time fractures, granting them visions of multiple timelines.",
    ]

    event.text = random.choice(time_texts).format(player)
    event._type = EventType.PASSIVE

    if random.random() < 0.6:
        event._type = EventType.POSITIVE
        event.text += (
            f"\n{player} uses this gift to escape danger and gain valuable time."
        )
        add_item(player, "temporal_edge")
    else:
        event._type = EventType.NEGATIVE
        event.text += (
            f"\nThe distortion leaves {player} disoriented and struggling to function."
        )
        player.is_injured = True

    await player.save()
    return event


async def oracle_riddle(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    oracle_texts = [
        "An ancient oracle appears before {} and speaks a cryptic riddle.",
        "{} encounters a mysterious voice that poses a deadly puzzle.",
        "A ghostly presence challenges {} with a riddle that could save or doom them.",
    ]

    event.text = random.choice(oracle_texts).format(player)

    if has_item(player, "map") or has_item(player, "charm"):
        event._type = EventType.POSITIVE
        event.text += f"\n{player} solves the riddle and receives a legendary reward."
        add_item(player, "oracle_blessing")
    elif random.random() < 0.5:
        event._type = EventType.POSITIVE
        event.text += f"\nBy luck, {player} answers correctly and gains knowledge."
        add_item(player, "knowledge_shard")
    else:
        event._type = EventType.NEGATIVE
        event.text += (
            f"\n{player} fails the test, and the oracle's curse leaves them weakened."
        )
        player.is_injured = True

    await player.save()
    return event


# SCARCITY EVENTS (Resource competition)


async def last_water_source(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    water_texts = [
        "{} finds the last known water source in the arena—but it's being guarded.",
        "A precious spring reveals itself to {}, but others are converging on the same location.",
        "{} discovers fresh water, but the sound of footsteps suggests they're not alone.",
    ]

    event.text = random.choice(water_texts).format(player)

    game, player, event = init_utils(**kwargs)
    players = await game.players.filter(is_alive=True).exclude(id=player.id)

    if not players or random.random() < 0.4:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} claims the water and gains a crucial advantage."
        add_item(player, "fresh_water")
    else:
        event._type = EventType.NEGATIVE
        rival = random.choice(players)
        event.text += (
            f"\nBut {rival} arrives first, and {player} must choose: fight or flee."
        )

    await player.save()
    return event


async def seed_cache(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    seed_texts = [
        "{} discovers a cache of seeds and supplies for growing food.",
        "A hidden garden emerges, offering {} the chance to cultivate survival.",
        "{} finds ancient seeds that could sustain multiple tributes.",
    ]

    event.text = random.choice(seed_texts).format(player)
    event._type = EventType.POSITIVE

    add_item(player, "seeds")
    add_item(player, "food")
    event.text += f"\n{player} gains both immediate sustenance and long-term hope."

    await player.save()
    return event


async def medicine_shortage(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    shortage_texts = [
        "{} realizes that medicine is running dangerously low in the arena.",
        "A plague of infection spreads, and {} watches as survival items vanish.",
        "{} discovers that all healing supplies in a region have been destroyed.",
    ]

    event.text = random.choice(shortage_texts).format(player)
    event._type = EventType.NEGATIVE

    if (
        has_item(player, "medkit")
        or has_item(player, "medicine")
        or has_item(player, "potion")
    ):
        event._type = EventType.POSITIVE
        event.text += f"\nLuckily, {player} has supplies before the shortage hits hard."
    else:
        if player.is_injured:
            event.text += (
                f"\n{player}'s injuries have no remedy, and infection sets in."
            )
            player.death_by = "infection"
            player.is_alive = False
        else:
            event.text += f"\n{player} desperately searches for any medical supplies they can find."

    await player.save()
    return event


async def armor_arms_race(**kwargs) -> Event:
    _, player, event = init_utils(**kwargs)

    race_texts = [
        "{} witnesses other tributes heavily armored, spurring a desperate gear hunt.",
        "Reports spread that {} is seeing heavily protected opponents everywhere.",
        "{} realizes the competition for protective gear is becoming increasingly desperate.",
    ]

    event.text = random.choice(race_texts).format(player)
    event._type = EventType.PASSIVE

    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\n{player} already has superior gear and feels confident."
    else:
        event._type = EventType.NEGATIVE
        event.text += (
            f"\n{player} feels vulnerable and must prioritize finding protection."
        )

    await player.save()
    return event


# === EXPANDED STANDARD EVENTS ===
async def underground_cavern(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} discovered an ancient underground cavern system."
    if random.random() < 0.6:
        event._type = EventType.POSITIVE
        treasures = random.choice(["knife", "map", "stamina", "potion"])
        add_item(player, treasures)
        event.text += f"\n{player} found a {treasures} hidden in the depths."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} got trapped briefly and lost precious time."

    await player.save()
    return event


async def crystal_pool(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} found a shimmering crystal pool with strange properties."
    if random.random() < 0.7:
        event._type = EventType.POSITIVE
        add_item(player, "divine_favor")
        event.text += f"\n{player} felt blessed by the pool's mystical energy."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} drank from the pool and was poisoned."
        player.is_injured = True

    await player.save()
    return event


async def merchant_caravan(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} encountered a mysterious merchant caravan in the arena."
    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        items_for_trade = random.choice(["food", "potion", "medicine"])
        add_item(player, items_for_trade)
        event.text += f"\n{player} made a deal and gained {items_for_trade}."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was overcharged and scammed!"

    await player.save()
    return event


async def ancient_ruins(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} explored the crumbling ancient ruins."
    if random.random() < 0.55:
        event._type = EventType.POSITIVE
        add_item(player, "ancient_relic")
        event.text += f"\n{player} unearthed an ancient relic of power."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} triggered a trap and was injured."
        player.is_injured = True

    await player.save()
    return event


async def windstorm(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"A fierce windstorm swept through the arena, affecting {player}."
    if has_item(player, "armor") or has_item(player, "shield"):
        event._type = EventType.POSITIVE
        event.text += f"\n{player}'s gear protected them from the fierce winds."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was blown around and disoriented."

    await player.save()
    return event


async def blood_moon(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"A blood moon rose over the arena, casting an eerie glow on {player}."
    event._type = random.choice([EventType.POSITIVE, EventType.NEGATIVE])
    if event._type == EventType.POSITIVE:
        add_item(player, "hope")
        event.text += f"\n{player} felt empowered by the crimson light."
    else:
        event.text += f"\n{player} was filled with dread and paranoia."

    await player.save()
    return event


async def beast_den(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} stumbled into a dangerous beast den."
    if random.random() < 0.45:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} managed to escape and claim some bones for tools."
        add_item(player, "knife")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was savagely attacked by the beasts."
        player.is_injured = True

    await player.save()
    return event


async def forgotten_shrine(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} discovered a forgotten shrine deep in the wilderness."
    if random.random() < 0.65:
        event._type = EventType.POSITIVE
        add_item(player, "blessing")
        event.text += f"\n{player} received a blessing from the ancient spirits."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} desecrated the shrine and was cursed."

    await player.save()
    return event


async def shadow_hunter(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} was hunted by a shadow figure throughout the day."
    players_count = len([p for p in game.players if p.is_alive and p != player])
    if players_count <= 2 or random.random() < 0.4:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} managed to evade the hunter."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was wounded by the relentless hunter."
        player.is_injured = True

    await player.save()
    return event


async def oasis(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} found a hidden oasis in the barren wasteland."
    if random.random() < 0.7:
        event._type = EventType.POSITIVE
        add_item(player, "fresh_water")
        event.text += f"\n{player} refreshed and rejuvenated at the oasis."
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} found the oasis was a mirage, draining their hope."

    await player.save()
    return event


async def eclipse_event(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"An eclipse darkened the sky, casting all into shadow momentarily."
    event._type = EventType.PASSIVE
    if random.random() < 0.6:
        event.text += f"\n{player} used the darkness to their advantage."
        add_item(player, "knowledge_shard")
    else:
        event.text += f"\n{player} was disoriented by the sudden darkness."

    await player.save()
    return event


# === EXPANDED LEGENDARY EVENTS ===
async def volcano_eruption(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"A massive volcano erupted, forever changing the arena landscape!"
    if random.random() < 0.3:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} survived and found molten treasure."
        add_item(player, "legendary_sword")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was caught in the lava flow."
        player.death_by = "volcano eruption"
        player.is_alive = False

    await player.save()
    return event


async def time_rift(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"A rift in time opened, and {player} was pulled into temporal chaos!"
    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} emerged with glimpses of the future."
        add_item(player, "temporal_edge")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was aged rapidly by the temporal forces."
        player.is_injured = True

    await player.save()
    return event


async def godly_wrath(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"The gods themselves turned their wrath upon {player}!"
    if has_item(player, "divine_favor"):
        event._type = EventType.POSITIVE
        event.text += f"\n{player}'s divine favor protected them from the wrath."
        remove_item(player, "divine_favor")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was struck down by divine punishment."
        player.death_by = "godly wrath"
        player.is_alive = False

    await player.save()
    return event


# === EXPANDED CHALLENGE EVENTS ===
async def dragon_encounter(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} encountered a dragon guarding an ancient hoard!"
    has_weapon = has_item(player, "legendary_sword") or has_item(player, "knife")
    if has_weapon and random.random() < 0.5:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} defeated the dragon and claimed its treasure."
        add_item(player, "crown")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} barely escaped the dragon's fire."
        player.is_injured = True

    await player.save()
    return event


async def cursed_temple(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} entered a cursed temple shrouded in dark magic."
    if random.random() < 0.4:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} broke the curse and found the temple's treasure."
        add_item(player, "oracle_blessing")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was cursed and weakened by the temple's magic."
        player.is_injured = True

    await player.save()
    return event


async def void_crossing(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} attempted to cross the void between dimensions."
    if has_item(player, "temporal_edge") or random.random() < 0.35:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} successfully crossed into a new realm of power."
        add_item(player, "knowledge_shard")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was lost between dimensions."
        player.death_by = "void"
        player.is_alive = False

    await player.save()
    return event


# === EXPANDED SOCIAL EVENTS ===
async def alliance_forged(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    players = [p for p in game.players if p.is_alive and p != player]
    if players:
        ally = random.choice(players)
        event.text = f"{player} and {ally} forged a powerful alliance!"
        event._type = EventType.POSITIVE
        add_item(player, "hope")
    else:
        event.text = f"{player} sought alliance but found no one."
        event._type = EventType.PASSIVE

    return event


async def betrayal_confirmed(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    players = [p for p in game.players if p.is_alive and p != player]
    if players:
        betrayer = random.choice(players)
        event.text = f"{betrayer} betrayed {player} in the cruelest way possible!"
        event._type = EventType.NEGATIVE
        if random.random() < 0.5:
            player.is_injured = True
            event.text += f"\n{player} was wounded by the treachery."
    else:
        event.text = f"{player} had no one to betray them."
        event._type = EventType.PASSIVE

    await player.save()
    return event


# === EXPANDED MYSTERY EVENTS ===
async def forbidden_knowledge(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} uncovered forbidden knowledge of the games' true nature."
    event._type = random.choice([EventType.POSITIVE, EventType.NEGATIVE])
    if event._type == EventType.POSITIVE:
        add_item(player, "knowledge_shard")
        event.text += f"\n{player} harnessed the knowledge for power."
    else:
        event.text += f"\n{player} was consumed by the weight of the truth."

    await player.save()
    return event


async def entity_whispers(**kwargs) -> Event:
    game, player, event = init_utils(**kwargs)

    event.text = f"{player} heard whispers from an unknown entity."
    if random.random() < 0.5:
        event._type = EventType.POSITIVE
        event.text += f"\n{player} understood the entity's guidance."
        add_item(player, "spirit_gift")
    else:
        event._type = EventType.NEGATIVE
        event.text += f"\n{player} was tormented by the entity's malicious whispers."

    await player.save()
    return event


# Event list
event_list: list[Event] = [
    # Standard Events (Common, balanced)
    Event(weight=200, callback=nothing),
    Event(weight=70, callback=wild_animals),
    Event(weight=50, callback=poisonous),
    Event(weight=60, callback=chest),
    Event(weight=50, callback=sponsors),
    Event(weight=90, callback=fight_player),
    Event(weight=42, callback=storm),
    Event(weight=55, callback=hidden_cache),
    Event(weight=45, callback=river_crossing),
    Event(weight=34, callback=alliance_offer),
    Event(weight=40, callback=food_cache),
    Event(weight=38, callback=ritual_site),
    Event(weight=52, callback=supply_drop),
    Event(weight=30, callback=bird_omen),
    Event(weight=28, callback=hunter_lair),
    Event(weight=36, callback=arena_fire),
    Event(weight=24, callback=fog_mystery),
    Event(weight=32, callback=old_map),
    Event(weight=30, callback=snare_trap),
    Event(weight=22, callback=stolen_signal),
    Event(weight=26, callback=ecology_bloom),
    Event(weight=20, callback=black_market),
    Event(weight=18, callback=graveyard_search),
    Event(weight=19, callback=moonlit_ritual),
    Event(weight=24, callback=scavenger_hunt),
    Event(weight=21, callback=broken_tower),
    Event(weight=17, callback=failing_sponsor),
    # Expanded Standard Events
    Event(weight=25, callback=underground_cavern),
    Event(weight=28, callback=crystal_pool),
    Event(weight=23, callback=merchant_caravan),
    Event(weight=26, callback=ancient_ruins),
    Event(weight=29, callback=windstorm),
    Event(weight=24, callback=blood_moon),
    Event(weight=20, callback=beast_den),
    Event(weight=22, callback=forgotten_shrine),
    Event(weight=19, callback=shadow_hunter),
    Event(weight=27, callback=oasis),
    Event(weight=18, callback=eclipse_event),
    # Legendary Events (Low Weight - Rare, High Impact)
    Event(weight=6, callback=legendary_discovery),
    Event(weight=7, callback=arena_collapse),
    Event(weight=5, callback=forbidden_vault),
    Event(weight=8, callback=celestial_intervention),
    Event(weight=4, callback=betrayal_cascade),
    Event(weight=6, callback=final_horizon),
    # Expanded Legendary Events
    Event(weight=5, callback=volcano_eruption),
    Event(weight=6, callback=time_rift),
    Event(weight=4, callback=godly_wrath),
    # Challenge Events (Test skill and loadout)
    Event(weight=15, callback=cliff_climb),
    Event(weight=14, callback=poison_swamp),
    Event(weight=16, callback=ice_lake),
    Event(weight=18, callback=abandoned_bunker),
    Event(weight=25, callback=ambush),
    Event(weight=12, callback=endurance_trial),
    Event(weight=10, callback=treasure_maze),
    Event(weight=9, callback=hidden_city),
    Event(weight=11, callback=avalanche),
    # Expanded Challenge Events
    Event(weight=16, callback=dragon_encounter),
    Event(weight=14, callback=cursed_temple),
    Event(weight=11, callback=void_crossing),
    # Disaster Events (Arena-wide catastrophes)
    Event(weight=8, callback=earthquake),
    Event(weight=7, callback=flooding),
    Event(weight=6, callback=meteor_strike),
    # Social Events (Alliance and player interaction)
    Event(weight=13, callback=rivalry_ignite),
    Event(weight=11, callback=healing_circle),
    Event(weight=10, callback=betrayal_warning),
    # Expanded Social Events
    Event(weight=12, callback=alliance_forged),
    Event(weight=11, callback=betrayal_confirmed),
    # Mystery Events (Supernatural and unknown)
    Event(weight=9, callback=ghost_encounter),
    Event(weight=8, callback=time_distortion),
    Event(weight=7, callback=oracle_riddle),
    # Expanded Mystery Events
    Event(weight=8, callback=forbidden_knowledge),
    Event(weight=7, callback=entity_whispers),
    # Scarcity Events (Resource competition)
    Event(weight=12, callback=last_water_source),
    Event(weight=10, callback=seed_cache),
    Event(weight=9, callback=medicine_shortage),
    Event(weight=8, callback=armor_arms_race),
]


events_weights = [event.weight for event in event_list]


# Get random event for the game
async def get_random_event() -> Event:
    """Returns a random event from the event list."""
    return random.choices(event_list, weights=events_weights)[0]
