from __future__ import print_function, unicode_literals
import json
from utils import sock

def send_to_channel(server, channel):
    def baked_send_to_channel(message):
        ircmsg = { 'server': server, 'channel': channel, 'message': message }
        sock.get_sock().send_multipart('MSG', 'output/irc/msg', json.dumps(ircmsg))
    return baked_send_to_channel
