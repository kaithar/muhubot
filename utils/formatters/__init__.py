import pprint

from .commit_formatter import commit_formatter

formatters = {
    'commits': commit_formatter
}

def default_formatter(*args, **kwargs):
    return "{}\n{}".format(pprint.pformat(args), pprint.pformat(kwargs))

def register_formatter(name, function):
    formatters[name] = function

def get_formatter(name):
    return formatters.get(name, default_formatter)
