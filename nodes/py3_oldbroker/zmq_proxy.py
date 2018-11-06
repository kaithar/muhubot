from __future__ import print_function, unicode_literals
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
from zmq.utils.monitor import recv_monitor_message
import sys
import os
import json
import time
import queue
import multiprocessing
import traceback
import config

class SockProcess(object):
    socket = None
    def __init__(self):
        self.ident = ""
        # Based on ironhouse.py
        base_dir = os.path.dirname(config.__file__)
        keys_dir = os.path.join(base_dir, 'certificates')
        self.public_keys_dir = os.path.join(base_dir, 'public_keys')
        self.secret_keys_dir = os.path.join(base_dir, 'private_keys')

        if not (os.path.exists(keys_dir) and
                os.path.exists(self.public_keys_dir) and
                os.path.exists(self.secret_keys_dir)):
            logging.critical("Certificates are missing - run generate_certificates.py script first")
            sys.exit(1)

    def set_queues(self, input_queue, output_queue, log_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.log_queue = log_queue

    def log(self, message):
        try:
            self.log_queue.put((self.ident, message))
        except:
            sys.stderr.write(message)

    def create_socket(self):
        self.context = zmq.Context()
        auth = ThreadAuthenticator(self.context)
        auth.start()
        #auth.allow('127.0.0.1')
        # Tell authenticator to use the certificate in a directory
        auth.configure_curve(domain='*', location=self.public_keys_dir)

        self.socket = self.context.socket(zmq.ROUTER)
        self.monitor = self.socket.get_monitor_socket()

        server_secret_file = os.path.join(self.secret_keys_dir, "server.key_secret")
        server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
        self.socket.curve_secretkey = server_secret
        self.socket.curve_publickey = server_public
        self.socket.curve_server = True  # must come before bind

        self.socket.set(zmq.LINGER, 1)
        self.socket.identity = b"mom"
        self.port = self.socket.bind_to_random_port("tcp://0.0.0.0")
        return self.port

    def main_loop(self, handshaking):
        try:
            self.ident = handshaking
            self.log('In proc')
            port = self.create_socket()
            self.log('Got port {}'.format(port))
            self.input_queue.put((port, 'PORT', handshaking))
            while True:
                if (self.socket.poll(timeout=100)):
                    request = self.socket.recv_multipart(copy=False)
                    pa = request[-1].get(b"Peer-Address")
                    request = [r.bytes for r in request]
                    self.input_queue.put((port,'RECV',pa,request))

                try:
                    o = self.output_queue.get(block=False)
                    self.socket.send_multipart(o)
                except queue.Empty:
                    pass
                
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
                            self.socket.unbind()
                            self.log('CONNECTION')
                        if evt['event'] == zmq.EVENT_DISCONNECTED:
                            self.log('DISCONNECT')
                            self.context.destroy(1)
                            break
                        if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
                            self.log('Monitor stopped')
                            self.context.destroy(1)
                            break

        except zmq.ZMQError as e:
            self.log('Exception!')
            if e.errno == zmq.ETERM:
                pass           # Interrupted
            else:
                self.log(''.join(traceback.format_exc(None)))
        except:
            self.log(''.join(traceback.format_exc(None)))
        self.log('Exiting thread!')


class Proxy(object):
    subs = None
    last_ping = 0
    def __init__(self, handshaking, input_queue, output_queue, log_queue):
        self.subs = []
        # For sanity the input and output queues are reversed on the other end
        # Our input_queue is SockProcess's output_queue
        # The swap happens in the reversal of the first two args passed to set_queues
        self.input_queue = input_queue
        self.sockproc = SockProcess()
        self.sockproc.set_queues(output_queue, input_queue, log_queue)
        self.proc = multiprocessing.Process(
            target=self.sockproc.main_loop,
            args=(handshaking,),
            daemon=True)
        self.proc.start()
