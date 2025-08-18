from coroutine import coroutine
from event_loop import EventLoop
from lib.logging import logger
from lib.time import Timer

@coroutine
def sleep(duration):
    import time
    start = time.time()
    while True:
        now = time.time()
        if now >= start+duration:
            return f'slept for ~ {now-start} seconds'
        yield

def main():
    with Timer('Creating and running all the sleep tasks'):
        loop = EventLoop([sleep(i) for i in range(5)])
        loop.run()

    for task, return_value in loop.tasks.items():
        logger.info(f'task: {task} | returned: {return_value}')
