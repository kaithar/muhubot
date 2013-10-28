import traceback
from twisted.words.protocols.jabber import jid, client
from twisted.words.xish import domish
from twisted.internet import reactor
from internals.commandRegistry import CommandRegistry

def instruction_parser(elem, registry=None):
    try:
        print elem.attributes
        if (elem.getAttribute('type',"") == "chat"):
            for e in elem.children:
                if (e.name == 'body'):
                    if (registry):
                        tg = elem['from'].split("/")[0]
                        ret = registry.interpret(elem['from'].split("/")[0], str(e))
                        retmsg = "%s, %s" % ((ret['success'] and ":)" or ":("), ret['answer'])
                        message = domish.Element((None, 'message'))
                        message['to'] = tg
                        message.addElement('body', content=retmsg.strip())
                        print message.toXml().encode('utf-8')
                        registry.jabber.send(message)
    except:
        traceback.print_exc(None)

def authd(xmlstream):
    print "authenticated"

    reg = CommandRegistry.getRegistry()
    reg.registerJabber(xmlstream)

    presence = domish.Element(('jabber:client','presence'))
    xmlstream.send(presence)

    xmlstream.addObserver('/message',  instruction_parser, registry=reg)
    xmlstream.addObserver('/message',  debug)
    xmlstream.addObserver('/presence', debug)
    xmlstream.addObserver('/iq',       debug)

#<message
#   xmlns='jabber:client'
#   to='dev.hubot@m247.com'
#   type='chat'
#   id='purple9082c802'
#   from='daniel.bradshaw@m247.com/d3d54b86'>
#       <active xmlns='http://jabber.org/protocol/chatstates'/>
#       <body>hi!</body>
#</message>
def debug(elem):
    print elem.toXml().encode('utf-8')
    print "="*20

def build(where, who, pword):
    myJid = jid.JID(who)
    factory = client.basicClientFactory(myJid, pword)
    factory.addBootstrap('//event/stream/authd',authd)
    reactor.connectTCP(where,5222,factory)

def relay(target):
    registry = CommandRegistry.getRegistry()
    def inner_relay(msg):
        message = domish.Element((None, 'message'))
        message['to'] = target
        message.addElement('body', content=msg.strip())
        registry.jabber.send(message)
    return inner_relay
