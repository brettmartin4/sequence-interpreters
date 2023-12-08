from test.support import interpreters
from textwrap import dedent
import os
import argparse
import threading
import time
import fcntl
import subprocess

#from .t_timeline import ThreadedTimeline

from thread_timeline import ThreadedTimeline, TholdNode


def cleanup_interpreters():
    for i in interpreters.list_all():
        if i.id == 0:
            continue
        try:
            print(f"Cleaning up interpreter: {i}")
        except RuntimeError:
            pass


def data_handler(send_fifo, recv_fifo, interp_id):
    count = 0
    result = subprocess.run(['ls'], stdout=subprocess.PIPE, text=True)
    output = result.stdout
    print(output)
    while count < 10:

        # Send data
        #send = open(send_fifo, 'w')
        #send.write(f"Data from interp {interp_id}: {count}")
        #send.flush()
        #send.close()

        with os.open(send_fifo, os.O_WRONLY | os.O_NONBLOCK) as send:
            flags = fcntl.fcntl(send, fcntl.F_GETFL)
            fcntl.fcntl(send, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            send.write(count)
            print(f"Interp {interp_id} sent: {count}")

        # Recv data
        #recv = open(recv_fifo, 'r')
        #recv_data = recv.readline().strip()
        with os.open(recv_fifo, os.O_RDONLY | os.O_NONBLOCK):
            print(f"Interp {interp_id} received: {recv_data}")

        count += 1
        time.sleep(1)


def main():

    # Get current interpreter
    cur = interpreters.get_current()
    main_interp = interpreters.get_main()

    print("Spawned interpreters...")
    time.sleep(3)

    current_directory = os.getcwd()

    # Set up unidirectional FIFO from main interpreter to subinterpreter
    try:
        sub_queue_path = os.path.join(current_directory, 'sub-queue')
        #sub_queue_path = 'sub-queue'
        os.mkfifo(sub_queue_path)
    except FileExistsError:
        pass

    # Set up unidirectional FIFO from subinterpreter to main interpreter
    try:
        main_queue_path = os.path.join(current_directory, 'main-queue')
        #main_queue_path = 'main-queue'
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
        file_path = './par_test_3.py'
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

    data_handler(send_fifo, recv_fifo, cur.id)

    time.sleep(3)

    cleanup_interpreters()


if __name__ == '__main__':
    main()