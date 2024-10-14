from prunpy.utils.resource_list import ResourceList
from prunpy.data_loader import loader

class Recipe:
    def __init__(self, rawdata):
        if isinstance(rawdata, Recipe):
            self.building = rawdata.building
            self.raw_duration = rawdata.raw_duration
            self.inputs = rawdata.inputs.copy()
            self.outputs = rawdata.outputs.copy()
            self.multipliers = rawdata.multipliers.copy()
            self.id = rawdata.id

        # Importing from buildings.json format
        elif 'BuildingRecipeId' in rawdata:
            self.building = rawdata.get('StandardRecipeName')[0:3].rstrip(':')
            self.raw_duration = rawdata.get('DurationMs')/1000/60/60
            self.id = rawdata.get('StandardRecipeName')

            self.inputs = ResourceList(rawdata.get('Inputs'))
            self.outputs = ResourceList(rawdata.get('Outputs'))
            self.multipliers = {}


        # Manually specified format
        else:
            self.building = rawdata.get('building')
            self.raw_duration = rawdata.get('raw_duration', None)
            if self.raw_duration is None:
                self.raw_duration = rawdata.get('duration', None)
                if self.raw_duration is None:
                    raise Exception(f"Invalid recipe, no duration or raw_duration: {rawdata}")

            self.inputs = rawdata.get('inputs')
            if not isinstance(self.inputs, ResourceList):
                self.inputs = ResourceList(self.inputs)
            self.outputs = rawdata.get('outputs')
            if not isinstance(self.outputs, ResourceList):
                self.outputs = ResourceList(self.outputs)
            
            self.multipliers = rawdata.get('multipliers', {})


            self.id = f"{self.building}:"
            for ticker, count in self.inputs.resources.items():
                self.id += f"{count}x{ticker}-"
            self.id = self.id[:-1]+"=>"

            for ticker, count in self.outputs.resources.items():
                self.id += f"{count}x{ticker}-"
            self.id = self.id[:-1]
    
    @property
    def duration(self):
        return self.raw_duration / self.multiplier
    
    @property
    def multiplier(self):
        total_multiplier = 1
        for multiplier in self.multipliers.values():
            total_multiplier *= multiplier
        return total_multiplier

    def convert_to_daily(self):
        daily_cycles = 24 / self.raw_duration
        new_rawdata = {
            'building': self.building,
            'raw_duration': 24,
            'inputs': self.inputs * daily_cycles,
            'outputs': self.outputs * daily_cycles,
            'multipliers': self.multipliers,
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

    def __json__(self):
        return self.__str__()

    def __str__(self):
        if self.multiplier == 1:
            return f"{self.outputs} <= {self.inputs} in {self.raw_duration:.1f}h @{self.building:<3}"
        else:
            return f"{self.outputs} <= {self.inputs} in {self.duration:.1f}h (x{self.multiplier:.0%}) @{self.building:<3}"
