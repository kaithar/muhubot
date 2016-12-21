from .. import base
import feedparser
import json


class RSS_poller(base.Periodic):
    timeout = 1000
    targets = None
    def __init__(self):
        self.sock.subscribe('config/service/rss', self.do_config)
        self.sock.send_multipart('MSG', 'config/request/rss', json.dumps({'requesting': 'config/service/rss'}))
        self.targets = {}

    def do_config(self, cmd, channel, body):
        # body = {'xkcd': {'feed': 'https://www.xkcd.com/atom.xml', 'period': 10*60}}
        for tag in body:
            if tag not in self.targets:
                newtarget = {'period': 10*60 }
                newtarget.update(body[tag])
                newtarget['due'] = newtarget['period']
                self.targets[tag] = newtarget
                self.sock.send_multipart('MSG', 'input/rss/config', json.dumps({'status': 'Adding feed', 'feed': body[tag]['feed']}))
                newtarget['seen'] = items = {}
                d = feedparser.parse(newtarget['feed'])
                newtarget['last'] = d
                for item in d.entries:
                    iid = item.get('id', item.link)
                    items[iid] = item
        for tag in self.targets:
            if tag not in body:
                self.sock.send_multipart('MSG', 'input/rss/config', json.dumps({'status': 'Removing feed', 'feed': self.targets[tag]['feed']}))
                del self.targets[tag]

    def run(self):
        for tag in self.targets:
            t = self.targets[tag]
            t['due'] -= 1
            if t['due'] > 0:
                continue
            t['due'] = t['period']
            if 'etag' in t['last']:
                d = feedparser.parse(t['feed'], etag=t['last'].etag)
            elif 'modified' in t['last']:
                d = feedparser.parse(t['feed'], modified=t['last'].modified)
            else:
                d = feedparser.parse(t['feed'])
            if d.status == 304:
                continue
            t['last'] = d
            old_items = t['seen']
            items = {}
            for item in d.entries:
                iid = item.get('id', item.link)
                if iid not in old_items:
                    self.sock.send_multipart('MSG', 'input/http/rss', json.dumps({'tag': tag, 'item': item}))
                items[iid] = item
            t['seen'] = items
