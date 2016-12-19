import pprint

from . import gitlab, http

def default_formatter(*args, **kwargs):
    return "{}\n{}".format(pprint.pformat(args), pprint.pformat(kwargs))
