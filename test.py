import mido
import time
import asyncio

msg_list = []

def make_stream():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    def callback(msg):
        #loop.call_soon_threadsafe(queue.put_nowait, message)
        msg_list.append(msg)
    async def stream():
        while True:
            yield await queue.get()
    return callback, stream()

async def print_messages():
    # create a callback/stream pair and pass callback to mido
    inp_name = mido.get_input_names()[1]
    callback, stream = make_stream()
    inp = mido.open_input(inp_name)
    inp.callback = callback
    print(inp)

    end_time = time.time() + 5
    # print messages as they come just by reading from stream
    print("You have 5 seconds to press a button")
    while True:
        if len(msg_list):
            print("you win")
            break
        if time.time() > end_time:
            print("you lose")
            break

asyncio.run(print_messages())
