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

def run_command(target = '*', instruction = 'test.ping', cmd_arg = None):
    if not cmd_arg:
        cmd_arg = ()
    def command_runner(dummy):
        global cid
        cid += 1
        my_cid = cid
        body = { 'cid': my_cid, 'target': target, 'instruction': instruction, 'cmd_arg': cmd_arg }
        asc = AsyncCall()
        tracker[my_cid] = asc
        sock.get_sock().send_multipart('MSG', 'output/salt/run', json.dumps(body).encode('utf-8'))
        raise asc
    return command_runner

from utils.plumbing import command_registry
import re

def register_salt_macros():
    try:
        sock.get_sock().chain('input/salt/run') >> receiver
        from config import salt
        # salt = {
        #     'macros': {
        #         'test': {'target': '*', 'instruction': 'test.ping', 'cmd_arg': ()}
        #     }
        # }
        macros = salt.get('macros', {})
        def salt_macro(body):
            # {'match': match, 'user': user, 'instruction': instruction, 'body': body, 'send_reply': send_reply}
            macro_name = body['match'].group(1)
            if not macro_name:
                return "Known macros: {}".format(", ".join(macros.keys()))
            macro = macros.get(macro_name.strip(), None)
            if not macro:
                return "Unknown macro"
            run_command(**macro)({})
        command_registry.getRegistry().registerInstruction(re.compile(r'salt macro( .*)?'), salt_macro, ("salt macro [name] - Run specified macro, omit name to get a list of macros",))
    except:
        print("Failed to register macros")
        traceback.print_exc(None)

register_salt_macros()

__all__ = ['receiver', 'run_command']
