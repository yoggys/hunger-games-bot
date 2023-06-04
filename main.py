from os import getenv

from dotenv import load_dotenv

from utils.client import HungerGamesBot

load_dotenv(override=True)

if __name__ == "__main__":
    client: HungerGamesBot = HungerGamesBot()
    client.run(getenv("TOKEN"))
