from __future__ import print_function

import traceback
#import tornado.ioloop
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, task

import codecs

class IrcBot(irc.IRCClient):
    """Expose stuff to irc"""
    
    nickname = "mubot"
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.factory.ircclient = self
        self.factory.connected = True
        self.handler.on_connection_made(self)

    def connectionLost(self, reason):
        self.factory.connected = False
        irc.IRCClient.connectionLost(self, reason)
        self.handler.on_connection_lost(self, reason)

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.handler.on_signed_on(self)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.handler.on_join(self, channel)

    def privmsg(self, user, channel, msg):
        self.handler.on_privmsg(self, user, channel, msg)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        self.handler.on_action(self, user, channel, msg)

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        self.handler.on_nick(self, prefix, params)

class IrcBotFactory(protocol.ClientFactory):
    """A factory for IRC connectors.
    """
    connected = False
    sendq = None

    def __init__(self, handler, nickname, channels, password = ""):
        self.nickname = nickname
        self.password = password
        self.handler = handler
        self.sendq = []
        loop = task.LoopingCall(self.another_message)
        loop.start(1.0)

    def another_message(self):
        if self.connected:
            if self.sendq:
                channel, l = self.sendq.pop(0)
                self.ircclient.msg(channel,l)

    def send_message(self, channel, message):
        msg = codecs.lookup("unicode_escape").encode(message)[0]
        for l in msg.split(r"\n"):
            self.sendq.append((channel, l))
            #self.ircclient.msg(channel, l)

    def relay(self, channel):
        def inner_relay(message):
            self.send_message(channel, message)
        return inner_relay

    def buildProtocol(self, addr):
        p = IrcBot()
        p.factory = self
        p.nickname = self.nickname
        p.password = self.password
        p.handler = self.handler
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        self.connected = False
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.connected = False
        print("connection failed: {}".format(reason))
        connector.connect()

