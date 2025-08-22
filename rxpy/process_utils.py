import multiprocessing as mp
import cloudpickle
from rx.subject import Subject
from logging_utils import logger


class SubprocessManager:
    def __init__(self, name=''):
        self.name = name + str(id(self))
        self.procs = []
        self.queues = []

    def __repr__(self):
        return self.name

    def get_worker(self):
        logger.info('creating worker')
        in_q, out_q = mp.Queue(), mp.Queue()
        p = mp.Process(target=self.worker_loop, args=(in_q, out_q))
        p.start()
        self.procs.append(p)
        self.queues.append((in_q, out_q))
        logger.info(f'process: {p.pid} and queues: {[in_q, out_q]} created')
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
                logger.info('running worker loop')
                result = func(data)
                out_q.put(result)
            except Exception as e:
                out_q.put(e)

    def shutdown(self):
        for in_q, _ in self.queues:
            in_q.put(None)
        for p in self.procs:
            p.join()


class execute:

    _managers = []

    def __init__(self):
        self.manager = None
        self._isSubProc = False

    def execute(self, location, func, input, scheduler=None):
        if location == "main":
            # Run locally, just like normal Rx
            out_stream = Subject()

            def wrapper(x):
                result = func(x)
                if result is not None:
                    out_stream.on_next(result)
            input.subscribe(wrapper, scheduler=scheduler)
            return out_stream

        elif location == "subprocess":
            # Run remotely
            self.manager = SubprocessManager()
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

    def __call__(self, location, func, input, scheduler=None):
        return self.execute(location, func, input, scheduler=scheduler)

    @classmethod
    def shutdown(cls):
        for manager in cls._managers:
            logger.info(f'Shutting down manager: {manager}')
            manager.shutdown()
