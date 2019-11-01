import threading
from GBN_client import start as gbn_client_start
from GBN_server import start as gbn_server_start
from SR_Client import start as sr_client_start
from SR_Server import start as sr_server_start


def main():
    t1 = threading.Thread(target=gbn_server_start, args=())
    t2 = threading.Thread(target=gbn_client_start, args=())
    # t1 = threading.Thread(target=sr_server_start, args=())
    # t2 = threading.Thread(target=sr_client_start, args=())
    t1.start()
    t2.start()


if __name__ == '__main__':
    main()
