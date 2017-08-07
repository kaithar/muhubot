from utils.protocol import Socket
import config

if getattr(config, 'http_sink', False):
    my_config = {
        'zmq_endpoint': getattr(config, 'zmq_endpoint', 'tcp://127.0.0.1:{}'),
        'node_name': 'http_sink',
        'port': 8808,
        'sinks': [], 'pollers': [], 'apis': []
    }
    my_config.update(config.http_sink)
    zmq_sock = Socket(my_config['node_name'], my_config['zmq_endpoint'], './client_certs')

    import tornado.ioloop
    ioloop = tornado.ioloop.IOLoop.current()
    zmq_sock.tornado_register(ioloop)

    from .base import Periodic, Api
    import importlib
    import traceback
    import tornado.web

    if  my_config['sinks']:
        print('Configuring for {} sink modules'.format(len(my_config['sinks'])))

        sink_handlers = []

        for sink in my_config['sinks']:
            s = None
            try:
                s = importlib.import_module('nodes.py3_http_sink.sinks.{}'.format(sink))
            except:
                traceback.print_exc(None)
            if not s:
                try:
                    s = importlib.import_module('{}'.format(sink))
                except:
                    traceback.print_exc(None)
            if s:
                for on in dir(s):
                    o = getattr(s, on)
                    if (type(o) == type) and (issubclass(o, tornado.web.RequestHandler)):
                        print("Binding {} to {}".format(o, o.path))
                        o.sock = zmq_sock
                        sink_handlers.append((o.path, o))

        for poller in my_config['pollers']:
            s = None
            try:
                s = importlib.import_module('nodes.py3_http_sink.pollers.{}'.format(poller))
            except:
                traceback.print_exc(None)
            if not s:
                try:
                    s = importlib.import_module('{}'.format(poller))
                except:
                    traceback.print_exc(None)
            if s:
                for on in dir(s):
                    o = getattr(s, on)
                    if (type(o) == type) and (issubclass(o, Periodic)):
                        print("Creating poller {} for every {}ms".format(o, o.timeout))
                        o.sock = zmq_sock
                        cb = o()
                        print("Adding t.i.PC")
                        pc = tornado.ioloop.PeriodicCallback(cb.run, o.timeout)
                        pc.start()

        for api in my_config['apis']:
            s = None
            try:
                s = importlib.import_module('nodes.py3_http_sink.apis.{}'.format(api))
            except:
                traceback.print_exc(None)
            if not s:
                try:
                    s = importlib.import_module('{}'.format(api))
                except:
                    traceback.print_exc(None)
            if s:
                for on in dir(s):
                    o = getattr(s, on)
                    if (type(o) == type) and (issubclass(o, Api)):
                        print("Creating api {}".format(o))
                        o.sock = zmq_sock
                        cb = o()
 

        if len(sink_handlers) == 0:
            print("No handlers detected")
        else:
            application = tornado.web.Application(sink_handlers)
            application.listen(my_config['port'])

            ioloop.start()
            s.stop_thread()
