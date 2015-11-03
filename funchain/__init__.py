from __future__ import print_function

class Mutation(object):
    func = None
    def __init__(self, func):
        self.func = func
        pass

class asRaw(Mutation):
    '''This takes a return of `a` and calls `input(a)`'''
    def doSomething(self, input):
        return self.func(input)

class asArgs(Mutation):
    '''This takes a return of `a` and calls `input(*a)`'''
    def doSomething(self, input):
        return self.func(*input)

class asKwargs(Mutation):
    '''This takes a return of `a` and calls `input(**a)`'''
    def doSomething(self, input):
        return self.func(**input)

class asArgsKwargs(Mutation):
    '''This takes a return of `(a,b)` and calls `input(*a, **b)`'''
    def doSomething(self, input):
        return self.func(*input[0],**input[1])

class Substitutor(object):
    '''This takes a return of `a` and calls `input(subs[a])`'''

class Emit(object):
    text = ""
    def __init__(self, text):
        self.text = text

class Chain(object):
    def __init__(self):
        self.list = []

    @classmethod
    def asArgs(cls, function):
        return asArgs(function)

    @classmethod
    def emit(cls, text):
        return Emit(text)

    '''substitutor(subs, default) => callable
        The callable returned takes `a` and returns `subs.get(a, default)`
    '''
    @classmethod
    def substitutor(cls, subs, default=None):
        def inner(a):
            return subs.get(a,default)

    def __or__(self, other):
        return self.__rshift__(other)
    def __ior__(self, other):
        return self.__rshift__(other)
    def __lshift__(self,other):
        return self.__rshift__(other)

    def __rshift__(self, other):
        #print(repr(other))
        if (isinstance(other,Mutation) or isinstance(other, Emit)):
            self.list.append(other)
            return self
        if (callable(other)):
            self.list.append(asRaw(other))
            return self
        outs = []
        for foo in other:
            if (isinstance(other,Mutation)):
                self.list.append(other)
                return self
            if callable(foo):
                outs.append(foo)
        self.list.append(outs)
        return self

    def __call__(self, *args, **kwargs):
        inl = None
        if (kwargs):
            inl = (args or (), kwargs)
        else:
            if len(args) == 1:
                inl = args[0]
            elif len(args) > 1:
                inl = args
        for i in self.list:
            if isinstance(i, Chain):
                i(inl)
            elif isinstance(i,Mutation):
                inl = i.doSomething(inl)
            elif isinstance(i, Emit):
                print('[{}] next input = {}'.format(i.text,repr(inl)))
            else:
                for j in i:
                    if callable(j):
                        j(inl)
                    elif isinstance(j,Mutation):
                        inl = j.doSomething(inl)
                    elif isinstance(j, Emit):
                        print('[{}] next input = {}'.format(j.text,repr(inl)))
        return inl

__all__ = ['Chain']
