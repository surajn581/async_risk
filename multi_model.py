import asyncio
from collections import defaultdict

class MultiModel:
    def __init__(self, models):
        self.models = models

    async def compute(self, instruments, market_data, changed_keys):
        model_to_insts = defaultdict(list)

        for inst in instruments:
            inst_deps = set(inst.depends_on())
            for model in self.models:
                model_deps = set(model.required_market_data())
                if inst_deps & model_deps & changed_keys:
                    model_to_insts[model].append(inst)

        tasks = [
            asyncio.create_task(model.compute(insts, market_data))
            for model, insts in model_to_insts.items()
        ]

        final_result = {}
        for task in tasks:
            model_result = await task
            for inst_id, result in model_result.items():
                final_result.setdefault(inst_id, {}).update(result)

        return final_result