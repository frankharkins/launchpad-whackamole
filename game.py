import mido
import time
import random
import asyncio

def coords_to_midi(coords):
    x, y = coords
    return x + (y*16)

def midi_to_coords(midi):
    x = midi % 16
    y = midi // 16
    return (x, y)

class Launchpad():
    def __init__(self, num=1):
        self.name = mido.get_input_names()[num]
        self.inp = mido.open_input(self.name)
        self.out = mido.open_output(self.name)
        self.dur = 3  # time to react
        self.IS_WORKING = False
        self.FAILED = False
        self.FAILED_COORDS = None
        self.LIVES = 2
        self.SCORE = 0
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
        self.LIVES = 3

        for life in range(self.LIVES):
            control = 104 + life
            msg = mido.Message('control_change', value=10, control=control)
            self.launchpad.out.send(msg)

    def clear(self):
        for v in range(8):
            control = 104 + v
            msg = mido.Message('control_change', value=0, control=control)
            self.launchpad.out.send(msg)

    def decrement(self):
        msg = mido.Message('control_change', value=0, control=103 + self.LIVES)
        self.launchpad.out.send(msg)
        self.LIVES -= 1

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
        if self.launchpad.FAILED:
            pass
        elif self.is_target:
            self.is_target = False
        elif strict:
            self.set(10)
            if self.launchpad.health_bar.LIVES:
                self.launchpad.health_bar.decrement()
                time.sleep(2)
                if not self.is_target:
                    self.set(0)
            else:
                self.launchpad.FAILED = True
        else:
            self.is_target = False
            self.set(5)
            time.sleep(0.2)
            self.set(0)
            self.is_target = False

    def be_target(self):
        self.is_target = True
        dur = self.launchpad.dur
        start_time = time.time()
        colours = [100, 60, 127, 110, None]
        self.set(colours.pop(0))
        while True:
            if self.launchpad.FAILED:
                self.set(0)
                break
            if not self.is_target:
                self.set(0)
                self.launchpad.SCORE += 1
                break
            now = time.time()
            if now > (start_time + dur/3):
                start_time = now
                colour = colours.pop(0)
                if colour is not None:
                    self.set(colour)
                else:
                    self.set(127)
                    self.launchpad.FAILED_COORDS = self.coords
                    self.launchpad.FAILED = True
                    self.set(127)
                    break
            time.sleep(0.1)


async def main():
    lp = Launchpad(1)
    lp.clear()
    loop = asyncio.get_event_loop()
    DUR = 2

    def testing_callback(msg):
        if not msg.is_meta:
            if msg.type == 'note_on':
                lp.IS_WORKING = True

    lp.inp.callback = testing_callback
    print("Press any button to start...")
    async def wait_for_is_working():
        while not lp.IS_WORKING:
            time.sleep(0.1)
        print("Working")
        return None

    task = loop.create_task(wait_for_is_working())
    await task

    START_TIME = time.time()

    def callback(msg):
        if not msg.is_meta:
            if msg.type == 'note_on':
                if msg.velocity > 1:
                    x, y = midi_to_coords(msg.note)
                    lp.squares[x][y].press(strict=(START_TIME+5)<time.time())

    lp.inp.callback = callback

    tasks = []
    next_increase = time.time() + 10
    while not lp.FAILED:
        x, y = random.randint(0, 7), random.randint(0, 7)
        tasks.append(loop.run_in_executor(None,
            lp.squares[x][y].be_target
            ))
        if time.time() > next_increase:
            next_increase = time.time() + 5
            DUR /= 1.5
        await asyncio.sleep((random.random()*2*DUR)+0.1)
    lp.inp.callback = None
    
    for task in tasks:
        await task
    print("You failed :(")
    print(f"Your score is {lp.SCORE}")

asyncio.run(main())
