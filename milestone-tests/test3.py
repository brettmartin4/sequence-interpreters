"""
Example SeQUeNCe script for demonstrating discrete event simulation.

"""


from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import time


class Store(object):
    def __init__(self, tl: Timeline):
        self.opening = False
        self.timeline = tl

    def open(self) -> None:
        self.opening = True

    def random_event(self) -> None:
        for i in range(10):
            print(f"Sleeping, round {i}")
            time.sleep(1)
            print(f"  - Exiting sleep, round {i}")


    def close(self) -> None:
        self.opening = False


# Create timeline for running entire simulation
tl = Timeline()
tl.show_progress = False

# Create instance of a store than can be opened and closed
store = Store(tl)

# open store at 7:00
open_proc = Process(store, 'open', [])
open_event = Event(7, open_proc)
tl.schedule(open_event)

tl.run()

print(tl.time, store.opening)

# close store at 19:00
close_proc = Process(store, 'close', [])
close_event = Event(19, close_proc)
tl.schedule(close_event)

tl.run()

print(tl.time, store.opening)

# what if we schedule two events before run simulation

tl.time = 0
tl.schedule(open_event)
tl.schedule(close_event)
tl.run()
print(tl.time, store.opening)


# what if we swap the order of scheduling two events

tl.time = 0
tl.schedule(open_event)
tl.schedule(close_event)
tl.run()
print(tl.time, store.opening)
