from __future__ import print_function, unicode_literals
import zmq
from zmq.utils.monitor import recv_monitor_message
import logging
import json
import sys

EVENT_MAP = {}

class sock(object):
    if (sys.version_info.major == 3):
        desired_type = str
    else:
        desired_type = unicode

    singleton = None
    connected = False
    def __init__(self):
        global EVENT_MAP
        for name in dir(zmq):
            if name.startswith('EVENT_'):
                value = getattr(zmq, name)
                EVENT_MAP[value] = name
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.monitor = self.socket.get_monitor_socket()
        self.subs = {}
        self.message_queue = []
        sock.singleton = self

    def connect(self, identity, endpoint):
        if (sys.version_info.major == 3 or type(identity) is self.desired_type):
            self.socket.identity = identity.encode('utf-8')
        else:
            self.socket.identity = identity
        self.socket.connect(endpoint)

    @staticmethod
    def get_sock():
        return sock.singleton

    @staticmethod
    def receiving(channel):
        def baked_subscription(f):
            sock.singleton.subscribe(channel, f)
            return f
        return baked_subscription

    @staticmethod
    def chain(channel):
        """This is intended to be used with funchain"""
        import funchain
        base = funchain.Chain()
        def baked_chain_link(cmd, channel, body):
            try:
                return base(body)
            except funchain.AsyncCall:
                # Won't finish immediately
                return None
        sock.singleton.subscribe(channel, baked_chain_link)
        return base

    def raw_send_multipart(self, safe_args):
        if self.connected:
            print('SENDING TO {}: {}'.format(safe_args[0], repr(safe_args[1:])[0:100]))
            self.socket.send_multipart(safe_args)
        else:
            print('QUEUED FOR {}: {}'.format(safe_args[0], repr(safe_args[1:])[0:100]))
            self.message_queue.append(safe_args)

    def send_multipart(self, *args):
        safe_args = [(a.encode('utf-8', 'backslashreplace') if (type(a) is self.desired_type) else a) for a in args]
        self.raw_send_multipart(safe_args)

    def subscribe(self, channel, callback):
        channel = channel.lower()
        if self.connected:
            self.send_multipart('SUB', channel)
        self.subs[channel] = callback

    def handle_MSG(self, cmd, chan, body):
        cb = self.subs.get(chan, None)
        if cb:
            cb(cmd, chan, json.loads(body))

    def thread(self):
        print('in thread')
        try:
            while self.running:
                if (self.socket.poll(timeout=100)):
                    data = self.socket.recv_multipart()
                    if (sys.version_info.major == 3):
                        safe_data = [d.decode('utf-8') for d in data]
                    else:
                        safe_data = [d for d in data]
                    print('(Thread loop) '+repr(safe_data)[0:100])
                    handler = getattr(self, 'handle_{}'.format(safe_data[0]), None)
                    if handler:
                        self.call_safely(handler, safe_data)
                if (self.monitor.poll(timeout=100)):
                    evt = recv_monitor_message(self.monitor)
                    evt.update({'description': EVENT_MAP[evt['event']]})
                    if evt['event'] not in (zmq.EVENT_CONNECT_RETRIED,
                                            zmq.EVENT_CONNECT_DELAYED,
                                            zmq.EVENT_CLOSED):
                        # Completely ignore these 3 events because they spam too much.
                        print("Event: {}".format(evt))
                        if evt['event'] == zmq.EVENT_CONNECTED:
                            self.connected = True
                            self.send_multipart('CONNECT')
                            for c in self.subs:
                                self.send_multipart('SUB', c)
                            while self.message_queue:
                                self.raw_send_multipart(self.message_queue.pop(0))
                        if evt['event'] == zmq.EVENT_DISCONNECTED:
                            print('DISCONNECT')
                            self.connected = False
                        if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
                            break
        except zmq.ZMQError as e:
            print('Exception!')
            if e.errno == zmq.ETERM:
                pass           # Interrupted
            else:
                raise
        print('Exiting thread!')

    def start_thread(self):
        self.running = True
        import threading
        self._thread = threading.Thread(target=self.thread)
        self._thread.setDaemon(True)
        self._thread.start()

    def stop_thread(self):
        print('Stopping')
        self.running = False
        self._thread.join()


    def twisted_call_safely(self, func, args):
        print('(Twisted_call_safely) '+repr(args)[0:100])
        self.reactor.callFromThread(func, *args)

    def tornado_call_safely(self, func, args):
        print('(Tornado_call_safely) '+repr(args)[0:100])
        self.ioloop.add_callback(func, *args)

    def direct_call_safely(self, func, args):
        print('(Direct_call_safely) '+str(func)+' '+repr(args)[0:100])
        func(*args)

    def twisted_register(self, reactor):
        self.reactor = reactor
        self.call_safely = self.twisted_call_safely
        self.start_thread()

    def tornado_register(self, ioloop):
        self.ioloop = ioloop
        self.call_safely = self.tornado_call_safely
        self.start_thread()

    def foreground(self):
        self.call_safely = self.direct_call_safely
        self.running = True
        self.thread()
