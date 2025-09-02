import asyncio
import multiprocessing as mp
import cloudpickle
from rx.subject import Subject
from logging_utils import logger
from enum import StrEnum, Enum
import traceback
import sys


class Location(StrEnum):
    SUBPROC = "subprocess"
    MAIN = "main"


class Phase(Enum):
    INIT = 1
    TICK = 2


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
        func = None
        in_stream = Subject()
        out_stream = None

        while True:
            try:
                # recv is blocking, run in thread
                msg = await asyncio.to_thread(conn.recv)
            except EOFError:
                break

            if msg is None:
                break

            phase, payload = msg

            if phase == Phase.INIT:
                func = cloudpickle.loads(payload)
                out_stream = func(in_stream)

                # Forward outputs back to parent
                def forward(x):
                    conn.send(x)
                out_stream.subscribe(forward)

            elif phase == Phase.TICK:
                in_stream.on_next(payload)

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

    def execute(self, location: Location, func, input: Subject, scheduler=None):

        if location == Location.MAIN:
            return func(input)

        if location == Location.SUBPROC:
            # Subprocess execution
            self.manager = SubprocessManager(func.__name__)
            self._managers.append(self.manager)
            conn = self.manager.get_worker()

            # Create local in/out streams
            out_stream = Subject()

            # Send function definition once
            func_bytes = cloudpickle.dumps(func)
            conn.send((Phase.INIT, func_bytes))

            # Forward inputs to subprocess
            def on_input(x):
                conn.send((Phase.TICK, x))
            input.subscribe(on_input, scheduler=scheduler)

            # Listen for outputs
            async def reader():
                while True:
                    msg = await asyncio.to_thread(conn.recv)
                    if msg is None:
                        break
                    out_stream.on_next(msg)

            asyncio.create_task(reader())
            return out_stream

        else:
            raise ValueError(f'Unknown value for location: {location}')

    @classmethod
    def run(cls, location, func, input, scheduler=None):
        return cls().execute(location, func, input, scheduler=scheduler)

    @classmethod
    def shutdown(cls):
        for manager in cls._managers:
            logger.info(f'Shutting down manager: {manager}')
            manager.shutdown()


execute = Execute.run
