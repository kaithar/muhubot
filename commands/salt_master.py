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

deployments = None

def run(target='*', instruction='test.ping', arg=None):
    def salt_runner(*args, **kwargs):
        if not arg:
            arg = ()
        client = LocalClient()
        t = client.cmd(target, instruction, arg=arg, timeout=120)
        ans = []
        for h,a in t.items():
            ans.append("{} responded with {}".format(h,repr(a)))
        return '\n'.join(ans)
    return salt_runner


def do_macro(registry, user, instruction, match):
    macro = match.group('target')
    if (macro not in deployments.keys()):
        return {'success': False, 'answer': "I don't currently know about %s" % macro}
    tgt = deployments[macro]
    client = LocalClient()
    t = client.cmd(tgt['target'], tgt['instruction'], arg=tgt['arg'], timeout=120)
    ans = []
    for h,a in t.items():
        ans.append("{} responded with {}".format(h,repr(a)))
    return {'success': True, 'answer': '\n'.join(ans)}

def register(deps):
    global deployments
    deployments = deps
    CommandRegistry.getRegistry().registerInstruction(
        re.compile(r'salt macro (?P<target>.+?)$'),
        do_macro,
        help=["salt macro <macro name> - Perform specified salt macro."]
        )
