# This example shows how to use websocket or REST to receive an event about a user's win.
# In game_utils\GamesManager.py go to the "winner_callback" method and add the following code:

from utils.models import PlayerModel  # ignore

## For REST:
import aiohttp


async def winner_callback(self, winner: PlayerModel) -> str:
    ENDPOINT = "..."

    async with aiohttp.ClientSession() as cs:
        async with cs.post(ENDPOINT, data={"winner_id": winner.user_id}) as res:
            return await res.text()


## For websocket:
import websockets
import json


async def winner_callback(self, winner: PlayerModel) -> str:
    ENDPOINT = "..."

    async with websockets.connect(f"wss://{ENDPOINT}") as ws:
        await ws.send(json.dumps({"winner_id": winner.user_id}))
        return await ws.recv()
