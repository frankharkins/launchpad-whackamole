import mido
import time
import random
import asyncio

from classes import Game

game = Game()

asyncio.run(game.setup_launchpad())
asyncio.run(game.play())
