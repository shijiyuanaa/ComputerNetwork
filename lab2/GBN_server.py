import socket
from random import random
import select


'''
分组格式
+--------+-----+-----------+
| is_ack | seq |    data   |
+--------+-----+-----------+
0表示不是ack
1表示是ack
is_ack占1位
seq占8位
'''


class Data:
    def __init__(self, is_ack, seq, data):
        self.is_ack = is_ack
        self.seq = seq
        self.data = data

    def __str__(self):
        return str(self.is_ack) + str(self.seq) + str(self.data)


class GBNServer:
    def __init__(self):
        self.window_size = 5   # 窗口大小
        self.max_send_time = 10   # 发送超时时间
        self.max_receive_time = 5  # 接收超时时间
        self.address = ('127.0.0.1', 8888)  # 发送方地址
        self.client_address = ('127.0.0.1', 9999)   # 接收方地址
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)
        self.send_window = []   # 发送窗口
        self.receive_buffer = []
        self.buffer_size = 1024

    def send_and_receive(self, buffer):
        send_timer = 0
        send_base = 0
        next_seq_num = send_base
        expected_num = 0
        receive_timer = 0
        total = len(buffer)
        while True:
            # 当有窗口中有序号可用时，发送数据
            while next_seq_num < send_base + self.window_size and next_seq_num < len(buffer):
                pkt = Data(0, '%8d' % next_seq_num, buffer[next_seq_num])
                self.socket.sendto(str(pkt).encode(), self.client_address)
                print('server send pkt ' + str(next_seq_num))
                self.send_window.append(pkt)
                if send_base == next_seq_num:
                    send_timer = 0
                next_seq_num = next_seq_num + 1

            # 发送窗口为空，结束server发送
            if not self.send_window and receive_timer > self.max_receive_time and send_timer > self.max_send_time:
                print('server finished sending')
                self.socket.sendto('finish'.encode(), self.client_address)
                with open('server_receive.txt', 'w') as f:
                    for data in self.receive_buffer:
                        f.write(data)
                return

            # 超时，重传发送窗口中的数据
            if send_timer > self.max_send_time:
                print('server send timeout, resend')
                timer = 0
                for pkt in self.send_window:
                    self.socket.sendto(str(pkt).encode(), self.client_address)
                    print('resend ' + str(pkt.seq))

            rs, ws, es = select.select([self.socket, ], [], [], 1)

            while len(rs) > 0:
                if random() < 0.2:
                    print('server丢失数据 ')
                    break
                if random() < 0.2:
                    print('server丢失ack ')
                    break
                rcv_pkt, address = self.socket.recvfrom(self.buffer_size)
                message = rcv_pkt.decode()

                # server发送结束
                if message == 'finish':
                    with open('client_receive.txt', 'w') as f:
                        for data in self.receive_buffer:
                            f.write(data)
                    break

                elif message[0] == '1':
                    ack_num = int(message[1:9])
                    self.send_window = self.send_window[ack_num:]
                    send_base = ack_num + 1
                    if send_base == next_seq_num:
                        break
                    else:
                        send_timer = 0
                elif message[0] == '0':
                    rcv_seq_num = message[1:9]
                    if int(rcv_seq_num) == expected_num:
                        print('server ack ' + rcv_seq_num)
                        self.receive_buffer.append(rcv_pkt.decode()[9:])
                        ack_pkt = Data(1, '%8d ' % expected_num, '')
                        self.socket.sendto(str(ack_pkt).encode(), self.client_address)   # 发送ack分组
                        expected_num += 1
                    else:
                        print('server收到错误分组, 重发ack ', expected_num)
                        ack_pkt = Data(1, '%8d ' % expected_num, '')
                        self.socket.sendto(str(ack_pkt).encode(), self.client_address)  # 发送ack分组
                else:
                    pass

            else:
                receive_timer += 1
                send_timer += 1


def main(server_socket):
    data = []
    with open('server_send.txt', 'r') as f:
        while True:
            pkt = f.read(10)
            if len(pkt) > 0:
                data.append(pkt)
            else:
                break

    while True:
        rs, ws, es = select.select([server_socket.socket, ], [], [], 1)
        if len(rs) > 0:
            message, address = server_socket.socket.recvfrom(server_socket.buffer_size)
            if message.decode() == '-testgbn':
                server_socket.send_and_receive(data)
            if message.decode() == '-finish':
                print('send finished')
                return


if __name__ == '__main__':
    server = GBNServer()
    main(server)