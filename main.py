import argparse
from os import getenv

from dotenv import load_dotenv

from utils.client import HungerGamesBot

load_dotenv(override=True)

parser = argparse.ArgumentParser(description="YogBot main file.")
parser.add_argument("-s", "--sync", action="store_true", help="Sync commands.")
args = parser.parse_args()

if __name__ == "__main__":
    client: HungerGamesBot = HungerGamesBot(args.sync)
    client.run(getenv("TOKEN"))
