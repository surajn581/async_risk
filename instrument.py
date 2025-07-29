from env import Env

class Instrument:
    def __init__(self, id: str, instrument_type: str):
        self.id = id
        self.type = instrument_type

    def depends_on(self):
        if self.type == "bond":
            return ["DiscountCurve"]
        elif self.type == "futures":
            return ["ForwardCurve"]
        else:
            return []

    def Price(self):
        if self.type == "bond":
            dsc = Env.get("DiscountCurve")
            return 100.0 if dsc == "USD_1" else 95.0
        elif self.type == "futures":
            fwd = Env.get("ForwardCurve")
            return 200.0 if fwd == "FW_1" else 190.0
        else:
            return 0.0