import functools

class Coroutine:
    '''
    Wrapper class to solve to take care of the priming of the generator
    and solve the double send problem with generators that accept input
    '''
    def __init__(self, task, *args, **kwargs):
        self.func = task
        self.args = args
        self.kwargs = kwargs
        self.task = self.func(*self.args, **self.kwargs)
        self.__iter__ = self.task.__iter__

    def send(self, input):
        '''
        send method that calls next() on the generator before sending the input
        to address the double send problem
        '''
        next(self.task)
        res = self.task.send(input)        
        return res

    def __next__(self):
        return next(self.task)
    
    def __repr__(self):
        return f'{self.__class__.__name__}({self.func.__name__}, *{self.args}, **{self.kwargs})'
    
def coroutine(func):
    '''
    decorator that returns a Coroutine object
    '''
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return Coroutine(func, *args, **kwargs)
    return wrapper