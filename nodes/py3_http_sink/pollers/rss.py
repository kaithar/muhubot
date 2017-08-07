from .. import base
import feedparser
import json
import tornado
from tornado import gen
import threading
import traceback
import socket

class RSS_poller(base.Periodic):
    timeout = 1000
    targets = None
    lock = None
    def __init__(self):
        self.sock.subscribe('config/service/rss', self.do_config)
        self.sock.subscribe('config/force/rss', self.force_tag)
        self.sock.send_multipart('MSG', 'config/request/rss', json.dumps({'requesting': 'config/service/rss'}))
        self.targets = {}
        self.lock = threading.Lock()

    def force_tag(self, cmd, channel, body):
        # body = {'tag': 'bleh'}
        tag = body.get('tag', None)
        if tag and tag in self.targets:
            self.targets[tag]['due'] = 0
            self.sock.msg('log/rss/forced', json.dumps({'status': 'Forcing tag', 'tag': tag}))

    def do_config(self, cmd, channel, body):
        # body = {'xkcd': {'feed': 'https://www.xkcd.com/atom.xml', 'period': 10*60}}
        if not self.lock.acquire():
            print("No lock")
            return
        try:
            print("Got lock")
            for tag in body:
                if tag not in self.targets.keys():
                    newtarget = {'period': 10*60 }
                    newtarget.update(body[tag])
                    newtarget['due'] = newtarget['period']
                    self.targets[tag] = newtarget
                    self.sock.send_multipart('MSG', 'input/rss/config', json.dumps({'status': 'Adding feed', 'feed': body[tag]['feed']}))
                    try:
                        with open('cache/{}.json'.format(tag), 'r') as f:
                            items = json.load(f)
                        self.targets[tag]['seen'] = items
                        print('Cache loaded for {}'.format(tag))
                    except FileNotFoundError:
                        print('No history for {}'.format(tag))
                        newtarget['seen'] = items = {}
                        d = feedparser.parse(newtarget['feed'])
                        newtarget['last'] = d
                        for item in d.entries:
                            iid = item.get('id', item.link)
                            items[iid] = item
                        print('Saving cache for {}'.format(tag))
                        with open('cache/{}.json'.format(tag), 'w') as f:
                            json.dump(items, f, indent=2)

            for tag in self.targets.keys():
                if tag not in body:
                    self.sock.send_multipart('MSG', 'input/rss/config', json.dumps({'status': 'Removing feed', 'feed': self.targets[tag]['feed']}))
                    del self.targets[tag]
        finally:
            self.lock.release()
            print("Released lock")

    @gen.coroutine
    def run(self):
        if not self.lock.acquire(blocking=False):
            print("No lock")
            return
        try:
            for tag in self.targets.keys():
                try:
                    t = self.targets[tag]
                    t['due'] -= 1
                    if t['due'] > 0:
                        continue
                    t['due'] = t['period']
                    headers = {}
                    lasttime = t.get('last', None)
                    # Just in case we're working from memory...
                    if lasttime:
                        if 'etag' in t['last']:
                            headers['If-None-Match'] = lasttime.etag
                        elif 'modified' in lasttime:
                            headers['If-Modified-Since'] = lasttime.modified
                    http_client = tornado.httpclient.AsyncHTTPClient()
                    req = yield http_client.fetch(t['feed'], headers=headers)
                    if req.code == 304:
                        continue
                    print("Considering {}".format(tag))
                    d = feedparser.parse(req.body)
                    t['last'] = d
                    old_items = t['seen']
                    items = {}
                    send = []
                    for item in d.entries:
                        iid = item.get('id', item.link)
                        if iid not in old_items:
                            send.append({'tag': tag, 'item': item})
                            print("[{}] New id! {}\n".format(tag,item.title).encode())
                            #self.sock.send_multipart('MSG', 'input/http/rss', json.dumps({'tag': tag, 'item': item}))
                        items[iid] = item
                    if send:
                        print("Sending {} items\n".format(len(send)))
                    for item in sorted(send, key=lambda x: x['item'].title):
                        self.sock.send_multipart('MSG', 'input/http/rss', json.dumps(item))
                    t['seen'] = items
                    with open('cache/{}.json'.format(tag), 'w') as f:
                        json.dump(items, f, indent=2)
                except socket.gaierror:
                    print("Socket error for %s!"%tag)
                    traceback.print_exc(None)
                except:
                    print("Something went very wrong")
                    traceback.print_exc(None)
                    raise
        finally:
            self.lock.release()
