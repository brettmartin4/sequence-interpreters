from test.support import interpreters
#import _xxsubinterpreters as interpreters
import os
from textwrap import dedent
from threading import Thread
import pickle


interp = interpreters.create()
main_r, main_s = interpreters.create_channel()
sub_r, sub_s = interpreters.create_channel()

code = dedent("""
    from test.support import interpreters
    import pickle
    print(interpreters.list_all_channels()[0])
    print(interpreters.list_all_channels()[1])
    
    for grouping in interpreters.list_all_channels():
        if grouping[0].id == interpreters.get_current().id:
            (sub_r, sub_s) = grouping
        else:
            (main_r, main_s) = grouping
    print(f"{sub_s},{sub_r},{main_s},{main_r}")
              
    
    sub_s.send_nowait(b'sub-spam')
    print(f"Sub: {pickle.loads(main_r.recv())}")
    """)

t = Thread(target=interp.run, args=(code,))
t.start()


main_s.send_nowait(pickle.dumps(["One", "Two"]))
print(f"Main: {sub_r.recv()}")
print(interpreters.list_all())

t.join()
