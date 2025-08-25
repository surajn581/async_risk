import multiprocessing as mp
import cloudpickle
from rx.subject import Subject
from logging_utils import logger
from enum import StrEnum


class Location(StrEnum):
    SUBPROC = "subprocess"
    MAIN = "main"


class SubprocessManager:
    def __init__(self, name=''):
        self.name = f'{name}:{str(id(self))}' if name else str(id(self))
        self.procs = []
        self.queues = []

    def __repr__(self):
        return self.name

    def get_worker(self):
        logger.info(f'[{self.__class__.__name__}] creating subprocess')
        in_q, out_q = mp.Queue(), mp.Queue()
        p = mp.Process(target=self.worker_loop, args=(in_q, out_q))
        p.start()
        self.procs.append(p)
        self.queues.append((in_q, out_q))
        logger.info(
            f'[{self.__class__.__name__}] subprocess: {p.pid} and queues: {[in_q, out_q]} created')
        return in_q, out_q

    @staticmethod
    def worker_loop(in_q, out_q):
        while True:
            msg = in_q.get()
            if msg is None:
                break
            func_bytes, data = msg
            func = cloudpickle.loads(func_bytes)
            try:
                result = func(data)
                out_q.put(result)
            except Exception as e:
                out_q.put(e)

    def shutdown(self):
        for in_q, _ in self.queues:
            in_q.put(None)
        for p in self.procs:
            logger.info(
                f'[{self.__class__.__name__}] Closing process: {p.pid}')
            p.join()


class Execute:

    _managers = []

    def __init__(self):
        self.manager = None
        self._isSubProc = False

    def execute(self, location: Location, func, input: Subject, scheduler=None):
        if location == Location.MAIN:
            # Run locally, just like normal Rx
            out_stream = Subject()

            def wrapper(x):
                result = func(x)
                if result is not None:
                    out_stream.on_next(result)
            input.subscribe(wrapper, scheduler=scheduler)
            return out_stream

        elif location == Location.SUBPROC:
            # Run remotely
            self.manager = SubprocessManager(func.__name__)
            self._managers.append(self.manager)
            in_q, out_q = self.manager.get_worker()
            func_bytes = cloudpickle.dumps(func)
            out_stream = Subject()

            def forwarder(x):
                in_q.put((func_bytes, x))
                result = out_q.get()
                if isinstance(result, Exception):
                    logger.info("[Subprocess error] {}".format(result))
                else:
                    out_stream.on_next(result)

            input.subscribe(forwarder, scheduler=scheduler)
            return out_stream

    @classmethod
    def run(cls, location, func, input, scheduler=None):
        return cls().execute(location, func, input, scheduler=scheduler)

    @classmethod
    def shutdown(cls):
        for manager in cls._managers:
            logger.info(f'Shutting down manager: {manager}')
            manager.shutdown()


execute = Execute.run
