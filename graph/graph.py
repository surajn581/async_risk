import ast
import inspect
from collections import deque
from lib.logging import logger, SuppressLogging, DEBUG

class GraphNode:
    """Graph Node"""
    def __init__(self, func, settable=False):
        self.func = func
        self.name = func.__name__
        self.settable = settable

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # Return a callable wrapper so g.A() still works
        def caller(*args, **kwargs):

            logger.debug(f'[GraphNode] looking for {self.func} in cache')
            if self.name in instance._cache:
                logger.debug(f'[GraphNode] found {self.func} in cache')
                return instance._cache[self.name]

            result = self.func(instance, *args, **kwargs)

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
        self._dependencies = self.getDependencyGraph()          # node -> set of dependencies
        self._dependents = self.getReverseDependencyGraph(self._dependencies)     # node -> set of dependents
        logger.debug('[Graph] __init__ end')

    def invalidate(self, node):
        """Invalidate node and all downstream dependents."""
        if node in self._cache:
            del self._cache[node]
        for dep in self._dependents.get(node, []):
            self.invalidate(dep)

    @staticmethod
    def _expandDependencyGraph(graph):
        # we do set(v).intersection(graph) since some times v can have instance attrs that are not graph nodes
        # eg: graph_node(D): self.constant * graph_node(A)
        # in this case v for D will have {A, constant} and, since we only want to track graph_nodes and the
        # ast walk only puts graph_nodes in the graph's key, performing v.interset(graph.keys) does the trick.
        # TODO find a way to handle it while doing the ast walk
        graph = {k: set(v).intersection(graph) for k, v in graph.items()}        
        nodesToExpand = deque(graph.keys())

        while nodesToExpand:
            node = nodesToExpand.popleft()
            current_deps = graph[node].copy()

            for dep in current_deps:
                new_items = graph[dep].difference(current_deps)
                if not new_items:
                    continue
                graph[node].update(new_items)
                nodesToExpand.append(node)
        
        return graph

    @staticmethod
    def _getDependencyGraphFromTree(tree):
        dependency_graph = {}
        for node in ast.walk(tree):
            if not hasattr(node, 'decorator_list'):
                continue
            if not any(d.func.id == graph_node.__name__ for d in node.decorator_list):
                continue
            dependency_graph[node.name] = set()
            for inner_node in node.body:
                for _n in ast.walk(inner_node):
                    if isinstance(_n, ast.Attribute) and _n.value.id=='self':
                        dependency_graph[node.name].add(_n.attr)
        return dependency_graph

    @classmethod
    def getDependencyGraph(cls):
        src = inspect.getsource(cls)
        tree = ast.parse(src)
        graph = cls._getDependencyGraphFromTree(tree)
        return cls._expandDependencyGraph(graph)
    
    @staticmethod
    def getReverseDependencyGraph(graph):
        reverseDependency = {}
        for fn_name, dependencies in graph.items():
            for dependancy in dependencies:
                if dependancy not in reverseDependency:
                    reverseDependency[dependancy] = set()
                reverseDependency[dependancy].add(fn_name)
        return reverseDependency
    
    def show(self):
        from visualize import visualizeGraphWithLevels
        with SuppressLogging(DEBUG):
            visualizeGraphWithLevels(self._dependencies)

