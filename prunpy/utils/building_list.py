import math
import re

from prunpy.models.planet import Planet
from prunpy.constants import DEFAULT_BUILDING_PLANET_NATURAL_ID as DEFAULT_PLANET

class BuildingList:
    def __init__(self, rawdata={}, planet=None):
        if isinstance(rawdata, BuildingList):
            buildings_dict = rawdata.buildings.copy()
        elif len(rawdata) == 0:
            buildings_dict = {}
        elif isinstance(rawdata, dict):
            buildings_dict = rawdata
        elif isinstance(rawdata, list):
            buildings_dict = {}
            for entry in rawdata:
                if isinstance(entry, str):
                    if entry in loader.all_building_tickers:
                        if entry not in buildings_dict:
                            buildings_dict[entry] = 0
                        buildings_dict[entry] += 1
                elif isinstance(entry, Building):
                    if entry.ticker not in buildings_dict:
                        buildings_dict[entry.ticker] = 0
                    buildings_dict[entry.ticker] += 1

        self.buildings = buildings_dict
        
        if planet is None:
            self.planet = Planet(natural_id=DEFAULT_PLANET)
        elif isinstance(planet, Planet):
            self.planet = planet
        elif isinstance(planet, str):
            self.planet = loader.get_planet(planet)
        else:
            raise Exception(f"Invalid planet type: {type(planet)}")


    # NOTE: Has to ceil amounts, since you can't actually have partial buildings
    def get_building_instances(self):
        from prunpy.data_loader import loader

        buildings = []
        for ticker, count in self.buildings.items():
            for _ in range(math.ceil(count)):
                buildings.append(loader.get_building(ticker, self.planet.natural_id))

        return buildings

    def get_single_building_instances(self):
        from prunpy.data_loader import loader
        buildings = []
        for ticker in self.buildings:
            buildings.append(loader.get_building(ticker, self.planet.natural_id))
        return buildings

    def get_total_cost(self, exchange=None):
        from prunpy.data_loader import loader 
        exchange = loader.get_exchange(exchange)

        total = 0
        for building in self.get_single_building_instances():
            cost = building.get_cost(exchange)
            total += cost * self.buildings[building.ticker]

        return total

    @property
    def cost(self):
        return self.get_total_cost()

    def get_total_materials(self, exchange=None):
        from prunpy.utils.resource_list import ResourceList
        from prunpy.data_loader import loader
        exchange = loader.get_exchange(exchange)

        total = ResourceList()
        for building in self.get_single_building_instances():
            total += building.construction_materials * self.buildings[building.ticker]

        return total

    @property
    def materials(self):
        return self.get_total_materials()

    def get_total_area(self, exchange=None):
        from prunpy.data_loader import loader
        exchange = loader.get_exchange(exchange)

        total = 0
        for building in self.get_single_building_instances():
            total += building.area * self.buildings[building.ticker]
        return total

    @property
    def area(self):
        return self.get_total_area()

    def get_population_needs(self, exchange=None):
        from prunpy.models.population import Population
        from prunpy.data_loader import loader
        exchange = loader.get_exchange(exchange)

        total_pop = Population({})
        for building in self.get_single_building_instances():
            total_pop += building.population_demand * self.buildings[building.ticker]

        return total_pop


    def get_housing_needs(self, priority='cost'):
        return self.get_population_needs().get_housing_needs(priority)

    def include_housing(self, priority='cost'):
        housing = self.get_housing_needs(priority)
        return self + housing
            

    def get_amount(self, ticker):
        return self.buildings.get(ticker, 0)

    def contains(self, ticker):
        return ticker in self.buildings.keys() and self.buildings[ticker] > 0

    def remove(self, ticker, quiet=False):
        if ticker in self.buildings:
            new_buildings = self.buildings.copy()
            del new_buildings[ticker]
            return BuildingList(new_buildings)
        elif not quiet:
            raise KeyError(f"Building '{ticker}' does not exist in the BuildingList.")

    @property
    def tickers(self):
        return list(self.buildings.keys())

    def invert(self):
        new_buildings = {ticker: -amount for ticker, amount in self.buildings.items()}
        return BuildingList(new_buildings)

    def prune_negatives(self):
        new_buildings = {ticker: amount for ticker, amount in self.buildings.items() if amount > 0}
        return BuildingList(new_buildings)

    def prune(self, threshold=0):
        new_resources = {ticker: amount for ticker, amount in self.buildings.items() if amount > threshold}
        return BuildingList(new_resources)

    def floor(self):
        new_buildings = {ticker: math.floor(amount) for ticker, amount in self.buildings.items()}
        return BuildingList(new_buildings)

    def ceil(self):
        new_buildings = {ticker: math.ceil(amount) for ticker, amount in self.buildings.items()}
        return BuildingList(new_buildings)

    def round(self):
        new_buildings = {ticker: round(amount) for ticker, amount in self.buildings.items()}
        return BuildingList(new_buildings)

    def add(self, ticker, amount=1):
        add_list = None
        if isinstance(ticker, dict):
            add_list = BuildingList(ticker)
        if isinstance(ticker, BuildingList):
            add_list = ticker
        if isinstance(ticker, str):
            add_list = BuildingList({ticker: amount})

        if add_list is not None:
            add_list = BuildingList(add_list)
            self += add_list
            return

        if ticker in self.buildings:
            self.buildings[ticker] += amount
        else:
            self.buildings[ticker] = amount

    def subtract(self, ticker, amount):
        sub_list = None
        if isinstance(ticker, dict):
            sub_list = BuildingList(ticker)
        if isinstance(ticker, BuildingList):
            sub_list = ticker
        if isinstance(ticker, str):
            sub_list = BuildingList({ticker: amount})

        if sub_list is not None:
            sub_list = BuildingList(add_list)
            self -= add_list
            return

        if ticker in self.buildings:
            self.buildings[ticker] += amount
        else:
            self.buildings[ticker] = amount

    def split(self):
        single_buildings = []
        for ticker, amount in self.buildings.items():
            single_buildings.append(BuildingList({ticker: amount}))
        return single_buildings

    def __add__(self, other):
        if not isinstance(other, BuildingList):
            return NotImplemented
        new_buildings = self.buildings.copy()
        for ticker, amount in other.buildings.items():
            if ticker in new_buildings:
                new_buildings[ticker] += amount
            else:
                new_buildings[ticker] = amount
        return BuildingList(new_buildings)

    def __sub__(self, other):
        if not isinstance(other, BuildingList):
            return NotImplemented
        new_buildings = self.buildings.copy()

        for ticker, amount in other.buildings.items():
            if ticker in new_buildings:
                new_buildings[ticker] -= amount
            else:
                new_buildings[ticker] = -amount

        return BuildingList(new_buildings)

    def __mul__(self, multiplier):
        if not isinstance(multiplier, int) and not isinstance(multiplier, float):
            return NotImplemented
        new_buildings = {ticker: amount * multiplier for ticker, amount in self.buildings.items()}
        return BuildingList(new_buildings)

    def __rmul__(self, multiplier):
        return self.__mul__(multiplier)

    def __truediv__(self, divisor):
        if not isinstance(divisor, int) and not isinstance(divisor, float):
            return NotImplemented
        if divisor == 0:
            raise ZeroDivisionError("Division by zero is not allowed.")
        new_buildings = {ticker: amount / divisor for ticker, amount in self.buildings.items()}
        return BuildingList(new_buildings)


    def __len__(self):
        return len(self.buildings)

    def __eq__(self, other):
        if isinstance(other, BuildingList):
            return self.buildings == other.buildings
        elif isinstance(other, dict):
            return self.buildings == other
        return NotImplemented


    def json(self):
        return json.dumps(self.buildings, indent=2)

    def copy(self):
        return BuildingList(self.buildings.copy())

    def __str__(self):
        def format_float(value, max_decimals=2):
            if value == round(value, 0):  # No decimals needed
                return f"{int(value)}"
            for decimals in range(1, max_decimals + 1):
                if value == round(value, decimals):
                    return f"{value:.{decimals}f}"
            return f"{value:.{max_decimals}f}"

        formatted_buildings = []
        for name, count in self.buildings.items():
            formatted_buildings.append(f"{format_float(count)} {name}")  # Display with 2 decimal places

        return ', '.join(formatted_buildings)
