from __future__ import print_function
import pydle
import traceback, re, json

class standard_bot(pydle.Client):
    def __init__(self, sock, nickname, server, channels, port=6667, ssl=False, password="", user_map={}):
        super(standard_bot, self).__init__(nickname)
        self.server = server
        self.want_channels = channels
        self.port = port
        self.ssl = ssl
        
        self.sock = sock
        self.user_map = user_map

    def on_connect(self):
        super().on_connect()
        for c in self.want_channels:
            self.join(c)


    def on_channel_message(self, channel, user, msg):
        try:
            """This will get called when the bot receives a message."""            
            auth_user = self.user_map.get(user,"Unknown")

            return_path = { 'to': 'output/irc/msg', 'args': {'server': self.server, 'channel': channel }}

            self.sock.send_multipart('MSG', 'input/irc/msg', json.dumps({'server': self.server, 'target': channel, 'source': user, 'authed_as':auth_user, 'msg': msg, 'return_path': return_path }))

            # Otherwise check to see if it is a message directed at me
            sec = re.match(r"[@!]?%s ?[:,;@-]? *(?P<instruct>.*)$"%self.nickname, msg)
            if sec:
                self.sock.send_multipart('MSG', 'input/irc/command', json.dumps(
                    {'server': self.server, 'target': channel, 'source': user, 'authed_as':auth_user, 'msg': msg, 'instruction': sec.group('instruct'), 'return_path': return_path }
                    ))
        except:
            traceback.print_exc(None)

    def send_msg(self, channel, message):
        self.message(channel, message)

    def relay(self, channel):
        def inner_relay(message):
            self.message(channel, message)
        return inner_relay

