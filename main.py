import asyncio
from instrument import Instrument
from risk_model import DiscountCurveModel
from multi_model import MultiModel

async def main():
    instruments = [
        Instrument("T1", "bond"),
        Instrument("T2", "bond"),
    ]

    market_data = {
        "DiscountCurve": "USD_1"
    }

    changed_keys = {"DiscountCurve"}

    multi_model = MultiModel([
        DiscountCurveModel()
    ])

    results = await multi_model.compute(instruments, market_data, changed_keys)
    for k, v in results.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())