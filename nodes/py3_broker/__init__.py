from random import randint
import time
import json
import pprint
import encodings

import textwrap
import curses
import traceback
import sys

import zmq

import multiprocessing
import queue
print(zmq.zmq_version_info())
print(zmq.pyzmq_version_info())

EVENT_MAP = {}
print("Event names:")
for name in dir(zmq):
    if name.startswith('EVENT_'):
        value = getattr(zmq, name)
        print("%21s : %4i" % (name, value))
        EVENT_MAP[value] = name

class server(object):
    def __init__(self):
        self.subs = {}
        self.servers = {}

    def send_multipart(self, *args):
        safe_args = [(a.encode('utf-8') if type(a) is str else a) for a in args]
        self.set_indent('{:10} <- {:6} '.format(safe_args[0].decode(), safe_args[1].decode()))
        if (safe_args[1] == b'PING'):
            self.csrcn.insstr(8, 7, '{:15}'.format(safe_args[0].decode()))
            self.csrcn.refresh()
        else:
            self.log(repr(safe_args[2:]))
        self.servers[safe_args[0]].input_queue.put(safe_args)

    def handle_CONNECT(self, port, pa, request):
        addr, cmd = request
        #if (addr not in self.servers):
        self.servers[addr] = self.servers[str(port).encode()]
        del self.servers[str(port).encode()]
        self.send_multipart(addr, 'CONNECT', 'OK')

    def handle_PING(self, port, pa, request):
        addr, cmd = request
        self.send_multipart(addr, cmd, 'PONG')

    def handle_PONG(self, port, pa, request):
        addr, cmd = request
        self.csrcn.insstr(9, 7, '{:15}'.format(addr.decode()))
        self.csrcn.refresh()

    def handle_SUB(self, port, pa, request):
        addr, cmd, chan = request
        if (chan not in self.subs):
            self.subs[chan] = [addr]
        else:
            if (addr not in self.subs[chan]):
                self.subs[chan].append(addr)
            else:
                self.log("WARNING: Client already subscribed to this channel!")
        if (chan not in self.servers[addr].subs):
            self.servers[addr].subs.append(chan)
        else:
            self.log("WARNING: Subbing to an already subscribed channel!")
        self.send_multipart(addr, cmd, 'OK')
    
    def handle_UNSUB(self, port, pa, request):
        addr, cmd, chan = request
        if (chan in self.subs):
            self.subs[chan].remove(addr)
        if (chan in self.servers[addr].subs):
            self.servers[addr].subs.remove(chan)
        self.send_multipart(addr, cmd, 'OK')
    
    def handle_MSG(self, port, pa, request):
        addr, cmd, chan, msg = request
        sent_to = 0
        if (chan in self.subs):
            for tgt in self.subs[chan]:
                self.send_multipart(tgt, cmd, chan, msg)
                sent_to += 1
        self.send_multipart(addr, 'MSGSTAT', 'OK', '{}'.format(sent_to))
        #foo = json.loads(msg.decode('utf'))

    def log(self, msg):
        self.log_queue.put((self.indent, msg))

    def log_print(self, indent, msg):
        try:
            indent = indent.decode()
        except:
            pass
        self.textwrapper.initial_indent = '{:20}'.format(indent)
        self.textwrapper.subequent_indent = ' '*max(20,len(indent))
        lines = self.textwrapper.wrap(msg)
        for l in lines:
            self.logwin.scroll()
            p = self.logwin.getmaxyx()
            self.logwin.addstr(p[0]-2,1,l)
        self.logwin.border()
        self.logwin.refresh()

    def set_indent(self, indent):
        self.indent = indent

    def setup_screen(self):
        self.textwrapper = textwrap.TextWrapper(width=curses.COLS-2)
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
    
    def ticker(self, ch):
        self.csrcn.insstr(7, 7, ch)
        self.csrcn.refresh()
        

    def loop(self, csrcn):
        sys.stdout = open('grr.log', 'w')
        sys.stderr = sys.stdout
        self.csrcn = csrcn
        self.setup_screen()
        import multiprocessing
        from . import port_broker
        from . import zmq_proxy
        from .zmq_proxy import Proxy
        port_broker.EVENT_MAP = EVENT_MAP
        zmq_proxy.EVENT_MAP = EVENT_MAP
        m = multiprocessing.Manager()
        log_queue = m.Queue()
        self.log_queue = log_queue
        shared_input = m.Queue()
        gatekeeper = port_broker.Socket(m, log_queue)


        last_ping = time.time()
        while True:
            nowish = time.time()
            self.ticker('.')
            # Do we have any new friends?
            try:
                gatekeeper.output_queue.get(timeout=0.050)
                # Cool!
                idnum = str(time.time()).encode()
                newbie = Proxy(idnum, m.Queue(), shared_input, log_queue)
                newbie.last_ping = nowish
                self.servers[idnum] = newbie
            except queue.Empty:
                # Aww, guess not.
                pass

            # Anyone got something to say?
            try:
                msg = shared_input.get(timeout=0.050)
                # Cool!
                self.ticker('+')
                # msg should look like (port, cmd, data, ...)
                if (msg[1] == 'PORT'):
                    # (1234, 'PORT', 1234.456)
                    self.servers[str(msg[0]).encode()] = self.servers[msg[2]]
                    del self.servers[msg[2]]
                    gatekeeper.input_queue.put(msg[0])
                elif (msg[1] == 'RECV'):
                    # (1234, 'RECV', 'tcp://1.2.3.4:5678', {})
                    port, _, pa, request = msg
                    self.set_indent('{:10} -> {:6} '.format(request[0].decode(), request[1].decode()))
                    handler = getattr(
                        self,
                        'handle_{}'.format(request[1].decode('utf-8')),
                        None)
                    try:
                        if handler:
                            handler(
                                port,
                                pa,
                                request)
                    except:
                        self.log(''.join(traceback.format_exc(None)))
                    if (request[0] in self.servers):
                        self.servers[request[0]].last_ping = nowish
                    else:
                        self.log("Server not in self.servers though. Uh oh.")
            except queue.Empty:
                # Awful quiet :(
                pass

            if (last_ping + 1 < nowish):
                last_ping = nowish
                for s in [x for x in self.servers.keys()]:
                    self.set_indent('Ping results: ')
                    thenish = nowish-10
                    deadish = nowish-20
                    if (deadish > self.servers[s].last_ping):
                        self.log("Ping timeout for {}".format(s))
                        self.send_multipart(s, 'RECONNECT')
                        self.set_indent('Ping results: ')
                        for c in self.servers[s].subs:
                            self.log('Clearing {}'.format(c))
                            if (c in self.subs):
                                self.log('Unsubbing {}'.format(c))
                                self.subs[c].remove(s)
                        self.servers[s].proc.terminate()
                        self.servers[s].proc.join()
                        del self.servers[s]
                    elif (thenish > self.servers[s].last_ping):
                        self.send_multipart(s, 'PING')

            # Got anything to say?
            try:
                while True:
                    ident, msg = log_queue.get(block=False)
                    # Cool!
                    self.log_print(ident, msg)
            except queue.Empty:
                # Aww, guess not.
                pass

s = server()
curses.wrapper(s.loop)
