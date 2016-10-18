import tornado.ioloop
import tornado.web

import tornado.platform.twisted
tornado.platform.twisted.install()
from twisted.internet import reactor

from internals.commandRegistry import CommandRegistry

from connectors import irc, jabber
from commands import shutdown, deploy

if __name__ == "__main__":
    import config
    reg = CommandRegistry.getRegistry()
    if reg.websinks:
        application = tornado.web.Application(reg.websinks)
        p = getattr(config, 'webport', 8808)
        application.listen(p)
    try:
        print "Starting loop"
        tornado.ioloop.IOLoop.instance().start()
    except:
        print "Stopping loop ... shutdown"
        reactor.fireSystemEvent('shutdown')
        print "Disconnect all"
        reactor.disconnectAll()
        print "Actual stop"
        tornado.ioloop.IOLoop.instance().stop()
        print "Stopped"
