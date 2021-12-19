import mido
import time
import random
import asyncio
from tools import midi_to_coords, coords_to_midi

class Game():
    def __init__(self):
        self.react_time = 3
        self.start_dur = 1.6
        self.dur_ramp = 1.3
        self.score = 0
        self.lives = 3
        self.failed = False
        self.failed_reason = None

    async def setup_launchpad(self):
        loop = asyncio.get_event_loop()
        self.launchpad = Launchpad(self)
        self.launchpad.clear()

        # Want to check input from the launchpad is working
        # (sometimes need to press 'menu' for messages to
        # come through.

        def _testing_callback(msg):
            if not msg.is_meta:
                if msg.type == 'control_change':
                    if msg.control == 111:
                        self.launchpad.is_working = True

        self.launchpad.inp.callback = _testing_callback

        # Display message and light up menu button
        print("Press 'menu' to start...", end="")
        menu_btn_on = mido.Message('control_change',
                                    control=111,
                                    value=127)
        self.launchpad.out.send(menu_btn_on)

        # Wait for menu button press
        async def wait_for_is_working():
            while not self.launchpad.is_working:
                time.sleep(0.1)
            print(" detected menu button press.")
            return None
        task = loop.create_task(wait_for_is_working())
        await task

        # Turn off menu button light and turn off callback
        menu_btn_off = mido.Message('control_change',
                            control=111,
                            value=0)
        self.launchpad.out.send(menu_btn_off)
        self.launchpad.out.callback = None

        return True
            

    async def play(self):

        loop = asyncio.get_event_loop()
        dur = self.start_dur
        tasks = []
        START_TIME = time.time()

        # First, set up launchpad callback

        def _callback(msg):
            if not msg.is_meta:
                if msg.type == 'note_on':
                    if msg.velocity > 1:
                        x, y = midi_to_coords(msg.note)
                        tasks.append(loop.run_in_executor(
                                None,
                                self.launchpad.squares[x][y].press,
                                (START_TIME+5)<time.time()
                                ))

        self.launchpad.inp.callback = _callback

        # Start main game loop
        next_increase = time.time() + 10
        while not self.failed:
            x, y = random.randint(0, 7), random.randint(0, 7)
            tasks.append(
                    loop.run_in_executor(
                        None,
                        self.launchpad.squares[x][y].be_target))
            if time.time() > next_increase:
                next_increase = time.time() + 5
                dur /= self.dur_ramp
            await asyncio.sleep(
                    (2*dur*random.random()) + 0.15)

        # End game & tidy up
        self.launchpad.inp.callback = None
        for task in tasks:
            await task
        print(f"You failed :(, {self.failed_reason}")
        print(f"Your score is {self.score}")

        # wait a bit to let other lights finish their thing
        task = loop.create_task(asyncio.sleep(2))
        await task

        return True




class Launchpad():
    def __init__(self, game, num=1):
        self.game = game
        self.name = mido.get_input_names()[num]
        self.inp = mido.open_input(self.name)
        self.out = mido.open_output(self.name)
        self.is_working = False
        self.health_bar = HealthBar(self)
        self.squares = []
        for x in range(8):
            self.squares.append([])
            for y in range(8):
                self.squares[x].append(
                        Square(self, (x, y)))
    def clear(self):
        for row in self.squares:
            for square in row:
                square.set(0)


class HealthBar():
    def __init__(self, launchpad):
        self.launchpad = launchpad
        lives = launchpad.game.lives

        for life in range(lives):
            control = 104 + life
            msg = mido.Message('control_change', value=10, control=control)
            self.launchpad.out.send(msg)

    def clear(self):
        for v in range(8):
            control = 104 + v
            msg = mido.Message('control_change', value=0, control=control)
            self.launchpad.out.send(msg)

    def decrement(self):
        msg = mido.Message('control_change', value=0,
                control=103 + self.launchpad.game.lives)
        self.launchpad.out.send(msg)
        self.launchpad.game.lives -= 1

class Square():
    def __init__(self, launchpad, coords):
        self.launchpad = launchpad
        self.coords = coords
        self.midi = coords_to_midi(coords)
        self.state = 'OFF'
        self.is_target = False

    def set(self, state):
        self.state = state
        msg = mido.Message('note_on',
                velocity=state,
                note=self.midi)
        self.launchpad.out.send(msg)

    def press(self, strict):
        if self.launchpad.game.failed:
            pass
        elif self.is_target:
            self.is_target = False
        elif strict:
            self.set(10)
            if self.launchpad.game.lives:
                self.launchpad.health_bar.decrement()
                time.sleep(2)
                if not self.is_target:
                    self.set(5)
                    time.sleep(1)
                if not self.is_target:
                    self.set(0)
            else:
                self.launchpad.game.failed_reason = "pressed wrong buttons too many times."
                self.launchpad.game.failed = True
        else:
            self.is_target = False
            self.set(5)
            time.sleep(0.2)
            self.set(0)
            self.is_target = False

    def be_target(self):
        self.is_target = True
        dur = self.launchpad.game.react_time
        start_time = time.time()
        colours = [100, 60, 110, 127, None]
        self.set(colours.pop(0))
        while True:
            if self.launchpad.game.failed:
                self.set(0)
                break
            if not self.is_target:
                self.set(0)
                self.launchpad.game.score += 1
                print(f"Score: {self.launchpad.game.score}", end="\r")
                break
            now = time.time()
            if now > (start_time + dur/3):
                start_time = now
                colour = colours.pop(0)
                if colour is not None:
                    self.set(colour)
                else:
                    self.set(127)
                    self.launchpad.game.failed_reason = "you missed one."
                    self.launchpad.game.failed = True
                    self.set(127)
                    break
            time.sleep(0.05)


