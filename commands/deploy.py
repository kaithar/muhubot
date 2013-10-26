from internals.commandRegistry import CommandRegistry
import re
import subprocess

def local_git_helper(target):
    try:
        out = subprocess.check_output(
            ["/usr/bin/git", "pull"],
            stderr=subprocess.STDOUT,
            cwd=target['directory']
        )
    except subprocess.CalledProcessError as e:
        return {'success': False, 'answer': "Return value is %d\n%s" % (e.returncode, e.output)}
    except OSError as e:
        return {'success': False, 'answer': str(e)}
    return {'success': True, 'answer': out}

def local_git(directory):
    return {'helper': local_git_helper, 'directory': directory}

deployments = None

def do_deploy(registry, user, instruction, match):
    project = match.group('project')
    if (project not in deployments.keys()):
        return {'success': False, 'answer': "I don't currently know about %s" % project}
    target = match.group('target')
    if (target not in deployments[project].keys()):
        return {'success': False, 'answer': "I don't currently how to deploy %s to %s" % (project, target)}
    return deployments[project][target]['helper'](deployments[project][target])

def register(deps):
    global deployments
    deployments = deps
    CommandRegistry.getRegistry().registerInstruction(
        re.compile(r'deploy (?P<project>.+?) (?:to)? ?(?P<target>.+)$'),
        do_deploy,
        help=["deploy <project name> [to] <target> - Perform specified deployment."]
        )
