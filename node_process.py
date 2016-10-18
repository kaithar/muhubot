from __future__ import print_function

import sys
print(sys.version)

import logging

logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')
logger = logging.getLogger()
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)

from importlib import import_module
import_module('nodes.{}'.format(sys.argv[1]))
