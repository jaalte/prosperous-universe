from prunpy.utils.resource_list import ResourceList

class Recipe:
    def __init__(self, rawdata):
        # Importing from buildings.json format
        if 'BuildingRecipeId' in rawdata:
            self.building = rawdata.get('StandardRecipeName')[0:3].rstrip(':')
            self.name = rawdata.get('BuildingRecipeId')
            self.duration = rawdata.get('DurationMs')/1000/60/60

            self.inputs = ResourceList(rawdata.get('Inputs'))
            self.outputs = ResourceList(rawdata.get('Outputs'))

        # Manually specified format
        else:
            self.building = rawdata.get('building')
            self.name = rawdata.get('name')
            self.duration = rawdata.get('duration')

            self.inputs = rawdata.get('inputs')
            if not isinstance(self.inputs, ResourceList):
                self.inputs = ResourceList(self.inputs)
            self.outputs = rawdata.get('outputs')
            if not isinstance(self.outputs, ResourceList):
                self.outputs = ResourceList(self.outputs)

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

    def __str__(self):
        return f"[{self.building:<3} Recipe: {self.inputs} => {self.outputs} in {self.duration}h]"
