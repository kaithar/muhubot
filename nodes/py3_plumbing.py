from __future__ import print_function, unicode_literals

from utils.protocol import Socket

import config

my_config = {
    'broker': getattr(config, 'broker', '127.0.0.1'),
    'node_name': 'plumbing'
}
try:
    my_config.update(config.plumbing_options)
except:
    print("Using default options")

s = Socket(my_config['node_name'], my_config['broker'], './certificates')

config.plumbing()

s.foreground()
