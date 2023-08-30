import ipaddress
import socket
import multiprocessing
from time import sleep
from random import random


class WorkerStopException(Exception):
    pass


def isReachable(ipOrName, port, timeout=2):
    # global pool
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ipOrName, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        print(ipOrName + ": ✅ online")
        # return ipOrName + ": ✅ online"
        # pool.terminate()
    except:
        print(ipOrName + ": ⛔ offline")
        # return ipOrName + ": ⛔ offline"
    finally:
        s.close()


# task to execute in another process
def task(arg):
    return isReachable(str(arg), 554)


# entry point for the program
if __name__ == "__main__":
    # global pool
    items = ipaddress.IPv4Network("192.168.0.0/24")
    print(
        f"my ip: {socket.gethostbyname(socket.gethostname())} itens: {items.num_addresses}"
    )
    # create the process pool
    pool = multiprocessing.Pool(60)
    pool.imap(task, items)
    pool.close()
    pool.join()
