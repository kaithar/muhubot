from __future__ import print_function, unicode_literals
import json
import tornado.web

class CommitHandler(tornado.web.RequestHandler):
    path = r"/hooks/repo/commit"
    callbacks = None
    sock = None
    def post(self):
        self.sock.send_multipart('MSG', 'input/http/commit', self.request.body)

