#! /home/brett/RESEARCH/cpython

"""
benchmark sending data between interpreters

"""

from test.support import interpreters
from textwrap import dedent
import os
import threading
import pickle
import time
import numpy


SIZE_DATA = 1000000
FIFO_NAME = 'newfifo'


def cleanup_interpreters():
    for i in interpreters.list_all():
        if i.id ==0:
            continue
        try:
            print(f"Cleaning up interpreter: {i}")
            i.close()
        except RuntimeError:
            pass


def main():

    test = numpy.arange(10)
    print(test)

    # Set up sub-interpreter
    interp = interpreters.create()

    t = threading.Thread(target=interp.run, args=(dedent(
        """
            import os
            import pickle
            import numpy
            #test = numpy.arange(10)
            msgs = list(range(1000000))
            serialized_msgs = pickle.dumps((msgs,))
            try:
                os.mkfifo('newfifo')
            except FileExistsError:
                pass
            pipe_write = os.open('newfifo', os.O_WRONLY)
            os.write(pipe_write, serialized_msgs)
            os.close(pipe_write)
        """),))

    t.start()

    # Wait for interpreter to spin up FIFO
    time.sleep(4)

    start_time = time.time()

    # Read data in from fifo
    with open(FIFO_NAME, "rb") as fifo:
        data = fifo.read()

    print(f"Total transmission time (subinterp/fifo): {time.time() - start_time} seconds")

    deserialized_data = pickle.loads(data)
    print(f"Received data from subinterpreter of size {len(deserialized_data[0])}")

    time.sleep(4)
    cleanup_interpreters()

    try:
        os.unlink(FIFO_NAME)
    except OSError as e:
        print(f"Error deleting FIFO: {e}")


if __name__ == "__main__":
    main()
