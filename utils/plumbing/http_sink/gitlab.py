from __future__ import print_function, unicode_literals
import json
from utils.protocol import Socket as sock
import traceback
from funchain import Chain

# reverse map
event_map = {
    'input/http/commit/push': 'push',
    'input/http/commit/tag_push': 'tag_push',
    'input/http/commit/issue': 'issue',
    'input/http/commit/note': 'note',
    'input/http/commit/merge_request': 'merge_request',
    'input/http/commit/pipeline': 'pipeline',
    'input/http/gitlab_admin/project': 'project',
    'input/http/gitlab_admin/team': 'team',
    'input/http/gitlab_admin/user': 'user',
    'input/http/gitlab_admin/group': 'group',
    'input/http/gitlab_admin/push': 'generic_push',
    'input/http/gitlab_admin/tag_push': 'generic_tag_push'
}

all_tracking = { }
proj_tracking = { }

def event_for_project(event, project):
    project_chain = proj_tracking[event].get(project, None)
    if not project_chain:
        project_chain = proj_tracking[event][project] = []
    c = Chain()
    project_chain.append(c)
    return c

def global_event(event):
    c = Chain()
    all_tracking[event].append(c)
    return c


def gitlab_receiver(cmd, channel, body):
    # 'input/http/commit/push' receives object_kind "push"
    event = event_map.get(channel, None)
    if not event:
        return
    callbacks = proj_tracking[event].get(body['project']['path_with_namespace'], None)
    if callbacks:
        cb = Chain() >> callbacks
        cb(body)
    if all_tracking[event]:
        cb = Chain() >> all_tracking[event]
        cb(body)

for k,v in event_map.items():
    all_tracking[v] = []
    proj_tracking[v] = {}
    sock.get_sock().subscribe(k, gitlab_receiver)

# Tag push


# 'tag_push': 'input/http/commit/tag_push',
# 'issue': 'input/http/commit/issue',
# 'note': 'input/http/commit/note',
# 'merge_request': 'input/http/commit/merge_request',
# 'pipeline': 'input/http/commit/pipeline'
# 'project_create': 'input/http/gitlab_admin/project',
# 'project_destroy': 'input/http/gitlab_admin/project',
# 'project_rename': 'input/http/gitlab_admin/project',
# 'project_transferred': 'input/http/gitlab_admin/project',
# 'user_add_to_team': 'input/http/gitlab_admin/team',
# 'user_remove_from_team': 'input/http/gitlab_admin/team',
# 'user_create': 'input/http/gitlab_admin/user',
# 'user_destroy': 'input/http/gitlab_admin/user',
# 'key_create': 'input/http/gitlab_admin/user',
# 'key_destroy': 'input/http/gitlab_admin/user',
# 'group_create': 'input/http/gitlab_admin/group',
# 'group_destroy': 'input/http/gitlab_admin/group',
# 'user_add_to_group': 'input/http/gitlab_admin/group',
# 'user_remove_from_group': 'input/http/gitlab_admin/group',
# 'push': 'input/http/gitlab_admin/push',
# 'tag_push': 'input/http/gitlab_admin/tag_push'
