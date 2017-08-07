
import textwrap
import curses
import sys

import zmq

print(zmq.zmq_version_info())
print(zmq.pyzmq_version_info())

class server(object):
    def __init__(self):
        self.subs = {}
        self.servers = {}

    def log_print(self, indent, msg):
        try:
            indent = indent.decode()
        except:
            pass
        self.textwrapper.initial_indent = '{:22}'.format(indent)
        self.textwrapper.subsequent_indent = ' '*max(22,len(indent))
        lines = self.textwrapper.wrap(msg)
        for l in lines:
            self.logwin.scroll()
            p = self.logwin.getmaxyx()
            self.logwin.addstr(p[0]-2,1,l)
        self.logwin.border()
        self.logwin.refresh()

    def setup_screen(self):
        self.textwrapper = textwrap.TextWrapper(width=curses.COLS-4)
        logwin= self.csrcn.subwin(curses.LINES-10,curses.COLS-2,10,1)
        logwin.border()
        logwin.refresh()
        self.csrcn.idlok(True)
        self.csrcn.scrollok(False)
        logwin.idlok(True)
        logwin.scrollok(True)
        logwin.setscrreg(1,curses.LINES-12)
        self.logwin = logwin
        self.csrcn.addstr(8, 1, 'PING: ')
        self.csrcn.addstr(9, 1, 'PONG: ')
        self.csrcn.refresh()

    def loop(self, csrcn):
        self.csrcn = csrcn
        self.setup_screen()
        ctx = zmq.Context()
        subby = ctx.socket(zmq.SUB)
        subby.bind('tcp://127.0.0.1:5142')
        subby.setsockopt(zmq.SUBSCRIBE, b"PING")
        subby.setsockopt(zmq.SUBSCRIBE, b"PONG")
        subby.setsockopt(zmq.SUBSCRIBE, b"TICKER")
        subby.setsockopt(zmq.SUBSCRIBE, b"LOG")

        while True:
            pkt = subby.recv_multipart()
            if pkt[0] == b'PING':
                self.csrcn.insstr(8, 7, '{:15}'.format(pkt[1].decode()))
            elif pkt[0] == b'PONG':
                self.csrcn.insstr(9, 7, '{:15}'.format(pkt[1].decode()))
            elif pkt[0] == b'TICKER':
                self.csrcn.insstr(7, 7, pkt[1].decode())
            elif pkt[0] == b'LOG':
                self.log_print(pkt[1].decode(), pkt[2].decode())
            self.csrcn.refresh()

s = server()
curses.wrapper(s.loop)
