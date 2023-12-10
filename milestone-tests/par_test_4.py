from test.support import interpreters
from textwrap import dedent
import os
import argparse
import threading
import time
import fcntl
import subprocess

# Get current interpreter
cur = interpreters.get_current()
main_interp = interpreters.get_main()

print("Spawned interpreters...")
time.sleep(3)

if(main_interp.id == cur.id):

    interp = interpreters.create()
    print(f"Sub-interpreter ID: {interp}")

    # Load current script so it can be ran from subinterpreter
    file_path = './par_text_4.py'
    with open(file_path, 'r') as file:
        file_contents = file.read()

    # Format code with appropriate whitespace
    code = dedent(file_contents)

    # Create new thread to run subinterpreter on
    #t = threading.Thread(target=interp.run, args=(code,))
    #t.start()
    interp.run(code)

    fifo_path_A_to_B = 'fifo_A_to_B'
    fifo_path_B_to_A = 'fifo_B_to_A'

    for fifo in [fifo_path_A_to_B, fifo_path_B_to_A]:
        if not os.path.exists(fifo):
            os.mkfifo(fifo)
        else:
            print(f"FIFO already exists at: {fifo}")

    fifo_A_to_B = os.open(fifo_path_A_to_B, os.O_WRONLY)

    print("Opened FIFO. Begin writing...")
    data_to_send = "Hello from proc a"
    os.write(fifo_A_to_B,data_to_send.encode())
    os.close(fifo_A_to_B)

    fifo_B_to_A = os.open(fifo_path_B_to_A, os.O_RDONLY)

    data_received = os.read(fifo_B_to_A, 4096).decode()
    print(f"Data recvd from Proc A: {data_received}")

    os.close(fifo_B_to_A)

else:
    fifo_path_A_to_B = 'fifo_A_to_B'
    fifo_path_B_to_A = 'fifo_B_to_A'

    for fifo in [fifo_path_A_to_B, fifo_path_B_to_A]:
        if not os.path.exists(fifo):
            os.mkfifo(fifo)
        else:
            print(f"FIFO already exists at: {fifo}")

    fifo_A_to_B = os.open(fifo_path_A_to_B, os.O_RDONLY)

    data_received = os.read(fifo_A_to_B, 4096).decode()
    print(f"Data recvd from Proc B: {data_received}")

    os.close(fifo_A_to_B)

    fifo_B_to_A = os.open(fifo_path_B_to_A, os.O_WRONLY)

    data_to_send = "Hello from proc b"
    os.write(fifo_B_to_A,data_to_send.encode())
    os.close(fifo_B_to_A)