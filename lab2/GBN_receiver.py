import socket
import select
from random import random


class GBNReceiver:
    def __init__(self):
        self.address = ('127.0.0.1', 7777)
        self.sender_address = ('127.0.0.1', 6666)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)
        self.buffer_size = 1024
        self.receive_buffer = []
        # self.max_seq_num = 8
        self.wait_time = 10

    def receive(self):
        expected_num = 0
        timer = 0
        while True:
            if timer > self.wait_time:
                print('receive finished')
                with open('receive.txt', 'w') as f:
                    for data in self.receive_buffer:
                        f.write(data)
                self.socket.sendto('-finish'.encode(), self.sender_address)
                break

            rs, ws, es = select.select([self.socket, ], [], [], 1)

            if len(rs) > 0:
                if random() < 0.5:
                    print('丢失数据')
                else:
                    rcv_pkt, address = self.socket.recvfrom(self.buffer_size)
                    rcv_seq_num = rcv_pkt.decode()[0:8]
                    if int(rcv_seq_num) == expected_num:
                        print('ack ' + rcv_seq_num)
                        self.receive_buffer.append(rcv_pkt.decode()[8:])
                        self.socket.sendto(str(expected_num).encode(), address)
                        expected_num = expected_num + 1
                    else:
                        self.socket.sendto(str(expected_num).encode(), address)
            else:
                timer += 1


def main(receiver_socket):
    receiver_socket.socket.sendto('-testgbn'.encode(), receiver_socket.sender_address)
    receiver_socket.receive()


if __name__ == '__main__':
    receiver = GBNReceiver()
    main(receiver)
