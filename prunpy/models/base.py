from prunpy.models.building import Building
from prunpy.models.population import Population
from prunpy.models.planet import Planet
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

class RealBase(Base):
    def __init__(self, planet_natural_id, username):

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

        base_production = fio.request('GET', f'/production/{username}/{planet_natural_id}')
        #print(json.dumps(base_production, indent=4))
        for rawbuilding in self.rawsite.get('Buildings', []):
            ticker = rawbuilding.get('BuildingTicker')
            if ticker:
                self.buildings.append(Building(ticker, self.planet))

        self.username = username