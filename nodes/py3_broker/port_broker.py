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

#sys.stdout = open('gk.log', 'w')
#sys.stderr = sys.stdout

EVENT_MAP = {}

class SockProcess(object):
    socket = None
    def __init__(self):
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
        self.log_queue.put(('GateKeeper', message))

    def create_socket(self):
        self.context = zmq.Context.instance()
        auth = ThreadAuthenticator(self.context)
        auth.start()
        #auth.allow('127.0.0.1')
        # Tell authenticator to use the certificate in a directory
        auth.configure_curve(domain='*', location=self.public_keys_dir)

        self.socket = self.context.socket(zmq.REP)
        self.monitor = self.socket.get_monitor_socket()

        server_secret_file = os.path.join(self.secret_keys_dir, "server.key_secret")
        server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
        self.socket.curve_secretkey = server_secret
        self.socket.curve_publickey = server_public
        self.socket.curve_server = True  # must come before bind
        self.socket.set(zmq.LINGER, 1)
        self.socket.identity = b"gatekeeper"
        self.socket.bind("tcp://0.0.0.0:5141")

    def main_loop(self):
        try:
            self.log('In proc')
            self.create_socket()
            while True:
                data = self.socket.recv()
                safe_data = data.decode('utf-8')
                self.log('I got one!')
                self.input_queue.put(True)
                port = self.output_queue.get()
                self.socket.send(str(port).encode())
                self.log('I sent one!')
                
                # Check for useful events
                if (self.monitor.closed == False and self.monitor.poll(timeout=100)):
                    evt = recv_monitor_message(self.monitor)
                    evt.update({'description': EVENT_MAP[evt['event']]})
                    if evt['event'] not in (zmq.EVENT_CONNECT_RETRIED,
                                            zmq.EVENT_CONNECT_DELAYED,
                                            zmq.EVENT_CLOSED):
                        # Completely ignore these 3 events because they spam too much.
                        self.log("Event: {}".format(evt))
                        if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
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

class Socket(object):
    def __init__(self, manager, log_queue):
        # For sanity the input and output queues are reversed on the other end
        # Our input_queue is SockProcess's output_queue
        # The swap happens in the reversal of the first two args passed to set_queues
        self.input_queue = manager.Queue()
        self.output_queue = manager.Queue()
        self.log_queue = log_queue
        self.sockproc = SockProcess()
        self.sockproc.set_queues(self.output_queue, self.input_queue, self.log_queue)
        self.proc = multiprocessing.Process(
            target=self.sockproc.main_loop,
            daemon=True)
        self.proc.start()
