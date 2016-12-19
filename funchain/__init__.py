from __future__ import print_function
import traceback

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

class Progress(object):
    def __init__(self, chain):
        self.chain = chain
        self.links = chain.list

    def items(self):
        #print("entering")
        for i in self.links:
            yield i
        raise StopIteration()

# TODO: Make this threadsafe
class AsyncCall(Exception):
    result = None
    fired = False
    directed = False
    def ready_callback(self, chain, progressor):
        if self.fired:
            return chain.resume(progressor, self.result)
        else:
            self.chain = chain
            self.progressor = progressor
            self.directed = True
            return None

    def fire_callback(self, result):
        if self.directed:
            self.chain.resume(self.progressor, result)
        else:
            self.result = result
            self.fired = True

class Chain(object):
    def __init__(self):
        self.list = []

    @classmethod
    def asArgs(cls, function):
        return asArgs(function)

    @classmethod
    def emit(cls, text):
        return Emit(text)

    '''Chain.substitutor(subs, default) => callable
        The callable returned takes `a` and returns `subs.get(a, default)`
    '''
    @classmethod
    def substitutor(cls, subs, default=None):
        def inner(a):
            return subs.get(a,default)
        return inner

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

    def resume(self, progressor, inl):
        try:
            for i in progressor:
                #print("inl >> {}".format(inl))
                if isinstance(i, Chain):
                    inl = i(inl)
                elif isinstance(i,Mutation):
                    inl = i.doSomething(inl)
                elif isinstance(i, Emit):
                    print('[{}] next input = {}'.format(i.text,repr(inl)))
                else:
                    #print("huh")
                    for j in i:
                        try:
                            if callable(j):
                                #print("callable nested")
                                j(inl)
                            elif isinstance(j,Mutation):
                                j.doSomething(inl)
                            elif isinstance(j, Emit):
                                print('[{}] next input = {}'.format(j.text,repr(inl)))
                        except AsyncCall as e:
                            # This should be ok...
                            pass
                        except:
                            # If something in the list errors we keep going
                            traceback.print_exc(None)
        except StopIteration:
            return inl
        except AsyncCall as e:
            # the call raising this exception is expected to call e.fire_callback(result)
            if e.ready_callback(self, progressor) == None:
                raise
        return inl

    def __call__(self, *args, **kwargs):
        inl = None
        if (kwargs):
            inl = (args or (), kwargs)
        else:
            if len(args) == 1:
                inl = args[0]
            elif len(args) > 1:
                inl = args
        progressor = Progress(self)
        return self.resume(progressor.items(), inl)

__all__ = ['Chain']

if __name__ == "__main__":
    def Test(a):
        print("Test")
        return 1
    def Test2(a):
        print("Test2")
        return a+1
    asc = AsyncCall()
    def TestCouple(a):
        print("TestCouple")
        raise asc
    foo = Chain() >> Test >> Test2
    print(foo())
    foo = Chain() >> Test >> TestCouple >> Test2
    try:
        foo()
    except AsyncCall:
        print("except")
    print("uh")
    print(asc.fire_callback(3))
