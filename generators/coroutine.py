import functools

class Coroutine:
    '''
    Wrapper class to solve to take care of the priming of the generator
    and solve the double send problem with generators that accept input
    '''
    def __init__(self, task, *args, **kwargs):
        self.task = task(*args, **kwargs)
        self._repr = self._makeRepr(task, args, kwargs)

    def _makeRepr(self, task, args, kwargs):
        reprStr = f'{self.__class__.__name__}({task.__name__}'
        argsStr = ",".join([str(arg) for arg in args])
        kwargsStr = ",".join( [ f'{key}={value}' for key, value in kwargs.items() ] )

        for _str in [argsStr, kwargsStr]:
            reprStr+=f', {_str}' if _str else ''

        reprStr += ')'
        return reprStr

    def send(self, input):
        '''
        send method that calls next() on the generator before sending the input
        to address the double send problem
        '''
        next(self.task)
        res = self.task.send(input)        
        return res
    
    def __iter__(self):
        return iter(self.task)

    def __next__(self):
        return next(self.task)
    
    def __repr__(self):
        return self._repr
    
def coroutine(func):
    '''
    decorator that returns a Coroutine object
    '''
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return Coroutine(func, *args, **kwargs)
    return wrapper