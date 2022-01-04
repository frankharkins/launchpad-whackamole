import mido
import time
import random
import asyncio

from classes import Game

game = Game()

asyncio.run(game.setup_launchpad())
asyncio.run(game.play())
while asyncio.run(game.ask_play_again()):
    print("Playing again...")
    asyncio.run(game.play())
asyncio.run(game.end())
print("Exiting, thank you for playing!")
