from test.support import interpreters
from textwrap import dedent
from threading import Thread, Lock
import os
import argparse
import time

from thread_timeline import ThreadedTimeline, TholdNode
    

def cleanup_interpreters():
    """
    Close all sub-interpreters to prevent fatal Python error on program exit.

    Raises:
        RuntimeError: Thrown when an interpreter cannot be properly closed.
    """

    for i in interpreters.list_all():
        if i.id == 0:
            continue
        try:
            print(f"Cleaning up interpreter: {i}")
            i.close()
        except RuntimeError:
            pass


def main():

    total_node = 2
    init_work = 300
    lookahead = 1
    stop_time = 1000

    # Get current interpreter
    cur = interpreters.get_current()
    main_interp = interpreters.get_main()

    # Establish paths for file queues for reading/writing between interpreters
    current_directory = os.getcwd()

    # MAIN THREAD ONLY
    if(main_interp.id == cur.id):

        # Create subinterpreter for the second thread
        interp = interpreters.create()
        print(f"Sub-interpreter ID: {interp}")

        # Create interpreter channels (1 set per interpreter)
        # create_channel method could probably be called once on each
        # interpreter, but for now, I'm calling it once per interpreter here
        # for testing purposes so I can manually assign channel ends.
        main_r, main_s = interpreters.create_channel()
        sub_r, sub_s = interpreters.create_channel()

        recv_channel = sub_r
        send_channel = main_s

        # Load current script so it can be ran from subinterpreter
        file_path = os.path.join(current_directory, 'test_thold.py')
        with open(file_path, 'r') as file:
            file_contents = file.read()

        # Format code with appropriate whitespace
        code = dedent(file_contents)

        # Create new thread to run subinterpreter on
        t = Thread(target=interp.run, args=(code,))
        t.setDaemon(True)

        # This next line takes this entire script and runs it using the newly-
        # spawned sub-interpreter.
        # Eveything under "MAIN THREAD ONLY" will run in the main interpreter
        # and everything under "SUBINTERPRETER ONLY" will run in the
        # subinterpreter. Everything else runs in both.
        t.start()

    # SUBINTERPRETER ONLY
    else:
        # Set proper channels for sub-interpreter
        for grouping in interpreters.list_all_channels():
            if grouping[0].id == cur.id:
                (sub_r, sub_s) = grouping
            else:
                (main_r, main_s) = grouping
        recv_channel = main_r
        send_channel = sub_s

    size = len(interpreters.list_all())

    # Calculate total num nodes per interpreter
    node_num = total_node // size
    # Create Threaded Timeline instance for current interpreter
    timeline = ThreadedTimeline(recv_channel, send_channel, lookahead, 
                                stop_time)
    neighbors = list(range(total_node))
    neighbors = list(map(str, neighbors))
    # Divide nodes between timelines, either adding to current timeline or to
    # current timeline's foreign entity list
    for i in range(total_node):
        if i // node_num == cur.id:
            node = TholdNode(str(i), timeline, init_work // 
                             total_node, lookahead, neighbors)
        else:
            timeline.foreign_entities[str(i)] = i // node_num

    # Initialize and run simulation
    print(f"Initializing timelines from interpreter: {cur.id}...")
    timeline.init()
    print("Running timelines...")
    start_time = time.time()
    timeline.run()
    print(f"Simulation ran in {time.time() - start_time} sec")


    """
    Prints simulation results:
     - Interpreter (or Timeline) ID
     - Timeline's current time (or time at which sim stops)
     - Time at which the top-most event occurs
     - Synchronization counter
     - Timeline run counter
     - Number of events remaining in the event buffer
     - Number of events in the timeline
    """
    print(timeline.id, timeline.now(), timeline.events.top().time, 
          timeline.sync_counter, timeline.run_counter,
          sum([len(buf) for buf in timeline.event_buffer]), 
          len(timeline.events))
    
    # Sleep for a moment to ensure other interpreter is done processing data
    time.sleep(1)
    
    if(main_interp.id == cur.id):
        # Clean up interpreters
        cleanup_interpreters()


if __name__ == "__main__":

    #parser = argparse.ArgumentParser()
    #parser.add_argument('total_node', type=int)
    #parser.add_argument('init_work', type=int)
    #parser.add_argument('lookahead', type=int)
    #parser.add_argument('stop_time', type=int)

    #args = parser.parse_args()

    #main(args)
    main()
