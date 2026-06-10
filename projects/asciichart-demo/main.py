import asciichartpy as acp
from random import randint


def main():
    x = [randint(0, 10) for _ in range(100)]
    print(acp.plot(x))


if __name__ == "__main__":
    main()
