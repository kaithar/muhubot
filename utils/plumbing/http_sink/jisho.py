from __future__ import print_function, unicode_literals
import json
from utils import sock
from funchain import AsyncCall
import traceback

tracker = {}

cid = 0

def receiver(body):
    asc = tracker.get(body['cid'], None)
    if asc:
        del tracker[body['cid']]
        asc.fire_callback(body['result'])

from utils.plumbing import command_registry
import re

def register_search():
    try:
        sock.get_sock().chain('plumbing/jisho/search') >> receiver
        def search(body):
            global cid
            # {'match': match, 'user': user, 'instruction': instruction, 'body': body, 'send_reply': send_reply}
            query = body['match'].group(2)
            if not query:
                return "usage: jisho words [keywords]"
            cid += 1
            my_cid = cid
            body = {'cid': my_cid, 'return_path': 'plumbing/jisho/search', 'query': query}
            asc = AsyncCall()
            tracker[my_cid] = asc
            sock.get_sock().send_multipart('MSG', 'api/jisho/words', json.dumps(body).encode('utf-8'))
            raise asc
        command_registry.getRegistry().registerInstruction(re.compile(r'jisho (words) ?(.*)?'), search, ("jisho words [keywords] - Search jisho.org for words",))
    except:
        print("Failed to register macros")
        traceback.print_exc(None)

register_search()

__all__ = ['receiver']
