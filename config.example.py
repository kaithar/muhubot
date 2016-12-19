from connectors import irc, jabber
from commands import shutdown, deploy
from sinks import commits

# The dict is a mapping of nicks to email addresses.
iec = irc.build('muhubot', 'irc.example.com', "#coding", {"Bob": "bob@example.com"})
# Jabber uses a 1:1 mapping of jabber id to email address
#jabber.build('jabber.example.com', 'dev.muhubot@example.com/muhubot', 'SuperSecurePassword')

commits.build(
    [
        iec.relay("#coding"),
        #jabber.relay("bob@example.com")
    ]
)

deploy.register(
    {
        'thesiteyo': {
            'production': deploy.local_git('/home/theproductionsite/code_checkout')
        }
    }
)

shutdown.register()

irc = {
    'nick': 'muhubot',
    'servers': [
        {
            'nick': 'muhubot2', # If you want to set nick on a per server basis
            'host': 'irc.example.com',
            'port': 6667,
            'ssl': False,
            'password': "",
            'channels': ['#coding'],
            'usermap': {"Bob!bob@example.com": "bob@example.com"}
        }
    ]
}
