import os
import shutil
import asyncio
from logging_utils import logger


class DirectoryListner:
    @staticmethod
    async def watch_directory(dirPath, stream, parse_fn, poll_interval=0.1):
        """Polls a directory and pushes new events into the given stream."""

        if not os.path.exists(os.path.join(dirPath, 'done')):
            os.mkdir(os.path.join(dirPath, 'done'))

        if not os.path.exists(os.path.join(dirPath, 'error')):
            os.mkdir(os.path.join(dirPath, 'error'))

        def readfiles():
            fileNames = [path for path in os.listdir(
                dirPath) if path.endswith('.txt')]
            if fileNames:
                logger.info('Processing {} {}...'.format(
                    len(fileNames), dirPath.split('/')[-1]))

            for fileName in fileNames:
                filePath = os.path.join(dirPath, fileName)
                try:
                    with open(filePath, "r") as f:
                        data = f.read().strip()
                        if data:
                            event = parse_fn(data)
                            stream.on_next(event)
                    shutil.move(filePath, os.path.join(
                        dirPath, 'done', fileName))
                except Exception as ex:
                    logger.exception(ex)
                    shutil.move(filePath, os.path.join(
                        dirPath, 'error', fileName))
                except asyncio.exceptions.CancelledError as cancelled_error:
                    logger.exception(cancelled_error)
                    shutil.move(filePath, os.path.join(
                        dirPath, 'error', fileName))
                    raise cancelled_error

        while True:
            try:
                readfiles()
            except FileNotFoundError:
                pass
            await asyncio.sleep(poll_interval)

    @classmethod
    def task(cls, dirPath, stream, parse_fn, poll_interval=0.1):
        return asyncio.create_task(cls().watch_directory(dirPath, stream, parse_fn, poll_interval=poll_interval))
