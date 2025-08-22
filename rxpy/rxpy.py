import os
import shutil
import asyncio
from lib.logging import logger
from rx.subject import Subject
from rx.scheduler.eventloop import AsyncIOScheduler

price_stream = Subject()
market_move_stream = Subject()
prediction_stream = Subject()


def create_circuit(price_stream, move_stream, sch):
    s_price_prev = []
    s_price = []
    s_move = []

    def on_price(price):
        logger.info("Price ticked: {}".format(price))
        s_price.append(price)
        s_price_prev.append(price)
        if s_move:
            logger.info('Re-ticking market move {}'.format(s_move[-1]))
            move_stream.on_next(s_move[-1])
            s_move.clear()

    def on_move(move):
        logger.info("Market move ticked: {}".format(move))
        s_move.append(move)
        if (s_price or s_price_prev):
            if not s_price:
                logger.info(
                    'Processing previously ticked prices with new market move')
            prediction = [p * move for p in (s_price or s_price_prev)]
            prediction_stream.on_next(prediction)
            s_price.clear()
        else:
            logger.info('No new prices to process')

    price_stream.subscribe(on_price, scheduler=sch)
    move_stream.subscribe(on_move, scheduler=sch)


def downstream(prediction_stream, sch):
    def on_predict(predicts):
        logger.info('Predicts: {}'.format(predicts))
    prediction_stream.subscribe(on_predict, scheduler=sch)


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
                shutil.move(filePath, os.path.join(dirPath, 'done', fileName))
            except Exception as ex:
                logger.exception(ex)
                shutil.move(filePath, os.path.join(dirPath, 'error', fileName))

    while True:
        try:
            readfiles()
        except FileNotFoundError:
            pass
        await asyncio.sleep(poll_interval)


async def main():
    loop = asyncio.get_event_loop()
    scheduler = AsyncIOScheduler(loop)

    create_circuit(price_stream, market_move_stream, scheduler)
    downstream(prediction_stream, scheduler)

    def dirPath(name): return os.path.join(
        'C:/Users/suraj/projects/async_risk/rxpy/', name)

    price_task = asyncio.create_task(
        watch_directory(dirPath('prices'), price_stream, lambda s: float(s))
    )
    move_task = asyncio.create_task(
        watch_directory(dirPath('market_moves'),
                        market_move_stream, lambda s: float(s))
    )

    await asyncio.gather(price_task, move_task)
