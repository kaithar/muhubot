import sys

from utils.protocol import Socket
import config

servers = []
 
def msg_relay(cmd, channel, body):
    # body = { 'server': 'irc.example.com', 'channel': '#moo', 'message': 'Hello you people!' }
    server = body.get('server', None)
    if server:
        channel = body.get('channel', None)
        if channel:
            msg = body.get('message', 'Message missing?!')
            for s in servers:
                if s.server == server and channel in s.channels:
                    for line in msg.split('\n'):
                        s.send_msg(channel, line.strip())
                else:
                    print("{} {} not in {}/{}".format(server, channel, s.server, repr(s.channels.keys())))
        else:
            print("No channel")
    else:
        print("No server")

# This stack of nested if/else statements would likely be better refactored to use exceptions.
if getattr(config, 'irc', False):
    my_config = {
        'zmq_endpoint': getattr(config, 'zmq_endpoint', 'tcp://127.0.0.1:{}'),
        'node_name': 'irc',
        'nickname': 'muhubot',
        'servers': []
    }
    my_config.update(config.irc)
    if my_config['servers']:
        print('Configuring for {} servers'.format(len(my_config['servers'])))
        zmq_sock = Socket(my_config['node_name'], my_config['zmq_endpoint'])
        import tornado.ioloop
        ioloop = tornado.ioloop.IOLoop.current()
        zmq_sock.tornado_register(ioloop)
        import pydle
        pool = pydle.ClientPool()
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
                from .standard_bot import standard_bot
                server = standard_bot(zmq_sock, **opts)
                servers.append(server)
                pool.connect(server, opts['server'], opts['port'], tls=opts['ssl'], password=opts['password'])
        if len(servers) > 0:
            zmq_sock.subscribe('output/irc/msg', msg_relay)
            pool.handle_forever()
            zmq_sock.stop_thread()
        else:
            print('No valid servers found')
    else:
        print('No servers found')
else:
    print('No config found')

