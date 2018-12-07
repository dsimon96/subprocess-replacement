"""
simple io use case - run another process, send it input, receive output
"""
from childprocess import ChildProcessBuilder as CPB

with CPB("lua -i -e \"_PROMPT=''\"").spawn() as cp:
    # hello world code from lua demos
    cp.stdin.write(b'io.write("Hello world, from ",_VERSION,"!\n")\n')
    print(cp.stdout.readline())
