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
        self.squares = []
        for x in range(8):
            self.squares.append([])
            for y in range(8):
                self.squares[x].append(
                        Square(self, (x, y)))



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

async def main():
    lp = Launchpad(1)
    loop = asyncio.get_event_loop()

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

    def callback(msg):
        if not msg.is_meta:
            if msg.type == 'note_on':
                x, y = midi_to_coords(msg.note)
                print(x, y)
                lp.squares[x][y].is_target = False

    lp.inp.callback = callback

    tasks = []
    game_start_time = time.time()
    while not lp.FAILED:
        x, y = random.randint(0, 7), random.randint(0, 7)
        tasks.append(loop.run_in_executor(None,
            lp.squares[x][y].be_target
            ))
        await asyncio.sleep(random.random()*2*(lp.dur/4))
    lp.inp.callback = None
    
    for task in tasks:
        await task
    print("You missed one.")

asyncio.run(main())
