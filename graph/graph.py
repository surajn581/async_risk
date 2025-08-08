import functools
from lib.logging import logger

def _getDependency(self, name):
    if not self._dependencies[name]:
        return []
    return list( [_name] + _getDependency(self, _name) for _name in self._dependencies[name] )[0]

def getDependency(self, name):
    return set(_getDependency(self, name))

def updateDependencies(self, name):
    if not self._current_stack:
        return
    stack_length = len(self._current_stack)
    while stack_length:
        parent = self._current_stack[stack_length-1]
        self._dependencies[parent].add(name)
        self._dependents[name].add(parent)
        stack_length-=1

def graph_node(func):
    """Decorator to mark a method as a graph node with caching + dependency tracking."""
    name = func.__name__

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        # update the dependency as soon as we enter the call stack
        updateDependencies(self, name)

        # If cached, return from cache
        logger.debug(f'looking for {name} in cache')
        if name in self._cache:
            logger.debug(f'found {name} in cache')
            return self._cache[name]

        # Track call stack to discover dependencies
        self._current_stack.append(name)
        logger.debug(f'{"...."*len(self._current_stack)}entered stack for {name} | stack: {self._current_stack}')
        result = func(self, *args, **kwargs)        
        self._current_stack.pop()
        logger.debug(f'{"...."*len(self._current_stack)}exitied stack for {name} | stack: {self._current_stack}')

        # Cache result
        logger.debug(f'adding {name}: {result} in cache')
        self._cache[name] = result
        return result

    wrapper._is_graph_node = True
    return wrapper


class Graph:
    def __init__(self):
        logger.debug('[Graph] __init__ start')
        self._cache = {}
        self._dependencies = {}   # node -> set of dependencies
        self._dependents = {}     # node -> set of dependents
        self._current_stack = []  # for dependency discovery

        # Initialize dependencies dict for all graph nodes
        for attr in dir(self):
            method = getattr(self, attr)
            if callable(method) and getattr(method, "_is_graph_node", False):
                self._dependencies[attr] = set()
                self._dependents[attr] = set()

        logger.debug('[Graph] __init__ end')

    def invalidate(self, node):
        """Invalidate node and all downstream dependents."""
        if node in self._cache:
            del self._cache[node]
        for dep in self._dependents.get(node, []):
            self.invalidate(dep)

    def set_value(self, node, value):
        """Set value of a leaf node and invalidate its dependents."""
        self._cache[node] = value
        self.invalidate(node)

# Example graph class
class MyGraph(Graph):
    def __init__(self):
        logger.debug('[MyGraph] __init__ start')
        self._A = 10
        super().__init__()
        logger.debug('[MyGraph] __init__ end')

    @graph_node
    def A(self):
        logger.debug('graph_node A called')
        return self._A

    @graph_node
    def B(self):
        logger.debug('graph_node B called')
        return self.A() ** 2

    @graph_node
    def C(self):
        logger.debug('graph_node C called')
        return self.B() + self.A()
    
    @graph_node
    def D(self, value):
        return value*self.B()
    
    @graph_node
    def E(self):
        return self.D( self.A() ) * 2
    
    @graph_node
    def F(self):
        if self.A() > 5:
            return self.E()*1.5
        else:
            return 14

    def set_A(self, value):
        self._A = value
        self.invalidate("A")
        logger.debug('graph_node A invalidated')