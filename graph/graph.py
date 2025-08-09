import functools
from lib.logging import logger

# def _getDependency(self, name):
#     if not self._dependencies[name]:
#         return []
#     return list( [_name] + _getDependency(self, _name) for _name in self._dependencies[name] )[0]

# def getDependency(self, name):
#     return set(_getDependency(self, name))

def updateDependencies(self, name):
    if not self._current_stack:
        return
    stack_length = len(self._current_stack)
    while stack_length:
        parent = self._current_stack[stack_length-1]
        self._dependencies[parent].add(name)
        self._dependents[name].add(parent)
        stack_length-=1

class GraphNode:
    """Graph Node"""
    def __init__(self, func, settable=False):
        self.func = func
        self.name = func.__name__
        self.settable = settable
        self._is_graph_node = True

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # Return a callable wrapper so g.A() still works
        @functools.wraps(self.func)
        def caller(*args, **kwargs):

            # update the dependency as soon as we enter the call stack
            # TODO noticed a bug when nested deps are not captured incase one of the nested dep is already cached.
            # eg:   if F > E > D > B > A and E is already in cache then when calling F()
            #       the call only marks F: {E}
            updateDependencies(instance, self.name)

            # If cached, return value
            logger.debug(f'[GraphNode] looking for {self.func} in cache')
            if self.name in instance._cache:
                logger.debug(f'[GraphNode] found {self.func} in cache')
                return instance._cache[self.name]

            # Track call stack for dependency discovery
            instance._current_stack.append(self.name)
            logger.debug(f'[GraphNode] {"...."*len(instance._current_stack)}entered stack for {self.func} | stack: {instance._current_stack}')
            result = self.func(instance, *args, **kwargs)
            instance._current_stack.pop()
            logger.debug(f'[GraphNode] {"...."*len(instance._current_stack)}exitied stack for {self.func} | stack: {instance._current_stack}')

            # Cache result
            logger.debug(f'[GraphNode] adding {self.func}: {result} in cache')
            instance._cache[self.name] = result
            return result

        # Attach .set() if settable
        if self.settable:
            def setter(value):
                instance._cache[self.name] = value
                instance.invalidate(self.name)
                logger.debug(f'[GraphNode] {self.func} invalidated')
            caller.set = setter

        return caller


def graph_node(settable=False):
    """ graph_node decorator
        input:
        ------
        settable: bool, if True, the node can be set with syntax: node.attr(value)
    """
    def decorator(func): return GraphNode(func, settable=settable)
    return decorator

class Graph:
    def __init__(self):
        logger.debug('[Graph] __init__ start')
        self._cache = {}
        self._dependencies = {}   # node -> set of dependencies
        self._dependents = {}     # node -> set of dependents
        self._current_stack = []  # for dependency discovery

        # Scan class attributes without triggering descriptors
        for attr, value in vars(self.__class__).items():
            if isinstance(value, GraphNode):
                self._dependencies[attr] = set()
                self._dependents[attr] = set()

        logger.debug('[Graph] __init__ end')

    def invalidate(self, node):
        """Invalidate node and all downstream dependents."""
        if node in self._cache:
            del self._cache[node]
        for dep in self._dependents.get(node, []):
            self.invalidate(dep)


class MyGraph(Graph):
    def __init__(self):
        logger.debug('[MyGraph] __init__ start')
        super().__init__()
        logger.debug('[MyGraph] __init__ end')

    @graph_node(settable=True)
    def A(self):
        logger.debug('[MyGraph] graph_node A called')
        return 10

    @graph_node()
    def B(self):
        logger.debug('[MyGraph] graph_node B called')
        return self.A() ** 2

    @graph_node()
    def C(self):
        logger.debug('[MyGraph] graph_node C called')
        return self.B() + self.A()
    
    @graph_node()
    def D(self, value):
        logger.debug('[MyGraph] graph_node D called')
        return value*self.B()
    
    @graph_node()
    def E(self):
        logger.debug('[MyGraph] graph_node E called')
        return self.D( self.A() ) * 2
    
    @graph_node()
    def F(self):
        logger.debug('[MyGraph] graph_node F called')
        if self.A() > 5:
            return self.E()*1.5
        else:
            return 14
