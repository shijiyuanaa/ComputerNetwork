import socket
import threading
import os
import urllib.parse as urlparse
import urllib.request as urllib2
import time
import sys


class ProxyServer:
    def __init__(self):
        self.port = 10240
        # 初始化socket
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.MAX_LISTEN = 20  # 最大连接数
        self.proxy_socket.bind(('', self.port))
        self.proxy_socket.listen(self.MAX_LISTEN)
        self.BUFFER_SIZE = 2048
        self.cache_dir = './cache/'
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)

    @staticmethod
    def filter_page(url):
        with open('filter_pages.txt', 'r') as f:
            filter_pages_list = f.readlines()
        if url in filter_pages_list:
            return True
        return False

    @staticmethod
    def filter_user(ip):
        with open('filter_users.txt', 'r') as f:
            filter_users_list = f.readlines()
        if ip in filter_users_list:
            return True
        return False

    @staticmethod
    def fish(url):
        with open('fish.txt', 'r') as f:
            fish_pages = f.readlines()
        if url in fish_pages:
            return True
        return False

    def connect(self, client_socket, address):
        # 从客户端接收http请求
        ori_message = client_socket.recv(self.BUFFER_SIZE)
        # print(ori_message)
        message = ori_message.decode('utf-8', 'ignore')
        header = message.split('\r\n')
        # print(header)
        # header的第一行为请求行
        # 将Request Line的method URL和version 3个部分分开 strip去除首部空格
        request_line = header[0].strip().split()
        if len(request_line) > 1:
            url = urlparse.urlparse(request_line[1][:-1] if request_line[1][-1] == '/' else request_line[1])
        else:
            print("url is null")
            client_socket.close()
            return
        # print(url)
        hostname = url.netloc

        # 防止报错
        # if '443' in hostname:
        #     client_socket.close()
        #     return

        # 判断url是否被过滤
        if self.filter_page(hostname):
            print('request to connect to ' + str(hostname) + ' is denied\n')
            client_socket.close()
            return

        # 判断ip地址是否被过滤
        if self.filter_user(address[0]):
            print('user '+address[0]+' is forbidden to connect to proxy server')
            client_socket.close()
            return

        # 判断是否访问钓鱼网站

        if self.fish(hostname):
            '''第一种方案：引导到本地html'''
            # print('request to ' + hostname + ' is redirected')
            # with open('fish_page.html') as f:
            #     client_socket.sendall(f.read().encode())
            # client_socket.close()
            # return

            '''第二种方案：引导到cs.hit.edu.cn'''
            print('request to ' + hostname + ' is redirected to cs.hit.edu.cn')
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect(('cs.hit.edu.cn', 80))
            # 修改头部url
            url = 'http://cs.hit.edu.cn'
            begin = message.index('h')
            end = message.index('H')
            message = message[:begin] + url + message[end-1:]
            print(message)
            server_socket.sendall(message.encode())
            while True:
                buff = server_socket.recv(self.BUFFER_SIZE)
                if not buff:
                    server_socket.close()
                    # print(address, "连接关闭")
                    break
                client_socket.sendall(buff)
            client_socket.close()
            return

        '''实现缓存功能'''
        cache_path = self.cache_dir + (hostname + url.path).replace('/', '_')
        is_modified = False
        if os.path.exists(cache_path):
            modified_time = os.stat(cache_path).st_mtime  # 缓存最后一次修改的时间
            headers = str('If-Modified-Since: '+time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(modified_time)))
            message = message[:-2] + headers + '\r\n\r\n'
            print(message)
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((hostname, 80))
            server_socket.sendall(message.encode())
            data = server_socket.recv(self.BUFFER_SIZE).decode('utf-8', 'ignore')
            server_socket.close()
            print('response:'+'\n'+data)
            if data[9:12] == '304':
                print("Read from cache")
                with open(cache_path, "rb") as f:
                    client_socket.sendall(f.read())
            else:
                is_modified = True

        if not os.path.exists(cache_path) or is_modified:
            # 连接服务器端
            # print(address, "尝试连接", url.geturl())
            # print(address, "hostname: " + hostname)
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((hostname, 80))
            server_socket.sendall(message.encode())
            f = open(cache_path, 'wb')
            # print(address, "连接成功")
            while True:
                buff = server_socket.recv(self.BUFFER_SIZE)
                if not buff:
                    f.close()
                    server_socket.close()
                    # print(address, "连接关闭")
                    break
                f.write(buff)
                client_socket.sendall(buff)
            client_socket.close()


def main():
    proxy = ProxyServer()
    while True:
        new_sock, address = proxy.proxy_socket.accept()
        print(address)
        threading.Thread(target=proxy.connect, args=(new_sock, address)).start()


if __name__ == '__main__':
    main()

