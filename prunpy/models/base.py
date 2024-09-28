from prunpy.models.building import Building
from prunpy.models.population import Population
from prunpy.models.planet import Planet
from prunpy.models.recipe import Recipe
from prunpy.utils.resource_list import ResourceList
from prunpy.api import fio
from prunpy.constants import DEMOGRAPHICS

import json

class Base:
    # Constructor. Either:
    # - a planet_natural_id and building counts
    # - a site object from FIO /sites/{username}
    def __init__(self, planet_natural_id, building_counts):

        self.planet = Planet(natural_id=planet_natural_id)
        self.building_counts = building_counts

        self.building_counts['CM'] = 1 # Add core module

        self.update_buildings()

    # Update the list of buildings based on the building counts
    def update_buildings(self):
        self.buildings = []
        for ticker, count in self.building_counts.items():
            for _ in range(count):
                self.buildings.append(Building(ticker, self.planet))

    def add_building(self, ticker):
        self.building_counts[ticker] += 1
        self.buildings.append(Building(ticker, self.planet))
        self.update_buildings()

    def remove_building(self, ticker):
        if ticker not in self.building_counts:
            print(f"Tried to remove {ticker} from {self} but it is not there!")
        self.building_counts[ticker] -= 1

        self.update_buildings()

    def get_construction_materials(self):
        materials = ResourceList()
        for building in self.buildings:
            materials += building.construction_materials
        return materials

    def get_daily_upkeep(self):
        upkeep = self.get_daily_building_maintenance()
        upkeep += self.get_daily_population_maintenance()
        return upkeep

    def get_daily_building_maintenance(self):
        upkeep = ResourceList()
        for building in self.buildings:
            upkeep += building.get_daily_maintenance()
        return materials

    def get_daily_population_maintenance(self):
        upkeep = ResourceList()
        for building in self.buildings:
            upkeep += building.population_demand.get_upkeep()
        return upkeep

    def get_area(self):
        return sum([building.area for building in self.buildings])

    @property
    def population_demand(self):
        population = Population({})
        for building in self.buildings:
            population += building.population_demand
        return Population(population)

    @property
    def population_upkeep(self):
        upkeep = ResourceList()
        for building in self.buildings:
            upkeep += building.population_upkeep
        return upkeep

    def optimize_housing(mode="cost"): # cost or space
        pass

    def get_available_recipes(self):
        self.available_recipes = [building.recipes for building in self.buildings]
        # Remove duplictes (same BuildingRecipeId)
        self.available_recipes = list(set([item for sublist in self.available_recipes for item in sublist]))

    def get_burn_rate(self):
        raw_burn_rate = loader.raw_burn_rate

    def __str__(self):
        buildings_str = ', '.join([f"{count} {name}" for name, count in self.building_counts.items()])
        return f"[Base ({self.planet.name}):\n  Buildings: {buildings_str}]"

class RealBase(Base):
    def __init__(self, planet_natural_id, username):
        self.username = username
        sites = fio.request('GET', f'/sites/{username}')

        # Find site whose PlanetIdentifier matches planet_natural_id
        for site in sites:
            if site.get('PlanetIdentifier') == planet_natural_id:
                self.rawsite = site
                break
        else:
            raise ValueError(f"Could not find site owned by {username} on planet {planet_natural_id}")

        self.building_counts = {}
        for rawbuilding in self.rawsite.get('Buildings', []):
            ticker = rawbuilding.get('BuildingTicker')
            if ticker:
                if ticker in self.building_counts:
                    self.building_counts[ticker] += 1
                else:
                    self.building_counts[ticker] = 1

        super().__init__(
            planet_natural_id=planet_natural_id,
            building_counts=self.building_counts
        )
        self.buildings = [] # Recreate with RealBuildings

        #print(json.dumps(self.rawsite['Buildings'], indent=4))

        self.raw_production = fio.request('GET', f'/production/{username}/{planet_natural_id}')
        #print(json.dumps(self.raw_production, indent=4))





        for rawbuilding in self.rawsite.get('Buildings', []):
            ticker = rawbuilding.get('BuildingTicker')
            if ticker:
                self.buildings.append(Building(ticker, self.planet))

    def get_storage(self):
        rawstorage = fio.request('GET', f'/storage/{self.username}/{self.planet.natural_id}')
        return ResourceList(rawstorage['StorageItems'])

    @property
    def storage(self):
        return self.get_storage()

    def get_daily_burn(self):
        # Gather all recurring orders that haven't started yet
        daily_burn = ResourceList({})
        for line in self.raw_production:
            recurring_orders = []
            capacity = line.get('Capacity')
            for order in line.get('Orders', []):
                if order.get('CompletedPercentage') == None: # Not-started only
                    inputs = ResourceList(order.get('Inputs'))
                    outputs = ResourceList(order.get('Outputs'))
                    #recipe = loader.get_recipe(order.get('BuildingRecipeId'))

                    recipe = Recipe({
                        'building': order.get('StandardRecipeName')[0:3].rstrip(':'),
                        'duration': order.get('DurationMs')/1000/60/60,
                        'inputs': inputs,
                        'outputs': outputs
                    })

                    order = {
                        'recipe': recipe,
                        'capacity': capacity
                    }

                    #print(f"Inputs: {inputs}, Outputs: {outputs}, Duration: {order['recipe'].duration}, Capacity: {capacity}")

                    recurring_orders.append(order)
            

            
            total_inputs = ResourceList({})
            total_outputs = ResourceList({})
            total_duration = 0
            for order in recurring_orders:
                total_inputs += order['recipe'].inputs
                total_outputs += order['recipe'].outputs
                total_duration += order['recipe'].duration 
            total_io = total_outputs - total_inputs
            total_io *= order['capacity']

            daily_cycles = 24/total_duration
            daily_burn += total_io * daily_cycles
            #print(f"Total IO: {total_io}, Duration: {total_duration}, Cycles: {daily_cycles}, Burn: {daily_burn}")

        return daily_burn

    @property
    def burn(self):
        return self.get_daily_burn()