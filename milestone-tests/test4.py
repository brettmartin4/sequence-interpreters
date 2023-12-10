"""
Example SeQUeNCe script for demonstrating discrete event simulation, with threading.

"""


from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import time
import threading
from numba import jit


NUM_ITER = 100000
SLEEP_TIME = 0.00001


class Store(object):
    def __init__(self, tl: Timeline):
        self.opening = False
        self.timeline = tl

    def open(self) -> None:
        self.opening = True

    def toggle_open(self) -> None:
        self.opening = not self.opening

    def random_event(self) -> None:
        for i in range(NUM_ITER):
            time.sleep(SLEEP_TIME)

    def close(self) -> None:
        self.opening = False


def main():
    # Create timeline for running entire simulation
    tl = Timeline()
    tl.show_progress = False

    # Create instance of a store than can be opened and closed
    store = Store(tl)

    # Add a bunch of events
    for i in range(NUM_ITER):
        new_proc = Process(store, 'toggle_open', [])
        new_event = Event(i, new_proc)
        tl.schedule(new_event)

    # Set up the simulation to run in separate thread from the Store's sleep method
    t1 = threading.Thread(target=store.random_event)
    t2 = threading.Thread(target=tl.run)

    # Begin timing simulation
    t_start = time.time()

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # End timing simulation
    t_end = time.time()

    print(f"[THREADING] Simulation executed in {t_end - t_start} seconds")
    print(f" - Number of iterations: {NUM_ITER}")
    print(f" - Sleep time per iteration: {SLEEP_TIME} s")

if __name__ == "__main__":
    main()
