import socket
import random
import select


class Data:
    def __init__(self, seq, data, is_ack=0):
        self.seq = seq
        self.data = data

    def __str__(self):
        return self.seq + str(self.data)


class GBNServer:
    def __init__(self):
        # self.next_seq_num = 1
        self.window_size = 5   # 窗口大小
        # self.max_seq_num = 20   # 可用序号范围0-7
        self.max_time = 5   # 超时时间
        self.address = ('127.0.0.1', 6666)  # 发送方地址
        self.client_address = ('127.0.0.1', 7777)   # 接收方地址
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)
        self.send_window = []   # 发送窗口
        # self.last_ack = 0
        self.buffer_size = 1024

    def send(self, buffer):
        # buffer 是待发数据
        timer = 0
        # 按照书上，send_base从1开始
        send_base = 0
        next_seq_num = send_base
        while next_seq_num < len(buffer):
            # if send_base < 4:
            #     flag = next_seq_num <= (send_base + self.window_size - 1) % self.max_seq_num
            # else:
            #     if next_seq_num >= send_base:
            #         flag = True
            #     else:
            #         flag = next_seq_num <= (send_base + self.window_size - 1) % self.max_seq_num
            while next_seq_num < send_base + self.window_size and next_seq_num < len(buffer):
                pkt = Data('%8d' % next_seq_num, buffer[next_seq_num], 0)
                self.socket.sendto(str(pkt).encode(), self.client_address)
                print('server send pkt ' + str(next_seq_num))
                self.send_window.append(pkt)
                if send_base == next_seq_num:
                    timer = 0
                next_seq_num = next_seq_num + 1
                # if send_base < 4:
                #     flag = next_seq_num <= (send_base + self.window_size - 1) % self.max_seq_num
                # else:
                #     if next_seq_num > send_base:
                #         flag = send_base < next_seq_num < send_base + self.window_size
                #     else:
                #         flag = next_seq_num <= (send_base + self.window_size - 1) % self.max_seq_num
            else:
                print('refused data')
            if timer > self.max_time:
                print('timeout, resend')
                timer = 0
                for pkt in self.send_window:
                    self.socket.sendto(str(pkt).encode(), self.client_address)
                    print('resend ' + str(pkt.seq))

            rs, ws, es = select.select([self.socket, ], [], [], 1)

            while len(rs) > 0:
                rcv_pkt, address = self.socket.recvfrom(self.buffer_size)
                ack_num = rcv_pkt.decode()
                self.send_window = self.send_window[int(ack_num):]
                send_base = int(ack_num) + 1
                if send_base == next_seq_num:
                    break
                else:
                    timer = 0
                rs, ws, es = select.select([self.socket, ], [], [], 1)
            else:
                timer += 1


def main(server_socket):
    data = []
    with open('send.txt', 'r') as f:
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
                server_socket.send(data)
            if message.decode() == '-finish':
                print('send finished')
                return


if __name__ == '__main__':
    server = GBNServer()
    main(server)


















