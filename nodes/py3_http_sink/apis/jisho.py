from .. import base
from tornado.httpclient import AsyncHTTPClient
from tornado.escape import url_escape
import json

class api_jisho(base.Api):
    def __init__(self):
        self.sock.subscribe('api/jisho/words', self.request_words)

    def request_words(self, cmd, channel, body):
        # body = { 'query': 'string', 'return_path': 'plumbing/jisho/search', 'cid': 1234 }
        request = 'http://jisho.org/api/v1/search/words?keyword={}'.format(url_escape(body['query']))
        print("Sending request for {}".format(request))
        hc = AsyncHTTPClient()
        hc.fetch(request, self.handle_words(body))

    def handle_words(self, body):
        tag_reduction = {
            'Honorific or respectful (sonkeigo)': 'Respectful/Sonkeigo',
            'Abbreviation': 'Abbrev.',
            'Usually written using kana alone': 'Usually in kana'
        }
        pos_reduction = {
            'Noun': 'n.',
            'No-adjective': 'No-adj.',
            'Suru verb': 'Suru v.',
            'Suru verb - irregular': 'Suru v. - irregular',
            'Godan verb with su ending': 'Godan -su v.',
            'Pronoun': 'Pron.',
            'Expression': 'Expr.',
            'Wikipedia definition': 'Wikipedia'
        }
        def inner_handle(response):
            print("Response!")
            if response.error:
                self.sock.send_multipart('MSG', body['return_path'], json.dumps({'result': response.error, 'cid': body['cid']}))
            else:
                responding = []
                res = json.loads(response.body.decode())
                if (len(res['data']) == 0):
                    self.sock.send_multipart('MSG', body['return_path'], json.dumps({'result': "No results found", 'cid': body['cid']}))
                    return
                responding.append('{} results on page 1, I can show at most 5.'.format(len(res['data'])))
                for item in res['data'][:5]:
                    words = ' '.join(["[ {} | {} ]".format(x.get('word',''), x.get('reading','')) for x in item['japanese']])
                    senses = []
                    for x in item['senses']:
                        #print(repr(x).encode())
                        x1 = ' | '.join([pos_reduction.get(y,str(y)) for y in x['parts_of_speech'] if y])
                        x2 = ' | ' if x1 else ''
                        x3 = '; '.join(x['english_definitions'])
                        x5 = ' | '.join([tag_reduction.get(y,str(y)) for y in x['tags'] if y])
                        x4 = ' | ' if x5 else ''
                        senses.append("[ {}{}{}{}{} ]".format(x1,x2,x3,x4,x5))
                    senses = ' '.join(senses)
                    tags = '({}) '.format('; '.join(item['tags'])) if item['tags'] else ""
                    responding.append("{} : {}{}".format(words, tags, senses))
                self.sock.send_multipart('MSG', body['return_path'], json.dumps({'result': "\n".join(responding), 'cid': body['cid']}))
        return inner_handle

