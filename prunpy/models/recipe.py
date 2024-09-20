from prunpy.utils.resource_list import ResourceList
from prunpy.data_loader import loader

class Recipe:
    def __init__(self, rawdata):
        if isinstance(rawdata, Recipe):
            self.building = rawdata.building.copy()
            self.duration = rawdata.duration.copy()
            self.inputs = rawdata.inputs.copy()
            self.outputs = rawdata.outputs.copy()

        # Importing from buildings.json format
        elif 'BuildingRecipeId' in rawdata:
            self.building = rawdata.get('StandardRecipeName')[0:3].rstrip(':')
            self.duration = rawdata.get('DurationMs')/1000/60/60

            self.inputs = ResourceList(rawdata.get('Inputs'))
            self.outputs = ResourceList(rawdata.get('Outputs'))

        # Manually specified format
        else:
            self.building = rawdata.get('building')
            self.duration = rawdata.get('duration')

            self.inputs = rawdata.get('inputs')
            if not isinstance(self.inputs, ResourceList):
                self.inputs = ResourceList(self.inputs)
            self.outputs = rawdata.get('outputs')
            if not isinstance(self.outputs, ResourceList):
                self.outputs = ResourceList(self.outputs)
         
    def convert_to_daily(self):
        mult = 24 / self.duration
        new_rawdata = {
            'building': self.building,
            'duration': 24,
            'inputs': self.inputs * mult,
            'outputs': self.outputs * mult,
        }
        return Recipe(new_rawdata)

    @property
    def daily(self):
        return self.convert_to_daily()

    @property
    def daily_burn(self):
        return self.convert_to_daily().inputs

    @property
    def delta(self):
        return self.outputs - self.inputs

    def apply_multiplier(self, multiplier):
        new_rawdata = {
            'building': self.building,
            'duration': self.duration / multiplier,
            'inputs': self.inputs,
            'outputs': self.outputs,
        }
        return Recipe(new_rawdata)

    def get_worker_upkeep_per_craft(self):
        building = loader.get_all_buildings()[self.building]
        daily_upkeep = building.population_demand.get_upkeep()
        return daily_upkeep * (self.duration / 24)

    def get_profit_per_craft(self, exchange='NC1'):
        input_cost = self.inputs.get_total_value(exchange, 'buy')
        output_cost = self.outputs.get_total_value(exchange, 'sell')
        return output_cost - input_cost

    def get_profit_ratio(self, exchange='NC1'):
        input_cost = self.inputs.get_total_value(exchange, 'buy')
        output_cost = self.outputs.get_total_value(exchange, 'sell')

        if input_cost == 0:
            if output_cost > 0:
                return float('inf')
            else:
                return 1

        return output_cost / input_cost

    def get_profit_per_hour(self, exchange):
        return self.get_profit_per_craft(exchange) / self.duration

    def get_profit_per_day(self, exchange):
        return self.get_profit_per_hour(exchange) * 24

    @property
    def throughput(self, output_ticker=None):
        if not output_ticker:
            output_ticker = self.outputs.tickers[0]

        return self.outputs.resources[output_ticker] / self.duration

    def copy(self):
        return Recipe(self)

    def __str__(self):
        return f"{self.outputs} <= {self.inputs} in {self.duration:.1f}h @{self.building:<3}"
