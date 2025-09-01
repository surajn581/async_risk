import asyncio
import multiprocessing as mp
import cloudpickle
from rx.subject import Subject
from logging_utils import logger
from enum import StrEnum
import traceback
import sys


class Location(StrEnum):
    SUBPROC = "subprocess"
    MAIN = "main"


class SubprocessManager:
    def __init__(self, name=''):
        self.name = f'{name}:{str(id(self))}' if name else str(id(self))
        self.procs = []
        self.pipes = []

    def __repr__(self):
        return self.name

    def get_worker(self):
        logger.info(f'[{self.__class__.__name__}] creating subprocess')
        parent_conn, child_conn = mp.Pipe(duplex=True)
        p = mp.Process(target=self.worker_loop, args=(child_conn,))
        p.start()
        child_conn.close()
        self.procs.append(p)
        self.pipes.append(parent_conn)
        logger.info(
            f'[{self.__class__.__name__}] subprocess: {p.pid} and pipe created')
        return parent_conn

    @staticmethod
    def worker_loop(conn):
        asyncio.run(SubprocessManager.worker_async_loop(conn))

    @staticmethod
    async def worker_async_loop(conn):
        while True:
            try:
                # recv is blocking, run in thread
                msg = await asyncio.to_thread(conn.recv)
            except EOFError:
                break

            if msg is None:
                break

            func_bytes, data = msg
            try:
                func = cloudpickle.loads(func_bytes)
                if asyncio.iscoroutinefunction(func):
                    result = await func(data)
                else:
                    # run sync func in executor to avoid blocking
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, func, data)
                await asyncio.to_thread(conn.send, result)
            except Exception as e:
                # Send exception back
                logger.exception(f'Worker Error: {e} {traceback.format_exc()}')
                await asyncio.to_thread(conn.send, e)

        conn.close()

    def shutdown(self):
        for conn in self.pipes:
            try:
                conn.send(None)  # signal to stop worker
                conn.close()
            except Exception:
                pass

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
            # Run remotely with async Pipe
            self.manager = SubprocessManager(func.__name__)
            self._managers.append(self.manager)
            conn = self.manager.get_worker()
            func_bytes = cloudpickle.dumps(func)
            out_stream = Subject()

            async def forwarder_async(x):
                conn.send((func_bytes, x))
                # await result without blocking using to_thread
                result = await asyncio.to_thread(conn.recv)
                if isinstance(result, Exception):
                    logger.exception(
                        f"[Subprocess error] {result}")
                else:
                    out_stream.on_next(result)

            # Wrap the async forwarder in a sync function for Rx subscription
            def forwarder(x):
                asyncio.create_task(forwarder_async(x))

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
