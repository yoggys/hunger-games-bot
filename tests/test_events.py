import asyncio
import random

import pytest
from tortoise import Tortoise, connections

from game_utils.Events import Event
from game_utils.events_data import event_list
from utils.models import GameModel, PlayerModel

loop = asyncio.get_event_loop_policy().new_event_loop()


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
