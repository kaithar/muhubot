
class CommandRegistry(object):
    singleton = None
    jabber = None
    irc = None
    instructions = None
    help = None
    @staticmethod
    def getRegistry():
        if CommandRegistry.singleton == None:
            CommandRegistry.singleton = CommandRegistry()
            CommandRegistry.singleton.irc = []
            CommandRegistry.singleton.instructions = []
            CommandRegistry.singleton.help = ["help - show this list",]
        return CommandRegistry.singleton

    def registerInstruction(self, express, callback, help = []):
        self.instructions.append((express, callback))
        if help:
            self.help.extend(help)
            self.help.sort()

    def showHelp(self):
        return {'success': True, 'answer': "Help text:\n" + "\n".join(CommandRegistry.singleton.help)}

    def interpret(self, user, instruction):
        if instruction.startswith("help"):
            return self.showHelp()
        else:
            for (express,callback) in self.instructions:
                match = express.match(instruction)
                if match:
                    return callback(self, user, instruction, match)
            return {'success': False, 'answer': 'Unknown command'}

    def registerJabber(self, jabber):
        self.jabber = jabber

        # elif (instruction.startswith("announce")):
        #     for x in self.irc:
        #         x[0].msg(x[1], "Announce: %s"%instruction[len("announce "):])
        #     return { 'success': True, 'answer': "Announced" }
        # a = "Winning ::%s::, baby!" % repr(instruction)
        # return { 'success': True, 'answer': a }
