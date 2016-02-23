#!/usr/bin/env python
#coding=utf-8
import sys,re,string,os,stat,socket
import Queue
import multiprocessing
import socket
import threading
from functools import partial
from time import *
from tornado.ioloop import IOLoop

class tail_f_producer:
	def __init__(self,filename="./README",tailnum=1024):
		self.targetFile=filename
		self._open()
		self.tailnum=tailnum
		self.delay=0.1
		self.size=self._fsize()
		self.newsize=0
	def _fsize(self):
		return os.fstat(self.openFile.fileno())[stat.ST_SIZE]
	def _open(self):
		self.openFile=open(self.targetFile,'rb')
	def _close(self):
		self.openFile.close()
	def tailFile(self):
		count=1
		rcount=1
		allLine=''
		with open(self.targetFile,"r") as file:
			while True:
				try:
					file.seek(-count,2)
				except IOError,e:
					break
				count+=1
				if file.read(1) == "\n":
					rcount+=1
				if rcount-2 == self.tailnum:
					break
			file.seek(-count+2,2)
			for line in file:
				allLine=allLine+line
		if len(allLine) < 1024:
			allLine="#"*(1024-len(allLine)-1)+"\n"+allLine #解决第一个chunked不足1024浏览器显示不出的问题
		return allLine
	def more(self):
		newLine=''
		self.newsize=self._fsize()
		if self.newsize < self.size:
			self.size=self.newsize
			self._close()
			return "==> File truncated <==\n"
		if self.size < self.newsize:
			moveCount=self.newsize-self.size
			self.openFile.seek(-moveCount,2)
			newLine=self.openFile.read(moveCount)
			self.size=self.newsize
			return newLine

def listen_file(que_out):
    loop_file={}
    file_list={}
    while 1:
        sleep(0.2)
        new=''
        if not que_out.empty():
            gay=que_out.get()
            target=gay.split(':')[0]
            fd=gay.split(':')[1]
            if not target in loop_file:
                loop_file[target]=[int(fd)]
                file_list[target]=tail_f_producer(target,1)
            else:
                loop_file[target].append(int(fd))
        for lf in file_list:
            new=file_list[lf].more()
            if new:
                for f in set(loop_file[lf]):
                    try:
                        fd_map[f].send('\r\n%s\r\n%s\r\n'%(hex(len(new)+1)[2:],new.strip()))
                    except:
                        loop_file[lf].remove(f)
                        fd_map.pop(f)
def http_header_time(x):
    now=localtime(time())
    if x != 1:
       now=localtime(os.stat(x).st_mtime)
    return strftime('%a, %d %b %Y %X %Z',now)

def handle_client(cli_addr, fd, event):
    REQUEST = re.compile ('([^ ]+) ([^ ]+)(( HTTP/([0-9.]+))*|.*)')
    s = fd_map[fd]
    if event & IOLoop.READ:
        data = s.recv(1024)
        if data:
            rq=REQUEST.match(data).group(2)
            print "     received '%s' from %s " % (data, cli_addr)
            req_list=rq.split('/')
            re_target='/'.join(req_list[1:-1])
            tail_target=os.path.join(sys.argv[1],re_target)
            tail_count=req_list[-1]
            try:
                file=tail_f_producer(tail_target,int(tail_count))
            except IOError,e:
                pass
            else:
                fb=file.tailFile()
                #ioloop.update_handler(fd, IOLoop.WRITE)
                # 接收到消息更改事件为写, 用于发送数据到对端
                send_header='HTTP/1.1 200 OK\r\nDate: %s\r\nLast-Modified: %s\r\nContent-Type: text/plain;charset=UTF-8\r\nCache-Control: max-age=0\r\nTransfer-Encoding: chunked\r\nServer: tornado/1.12\r\n'%(http_header_time(1),http_header_time(tail_target))
                ioloop.update_handler(fd, IOLoop.WRITE)
                message_queue_map[s].put(send_header)
                message_queue_map[s].put('\r\n%s\r\n%s\r\n'%(hex(len(fb)+1)[2:],fb.strip()))
                print fd,type(fd)
                q_file_out.put(tail_target+":"+str(fd))
                print "put to chriden"
                #listen_file=multiprocessing.Process(target=gg, args=())
                #listen_file.start()
                #d={tail_target}
                #q_file.put(str(f_watcher))
        else:
            print "     closing %s" % cli_addr
            ioloop.remove_handler(fd)
            s.close()
            del message_queue_map[s]

    if event & IOLoop.WRITE:
        try:
            next_msg = message_queue_map[s].get_nowait()
        except Queue.Empty:
            print "%s queue empty" % cli_addr
            ioloop.update_handler(fd, IOLoop.READ)
        else:
            print 'sending "%d" to %s' % (len(next_msg), cli_addr)
            s.send(next_msg)

    if event & IOLoop.ERROR:
        print " exception on %s" % cli_addr
        ioloop.remove_handler(fd)
        s.close()
        del message_queue_map[s]


def handle_server(fd, event):
    s = fd_map[fd]
    if event & IOLoop.READ:
        conn, cli_addr = s.accept()
        print "     connection %s" % cli_addr[0]
        conn.setblocking(0)
        conn_fd = conn.fileno()
        fd_map[conn_fd] = conn
        handle = partial(handle_client, cli_addr[0])   # 将cli_addr作为第一个参数
        # 将连接和handle注册为读事件加入到 tornado ioloop
        ioloop.add_handler(conn_fd, handle, IOLoop.READ)
        message_queue_map[conn] = Queue.Queue()   # 创建对应的消息队列
if __name__=='__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(0)              # 将socket设置为非阻塞
    ##统一编码
    reload(sys)
    sys.setdefaultencoding('utf-8')

    server_address = ("0.0.0.0", int(sys.argv[2]))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(server_address)
    sock.listen(5)
    manager = multiprocessing.Manager()
    q_file_out = multiprocessing.Queue()
    #P_file_loop = multiprocessing.Process(target=listen_file,args=(q_file_out,))
    P_file_loop = threading.Thread(target=listen_file,args=(q_file_out,))
    P_file_loop.start()

    message_queue_map = {}   # socket到消息队列的映射
    #global fd_map
    fd_map={}  # 文件描述符到socket的映射

    fd = sock.fileno()
    fd_map[fd] = sock
    ioloop = IOLoop.instance()
    ioloop.add_handler(fd, handle_server, IOLoop.READ)
    ioloop.start()
