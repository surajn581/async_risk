from lib.logging import logger
from graph import Graph, graph_node

class MyGraph(Graph):
    def __init__(self):
        logger.debug('[MyGraph] __init__ start')
        super().__init__()
        self.constant = 4
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
            return self.D(self.constant)
