from abc import ABC, abstractmethod
from env import Env

class RiskModel(ABC):
    @abstractmethod
    def required_market_data(self):
        pass

    @abstractmethod
    async def compute(self, instruments, market_data):
        pass

class DiscountCurveModel(RiskModel):
    def required_market_data(self):
        return ["DiscountCurve"]

    async def compute(self, instruments, market_data):
        results = {}
        for inst in instruments:
            with Env(DiscountCurve=market_data["DiscountCurve"]):
                price = inst.Price()
                results[inst.id] = {"price": price}
        return results

class ForwardCurveModel(RiskModel):
    def required_market_data(self):
        return ["ForwardCurve"]

    async def compute(self, instruments, market_data):
        results = {}
        for inst in instruments:
            with Env(ForwardCurve=market_data["ForwardCurve"]):
                price = inst.Price()
                results[inst.id] = {"price": price}
        return results