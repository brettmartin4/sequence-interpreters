from test.support import interpreters
from textwrap import dedent
import os
import threading
import time
from threading import Lock
    

def cleanup_interpreters():
    for i in interpreters.list_all():
        if i.id == 0:
            continue
        try:
            print(f"Cleaning up interpreter: {i}")
        except RuntimeError:
            pass


def data_handler(send_file, recv_file, interp_id, mutex):

    count = 0
    while count < 10:

        # Send data
        with mutex:   # Acquire mutex lock
            with open(send_file, 'w') as file:
                file.seek(0)
                file.write(f"Data from interp {interp_id}: {count}")
                file.truncate()

        # Recv data
        while True:
            try:
                with mutex:   # Acquire mutex lock
                    with open(recv_file, 'r+') as file:
                        file_size = os.fstat(file.fileno()).st_size

                        if file_size == 0:
                            continue

                        file.seek(0)
                        data = file.read()
                        print(f"Data received: {data}")
                        file.truncate(0)

                        break
            except IOError as e:
                if e.errno != 11:  # Ignore "Resource temporarily unavailable" error
                    raise
                pass

        count += 1
        time.sleep(1)

def main():

    # Get current interpreter
    cur = interpreters.get_current()
    main_interp = interpreters.get_main()

    mutex = Lock()

    current_directory = os.getcwd()

    sub_queue_path = os.path.join(current_directory, 'sub-queue.txt')
    main_queue_path = os.path.join(current_directory, 'main-queue.txt')

    # Create files:
    for path in [main_queue_path, sub_queue_path]:
        with open(path, 'w') as file:
            pass

    # MAIN THREAD ONLY
    if(main_interp.id == cur.id):
        
        recv_file = main_queue_path
        send_file = sub_queue_path

        # Create subinterpreter for the second thread
        interp = interpreters.create()
        print(f"Sub-interpreter ID: {interp}\n")

        # Load current script so it can be ran from subinterpreter
        file_path = './par_test_5.py'
        with open(file_path, 'r') as file:
            file_contents = file.read()

        # Format code with appropriate whitespace
        code = dedent(file_contents)

        # Create new thread to run subinterpreter on
        #interp.run(code)
        t = threading.Thread(target=interp.run, args=(code,))
        t.start()
        time.sleep(1)

    # SUBINTERPRETER ONLY
    else:
        recv_file = sub_queue_path
        send_file = main_queue_path

    data_handler(send_file, recv_file, cur.id, mutex)

    time.sleep(1)

    if(main_interp.id == cur.id):
        cleanup_interpreters()


if __name__ == '__main__':
    main()