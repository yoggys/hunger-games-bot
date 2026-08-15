import asyncio
import random
from types import SimpleNamespace

import pytest
from tortoise import Tortoise, connections

from game_utils.GamesManager import GamesManager

from game_utils.Events import Event
from game_utils.events_data import event_list
from utils.models import GameModel, PlayerModel

loop = asyncio.new_event_loop()


async def initialize():
    await Tortoise.init(
        db_url="sqlite://:memory:", modules={"models": ["utils.models"]}
    )
    await Tortoise.generate_schemas()


def cleanup():
    loop.run_until_complete(Tortoise._drop_databases())
    loop.run_until_complete(connections.close_all())


@pytest.fixture(scope="session", autouse=True)
def initialize_tests(request: pytest.FixtureRequest):
    loop.run_until_complete(initialize())
    request.addfinalizer(cleanup)


@pytest.mark.asyncio()
async def test_event_pool_is_expanded():
    assert len(event_list) >= 12


@pytest.mark.asyncio()
async def test_events():
    for event in event_list:
        # Test events type
        assert isinstance(event, Event)

        # Test events attributes
        assert event._type == None
        assert event.text == None
        assert event.weight > 0
        assert event.callback != None

        # Test model creation
        game = await GameModel.create(guild_id=0, channel_id=0, owner_id=0)
        for index in range(0, 10):
            await PlayerModel.create(game=game, user_id=index)
        players = await PlayerModel.filter(game=game)

        await game.fetch_related("players")
        assert len(game.players) == len(players) and list(game.players) == players

        # Test events callback with required arguments
        player = random.choice(players)
        event = await event.execute(game=game, player=player, event=event)

        # Test events attributes after callback
        assert event.text != None
        assert event._type != None


@pytest.mark.asyncio()
async def test_rare_items_are_part_of_event_correlations(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.99)
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

    game = await GameModel.create(guild_id=1, channel_id=1, owner_id=1)
    player = await PlayerModel.create(game=game, user_id=99)

    cases = [
        ("oracle_riddle", ["oracle_blessing"], "oracle_blessing"),
        ("time_distortion", ["temporal_edge"], "temporal_edge"),
        ("ghost_encounter", ["spirit_gift"], "spirit_gift"),
        ("last_water_source", ["fresh_water"], "fresh_water"),
        ("seed_cache", ["seeds"], "food"),
        ("rivalry_ignite", ["rivalry_marker"], "rivalry_marker"),
    ]

    for callback_name, inventory, expected_item in cases:
        player.inventory = inventory
        player.is_injured = False
        player.is_alive = True
        await player.save()

        callback = {
            "oracle_riddle": __import__(
                "game_utils.events_data", fromlist=["oracle_riddle"]
            ).oracle_riddle,
            "time_distortion": __import__(
                "game_utils.events_data", fromlist=["time_distortion"]
            ).time_distortion,
            "ghost_encounter": __import__(
                "game_utils.events_data", fromlist=["ghost_encounter"]
            ).ghost_encounter,
            "last_water_source": __import__(
                "game_utils.events_data", fromlist=["last_water_source"]
            ).last_water_source,
            "seed_cache": __import__(
                "game_utils.events_data", fromlist=["seed_cache"]
            ).seed_cache,
            "rivalry_ignite": __import__(
                "game_utils.events_data", fromlist=["rivalry_ignite"]
            ).rivalry_ignite,
        }[callback_name]

        event = Event(weight=1, callback=callback)
        result = await event.execute(game=game, player=player, event=event)

        assert result._type is not None
        assert (
            result._type
            != __import__(
                "game_utils.events_data", fromlist=["EventType"]
            ).EventType.NEGATIVE
        )
        assert expected_item in [
            str(item).strip().lower() for item in (player.inventory or [])
        ], (
            callback_name,
            result.text,
            player.inventory,
        )


@pytest.mark.asyncio()
async def test_end_game_tracks_winner_only_via_relation(monkeypatch):
    game = await GameModel.create(guild_id=10, channel_id=20, owner_id=30)
    winner = await PlayerModel.create(game=game, user_id=101, is_alive=True)
    await PlayerModel.create(game=game, user_id=102, is_alive=False)

    class DummyChannel:
        async def send(self, *args, **kwargs):
            return None

    manager = GamesManager(
        client=SimpleNamespace(
            get_channel=lambda *_args, **_kwargs: DummyChannel(),
            get_guild=lambda *_args, **_kwargs: SimpleNamespace(
                get_member=lambda *_: None
            ),
        )
    )

    async def fake_winner_callback(winner):
        return None

    monkeypatch.setattr(manager, "winner_callback", fake_winner_callback)

    result = await manager.end_game(game=game)

    stored_winner = await PlayerModel.get(id=winner.id)
    assert result is None
    assert stored_winner.winner_of_id == game.id
    assert not hasattr(stored_winner, "is_winner")
