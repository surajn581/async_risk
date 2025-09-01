import os
import shutil
import asyncio
from logging_utils import logger
from rx.subject import Subject
from rx.scheduler.eventloop import AsyncIOScheduler
from process_utils import execute, Location, Execute
from event_listner import DirectoryListner


def calc_predict(price_stream, move_stream, prediction_stream):
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

    price_stream.subscribe(on_price)
    move_stream.subscribe(on_move)


def post_process(predicts):
    logger.info('[post_process] received predicts: {}'.format(predicts))
    logger.info('[post_process] scaling by 2')
    return [p*2 for p in predicts]


def downstream_process(predicts):
    logger.info('[Downstream] received: {}'.format(predicts))


def stop_circut(trigger):
    logger.info(f'Stop handler triggered with: {trigger}')
    Execute.shutdown()
    raise asyncio.exceptions.CancelledError('Stopping Circuit')


async def main():
    loop = asyncio.get_event_loop()
    scheduler = AsyncIOScheduler(loop)

    price_stream = Subject()
    market_move_stream = Subject()
    prediction_stream = Subject()
    cancel_trigger = Subject()

    calc_predict(price_stream, market_move_stream, prediction_stream)

    processed = execute(Location.SUBPROC, post_process,
                        prediction_stream, scheduler)

    execute(Location.SUBPROC, downstream_process, processed, scheduler)

    def dirPath(name): return os.path.join(
        'C:/Users/suraj/projects/async_risk/rxpy/', name)

    price_task = DirectoryListner.task(
        dirPath('prices'), price_stream, lambda s: float(s))

    move_task = DirectoryListner.task(dirPath('market_moves'),
                                      market_move_stream, lambda s: float(s))

    cancel_task = DirectoryListner.task(dirPath('cancel_trigger'),
                                        cancel_trigger, lambda s: s)

    cancel_trigger.subscribe(stop_circut)

    await asyncio.gather(price_task, move_task, cancel_task)

if __name__ == "__main__":
    asyncio.run(main())
