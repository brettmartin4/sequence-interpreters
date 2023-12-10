"""
Example Python 3.12 Subinterpreters script for spawning two concurrent threads.

Updated to include message-passing between interpreters using Redis

"""


#import _xxsubinterpreters as interpreters
from test.support import interpreters
from textwrap import dedent
import os

import redis


def _captured_script(script):
    r,w = os.pipe()
    indented = script.replace('\n', '\n                ')
    wrapped = dedent(f"""
        import contextlib
        with open({w}, 'w', encoding="utf-8") as spipe:
            with contextlib.redirect_stdout(spipe):
                {indented}
        """)
    return wrapped, open(r, encoding="utf-8")


def _run_output(interp, request, channels=None):
    script, rpipe = _captured_script(request)
    with rpipe:
        interp.run(script, channels=channels)
        return rpipe.read()
    

def cleanup_interpreters():
    for i in interpreters.list_all():
        if i.id ==0:
            continue
        try:
            print(f"Cleaning up interpreter: {i}")
            i.close()
        except RuntimeError:
            pass


main = interpreters.get_main()
print(f"Main interpreter ID: {main}")

interp = interpreters.create()
print(f"Sub-interpreter ID: {interp}")

r = redis.Redis(host='localhost', port=6379,decode_responses=True)
test_val = 15
r.set('test_val', str(test_val))

print(f"Test value: {test_val}")

code = dedent("""
    from test.support import interpreters
    import redis
    r = redis.Redis(host='localhost', port=6379,decode_responses=True)
    cur = interpreters.get_current()
    print(cur.id)
    recv_data = r.get('test_val')
    r.set('test_val', '25')
    print(f"Test value set from {recv_data} to: {r.get('test_val')}")
    """)

out = _run_output(interp, code)
print(f"All interpreters: {interpreters.list_all()}")
print(f"Output: {out}")
print(f"New test value: {r.get('test_val')}")

cleanup_interpreters()
