from test.support import interpreters
from textwrap import dedent
from threading import Thread, Lock
import os
import argparse
import time

from thread_timeline import ThreadedTimeline, TholdNode
    

def cleanup_interpreters():
    for i in interpreters.list_all():
        if i.id == 0:
            continue
        try:
            print(f"Cleaning up interpreter: {i}")
        except RuntimeError:
            pass


def main(args):

    # Get current interpreter
    cur = interpreters.get_current()
    main_interp = interpreters.get_main()

    # Create mutex for locking files for reading/writing between interpreters
    mutex = Lock()

    # Establish paths for file queues for reading/writing between interpreters
    current_directory = os.getcwd()
    sub_queue_path = os.path.join(current_directory, 'sub-queue.pkl')
    main_queue_path = os.path.join(current_directory, 'main-queue.pkl')
    signal_file = os.path.join(current_directory, 'signal.txt')

    # Create queue files:
    for path in [main_queue_path, sub_queue_path]:
        with open(path, 'w') as file:
            pass

    # MAIN THREAD ONLY
    if(main_interp.id == cur.id):
        print(f"Interpreter {cur.id} initializing in main interpreter ({os.getcwd()})...")

        if os.path.exists(signal_file):
            os.remove(signal_file)

        recv_file = main_queue_path
        send_file = sub_queue_path

        # Create subinterpreter for the second thread
        interp = interpreters.create()
        print(f"Sub-interpreter ID: {interp}")

        # Load current script so it can be ran from subinterpreter
        file_path = os.path.join(current_directory, 'test_thold.py')
        with open(file_path, 'r') as file:
            file_contents = file.read()

        # Format code with appropriate whitespace
        code = dedent(file_contents)

        # Create new thread to run subinterpreter on
        t = Thread(target=interp.run, args=(code,))
        t.start()

        # Must sleep for a moment while sub-interpreter spins online.
        # Otherwise, errors might occur.
        #time.sleep(1)

    # SUBINTERPRETER ONLY
    else:
        print(f"Interpreter {cur.id} initializing in subinterpreter ({os.getcwd()})...")
        recv_file = sub_queue_path
        send_file = main_queue_path

    size = len(interpreters.list_all())

    node_num = args.total_node // size
    timeline = ThreadedTimeline(recv_file, send_file, mutex, args.lookahead, args.stop_time)
    neighbors = list(range(args.total_node))
    neighbors = list(map(str, neighbors))
    for i in range(args.total_node):
        if i // node_num == cur.id:
            node = TholdNode(str(i), timeline, args.init_work // args.total_node, args.lookahead, neighbors)
        else:
            timeline.foreign_entities[str(i)] = i // node_num

    print(f"Initializing timelines from interpreter: {cur.id}...")
    timeline.init()
    print("Running timelines...")
    start_time = time.time()
    timeline.run()
    print(f"Simulation ran in {time.time() - start_time} sec")


    # Print simulation results
    print(timeline.id, timeline.now(), timeline.events.top().time, timeline.sync_counter, timeline.run_counter,
          sum([len(buf) for buf in timeline.event_buffer]), len(timeline.events), timeline.read_ops, timeline.write_ops)
    
    time.sleep(1)

    # Signals other interpreter to quit if hung up
    with open(signal_file, "w") as file:
        pass
    
    if(main_interp.id == cur.id):
        # Clean up interpreters
        time.sleep(1)
        cleanup_interpreters()
        # Clean up files
        for file in [main_queue_path, sub_queue_path, signal_file]:
            if os.path.exists(file):
                os.remove(file)



if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('total_node', type=int)
    parser.add_argument('init_work', type=int)
    parser.add_argument('lookahead', type=int)
    parser.add_argument('stop_time', type=int)

    args = parser.parse_args()

    main(args)
