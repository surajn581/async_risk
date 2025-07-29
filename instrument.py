from env import Env

class Instrument:
    def __init__(self, id: str, instrument_type: str):
        self.id = id
        self.type = instrument_type

    def depends_on(self):
        return ["DiscountCurve"]

    def Price(self):
        dsc = Env.get("DiscountCurve")
        return 100.0 if dsc == "USD_1" else 95.0