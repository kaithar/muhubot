
# {
#   "object_kind": "push",
#   "before": "95790bf891e76fee5e1747ab589903a6a1f80f22",
#   "after": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
#   "ref": "refs/heads/master",
#   "checkout_sha": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
#   "user_name": "John Smith",
#   "user_email": "john@example.com",
#   "user_avatar": "https://s.gravatar.com/avatar/d4c74594d841139328695756648b6bd6?s=8://s.gravatar.com/avatar/d4c74594d841139328695756648b6bd6?s=80",
#   "project":{
#     "name":"Diaspora",
#     "path_with_namespace": "mark/Diaspora"
#   },
#   "commits": [
#     {
#       "id": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
#       "message": "fixed readme",
#       "timestamp": "2012-01-03T23:36:29+02:00",
#       "url": "http://example.com/mike/diaspora/commit/da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
#       "author": {
#         "name": "GitLab dev user",
#         "email": "gitlabdev@dv6700.(none)"
#       },
#       "added": ["CHANGELOG"],
#       "modified": ["app/controller/application.rb"],
#       "removed": []
#     }
#   ],
#   "total_commits_count": 4
# }


def commits(commit):
    print("For commit %s"%repr(commit))
    msg = "%s: Pushing %d commits to %s"%(
        commit['user_name'], commit['total_commits_count'],
        commit['project']['path_with_namespace'],
    )
    for ct in commit['commits']:
        msg += "\n%s: [%s] %s"%(
            ct['author']['name'], ct['id'][:9],
            ct['message']
           )
    print(msg)
    return msg
