from prunpy.models.building import Building
from prunpy.models.population import Population
from prunpy.models.planet import Planet
from prunpy.utils.resource_list import ResourceList

from prunpy.constants import DEMOGRAPHICS

class Base:
    # Constructor. Either:
    # - a planet_natural_id and building counts
    # - a site object from FIO /sites/{username}
    def __init__(self, planet_natural_id, building_counts, rawdata=None):

        if rawdata:
            if planet_natural_id and planet_natural_id != rawdata.get('PlanetNaturalId'):
                print("Base constructor called with conflicting planet_natural_id")
            else:
                self.planet = Planet(planet_id=self.rawdata.get('PlanetId'))
                # Extract and count buildings by their ticker
                self.building_counts = {}
                for building in rawdata.get('Buildings', []):
                    ticker = building.get('BuildingTicker')
                    if ticker:
                        if ticker in self.building_counts:
                            self.building_counts[ticker] += 1
                        else:
                            self.building_counts[ticker] = 1
                self.exists = True
        else: # If there is no rawdata (and in most cases can't be)
            self.planet = Planet(natural_id=planet_natural_id)
            self.building_counts = building_counts
            self.exists = False

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
            upkeep += building.population_needs.get_upkeep()
        return upkeep

    def get_area(self):
        return sum([building.area for building in self.buildings])

    @property
    def population_demand(self):
        population = self.buildings[0].population_needs
        for building in self.buildings[1:]:
            for key in DEMOGRAPHICS:
                population[key] += building.population_needs[key]
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
