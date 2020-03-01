from __future__ import print_function, unicode_literals
import sys
import os
import time
import multiprocessing
import logging
import msgpack
import ssl
import socket
import traceback

try:
    import queue
except ImportError:
    import Queue as queue

class SockProcess(object):
    if (sys.version_info.major == 3):
        desired_type = str
    else:
        desired_type = unicode

    connected = False
    identity = ""
    endpoint = ""
    socket = None
    sslctx = None

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

    def set_running(self, running):
        self.running = running

    def log(self, message):
        print(message)
        self.log_queue.put(message)

    def create_context(self):
        self.log("Creating context")
        self.sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
        self.sslctx.load_cert_chain(os.path.join(self.keys_dir, "client.crt"), os.path.join(self.keys_dir, "client.key"))
        self.sslctx.load_verify_locations(os.path.join(self.keys_dir, "ca.crt"))
    
    def _connect(self):
        num = int(time.time())%100
        iden = "{}_{}".format(self.identity, num)
        self.log("Connecting as {}".format(iden))
        self.cur_identity = iden
        #if (sys.version_info.major == 3 or type(iden) is self.desired_type):
        #    self.socket.identity = iden.encode('utf-8')
        #else:
        #    self.socket.identity = iden

        self.log("Loading socket")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = self.sslctx.wrap_socket(sock)
        ssl_sock.connect((self.endpoint, 6161))
        self.socket = ssl_sock
        ssl_sock.settimeout(0.1)
        self.last_activity = time.time()
        self.connected = True
        self.send_multipart('CONNECT', iden)
        for c in self.subs:
            self.send_multipart('SUB', c)
        while self.message_queue:
            self.raw_send_multipart(self.message_queue.pop(0))


    def connect(self, identity, endpoint):
        self.identity = identity
        self.endpoint = endpoint
        self.reconnect()

    def reconnect(self):
        self.log("Reconnecting")
        self.connected = False
        if self.socket:
            self.log("Closing socket")
            self.socket.close()
        if not self.sslctx:
            self.create_context()
        try:
            self._connect()
        except ConnectionRefusedError:
            print("Connection refused!")
            return
        except:
            print("Error!")
            traceback.print_exc()
            return
        self.unpacker = msgpack.Unpacker(raw=False)

    def raw_send_multipart(self, safe_args):
        if self.connected:
            if (safe_args[0] != 'PONG'):
                self.log('SENDING TO {}: {}'.format(safe_args[0], repr(safe_args[1:])[0:100]))
            msgpack.pack(safe_args, self.socket)
        else:
            self.log('QUEUED FOR {}: {}'.format(safe_args[0], repr(safe_args[1:])[0:100]))
            self.message_queue.append(safe_args)

    def send_multipart(self, *args):
        #safe_args = [(a.encode('utf-8', 'backslashreplace') if (type(a) is self.desired_type) else a) for a in args]
        self.raw_send_multipart(args)

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
        self.running.wait()
        self.connect(identity, endpoint)
        while self.running.is_set():
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
            try:
                try:
                    inc = self.socket.read()
                except ValueError:
                    self.log('ValueError, reconnecting!')
                    self.reconnect()
                    continue
                self.unpacker.feed(inc)
                for data in self.unpacker:
                    self.last_activity = nowish
                    if (data[0] != 'PING'):
                        self.log(repr(data)[0:100])

                    handler = getattr(self, 'handle_{}'.format(data[0]), None)
                    if handler:
                        handler(*data)
                    else:
                        self.output_queue.put(data)
            except socket.timeout:
                pass
            except:
                print("Exception!")
                traceback.print_exc()
                self.last_activity = nowish - 15
                pass

            # Did the server go quiet?
            if (nowish - 30 > self.last_activity):
                self.log('No recent activity, reconnecting!')
                self.reconnect()
        self.log('Exiting thread!')


class Socket(object):
    singleton = None
    subs = None

    def __init__(self, identity, endpoint, certificate_path, delayStart=False):
        m = multiprocessing.Manager()
        self.manager = m
        # For sanity the input and output queues are reversed on the other end
        # Our input_queue is SockProcess's output_queue
        # The swap happens in the reversal of the first two args passed to set_queues
        self.input_queue = m.Queue()
        self.output_queue = m.Queue()
        self.log_queue = m.Queue()
        self.running = m.Event()
        self.running.set()
        self.sockproc = SockProcess(certificate_path)
        self.sockproc.set_queues(self.output_queue, self.input_queue, self.log_queue)
        self.sockproc.set_running(self.running)
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
        import threading
        self._thread = threading.Thread(target=self.thread)
        self._thread.setDaemon(True)
        self._thread.start()

    def stop_thread(self):
        print('Stopping')
        self.running.clear()
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
        import tornado.autoreload
        self.ioloop = ioloop
        self.call_safely = self.tornado_call_safely
        tornado.autoreload.add_reload_hook(self.stop_thread)
        self.start_thread()

    def foreground(self):
        self.call_safely = self.direct_call_safely
        self.running.set()
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
            cb(cmd, chan, body)

    def thread(self):
        print('in thread')
        while self.running.is_set():
            try:
                msg = self.log_queue.get(False)
                print("(thread) "+msg)
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
        print('Thread waiting!')
        self.proc.join()
        print('Exiting thread!')

    ###

    def send_multipart(self, *args):
        self.output_queue.put(args)

    def msg(self, channel, message):
        self.send_multipart('MSG', channel, message)

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


        
