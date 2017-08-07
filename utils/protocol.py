from __future__ import print_function, unicode_literals
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
from zmq.utils.monitor import recv_monitor_message
import sys
import os
import json
import time
import multiprocessing

try:
    import queue
except ImportError:
    import Queue as queue

EVENT_MAP = {}

class SockProcess(object):
    if (sys.version_info.major == 3):
        desired_type = str
    else:
        desired_type = unicode

    connected = False
    identity = ""
    endpoint = ""
    socket = None

    last_activity = 0

    def __init__(self, certificate_path):
        self.subs = {}
        self.message_queue = []
        self.keys_dir = certificate_path

        if not os.path.exists(self.keys_dir):
            logging.critical("Certificates are missing")
            sys.exit(1)

    def set_queues(self, input_queue, output_queue, log_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.log_queue = log_queue

    def log(self, message):
        print(message)
        self.log_queue.put(message)

    def create_socket(self):
        self.log("Creating context")
        self.context = zmq.Context()
        self.log("Creating socket")
        self.socket = self.context.socket(zmq.DEALER)
        # Based on ironhouse.py
        client_secret_file = os.path.join(self.keys_dir, "client.key_secret")
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
        self.socket.curve_secretkey = client_secret
        self.socket.curve_publickey = client_public

        server_public_file = os.path.join(self.keys_dir, "server.key")
        server_public, _ = zmq.auth.load_certificate(server_public_file)
        # The client must know the server's public key to make a CURVE connection.
        self.socket.curve_serverkey = server_public
        self.log("Creating monitor")
        self.monitor = self.socket.get_monitor_socket()

    def _connect(self):
        num = int(time.time())%100
        iden = "{}_{}".format(self.identity, num)
        self.log("Connecting as {}".format(iden))
        if (sys.version_info.major == 3 or type(iden) is self.desired_type):
            self.socket.identity = iden.encode('utf-8')
        else:
            self.socket.identity = iden

        while True:
            self.log("Requesting port")
            qsock = self.context.socket(zmq.REQ)
            client_secret_file = os.path.join(self.keys_dir, "client.key_secret")
            client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
            qsock.curve_secretkey = client_secret
            qsock.curve_publickey = client_public

            server_public_file = os.path.join(self.keys_dir, "server.key")
            server_public, _ = zmq.auth.load_certificate(server_public_file)
            # The client must know the server's public key to make a CURVE connection.
            qsock.curve_serverkey = server_public
            qsock.set(zmq.LINGER, 1)
            qsock.connect(self.endpoint.format("5141"))
            qsock.send(b'')
            if qsock.poll(timeout=1000):
                port = int(qsock.recv())
                self.log("Got port {}".format(port))
                qsock.close()
                break
            else:
                self.log("Timeout requesting port")
                qsock.close()

        self.socket.connect(self.endpoint.format(port))
        self.log("Socket connect requested")
        self.last_activity = time.time()

    def connect(self, identity, endpoint):
        self.identity = identity
        self.endpoint = endpoint
        self.reconnect()

    def reconnect(self):
        self.log("Reconnecting")
        self.connected = False
        if self.socket:
            self.log("Closing socket")
            self.socket.close(1)
            self.log("Destroying context")
            self.context.destroy(1)
        self.create_socket()
        self._connect()

    def raw_send_multipart(self, safe_args):
        if self.connected:
            if (safe_args[0] != b'PONG'):
                self.log('SENDING TO {}: {}'.format(safe_args[0], repr(safe_args[1:])[0:100]))
            self.socket.send_multipart(safe_args)
        else:
            self.log('QUEUED FOR {}: {}'.format(safe_args[0], repr(safe_args[1:])[0:100]))
            self.message_queue.append(safe_args)

    def send_multipart(self, *args):
        safe_args = [(a.encode('utf-8', 'backslashreplace') if (type(a) is self.desired_type) else a) for a in args]
        self.raw_send_multipart(safe_args)

    def send_SUB(self, channel):
        channel = channel.lower()
        if self.connected:
            self.send_multipart('SUB', channel)
        self.subs[channel] = True

    def handle_PING(self, *args):
        self.send_multipart('PONG')

    def handle_PONG(self, *args):
        pass

    def handle_RECONNECT(self, *args):
        self.log('Reconnect received!')
        self.reconnect()

    def main_loop(self, identity, endpoint):
        print('In proc')
        self.connect(identity, endpoint)
        try:
            while True:
                # First the outgoing instructions...
                try:
                    command = self.input_queue.get(False)
                    # Command is like ('SUB', channel)
                    handler = getattr(self, 'send_{}'.format(command[0].upper()), None)
                    if handler:
                        handler(*command[1:])
                    else:
                        self.send_multipart(*command)
                except queue.Empty:
                    pass # Nothing to pull
                
                # Now the incoming
                nowish = time.time()
                if (self.socket.poll(timeout=100)):
                    self.last_activity = nowish
                    data = self.socket.recv_multipart()
                    if (sys.version_info.major == 3):
                        safe_data = [d.decode('utf-8') for d in data]
                    else:
                        safe_data = [d for d in data]

                    if (safe_data[0] != 'PING'):
                        self.log(repr(safe_data)[0:100])

                    handler = getattr(self, 'handle_{}'.format(safe_data[0]), None)
                    if handler:
                        handler(*safe_data)
                    else:
                        self.output_queue.put(safe_data)

                # Did the server go quiet?
                if (nowish - 30 > self.last_activity):
                    self.log('No recent activity, reconnecting!')
                    self.reconnect()
                
                # Check for useful events
                if (self.monitor.closed == False and self.monitor.poll(timeout=100)):
                    evt = recv_monitor_message(self.monitor)
                    evt.update({'description': EVENT_MAP[evt['event']]})
                    if evt['event'] not in (zmq.EVENT_CONNECT_RETRIED,
                                            zmq.EVENT_CONNECT_DELAYED,
                                            zmq.EVENT_CLOSED):
                        # Completely ignore these 3 events because they spam too much.
                        self.log("Event: {}".format(evt))
                        if evt['event'] == zmq.EVENT_CONNECTED:
                            self.connected = True
                            self.send_multipart('CONNECT')
                            for c in self.subs:
                                self.send_multipart('SUB', c)
                            while self.message_queue:
                                self.raw_send_multipart(self.message_queue.pop(0))
                        if evt['event'] == zmq.EVENT_DISCONNECTED:
                            self.log('DISCONNECT')
                            self.reconnect()
                        if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
                            break
        except zmq.ZMQError as e:
            self.log('Exception!')
            if e.errno == zmq.ETERM:
                pass           # Interrupted
            else:
                raise
        self.log('Exiting thread!')


class Socket(object):
    singleton = None
    subs = None

    def __init__(self, identity, endpoint, certificate_path, delayStart=False):
        global EVENT_MAP
        for name in dir(zmq):
            if name.startswith('EVENT_'):
                value = getattr(zmq, name)
                EVENT_MAP[value] = name
        m = multiprocessing.Manager()
        self.manager = m
        # For sanity the input and output queues are reversed on the other end
        # Our input_queue is SockProcess's output_queue
        # The swap happens in the reversal of the first two args passed to set_queues
        self.input_queue = m.Queue()
        self.output_queue = m.Queue()
        self.log_queue = m.Queue()
        self.sockproc = SockProcess(certificate_path)
        self.sockproc.set_queues(self.output_queue, self.input_queue, self.log_queue)
        # After 3.3 it would be better to pass daemon as a kwarg in this constructor
        self.proc = multiprocessing.Process(
            target=self.sockproc.main_loop,
            args=(identity, endpoint))
        # But since this supports lower than 3.3, set the daemon flag like this
        self.proc.daemon=True
        if not delayStart:
            self.proc.start()
        Socket.singleton = self
        self.subs = {}

    def start():
        self.proc.start()

    ###

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
        if (args[0] != 'PING'):
            print('(Twisted_call_safely) '+repr(args)[0:100])
        self.reactor.callFromThread(func, *args)

    def tornado_call_safely(self, func, args):
        if (args[0] != 'PING'):
            print('(Tornado_call_safely) '+repr(args)[0:100])
        self.ioloop.add_callback(func, *args)

    def direct_call_safely(self, func, args):
        if (args[0] != 'PING'):
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

    ###

    @staticmethod
    def get_sock():
        return Socket.singleton

    @staticmethod
    def receiving(channel):
        def baked_subscription(f):
            Socket.singleton.subscribe(channel, f)
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
        Socket.singleton.subscribe(channel, baked_chain_link)
        return base

    ###

    def handle_MSG(self, cmd, chan, body):
        cb = self.subs.get(chan, None)
        if cb:
            cb(cmd, chan, json.loads(body))

    def thread(self):
        print('in thread')
        while self.running:
            try:
                msg = self.log_queue.get(False)
                print("(proc) "+msg)
            except queue.Empty:
                pass # Nothing to pull
            except EOFError:
                print("!?")
                break

            try:
                command = self.input_queue.get(False)
                # Command is like ('MSG', channel, jsonblob)
                handler = getattr(self, 'handle_{}'.format(command[0].upper()), None)
                if handler:
                    self.call_safely(handler, command)
            except queue.Empty:
                #print("+")
                pass # Nothing to pull
            except EOFError:
                break

            time.sleep(0.05)

        print('Exiting thread!')

    ###

    def send_multipart(self, *args):
        self.output_queue.put(args)

    def msg(self, channel, message):
        self.send_multipart('MSG', channel, json.dumps(message))

    def msgstat(self, count):
        self.send_multipart('MSGSTAT', 'OK', count)

    def subscribe(self, channel, callback):
        channel = channel.lower()
        self.send_multipart('SUB', channel)
        self.subs[channel] = callback

    def ping(self):
        self.send_multipart('PING')

    def pong(self):
        self.send_multipart('PONG')

    def connect(self, endpoint_fmt):
        self.send_multipart('CONNECT')

    def reconnect(self):
        self.send_multipart('RECONNECT')


        
