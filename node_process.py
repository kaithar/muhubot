from __future__ import print_function, unicode_literals
import logging
import traceback


class fmter(logging.Formatter):
	longestname = 0
	alternate = True
	def __init__(self, *args, **kargs):
		super(fmter, self).__init__(*args, **kargs)
		self.fgfmt = '\033[38;5;{0}m'
		self.bgfmt = '\033[48;5;{0}m'
		self.PL_delim = '\033[38;5;{0};48;5;{1}m\033[38;5;{2}m'
		self.reset = '\033[0m'
		self.bg_grey = self.bgfmt.format(240)
	def map(self, r,g,b):
		return 16 + round(r%256/51.2)*36 + round(g%256/51.2)*6 + round(b%256/51.2)
	levelmap = { 'DEBUG': (240, 'Debug'),
				 'INFO': (34, 'Info'), 
				 'WARNING': (166, 'Warn'),
				 'ERROR': (88, 'Error'),
				 'CRITICAL': (196, 'Crit') 
				}
	alternatemap = { True: 19, False: 25 }
	def format(self, r):
		self.longestname = min(20,max(self.longestname,len(r.name)))
		nargs = []
		levelc, leveln = self.levelmap[r.levelname]
		ac = self.alternatemap[self.alternate]
		self.alternate = not self.alternate
		nargs.append(self.bgfmt.format(ac))
		nargs.append(self.fgfmt.format(15))
		nargs.append(self.formatTime(r, ' %H:%M:%S '))
		nargs.append(self.PL_delim.format(ac,levelc, 15))
		nargs.append(' {:5} '.format(leveln))
		nargs.append(self.PL_delim.format(levelc,ac, 15))
		nargs.append((' {:'+str(self.longestname)+'} ').format(r.name))
		nargs.append(self.PL_delim.format(ac,ac+36, 15))
		nargs.append(' {}[{}] '.format(r.module, r.lineno))
		nargs.append(self.PL_delim.format(ac+36,0, ac+228))
		prefix = ''.join(nargs)
		lines = r.msg%r.args
		if r.exc_info:
			lines += "\n"+''.join(traceback.format_exception(*r.exc_info))
		return '\n'.join(['{} {}{}'.format(prefix, l, self.reset) for l in (r.msg%r.args).split("\n")])

if __name__ == '__main__':
	import locale
	locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')

	import sys
	print(sys.version)

	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)
	sh = logging.StreamHandler()
	sh.setLevel(logging.DEBUG)
	sh.setFormatter(fmter())
	logger.addHandler(sh)

	from importlib import import_module
	import_module('nodes.{}'.format(sys.argv[1]))
