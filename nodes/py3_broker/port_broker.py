from __future__ import print_function, unicode_literals
import zmq
from zmq.utils.monitor import recv_monitor_message
import sys
import json
import time
import queue
import multiprocessing
import traceback

sys.stdout = open('gk.log', 'w')
sys.stderr = sys.stdout

EVENT_MAP = {}

class SockProcess(object):
    socket = None
    def __init__(self):
        pass

    def set_queues(self, input_queue, output_queue, log_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.log_queue = log_queue

    def log(self, message):
        try:
            self.log_queue.put(('GateKeeper', message))
        except:
            sys.stderr.write(message)

    def create_socket(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.monitor = self.socket.get_monitor_socket()
        self.socket.set(zmq.LINGER, 1)
        self.socket.identity = b"gatekeeper"
        self.socket.bind("tcp://127.0.0.1:5141")

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
        try:
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
        except:
            sys.stderr.write(''.join(traceback.format_exc(None)))
