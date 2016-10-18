from __future__ import print_function
from . import basic_bot
from twisted.internet import reactor

class Irc_abstraction (object):
    underlying_irc = None
    server = None
    channels = None
    port = None
    ssl = None
    password = None
    tw_factory = None
    joined = None

    def __init__(self, nickname, server, channels, port=6667, ssl=False, password=""):
        self.nickname = nickname
        self.server = server
        self.channels = channels
        self.port = port
        self.ssl = ssl
        self.password = password
        self.joined = []
        self.tw_factory = f = basic_bot.IrcBotFactory(self, nickname, channels, password)
        print("Trying to connect to {}:{}")
        reactor.connectTCP(server, port, f)
        return f

    def on_connection_made(self, irc):
        pass

    def on_connection_lost(self, irc, reason):
        self.joined = []

    def on_signed_on(self, irc):
        for c in self.channels:
            print('Joining {}'.format(c))
            irc.join(c)

    def on_join(self, irc, channel):
        self.joined.append((self, irc, channel))

    def on_privmsg(self, irc, user, channel, msg):
        pass

    def on_action(self, irc, user, channel, msg):
        pass

    def on_nick(self, irc, prefix, params):
        old_nick = prefix.split('!')[0]
        new_nick = params[0]

    def send_msg(self, channel, message):
        msg = message.encode("utf-8")
        for l in msg.split(r"\n"):
            self.tw_factory.ircclient.msg(channel, l)

    def relay(self, channel):
        def inner_relay(message):
            msg = message.encode("utf-8")
            for l in msg.split(r"\n"):
                self.tw_factory.ircclient.msg(channel, l)
        return inner_relay
