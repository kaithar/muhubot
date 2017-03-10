from utils.protocol import Socket as sock
import json
import funchain

def getRegistry():
    if CommandRegistry.singleton == None:
        CommandRegistry.singleton = CommandRegistry()
        CommandRegistry.singleton.instructions = []
        CommandRegistry.singleton.help = ["help - show this list",]
    return CommandRegistry.singleton

class CommandRegistry(object):
    singleton = None
    instructions = None
    help = None
    blockHelp = False

    def registerInstruction(self, express, callback, help = []):
        self.instructions.append((express, callback))
        if help:
            self.help.extend(help)
            self.help.sort()

    def showHelp(self):
        return "Help text:\n" + "\n".join(CommandRegistry.singleton.help)

    def interpret(self, body):
        # Body looks something like:
        # {
        #   'server': self.server,
        #   'target': channel,
        #   'source': user,
        #   'authed_as':auth_user,
        #   'msg': msg,
        #   'instruction': sec.group('instruct'),
        #   'return_path': { 'to': 'output/irc/msg', 'args': {'server': self.server, 'channel': channel }}
        # }
        # From this we can construct a return path call regardless of the service that sent it.

        if 'return_path' in body:
            return_body = body['return_path']['args']
            return_target = body['return_path']['to']
            user, instruction = body['source'], body['instruction']
            def send_reply(message):
                return_body['message'] = message
                sock.get_sock().send_multipart('MSG', return_target, json.dumps(return_body))

            if instruction.startswith("help"):
                if not self.blockHelp:
                    send_reply(self.showHelp())
            else:
                for (express,callback) in self.instructions:
                    match = express.match(instruction)
                    if match:
                        cb = funchain.Chain() >> callback
                        cb >> send_reply
                        try:
                            cb({'match': match, 'user': user, 'instruction': instruction, 'body': body, 'send_reply': send_reply})
                        except funchain.AsyncCall as e:
                            send_reply('Command running')
                        return
                send_reply('Unknown command')
