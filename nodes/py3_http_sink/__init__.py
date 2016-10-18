from utils import sock
zmq_sock = sock()
import config

import importlib
import traceback
import tornado.web

if getattr(config, 'http_sink', False):
    my_config = {
        'zmq_endpoint': getattr(config, 'zmq_endpoint', 'tcp://127.0.0.1:5140'),
        'node_name': 'http_sink',
        'port': 8808,
        'sinks': []
    }
    my_config.update(config.http_sink)
    if  my_config['sinks']:
        print('Configuring for {} sink modules'.format(len(my_config['sinks'])))

        import tornado.ioloop
        ioloop = tornado.ioloop.IOLoop.current()

        zmq_sock.connect(my_config['node_name'], my_config['zmq_endpoint'])
        zmq_sock.tornado_register(ioloop)

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

        if len(sink_handlers) == 0:
            print("No handlers detected")
        else:
            application = tornado.web.Application(sink_handlers)
            application.listen(my_config['port'])

            ioloop.start()
            s.stop_thread()