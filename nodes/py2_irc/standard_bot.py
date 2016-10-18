from __future__ import print_function
from .abstraction import Irc_abstraction
import traceback, re, json

class standard_bot(Irc_abstraction):
    def __init__(self, sock, nickname, server, channels, port=6667, ssl=False, password="", user_map={}):
        super(standard_bot, self).__init__(nickname, server, channels, port, ssl, password)
        self.sock = sock
        self.user_map = user_map

    def on_privmsg(self, irc, user, channel, msg):
        try:
            """This will get called when the bot receives a message."""
            #user = user.split('!', 1)[0]
            
            # Check to see if they're sending me a private message
            if channel == self.nickname:
                return

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

