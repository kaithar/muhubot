from random import randint
import time
import json
import pprint
import encodings

import traceback
import sys
import logging
import zmq

import multiprocessing
import queue

import ssl
import asyncio
import msgpack

class client(object):
    subs = None
    last_ping = 0
    ident = None
    def __init__(self):
        self.subs = []

class server(object):
    def __init__(self):
        self.subs = {}
        self.servers = {}
        self.mon = None

    def send_multipart(self, target, *args):
        if type(target) is str:
            target = self.servers[target]
        #safe_args = [(a.encode('utf-8') if type(a) is str else a) for a in args]
        self.set_indent('{:12} <- {:6} '.format(target.ident, args[0]))
        if (args[0] == 'PING'):
            if self.mon:
                msgpack.pack(['PING', target.ident], self.mon.writer)
        else:
            self.log(target.ident, repr(args))
        msgpack.pack(args, target.writer)

    def handle_CONNECT(self, client, _, val):
        client.ident = val
        self.send_multipart(client, 'CONNECT', 'OK')
        pass

    def handle_LOGMON(self, client, _):
        self.mon = client
        del self.servers[id(client.writer)]

    def handle_PING(self, client, _):
        self.send_multipart(client, 'PONG')

    def handle_PONG(self, client, _):
        msgpack.pack(['PONG', client.ident], self.mon.writer)

    def handle_SUB(self, client, _, chan):
        if (chan not in self.subs):
            self.subs[chan] = [client]
        else:
            if (client not in self.subs[chan]):
                self.subs[chan].append(client)
            else:
                self.log(client.ident, "WARNING: Client already subscribed to this channel!")
        if (chan not in client.subs):
            client.subs.append(chan)
        else:
            self.log(client.ident, "WARNING: Subbing to an already subscribed channel!")
        self.send_multipart(client, 'SUB', 'OK')
    
    def handle_UNSUB(self, client, _, chan):
        if (chan in self.subs):
            self.subs[chan].remove(client)
        if (chan in client.subs):
            client.subs.remove(chan)
        self.send_multipart(client, 'UNSUB', 'OK')
    
    def handle_MSG(self, client, _, chan, msg):
        sent_to = 0
        if (chan in self.subs):
            for tgt in self.subs[chan]:
                self.send_multipart(tgt, 'MSG', chan, msg)
                sent_to += 1
        self.send_multipart(client, 'MSGSTAT', 'OK', '{}'.format(sent_to))
        #foo = json.loads(msg.decode('utf'))

    def log(self, ident, msg):
        if self.mon:
            msgpack.pack(['LOG', ident, msg], self.mon.writer)
        self.logger.info("%s %s", self.indent, msg)

    def log_print(self, indent, msg):
        try:
            indent = indent.decode()
        except:
            pass
        self.mon.send_multipart(['LOG', indent, msg])
        self.logger.info("%s %s", indent, msg)

    def set_indent(self, indent):
        self.indent = indent
    
    def ticker(self, ch):
        if self.mon:
            msgpack.pack(['TICKER', ch], self.mon.writer)

    def close_connection(self, target):
        for c in target.subs:
            self.log(target.ident, 'Clearing {}'.format(c))
            if (c in self.subs):
                self.log(target.ident, 'Unsubbing {}'.format(c))
                self.subs[c].remove(target)

    def ping_loop(self):
        self.ticker('.')
        try:
            nowish = time.time()
            thenish = nowish-10
            deadish = nowish-20
            for s in [x for x in self.servers.keys()]:
                self.set_indent('Ping results: ')
                if (deadish > self.servers[s].last_ping):
                    self.log(self.servers[s], "Ping timeout for {}".format(s))
                    self.send_multipart(s, 'RECONNECT')
                    self.set_indent('Ping results: ')
                    self.close_connection(self.servers[s])
                    del self.servers[s]
                elif (thenish > self.servers[s].last_ping):
                    self.send_multipart(self.servers[s], 'PING')
            asyncio.get_event_loop().call_later(1, self.ping_loop)
        except:
            traceback.print_exc()


    def handle_packet(self, client_id, packet):
        self.ticker('+')
        pkt_from = self.servers.get(client_id, None)
        self.set_indent('{:10} -> {:6} '.format(pkt_from.ident, packet[0]))
        handler = getattr(self, 'handle_{}'.format(packet[0]), None)
        #try:
        if handler:
            handler(pkt_from, *packet)
        #except:
        #    self.log(''.join(traceback.format_exc(None)))
        pkt_from.last_ping = time.time()

server_obj = server()

def new_client(reader, writer):
    this_client = id(writer)
    server_obj.servers[this_client] = c = client()
    c.peername = writer.get_extra_info('peername')
    c.peercert = writer.get_extra_info('peercert')
    c.ident = str(this_client)
    c.writer = writer
    print(c.peername)
    print(c.peercert)
    unpacker = msgpack.Unpacker(raw=False)
    while True:
        data = yield from reader.read(10000)
        if not data:
            reader.feed_eof()
            break
        #print("Received %r" % data)
        unpacker.feed(data)
        for o in unpacker:
            #print(o)
            try:
                server_obj.handle_packet(this_client, o)
            except KeyboardInterrupt:
                break
            except:
                traceback.print_exc()
    try:
        if c == server_obj.mon:
            server_obj.mon = None
        else:
            server_obj.set_indent('Closing: ')
            server_obj.close_connection(c)
            del server_obj.servers[this_client]
    except:
        traceback.print_exc()

def main():
    logger = logging.getLogger()
    server_obj.logger = logger

    sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    sslctx.load_cert_chain('certificates/server.crt', 'certificates/server.key')
    sslctx.load_verify_locations('certificates/ca.crt')
    sslctx.verify_mode = ssl.CERT_REQUIRED

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(new_client, port=6161, ssl=sslctx, loop=loop)
    server = loop.run_until_complete(coro)
    loop.call_later(1, server_obj.ping_loop)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

main()