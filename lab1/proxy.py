import socket
import threading
import os
import time


class ProxyServer:
    def __init__(self):
        self.port = 10240  # 绑定的端口号
        # 初始化socket
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # 创建主socket 用于监听
        self.proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # 设置socket参数
        self.MAX_LISTEN = 20  # 最大连接数
        self.proxy_socket.bind(('', self.port))
        self.proxy_socket.listen(self.MAX_LISTEN)
        self.BUFFER_SIZE = 2048
        self.cache_dir = './cache/'  # cache文件夹
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)     # 创建cache目录

    @staticmethod
    def filter_page(url):
        # 判断url是否被过滤
        with open('filter_pages.txt', 'r') as f:
            filter_pages_list = f.readlines()
        if url in filter_pages_list:
            return True
        return False

    @staticmethod
    def filter_user(ip):
        # 判断用户ip是否被过滤
        with open('filter_users.txt', 'r') as f:
            filter_users_list = f.readlines()
        if ip in filter_users_list:
            return True
        return False

    @staticmethod
    def fish(url):
        # 判断用户访问的是否是钓鱼网站
        with open('fish.txt', 'r') as f:
            fish_pages = f.readlines()
        if url in fish_pages:
            return True
        return False

    def connect(self, client_socket, address):
        # 从客户端接收http请求
        ori_message = client_socket.recv(self.BUFFER_SIZE)
        message = ori_message.decode('utf-8', 'ignore')   # 将bytes类型的报文转换为字符串
        header = message.split('\r\n')   # 把报文以\r\n分割 得到list
        # header的第一行为请求行
        # 将Request Line的method URL和version 3个部分分开 strip去除首部空格
        request_line = header[0].split()
        # print(message)
        if len(request_line) > 1:
            tmp = request_line[1][7:]    # 将http://后的部分取出
            if '?' in tmp:
                # 有些url内包含'?',不能作为文件路径,应该去掉'?'之后的部分
                path = tmp[:tmp.index('?')]    # path为cache文件的路径
            else:
                path = tmp
            hostname = path[:path.index('/')]   # 提取主机名
            if path[-1] == '/':   # 若path的最后一个字符为'/'则删去
                path = path[:-1]
        else:
            # url为空时关闭线程
            print("url is null")
            client_socket.close()
            return

        # 判断url是否被过滤
        if self.filter_page(hostname):
            print('request to connect to ' + str(hostname) + ' is rejected\n')
            client_socket.close()
            return

        # 判断ip地址是否被过滤
        if self.filter_user(address[0]):
            print('user '+address[0]+' is forbidden to connect to proxy server')
            client_socket.close()
            return

        # 判断是否访问钓鱼网站
        if self.fish(hostname):
            # 将客户引导到钓鱼网站
            new_hostname = 'today.hit.edu.cn'  # 钓鱼网站的主机名
            print('request to ' + hostname + ' is redirected to ' + new_hostname)
            begin = message.index('h')
            end = message.index('/', 12)   # 找到url中主机名的部分
            message = message[:begin+7] + new_hostname + '/' + message[end+1:]   # 将主机名部分修改为新的主机名
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((new_hostname, 80))   # 与钓鱼网站的服务器建立连接
            server_socket.sendall(message.encode())    # 将请求报文发送给钓鱼网站服务器
            while True:
                # 从服务器接收数据,转发给客户端
                buff = server_socket.recv(self.BUFFER_SIZE)
                if not buff:
                    server_socket.close()
                    break
                client_socket.sendall(buff)
            client_socket.close()
            server_socket.close()
            return

        '''实现缓存功能'''
        cache_path = self.cache_dir + path.replace('/', '_')  # 将路径中的'/'换成'_', 因为windows文件名不能带'/'
        is_modified = False   # 将是否修改过的flag设为false
        if os.path.exists(cache_path):
            # 若缓存文件存在 则判断服务器端是否修改过这个网页
            modified_time = os.stat(cache_path).st_mtime  # 获得缓存最后一次修改的时间
            headers = str('If-Modified-Since: '+time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(modified_time)))
            # 把modified-time按报文要求的格式格式化
            message = message[:-2] + headers + '\r\n\r\n'  # 把If-Modified-Since字段加入到请求报文中, 注意http用\r\n\r\n判断请求头部结束

            # 向服务器发送该请求
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((hostname, 80))
            server_socket.sendall(message.encode())
            data = server_socket.recv(self.BUFFER_SIZE).decode('utf-8', 'ignore')
            server_socket.close()

            if data[9:12] == '304':
                # 若收到的响应代码为304,则说明服务器未修改该网页,故从缓存读取数据交给客户端
                print("Read from cache")
                with open(cache_path, "rb") as f:
                    client_socket.sendall(f.read())
            else:
                # 否则说明网站该过该网页,将is_modified设为True
                is_modified = True

        if not os.path.exists(cache_path) or is_modified:
            # 若不存在该缓存文件或服务器修改过该网页,则需要向服务器请求访问
            # 连接服务器端
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((hostname, 80))
            server_socket.sendall(message.encode())
            f = open(cache_path, 'wb')
            while True:
                buff = server_socket.recv(self.BUFFER_SIZE)
                if not buff:
                    f.close()
                    server_socket.close()
                    break
                f.write(buff)  # 将接收到的数据写入缓存
                client_socket.sendall(buff)  # 将接收到的数据转发给客户端
            client_socket.close()


def main():
    proxy = ProxyServer()  # 初始化代理服务器
    while True:
        # 进入循环, 监听10240端口, 收到客户端的请求则调用accept 并创建一个线程, 调用proxy.connect()对请求进行处理
        new_sock, address = proxy.proxy_socket.accept()
        print(address)
        threading.Thread(target=proxy.connect, args=(new_sock, address)).start()


if __name__ == '__main__':
    main()

