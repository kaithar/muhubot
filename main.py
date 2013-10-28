import tornado.ioloop
import tornado.web

import tornado.platform.twisted
tornado.platform.twisted.install()

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
    tornado.ioloop.IOLoop.instance().start()
