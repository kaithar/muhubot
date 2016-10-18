from __future__ import print_function, unicode_literals

from utils import sock

s = sock()
import config

my_config = {
    'zmq_endpoint': getattr(config, 'zmq_endpoint', 'tcp://127.0.0.1:5140'),
    'node_name': 'plumbing'
}
try:
    my_config.update(config.plumbing_options)
except:
    print("Using default options")

config.plumbing()

s.connect(my_config['node_name'], my_config['zmq_endpoint'])
s.foreground()
