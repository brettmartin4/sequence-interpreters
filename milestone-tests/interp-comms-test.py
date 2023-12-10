from test.support import interpreters
from textwrap import dedent
import os
import threading


FIFO_NAME = 'newfifo'


# Set up sub-interpreter
interp = interpreters.create()

t = threading.Thread(target=interp.run, args=(dedent(
    f"""
        import os
        try:
            os.mkfifo('newfifo')
        except FileExistsError:
            pass
        pipe_write = os.open('newfifo', os.O_WRONLY)
        os.write(pipe_write, b"Data from subinterp")
        os.close(pipe_write)
    """),))

t.start()

fifo_read = os.open(FIFO_NAME, os.O_RDONLY)
data = os.read(fifo_read, 100)
print(f"Received data: {data.decode()}")

os.close(fifo_read)

try:
    os.unlink(FIFO_NAME)
except OSError as e:
    print(f"Error deleting FIFO: {e}")
