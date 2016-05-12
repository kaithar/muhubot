from internals.commandRegistry import CommandRegistry
from salt.client import LocalClient
import re

# salt.register(
#     {
#         'some command phrase': {
#             'target': 'salt-client-1',
#             'instruction': 'state.sls',
#             'arg': ("my-state-name",)
#     }
# )

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

deployments = None

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


def do_macro(registry, user, instruction, match):
    macro = match.group('target')
    if (macro not in deployments.keys()):
        return {'success': False, 'answer': "I don't currently know about %s" % macro}
    tgt = deployments[macro]
    print "Starting macro %s"%macro
    client = LocalClient()
    t = client.cmd(tgt['target'], tgt['instruction'], arg=tgt['arg'], timeout=120)
    if (tgt['instruction'] == "state.sls"):
        ans = formatter_state(t)
    else:
        ans = formatter_raw(t)
    return {'success': True, 'answer': ans}

def register(deps):
    global deployments
    deployments = deps
    CommandRegistry.getRegistry().registerInstruction(
        re.compile(r'salt macro (?P<target>.+?)$'),
        do_macro,
        help=["salt macro <macro name> - Perform specified salt macro."]
        )
