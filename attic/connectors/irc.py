from __future__ import print_function

import traceback
#import tornado.ioloop
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from internals.commandRegistry import CommandRegistry

import re, codecs, json

from utils import sock

class IrcBot(irc.IRCClient):
    """Expose stuff to irc"""
    
    nickname = "mubot"
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.factory.ircclient = self

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        for x in self.reg.irc[:]:
            if x[0] == self:
                self.reg.irc.remove(x)

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.reg.irc.append((self, channel))

    def privmsg(self, user, channel, msg):
        try:
            """This will get called when the bot receives a message."""
            user = user.split('!', 1)[0]
            
            # Check to see if they're sending me a private message
            if channel == self.nickname:
                return

            auth_user = self.factory.usermap.get(user,"Unknown")

            self.sock.send_multipart('MSG', 'input/irc/msg', json.dumps({'target': channel, 'source': user, 'authed_as':auth_user, 'msg': msg}))

            # Otherwise check to see if it is a message directed at me
            sec = re.match(r"@?%s ?[:,;@-]? *(?P<instruct>.*)$"%self.nickname, msg)
            if sec:
                ret = self.reg.interpret(self.factory.usermap.get(user,"Unknown"), sec.group('instruct'))
                msg = "%s: %s, %s" % (user , (ret['success'] and "Success" or "Failure"), ret['answer'])
                for line in msg.strip().split("\n"):
                    self.msg(channel, line)
            if hasattr(self.factory,"onPrivmsg"):
                self.factory.onPrivmsg(user, channel, msg)
        except:
            traceback.print_exc(None)


    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        pass

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]

class IrcBotFactory(protocol.ClientFactory):
    """A factory for IRC connectors.
    """

    def __init__(self, sock, name, channel, usermap = {}, pword = ""):
        self.name = name
        self.channel = channel
        self.usermap = usermap
        self.pword = pword
        self.sock = sock
        sock.subscribe('output/irc/say', self.sinkIrcSay)

    def sinkIrcSay(self, cmd, channel, body):
        # body = { 'server': 'irc.example.com', 'channel': '#moo', 'message': 'Hello you people!' }
        trg = body.get('channel', None).encode("utf-8")
        if trg:
            #msg = codecs.lookup("unicode_escape").encode(body.get('message', 'Message missing?!'))[0]
            msg = body.get('message', 'Message missing?!').encode("utf-8")
            for l in msg.split(r"\n"):
                self.ircclient.msg(trg, l)

    def relay(self, channel):
        def inner_relay(message):
            msg = codecs.lookup("unicode_escape").encode(message)[0]
            for l in msg.split(r"\n"):
                self.ircclient.msg(channel, l)
        return inner_relay

    def buildProtocol(self, addr):
        p = IrcBot()
        p.factory = self
        p.reg = CommandRegistry.getRegistry()
        p.nickname = self.name
        p.password = self.pword
        p.sock = self.sock
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print("connection failed: {}".format(reason))
        reactor.fireSystemEvent('shutdown')
        reactor.disconnectAll()
        tornado.ioloop.IOLoop.instance().stop()

def build(name, server, channel, usermap = {}, port=6667, ssl=False, pword="", s=None, zmq_endpoint='tcp://127.0.0.1:5140'):
    if not s:
        s = sock('irc_'+server, zmq_endpoint)
        s.twisted_register(reactor)
    f = IrcBotFactory(s, name, channel, usermap, pword)
    reactor.connectTCP(server, port, f)
    return f
