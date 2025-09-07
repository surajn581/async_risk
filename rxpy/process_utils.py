import asyncio
import multiprocessing as mp
import cloudpickle
from rx.subject import Subject
from logging_utils import logger
from enum import StrEnum, Enum
import traceback
import sys
from functools import partial


class Location(StrEnum):
    SUBPROC = "subprocess"


class Phase(Enum):
    INIT = 1
    TICK = 2


DEBUG = False


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
        out_stream = None
        input_streams = {}

        while True:
            try:
                # recv is blocking, run in thread
                msg = await asyncio.to_thread(conn.recv)
            except EOFError as eof:
                logger.exception(f'[worker_async_loop] {eof}')

            if msg is None:
                break

            phase, payload = msg

            if phase == Phase.INIT:
                func = cloudpickle.loads(payload)
                # Forward inputs to subprocess
                input_streams = {
                    key: Subject() for key, _ in func.__annotations__.items()
                    if key != 'return'}
                out_stream = func(**input_streams)

                # Forward outputs back to parent
                def forward(x):
                    conn.send(x)
                out_stream.subscribe(forward)

            elif phase == Phase.TICK:
                stream_name, tick_value = payload
                input_streams[stream_name].on_next(tick_value)

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

    def execute(self, location: Location, func, input_streams: dict[str:Subject], scheduler=None):

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

            def on_input(stream_name, x):
                conn.send((Phase.TICK, (stream_name, x)))

            # Forward inputs to subprocess
            for stream_name, stream in input_streams.items():
                stream.subscribe(
                    partial(on_input, stream_name), scheduler=scheduler)

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
    def run(cls, location, func, scheduler=None, **inputs):
        return cls().execute(location, func, inputs, scheduler=scheduler)

    @classmethod
    def shutdown(cls):
        for manager in cls._managers:
            logger.info(f'Shutting down manager: {manager}')
            manager.shutdown()


execute = Execute.run
