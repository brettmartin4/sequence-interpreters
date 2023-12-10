"""
Example SeQUeNCe script for demonstrating discrete event simulation, with subinterpreters.

"""


from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import time
from test.support import interpreters
from textwrap import dedent
import os


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

    def close(self) -> None:
        self.opening = False
    

def cleanup_interpreters():
    for i in interpreters.list_all():
        if i.id ==0:
            continue
        try:
            #print(f"Cleaning up interpreter: {i}")
            i.close()
        except RuntimeError:
            pass


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
    sub_interp = interpreters.create()
    #print(f"Spawning new sub-interpreter w/ ID: {sub_interp}...")
    code = dedent(f"""
                import time
                for i in range({NUM_ITER}):
                    time.sleep({SLEEP_TIME})
                """)
        
    # Begin timing output
    t_start = time.time()

    # Run code in sub-interpreter
    sub_interp.run(code, channels=None)

    # Run simulation
    tl.run()

    # Conclude timing output
    t_end = time.time()

    cleanup_interpreters()

    print(f"[SUB-INTERPRETERS] Simulation executed in {t_end - t_start}")
    print(f" - Number of iterations: {NUM_ITER}")
    print(f" - Sleep time per iteration: {SLEEP_TIME} s")


if __name__ == "__main__":
    main()