from __future__ import print_function, unicode_literals
import json
import tornado.web

class GitlabCommitHandler(tornado.web.RequestHandler):
    path = r"/hooks/gitlab/commit"
    callbacks = None
    sock = None
    channels = {
        'push': 'input/http/commit/push',
        'tag_push': 'input/http/commit/tag_push',
        'issue': 'input/http/commit/issue',
        'note': 'input/http/commit/note',
        'merge_request': 'input/http/commit/merge_request',
        'pipeline': 'input/http/commit/pipeline'
    }
    def post(self):
        body = json.loads(self.request.body.decode())
        object_kind = body.get('object_kind', None)
        print(object_kind)
        if (object_kind):
            chan = self.channels.get(object_kind, None)
            if chan:
                self.sock.send_multipart('MSG', chan, self.request.body)

class GitlabSystemHandler(tornado.web.RequestHandler):
    path = r"/hooks/gitlab/system"
    callbacks = None
    sock = None
    channels = {
        'project_create': 'input/http/gitlab_admin/project',
        'project_destroy': 'input/http/gitlab_admin/project',
        'project_rename': 'input/http/gitlab_admin/project',
        'project_transferred': 'input/http/gitlab_admin/project',
        'user_add_to_team': 'input/http/gitlab_admin/team',
        'user_remove_from_team': 'input/http/gitlab_admin/team',
        'user_create': 'input/http/gitlab_admin/user',
        'user_destroy': 'input/http/gitlab_admin/user',
        'key_create': 'input/http/gitlab_admin/user',
        'key_destroy': 'input/http/gitlab_admin/user',
        'group_create': 'input/http/gitlab_admin/group',
        'group_destroy': 'input/http/gitlab_admin/group',
        'user_add_to_group': 'input/http/gitlab_admin/group',
        'user_remove_from_group': 'input/http/gitlab_admin/group',
        'push': 'input/http/gitlab_admin/push',
        'tag_push': 'input/http/gitlab_admin/tag_push'
    }
    def post(self):
        body = json.loads(self.request.body.decode())
        object_kind = body.get('object_kind', None)
        print(object_kind)
        if (object_kind):
            chan = self.channels.get(object_kind, None)
            if chan:
                self.sock.send_multipart('MSG', chan, self.request.body)


