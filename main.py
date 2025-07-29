import asyncio
from instrument import Instrument
from risk_model import DiscountCurveModel, ForwardCurveModel
from multi_model import MultiModel

async def simulate_market_ticks():
    instruments = [
        Instrument("T1", "bond"),
        Instrument("T2", "bond"),
        Instrument("T3", "futures"),
        Instrument("T4", "futures"),
    ]

    multi_model = MultiModel([
        DiscountCurveModel(),
        ForwardCurveModel()
    ])

    tick_data = [
        {"DiscountCurve": "USD_1", "ForwardCurve": "FW_1"},
        {"DiscountCurve": "USD_2", "ForwardCurve": "FW_1"},
        {"DiscountCurve": "USD_2", "ForwardCurve": "FW_2"},
        {"DiscountCurve": "USD_1", "ForwardCurve": "FW_2"},
    ]

    prev_data = {}

    for i, market_data in enumerate(tick_data):
        print(f"\n--- Tick {i+1} ---")
        changed_keys = {
            k for k in market_data if market_data.get(k) != prev_data.get(k)
        }
        results = await multi_model.compute(instruments, market_data, changed_keys)
        for inst_id, val in results.items():
            print(f"{inst_id}: {val}")
        prev_data = market_data
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(simulate_market_ticks())
