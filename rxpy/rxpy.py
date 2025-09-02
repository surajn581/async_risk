import asyncio
from rx import create
from rx import operators as ops
from rx.subject import Subject
from rx.scheduler.eventloop import AsyncIOScheduler
from logging_utils import logger
from event_listner import DirectoryListner, os
from process_utils import execute, Execute, Location


def calc_predict(price_stream: Subject, move_stream: Subject) -> Subject:
    """Predicts based on prices and market moves"""
    output_stream = Subject()
    s_price, s_price_prev, s_move = [], [], []

    def on_price(price):
        logger.info(f"[calc_predict] Price ticked: {price}")
        s_price.append(price)
        s_price_prev.append(price)
        if s_move:
            logger.info(f"[calc_predict] Re-ticking market move {s_move[-1]}")
            move_stream.on_next(s_move[-1])
            s_move.clear()

    def on_move(move):
        logger.info(f"[calc_predict] Market move ticked: {move}")
        s_move.append(move)
        if (s_price or s_price_prev):
            if not s_price:
                logger.info(
                    "[calc_predict] Processing previous prices with new market move")
            prediction = [p * move for p in (s_price or s_price_prev)]
            output_stream.on_next(prediction)
            s_price.clear()
        else:
            logger.info("[calc_predict] No new prices to process")

    price_stream.subscribe(on_price)
    move_stream.subscribe(on_move)
    return output_stream


def post_process(input_stream: Subject) -> Subject:
    """Scales predictions by 2"""
    output_stream = Subject()

    def on_input(inputs: list[float]):
        logger.info(f"[post_process] received inputs: {inputs}")
        scaled = [p * 2 for p in inputs]
        logger.info("[post_process] scaling by 2")
        output_stream.on_next(scaled)

    input_stream.subscribe(on_input)
    return output_stream


def downstream_process(input_stream: Subject) -> Subject:
    """Final downstream handler"""
    output_stream = Subject()

    def on_input(inputs: list[float]):
        logger.info(f"[downstream_process] received: {inputs}")
        output_stream.on_next("Success")

    input_stream.subscribe(on_input)
    return output_stream


def stop_circuit(trigger: bool):
    logger.info(f"[stop_circuit] Stop handler triggered with: {trigger}")
    raise asyncio.CancelledError("Stopping Circuit")


def main_circuit(price_stream: Subject, market_move_stream: Subject) -> Subject:
    calc_predict_out = calc_predict(price_stream, market_move_stream)
    post_process_out = execute(
        Location.SUBPROC,
        post_process,
        calc_predict_out)
    downstream_out = downstream_process(post_process_out)

    # Subscribe to final output
    def on_status(status):
        logger.info(f"[main_circuit] downstream sent status: {status}")

    downstream_out.subscribe(on_status)
    return downstream_out


async def main():
    price_stream = Subject()
    market_move_stream = Subject()
    cancel_trigger = Subject()

    main_circuit(price_stream, market_move_stream)
    cancel_trigger.subscribe(stop_circuit)

    def dirPath(name): return os.path.join(
        'C:/Users/suraj/projects/async_risk/rxpy/', name)

    price_task = DirectoryListner.task(
        dirPath('prices'), price_stream, lambda s: float(s))

    move_task = DirectoryListner.task(dirPath('market_moves'),
                                      market_move_stream, lambda s: float(s))

    cancel_task = DirectoryListner.task(dirPath('cancel_trigger'),
                                        cancel_trigger, lambda s: s)

    await asyncio.gather(price_task, move_task, cancel_task)


if __name__ == "__main__":
    asyncio.run(main())
