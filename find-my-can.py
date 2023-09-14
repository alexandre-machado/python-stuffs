import ipaddress
import socket
import multiprocessing
import re
import time
from random import random
from tqdm import tqdm


def isReachable(ipOrName, port, timeout=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ipOrName, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        # print(ipOrName + ": ✅ online")
        return ipOrName + ": ✅ online"
        # pool.terminate()
    except:
        # print(ipOrName + ": ⛔ offline")
        return ipOrName + ": ⛔ offline"
    finally:
        s.close()


# task to execute in another process
def task(arg):
    return isReachable(str(arg), 554)
    # time.sleep(0.5)

    # return str(arg)


def main():
    # entry point for the program
    items = ipaddress.IPv4Network("192.168.0.0/22")
    print(
        f"my ip: {socket.gethostbyname(socket.gethostname())} itens: {items.num_addresses}"
    )

    # create the process pool
    pool = multiprocessing.Pool(60)
    result_list = []
    for result in tqdm(pool.imap(func=task, iterable=items), total=items.num_addresses):
        result_list.append(result)

    print("found ips:")
    print([x for x in result_list if re.match(".*online.*", x)])

    # print(result_list.index("192.168.0.228: ⛔ offline"))
    # pool.imap(task, items)
    # pool.close()
    # pool.join()


if __name__ == "__main__":
    main()
