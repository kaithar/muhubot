import tornado.ioloop
import tornado.web

import tornado.platform.twisted
tornado.platform.twisted.install()

from connectors import irc, jabber
from commands import shutdown, deploy

if __name__ == "__main__":
    import config
    tornado.ioloop.IOLoop.instance().start()
