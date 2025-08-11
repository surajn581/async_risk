from graphviz import Digraph
from collections import deque

def kahnToposortLevels(graph):
    inDegree = {node: 0 for node in graph}
    for deps in graph.values():
        for dep in deps:
            inDegree[dep] += 1

    queue = deque([node for node, deg in inDegree.items() if deg == 0])
    levels = []
    processedCount = 0
    
    while queue:
        levelSize = len(queue)
        currentLevel = []

        for _ in range(levelSize):
            node = queue.popleft()
            currentLevel.append(node)
            processedCount += 1

            for neighbor in graph[node]:
                inDegree[neighbor] -= 1
                if inDegree[neighbor] == 0:
                    queue.append(neighbor)

        levels.append(currentLevel)

    if processedCount != len(graph):
        raise ValueError("Graph has a cycle!")

    return levels


def visualizeGraphWithLevels(graph):
    levels = kahnToposortLevels(graph)[::-1]

    dot = Digraph(format="png")
    dot.attr(rankdir="LR")  # left-to-right layout (use TB for top-to-bottom)

    colors = ['lightblue', 'lightgreen', 'pink', 'yellow', 'green', 'red']

    # Create nodes in their levels
    for levelIdx, nodes in enumerate(levels):
        with dot.subgraph() as s:
            s.attr(rank='same')
            for node in nodes:
                s.node(node, shape="circle", style="filled", fillcolor=colors[levelIdx % len(colors)])

    # Add edges
    for node, deps in graph.items():
        for dep in deps:
            dot.edge(dep, node)

    dot.render("graph_output", view=True)
    return dot
