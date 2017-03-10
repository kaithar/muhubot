from __future__ import print_function, unicode_literals
import json
from utils.protocol import Socket as sock
from funchain import Chain, AsyncCall
import traceback

from utils.plumbing import command_registry
import re


tracker = {}
feeds = {}
callbacks = {}

cid = 0

def rss_receiver(cmd, channel, body):
    # {'tag': 'xkcd', 'item': rss_item}
    asc = body.get('tag', None)
    cbs = callbacks.get(asc, None)
    if cbs:
        cb = Chain() >> cbs
        try:
            cb(body)
        except:
            print("Callback exception")
            traceback.print_exc(None)

def poll_feed(tag, url, period = 10*60):
    global feeds, callbacks
    if tag not in feeds:
        feeds[tag] = {'feed': url, 'period': period}
        sock.get_sock().send_multipart('MSG', 'config/service/rss', json.dumps(feeds))
    if tag not in callbacks:
        callbacks[tag] = []
    c = Chain()
    callbacks[tag].append(c)
    return c

def rss_config(cmd, channel, body):
    global feeds
    sock.get_sock().send_multipart('MSG', body['requesting'], json.dumps(feeds))

def force_feed(body):
    # {'match': match, 'user': user, 'instruction': instruction, 'body': body, 'send_reply': send_reply}
    sock.get_sock().msg('config/force/rss', {'tag': body['match'].group(1)})
    return "I'll ask for you..."

def register_subs():
    try:
        sock.get_sock().subscribe('config/request/rss', rss_config)
        sock.get_sock().subscribe('input/http/rss', rss_receiver)
        command_registry.getRegistry().registerInstruction(
            re.compile(r'rss force (.*)'), force_feed, ("rss force [tag] - If you know the tag, you can force a recheck for it",))
    except:
        print("Failed to register subscriptions")
        traceback.print_exc(None)

register_subs()
