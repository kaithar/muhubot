
#{
# "before":"374819e338845a23e9e4f2f76a659a3c8b41a534",
# "after":"82897e41903ba4d30b5aba0ae25444cd43fc7894",
# "ref":"refs/heads/master",
# "user_id":1,
# "user_name":"Kaithar",
# "repository":{
#   "name":"muhubot",
#   "url":"path_to_repo.git",
#   "description":null,
#   "homepage":"path_to_project.com"
# },
# "commits":[
#   {"id":"82897e41903ba4d30b5aba0ae25444cd43fc7894",
#    "message":"Web sink support",
#    "timestamp":"2013-10-28T04:08:33+00:00",
#    "url":"http://path_to_project/commit/82897e41903ba4d30b5aba0ae25444cd43fc7894",
#    "author":{
#      "name":"Kaithar","email":"kaithar@blah"
#    }
#   }
# ],
# "total_commits_count":1
#}

def commit_formatter(commit):
    print("For commit %s"%repr(commit))
    msg = "%s: Pushing %d commits to %s"%(
        commit['user_name'], commit['total_commits_count'],
        commit['repository']['name'],
    )
    for ct in commit['commits']:
        msg += "\n%s: [%s] %s"%(
            ct['author']['name'], ct['id'][:9],
            ct['message']
           )
    print(msg)
    return msg
