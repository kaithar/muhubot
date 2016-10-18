import sys, json, traceback

from utils import sock
zmq_sock = sock()
import config

from salt.client import LocalClient


def formatter_raw(result):
    ans = []
    for h,a in result.items():
        ans.append("{} responded with {}".format(h,repr(a)))
    return '\n'.join(ans)

#{
#    'git_|-git@blahblah_|-git@blahblah_|-latest': {
#        'comment': 'Repository /blahblah/ is up-to-date', 'name': 'git@blahblah', 'start_time': '02:17:43.048571',
#        'result': True, 'duration': 3455.455, '__run_num__': 3, 'changes': {}, '__id__': 'git@blahblah'},
# ....
#}

def formatter_state(result):
    ans = []
    for h,a in result.items():
        state_lines = []
        for s, a2 in a.items():
            sp = s.split('_|-')
            a2['PF'] = 'P' if a2['result'] else 'F'
            a2['short'] = "%s.%s"%(sp[0], sp[-1])
            a2['duration'] = int(a2['duration'])
            state_lines.append("{PF} {short} {name}: {comment} ({duration}ms)".format(**a2))
        ans.append("{} responded with \n{}".format(h,"\n".join(state_lines)))
    return '\n'.join(ans)

def run(target='*', instruction='test.ping', cmd_arg=None):
    if not cmd_arg:
        cmd_arg = ()
    def salt_runner(*args, **kwargs):
        print "In salt_runner"
        client = LocalClient()
        t = client.cmd(target, instruction, arg=cmd_arg, timeout=120)
        if (instruction == "state.sls"):
            ans = formatter_state(t)
        else:
            ans = formatter_raw(t)
        return ans
    return salt_runner

def do_run(cmd, channel, body):
    # {'cid': 'blahblah', 'target': '*', 'instruction': 'test.ping', cmd_arg: ['']}
    try:
        cmd_arg = body.get('cmd_arg', ())
        instruction = body.get('instruction', 'test.ping')
        target = body.get('target', '*')
        client = LocalClient()
        t = client.cmd(target, instruction, arg=cmd_arg, timeout=240)
        if (instruction == "state.sls"):
            ans = formatter_state(t)
        else:
            ans = formatter_raw(t)
        result = {'cid': body.get('cid', None), 'result': ans}
        zmq_sock.send_multipart('MSG', 'input/salt/run', json.dumps(result))
    except:
        traceback.print_exc(None)
        result = {'cid': body.get('cid', None), 'result': 'An exception occurred'}
        zmq_sock.send_multipart('MSG', 'input/salt/run', json.dumps(result))

my_config = {
    'zmq_endpoint': getattr(config, 'zmq_endpoint', 'tcp://127.0.0.1:5140'),
    'node_name': 'salt'
}
if getattr(config, 'salt', False):
    my_config.update(config.salt)

zmq_sock.connect(my_config['node_name'], my_config['zmq_endpoint'])

zmq_sock.subscribe('output/salt/run', do_run)
zmq_sock.foreground()
