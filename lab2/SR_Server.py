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


class DataGram:
    def __init__(self, pkt, timer=0, is_acked=False):
        self.pkt = pkt
        self.timer = timer
        self.is_acked = is_acked


class SRServer:
    def __init__(self):
        self.send_window_size = 5   # 发送窗口大小
        self.receive_window_size = 5  # 接收窗口大小
        self.max_send_time = 5  # 发送超时时间
        self.max_receive_time = 15  # 接收超时时间
        self.address = ('127.0.0.1', 1111)  # 发送方地址
        self.client_address = ('127.0.0.1', 2222)   # 接收方地址
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)
        self.send_window = []   # 发送窗口
        self.receive_data = []  # 有序数据
        self.receive_window = {}  # 接收窗口
        self.buffer_size = 1024
        self.send_finished = False
        self.receive_finished = False

    def send_and_receive(self, buffer):
        send_base = 0
        next_seq_num = send_base
        expected_num = 0
        receive_timer = 0
        total = len(buffer)
        while True:
            # print(self.send_finished)
            # print(self.receive_finished)
            if not self.send_window and receive_timer > self.max_receive_time:
                with open('server_receive.txt', 'w') as f:
                    for data in self.receive_data:
                        f.write(data)
                break

            # 当有窗口中有序号可用时，发送数据
            while next_seq_num < send_base + self.send_window_size and next_seq_num < total:
                pkt = Data(0, '%8d' % next_seq_num, buffer[next_seq_num])
                self.socket.sendto(str(pkt).encode(), self.client_address)
                print('server send pkt ' + str(next_seq_num))
                # 给每个分组计时器初始化为0  把数据报加入发送窗口
                self.send_window.append(DataGram(pkt))
                next_seq_num = next_seq_num + 1

            # 发送窗口为空，将send_finished设为True 反复发finish 以防finish丢失
            # if not self.send_window:
                # print('server finished sending')
                # self.socket.sendto('finish'.encode(), self.client_address)
                # self.send_finished = True

            # 遍历已发送未确认分组，若有超时的分组，则重发
            for dgram in self.send_window :
                if dgram.timer > self.max_send_time and not dgram.is_acked:
                    self.socket.sendto(str(dgram.pkt).encode(), self.client_address)
                    # print('resend ' + str(dgram.pkt.seq))

            '''
            select()的机制中提供一fd_set的数据结构，实际上是一long类型的数组， 每一个数组元素都能与一打开的文件句柄
            （不管是Socket句柄，还是其他文件或命名管道或设备句柄）建立联系，建立联系的工作由程序员完成， 当调用select()
            时，由内核根据IO状态修改fd_set的内容，由此来通知执行了select()的进程哪一Socket或文件可读或可写。
            返回值：准备就绪的描述符数，若超时则返回0，若出错则返回-1。
            '''

            # 非阻塞监听
            rs, ws, es = select.select([self.socket, ], [], [], 0.01)

            while len(rs) > 0:
                rcv_pkt, address = self.socket.recvfrom(self.buffer_size)
                # 模拟丢包
                if random() < 0.2:
                    for dgram in self.send_window:
                        dgram.timer += 1
                    receive_timer += 1
                    print('server 丢包 ')
                    rs, ws, es = select.select([self.socket, ], [], [], 0.01)
                    continue
                message = rcv_pkt.decode()
                receive_timer = 0
                # if message == 'finish':
                #     with open('server_receive.txt', 'w') as f:
                #         for data in self.receive_data:
                #             f.write(data)
                #     self.receive_finished = True

                # 收到的是ACK分组
                if message[0] == '1':
                    # 获取ACK的序号
                    ack_num = int(message[1:9])
                    print('server 收到ack分组, ack: ' + str(ack_num))
                    for dgram in self.send_window:
                        # 在窗口中找序号为ack_num的分组，并把is_acked设为True
                        if int(dgram.pkt.seq) == ack_num:
                            dgram.timer = 0
                            dgram.is_acked = True
                            # 如果ack的是窗口中的第一个分组
                            if self.send_window.index(dgram) == 0:
                                idx = -1  # 用idx表示窗口中最后一个被ack的分组的下标
                                for i in self.send_window:
                                    if i.is_acked:
                                        idx += 1
                                    else:
                                        break
                                # 窗口滑动
                                send_base = int(self.send_window[idx].pkt.seq) + 1
                                self.send_window = self.send_window[idx+1:]
                            break
                # 收到数据分组
                elif message[0] == '0':
                    # 发送窗口中所有分组计时器+1
                    for dgram in self.send_window:
                        dgram.timer += 1
                    rcv_seq_num = message[1:9]
                    # 收到了期望的分组
                    if int(rcv_seq_num) == expected_num:
                        # 先发送ack
                        print('server ack ' + rcv_seq_num)
                        ack_pkt = Data(1, '%8d ' % expected_num, '')
                        self.socket.sendto(str(ack_pkt).encode(), self.client_address)   # 发送ack分组
                        # 再看它后面有没有能合并的分组
                        # 收到数据先加入接收窗口
                        self.receive_window[int(rcv_seq_num)] = rcv_pkt
                        tmp = [(k, self.receive_window[k]) for k in sorted(self.receive_window.keys())]
                        idx = 0   # idx为接受窗口中能合并到的最后一个分组
                        for i in range(len(tmp) - 1):
                            if tmp[i + 1][0] - tmp[i][0] == 1:
                                idx += 1
                            else:
                                break
                        for i in range(idx + 1):
                            self.receive_data.append(tmp[i][1].decode()[9:])   # 把接收窗口中的数据提交给receive_data
                        base = int(tmp[0][1].decode()[1:9])
                        end = int(tmp[idx][1].decode()[1:9])
                        if base != end:
                            print('server 向上层提交数据: ' + str(base) + ' ~ ' + str(end))
                        else:
                            print('server 向上层提交数据: ' + str(base))
                        expected_num = tmp[idx][0]+1
                        tmp = tmp[idx + 1:]   # 接收窗口滑动
                        self.receive_window = dict(tmp)
                    else:
                        '''
                        tmp 的格式为  [(序号，数据分组)...]
                        '''
                        tmp = [(k, self.receive_window[k]) for k in sorted(self.receive_window.keys())]
                        # 若在rcv_base~rcv_base + N -1之内则加入接收窗口
                        if expected_num < int(rcv_seq_num) < expected_num + self.receive_window_size - 1:
                            self.receive_window[int(rcv_seq_num)] = rcv_pkt
                            ack_pkt = Data(1, '%8d ' % int(rcv_seq_num), '')
                            print('server ack ' + rcv_seq_num)
                            self.socket.sendto(str(ack_pkt).encode(), self.client_address)  # 发送ack分组
                        elif int(rcv_seq_num) < expected_num:
                            ack_pkt = Data(1, '%8d ' % int(rcv_seq_num), '')
                            print('server 重复 ack ' + rcv_seq_num)
                            self.socket.sendto(str(ack_pkt).encode(), self.client_address)  # 发送ack分组
                        else:
                            pass
                else:
                    pass
                rs, ws, es = select.select([self.socket, ], [], [], 0.01)
            else:
                receive_timer += 1
                for dgram in self.send_window:
                    dgram.timer += 1


def start():
    server_socket = SRServer()
    data = []
    with open('server_send.txt', 'r') as f:
        while True:
            pkt = f.read(10)
            if len(pkt) > 0:
                data.append(pkt)
            else:
                break
    timer = 0
    while True:
        # 服务器计时器，如果收不到客户端的请求则退出
        if timer > 20:
            return

        rs, ws, es = select.select([server_socket.socket, ], [], [], 1)
        if len(rs) > 0:
            message, address = server_socket.socket.recvfrom(server_socket.buffer_size)
            if message.decode() == '-testsr':
                server_socket.send_and_receive(data)
            if message.decode() == '-finish':
                print('finished')
                return
        # print(timer)
        # print('here')
        timer += 1


if __name__ == '__main__':
    start()
