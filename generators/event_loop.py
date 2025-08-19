from coroutine import Coroutine
class EventLoop:
    def __init__(self, tasks):
        self.tasks = {t: None for t in tasks}
        self.pending = tasks

    def run(self):
        while self.pending:
            for task in self.pending:
                try:
                    self.tasks[task] = next(task)
                except StopIteration as si:
                    if len(si.args):
                        self.tasks[task] = si.args[0]
                    self.pending.remove(task)