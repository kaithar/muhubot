import tornado.ioloop
from twisted.internet import reactor

from internals.commandRegistry import CommandRegistry
import re

def going_away(registry, user, instruction, match):
    reactor.fireSystemEvent('shutdown')
    reactor.disconnectAll()
    tornado.ioloop.IOLoop.instance().stop()
    return {'success': True, 'answer': "So long and thanks for all the fish."}

def register():
    CommandRegistry.getRegistry().registerInstruction(re.compile(r'(go away|shutdown)!?'), going_away)
