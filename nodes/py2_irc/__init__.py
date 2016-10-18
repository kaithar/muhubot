import sys

from utils import sock
zmq_sock = sock()
import config

from .standard_bot import standard_bot
from utils import sock

from twisted.internet import reactor
from twisted.python import log
log.startLogging(sys.stdout)

servers = []

def msg_relay(cmd, channel, body):
    # body = { 'server': 'irc.example.com', 'channel': '#moo', 'message': 'Hello you people!' }
    server = body.get('server', None).encode("utf-8")
    if server:
        channel = body.get('channel', None).encode("utf-8")
        if channel:
            msg = body.get('message', 'Message missing?!')
            for s in servers:
                if s.server == server and channel in s.channels:
                    s.send_msg(channel, msg)

# This stack of nested if/else statements would likely be better refactored to use exceptions.
if getattr(config, 'irc', False):
    my_config = {
        'zmq_endpoint': getattr(config, 'zmq_endpoint', 'tcp://127.0.0.1:5140'),
        'node_name': 'irc',
        'nickname': 'muhubot',
        'servers': []
    }
    my_config.update(config.irc)
    if my_config['servers']:
        print('Configuring for {} servers'.format(len(my_config['servers'])))
        zmq_sock.connect(my_config['node_name'], my_config['zmq_endpoint'])
        zmq_sock.twisted_register(reactor)
        for s in my_config['servers']:
            if 'server' not in s:
                print('Missing "server" config value')
            elif ('channels' not in s) or (type(s['channels']) != list) or (len(s['channels']) == 0):
                print('Invalid "channels" list for {}'.format(s['server']))
            else:
                opts = {
                    'nickname': my_config['nickname'], 'port': 6667, 'ssl': False, 'password': "", 'user_map': {}
                }
                opts.update(s)
                server = standard_bot(zmq_sock, **opts)
                servers.append(server)
        if len(servers) > 0:
            zmq_sock.subscribe('output/irc/msg', msg_relay)
            reactor.run()
            zmq_sock.stop_thread()
        else:
            print('No valid servers found')
    else:
        print('No servers found')
else:
    print('No config found')

