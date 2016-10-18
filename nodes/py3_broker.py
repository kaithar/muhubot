from random import randint
import time
import json
import pprint
import encodings

import zmq
from zmq.devices import monitored_queue
from zmq.utils.monitor import recv_monitor_message

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
    def __init__(self, bind, identity):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.identity = identity
        self.socket.bind(bind)
        self.subs = {}
        self.servers = {}
        self.fds = {}
        self.monitor = self.socket.get_monitor_socket()

    def send_multipart(self, *args):
        safe_args = [(a.encode('utf-8') if type(a) is str else a) for a in args]
        print('{} <- {}: {}'.format(safe_args[0], safe_args[1], repr(safe_args[2:])))
        self.socket.send_multipart(safe_args)

    def handle_CONNECT(self, addr, cmd):
        #if (addr not in self.servers):
        self.servers[addr] = { 'subs':[] }
        self.send_multipart(addr, cmd, 'OK')

    def handle_PING(self, addr, cmd):
        self.send_multipart(addr, cmd, 'PONG')

    def handle_SUB(self, addr, cmd, chan):
        if (chan not in self.subs):
            self.subs[chan] = [addr]
        else:
            if (addr not in self.subs[chan]):
                self.subs[chan].append(addr)
            else:
                print("WARNING: Client already subscribed to this channel!")
        if (chan not in self.servers[addr]['subs']):
            self.servers[addr]['subs'].append(chan)
        else:
            print("WARNING: Subbing to an already subscribed channel!")
        self.send_multipart(addr, cmd, 'OK')
    
    def handle_UNSUB(self, addr, cmd, chan):
        if (chan in self.subs):
            self.subs[chan].remove(addr)
        if (chan in self.servers[addr]['subs']):
            self.servers[addr]['subs'].remove(chan)
        self.send_multipart(addr, cmd, 'OK')
    
    def handle_MSG(self, addr, cmd, chan, msg):
        sent_to = 0
        if (chan in self.subs):
            for tgt in self.subs[chan]:
                self.send_multipart(tgt, cmd, chan, msg)
                sent_to += 1
        self.send_multipart(addr, 'MSGSTAT', 'OK', '{}'.format(sent_to))
        foo = json.loads(msg.decode('utf'))

    def loop(self):
        while True:
            if (self.socket.poll(timeout=100)):
                request = self.socket.recv_multipart(copy=False)
                fd = request[-1].get(zmq.SRCFD)
                pa = request[-1].get(b"Peer-Address")
                request = [r.bytes for r in request]
                print('{}({}/{}) -> {}: {}'.format(request[0], fd, pa, request[1], repr(request[2:])))
                handler = getattr(self, 'handle_{}'.format(request[1].decode('utf-8')), None)
                try:
                    if handler:
                        handler(*request)
                except:
                    traceback.print_exc(None)
                #if request[0] in self.servers:
                #    print('Setting fd for {} to {}'.format(request[0], fd))
                #    self.servers[request[0]]['fd'] = fd
                #self.fds[fd] = request[0]
            if (self.monitor.poll(timeout=100)):
                evt = recv_monitor_message(self.monitor)
                evt.update({'description': EVENT_MAP[evt['event']]})
                print("Event: {}".format(evt))
                #if evt['event'] == zmq.EVENT_DISCONNECTED:
                    #print(self.subs)
                    #print(self.servers)
                    #if evt['value'] in self.fds:
                    #    ident = self.fds[evt['value']]
                    #    print('DISCONNECT: {}'.format(ident))
                    #     if ident in self.servers:
                    #         print('Clearing server')
                    #         for c in self.servers[ident]['subs']:
                    #             print('Clearing {}'.format(c))
                    #             if (c in self.subs):
                    #                 print('Unsubbing {}'.format(c))
                    #                 self.subs[c].remove(ident)
                    #         del self.servers[ident]
                    # print(self.subs)
                    # print(self.servers)
                    # print('')
                if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
                    break
        self.socket.close()
        self.context.term()

s = server("tcp://127.0.0.1:5140", b"mom")
s.loop()
