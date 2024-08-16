import json
import math
from fio_api import fio

# Constants
EXTRACTORS = {
    'COL': {
        'ticker': 'COL',
        'type': 'GASEOUS',
        'cycle_time': 6, # hours per cycle
        'multiplier': 0.6,
    },
    'RIG': {
        'ticker': 'RIG',
        'type': 'LIQUID',
        'cycle_time': 4.8,
        'multiplier': 0.7,
    },
    'EXT': {
        'ticker': 'EXT',
        'type': 'MINERAL',
        'cycle_time': 12,
        'multiplier': 0.7,
    },
}

EXCHANGES = {
    'AI1': {
        'ticker': 'AI1',
        'systemId': 'ZV-307',
        'systemName': 'Antares',
    },
    'CI1': {
        'ticker': 'CI1',
        'systemId': 'UV-351',
        'systemName': 'Benten',
    },
    'CI2': {
        'ticker': 'CI2',
        'systemId': 'AM-783',
        'systemName': 'Arclight',
    },
    'IC1': {
        'ticker': 'IC1',
        'systemId': 'VH-331',
        'systemName': 'Hortus',
    },
    'NC1': {
        'ticker': 'NC1',
        'systemId': 'OT-580',
        'systemName': 'Moria',
    },
    'NC2': {
        'ticker': 'NC2',
        'systemId': 'TD-203',
        'systemName': 'Hubur',
    },
}

# Create a lookup dictionary for all materials by MaterialId
allmaterials = fio.request("GET", "/material/allmaterials", cache=60*60*24)
material_lookup = {material['MaterialId']: material for material in allmaterials}

# Create a lookup dictionary for all planets by PlanetId
allplanets = fio.request("GET", f"/planet/allplanets/full", cache=-1)
planet_lookup = {planet['PlanetId']: planet for planet in allplanets}

class Planet:
    def __init__(self, planet_id):
        #self.rawdata = fio.request("GET", f"/planet/{planet_id}")
        # Rather than doing a separate request, use the full planet list to get the raw data
        # Find the planet whose planetIdentifier matches the given planet_id
        self.rawdata = planet_lookup.get(planet_id)
        self.name = self.rawdata.get('PlanetName')
        self.id = self.rawdata.get('PlanetId')
        self.identifier = self.rawdata.get('PlanetIdentifier')
        self.resources = {}

        # Process the resources in rawdata
        for resource in self.rawdata.get('Resources', []):
            material_id = resource.get('MaterialId')
            material_data = material_lookup.get(material_id)

            if material_data:
                ticker = material_data['Ticker']
                resource_type = resource.get('ResourceType')
                factor = threshold_round(resource.get('Factor', 0))
                
                for building, info in EXTRACTORS.items():
                    if info["type"] == resource_type:
                        extractor_building = building
                        break
                
                daily_amount = factor * 100 * EXTRACTORS[extractor_building]["multiplier"]
                process_hours, process_amount = self.calculate_process_time_and_amount(extractor_building, daily_amount)

                self.resources[ticker] = {
                    'name': material_data['Name'],
                    'ticker': ticker,
                    'category': material_data['CategoryName'],
                    'weight': threshold_round(material_data['Weight']),
                    'volume': threshold_round(material_data['Volume']),
                    'type': resource_type,
                    'factor': factor,
                    'extractor_building': extractor_building,
                    'daily_amount': daily_amount,
                    'process_amount': process_amount,
                    'process_hours': process_hours
                }

    def calculate_process_time_and_amount(self, extractor_building, daily_amount):
        """Calculate the process hours and process amount based on the extractor type."""
        base_cycle_time = EXTRACTORS[extractor_building]["cycle_time"]

        cycles_per_day = 24 / base_cycle_time
        base_process_amount = daily_amount / cycles_per_day

        fractional_part = math.ceil(base_process_amount) - base_process_amount
        if fractional_part > 0:
            # Adjust the process time based on the fractional part
            additional_time = base_cycle_time * (fractional_part / base_process_amount)
            process_hours = base_cycle_time + additional_time
            process_amount = int(base_process_amount) + 1
        else:
            process_hours = base_cycle_time
            process_amount = int(base_process_amount)

        return threshold_round(process_hours), process_amount

    def get_nearest_exchange(self):
        nearest_distance = 99999999
        nearest_exchange = None
        for ticker in EXCHANGES:
            exchange = EXCHANGES[ticker]
            distance = jump_distance(EXCHANGES['ticker']['systemId'], self.id)
            if distance < nearest_distance:
                nearest_exchange = exchange
                nearest_distance = distance
        return nearest_exchange, nearest_distance

    #def is_colonized(self):

class Recipe:
    def __init__(self, rawdata):
        # Importing from buildings.json format
        if 'BuildingRecipeId' in rawdata:
            self.building = rawdata.get('StandardRecipeName')[0:3]
            self.name = rawdata.get('BuildingRecipeId')
            self.duration = rawdata.get('DurationMs')/1000/60/60

            self.inputs = {}
            for inputResource in rawdata.get('Inputs', []):
                ticker = inputResource.get('CommodityTicker')
                amount = inputResource.get('Amount')
                self.inputs[ticker] = amount
            
            self.outputs = {}
            for outputResource in rawdata.get('Outputs', []):
                ticker = outputResource.get('CommodityTicker')
                amount = outputResource.get('Amount')
                self.outputs[ticker] = amount
        # Manually specified format
        else:
            self.building = rawdata.get('building')
            self.name = rawdata.get('name')
            self.duration = rawdata.get('duration')
            self.inputs = rawdata.get('inputs')
            self.outputs = rawdata.get('outputs')

    def __str__(self):
        return f"{self.name} {self.duration}h"

class Base:
    def __init__(self, rawdata):
        # Store the raw JSON data
        self.rawdata = rawdata

        # Create a Planet object
        self.planet = Planet(planet_id=self.rawdata.get('PlanetId'))

        # Extract and count buildings by their ticker
        self.buildingCounts = {}
        for building in rawdata.get('Buildings', []):
            ticker = building.get('BuildingTicker')
            if ticker:
                if ticker in self.buildingCounts:
                    self.buildingCounts[ticker] += 1
                else:
                    self.buildingCounts[ticker] = 1
        
        # Now we need to aggregate building recipes
        
        available_recipes = []
        for building_ticker in list(self.buildingCounts.keys()):
            # Extractors will need to be handled separately based on the planet resources
            if building_ticker == 'COL' or building_ticker == 'RIG' or building_ticker == 'EXT':
                available_recipes += self.get_extractor_recipes(building_ticker)
            else:
                available_recipes += self.get_crafter_recipes(building_ticker)

        for recipe in available_recipes:
            print(recipe)
    
    def get_crafter_recipes(self, building_ticker):
        allbuildings = fio.request("GET", f"/building/allbuildings", cache=-1)
        for building in allbuildings:
            if building['Ticker'] == building_ticker:
                rawrecipes = building.get('Recipes', [])
                recipes = []
                for rawrecipe in rawrecipes:
                    recipe = Recipe(rawrecipe)
                    recipes.append(recipe)
                    #recipe["Building"] = building_ticker
                    #recipe["BuildingCount"] = self.buildingCounts[building_ticker]
                return recipes

    def get_extractor_recipes(self, building_ticker):
        recipes = []
        for ticker in self.planet.resources:
            resource = self.planet.resources[ticker]

            # Skip resources that aren't for this extractor
            if resource["extractor_building"] == building_ticker:
                recipedata = {
                    'building': building_ticker,
                    'name': f"@{building_ticker}=>{resource["process_amount"]}x{ticker}",
                    'duration': resource["process_hours"],
                    'inputs': {},
                    'outputs': {
                        ticker: resource["process_amount"]
                    }
                }
                recipes.append(Recipe(recipedata))
        return recipes
            

    def __str__(self):
        buildings_str = ', '.join([f"{count} {name}" for name, count in self.buildingCounts.items()])
        resources_str = ', '.join(self.planet.resources.keys())
        return f"Base ({self.planet.name}):\n  Buildings: {buildings_str}\n  Resources: {resources_str}"


# Rounds a given value to a specified threshold.
def threshold_round(val, threshold=1e-5):
    for decimal_places in range(15):  # Check rounding from 0 to 14 decimal places
        rounded_value = round(val, decimal_places)
        if abs(val - rounded_value) < threshold:
            return rounded_value
    return val

def get_all_planets():
    planets = {}
    for planet in allplanets:
        planet_class = Planet(planet_id=planet.get('PlanetId'))
        planets[planet_class.name] = planet_class
    return planets