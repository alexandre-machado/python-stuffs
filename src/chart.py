import asciichartpy as acp
from random import randint

x = [randint(0, 10) for _ in range(100)]

print(acp.plot(x))
