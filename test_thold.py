from test.support import interpreters
from textwrap import dedent
import os
import argparse
import threading

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

    current_directory = os.getcwd()

    # Set up unidirectional FIFO from main interpreter to subinterpreter
    try:
        sub_queue_path = os.path.join(current_directory, 'sub-queue')
        os.mkfifo(sub_queue_path)
    except FileExistsError:
        pass

    # Set up unidirectional FIFO from subinterpreter to main interpreter
    try:
        main_queue_path = os.path.join(current_directory, 'main-queue')
        os.mkfifo(main_queue_path)
    except FileExistsError:
        pass

    # MAIN THREAD ONLY
    if(main_interp.id == cur.id):
        print(f"Interpreter {cur.id} initializing in main interpreter ({os.getcwd()})...")

        recv_fifo = main_queue_path
        send_fifo = sub_queue_path

        # Create subinterpreter for the second thread
        interp = interpreters.create()
        print(f"Sub-interpreter ID: {interp}")

        # Load current script so it can be ran from subinterpreter
        file_path = './test_thold.py'
        with open(file_path, 'r') as file:
            file_contents = file.read()

        # Format code with appropriate whitespace
        code = dedent(file_contents)

        # Create new thread to run subinterpreter on
        t = threading.Thread(target=interp.run, args=(code,))
        t.start()

    # SUBINTERPRETER ONLY
    else:
        print(f"Interpreter {cur.id} initializing in subinterpreter ({os.getcwd()})...")
        recv_fifo = sub_queue_path
        send_fifo = main_queue_path

    size = len(interpreters.list_all())

    node_num = args.total_node // size
    timeline = ThreadedTimeline(recv_fifo, send_fifo, args.lookahead, args.stop_time)
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
    timeline.run()

    print(timeline.id, timeline.now(), timeline.events.top().time, timeline.sync_counter, timeline.run_counter,
          sum([len(buf) for buf in timeline.event_buffer]), len(timeline.events))
    


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('total_node', type=int)
    parser.add_argument('init_work', type=int)
    parser.add_argument('lookahead', type=int)
    parser.add_argument('stop_time', type=int)

    args = parser.parse_args()

    main(args)
