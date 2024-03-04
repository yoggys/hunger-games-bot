import argparse
import asyncio
from os import getenv
from typing import Optional

from dotenv import load_dotenv
from tortoise import Tortoise, connections

from utils.client import HungerGamesBot

load_dotenv(override=True)

parser = argparse.ArgumentParser(description="YogBot main file.")
parser.add_argument("-s", "--sync", action="store_true", help="Sync commands.")
args = parser.parse_args()

client: Optional[HungerGamesBot] = None


async def init():
    await Tortoise.init(db_url="sqlite://main.db", modules={"models": ["utils.models"]})
    await Tortoise.generate_schemas()

    global client
    client = HungerGamesBot(args.sync)
    client.run(getenv("TOKEN"))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init())
    except (KeyboardInterrupt, Exception) as e:
        if not isinstance(e, KeyboardInterrupt):
            print(e)
        loop.run_until_complete(connections.close_all())
        if client and not client.is_closed():
            loop.run_until_complete(client.close())
    finally:
        if loop.is_running():
            loop.close()
