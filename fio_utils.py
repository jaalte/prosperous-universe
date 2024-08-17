import json
import math
from fio_api import fio
from pathfinding import jump_distance

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

PLANET_THRESHOLDS = {
    'temperature': (-25, 75),
    'pressure': (0.25, 2),
    'gravity': (0.25, 2.5),
}

# Create a lookup dictionary for all materials by MaterialId
allmaterials = fio.request("GET", "/material/allmaterials", cache=60*60*24)
material_lookup = {material['MaterialId']: material for material in allmaterials}

# Create a lookup dictionary for all planets by PlanetId
allplanets = fio.request("GET", f"/planet/allplanets/full", cache=-1)
planet_lookup = {planet['PlanetId']: planet for planet in allplanets}

# Create a lookup dictionary keyed by SystemId each equal a list of PlanetName
system_planet_lookup = {}
for planet in allplanets:
    if planet['SystemId'] not in system_planet_lookup:
        system_planet_lookup[planet['SystemId']] = []
    system_planet_lookup[planet['SystemId']].append(planet['PlanetName'])


rawsystemstars = fio.request("GET", f"/systemstars", cache=-1)
systemstars_lookup = {system["SystemId"]: system for system in rawsystemstars}

rawexchangedata = fio.request("GET", f"/exchange/full", cache=60*15, message="Fetching exchange data...") # 15m
# Split list into dicts by ExchangeCode
exchange_goods = {}
for good in rawexchangedata:
    if good['ExchangeCode'] not in exchange_goods:
        exchange_goods[good['ExchangeCode']] = {}
    exchange_goods[good['ExchangeCode']][good['MaterialTicker']] = good

#print(json.dumps(exchange_goods, indent=4))

class Planet:
    def __init__(self, planet_id):
        self.rawdata = planet_lookup.get(planet_id)
        self.name = self.rawdata.get('PlanetName')
        self.id = self.rawdata.get('PlanetId')
        self.natural_id = self.rawdata.get('PlanetNaturalId')
        self.system_natural_id = self.rawdata.get('PlanetNaturalId')[:-1]
        self.resources = {}
        #self.exchange = self.get_nearest_exchange()

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
        
        # Process environmental properties
        self.environment = {}
        self.environment['temperature'] = threshold_round(self.rawdata.get('Temperature'))
        self.environment['pressure'] = threshold_round(self.rawdata.get('Pressure'))
        self.environment['gravity'] = threshold_round(self.rawdata.get('Gravity'))
        
        self.environment_class = {}
        for prop in ['temperature', 'pressure', 'gravity']:
            if self.environment[prop] < PLANET_THRESHOLDS[prop][0]:
                self.environment_class[prop] = 'low'
            elif self.environment[prop] > PLANET_THRESHOLDS[prop][1]:
                self.environment_class[prop] = 'high'
            else:
                self.environment_class[prop] = 'normal'
        self.environment_class['surface'] = threshold_round(self.rawdata.get('Surface'))




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
        for ticker, exchange in exchanges.items():
            distance = jump_distance(exchange.system_natural_id, self.system_natural_id)
            if distance < nearest_distance:
                nearest_exchange = exchange
                nearest_distance = distance
        self.exchange = nearest_exchange
        self.exchange_distance = nearest_distance
        return nearest_exchange

    def get_sites(self):
        sites = fio.request("GET", f"/planet/sites/{self.natural_id}", cache=60*60*24*7)
        self.sites = sites
        return sites

    def has_infrastructure(self):
        keys = [
            'HasLocalMarket',
            'HasChamberOfCommerce',
            'HasWarehouse',
            'HasAdministrationCenter',
            'HasShipyard'
        ]
        
        # If any of these keys in self.rawdata are True, return True
        return any([self.rawdata[key] for key in keys])

    def get_environment_string(self):
        text = ""

        # Define the mapping for each property
        property_mapping = {
            'temperature': 'T',
            'pressure': 'P',
            'gravity': 'G',
            'surface': '^'
        }

        # Loop through each property and build the string
        for prop in property_mapping.keys():
            if prop != 'surface':  # Handle surface separately as it's a boolean
                if self.environment_class[prop] == 'high':
                    text += property_mapping[prop]
                elif self.environment_class[prop] == 'low':
                    text += property_mapping[prop].lower()
                else:
                    text += ' '  # For normal values, add a space
            else:
                # Add s if surface is true, otherwise add space
                text += property_mapping[prop] if not self.environment_class['surface'] else ' '

        return text



    # Make Planet printable
    def __str__(self):
        # Note: Reimplement once Planet.system class is added
        return f"(Planet {self.name} ({self.natural_id}) in the {self.system_natural_id} system)"

class System:
    def __init__(self, hashid):
        rawdata = systemstars_lookup[hashid]

        self.name = rawdata.get('Name')
        self.natural_id = rawdata.get('NaturalId')
        self.id = rawdata.get('NaturalId')
        self.hash = rawdata.get('SystemId')
        self.pos = {
            'x': rawdata.get('PositionX'),
            'y': rawdata.get('PositionY'),
            'z': rawdata.get('PositionZ'),
        }
        self.sectorid = rawdata.get('SectorId')
        self.subsectorid = rawdata.get('SubSectorId')

        self.connections = {}
        for connection in rawdata.get('Connections', []):
            system_hash = connection["ConnectingId"]
            other_system = systemstars_lookup[system_hash]
            connection_name = other_system.get('Name')
            connection_pos = {
                'x': other_system.get('PositionX'),
                'y': other_system.get('PositionY'),
                'z': other_system.get('PositionZ')
            }
            self.connections[connection_name] = {
                'system': connection_name,
                'distance': distance(self.pos, connection_pos),
            }
        
        self.planets = system_planet_lookup.get(hashid, [])  

    def __str__(self):
        return f"[System {self.name} ({self.natural_id}), {len(self.connections)} connections, {len(self.planets)} planets]"


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

class Exchange:
    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.ticker = rawdata.get('ComexCode')
        self.name = rawdata.get('ComexName')
        self.currency = rawdata.get('CurrencyCode')
        self.country = rawdata.get('CountryCode')
        self.system_natural_id = rawdata.get('SystemNaturalId')
        self.goods = exchange_goods[self.ticker]
    
    def get_average_price(self, material, buy_or_sell, amount):
        good = self.goods[material]
        if buy_or_sell == "Buy":
            pass


# Rounds a given value to a specified threshold.
def threshold_round(val, threshold=1e-5):
    for decimal_places in range(15):  # Check rounding from 0 to 14 decimal places
        rounded_value = round(val, decimal_places)
        if abs(val - rounded_value) < threshold:
            return rounded_value
    return val

def distance(pos1, pos2):
    return math.sqrt((pos1['x'] - pos2['x'])**2 + (pos1['y'] - pos2['y'])**2 + (pos1['z'] - pos2['z'])**2)

# Get a dict of all planets in the game keyed by name
def get_all_planets():
    planets = {}
    total = len(allplanets)
    for i, planet in enumerate(allplanets):
        planet_class = Planet(planet_id=planet.get('PlanetId'))
        planets[planet_class.name] = planet_class
        print(f"\rLoading all planets: {i+1}/{total}", end="")
    print("\n")
    return planets

# Get a dict of all systems in the game keyed by name
def get_all_systems():
    systems = {}
    total = len(systemstars_lookup)
    for system_hash in systemstars_lookup.keys():
        system_class = System(system_hash)
        systems[system_class.name] = system_class
    return systems


# Get a dict of all exchanges in the game keyed by ticker
def get_all_exchanges():
    rawexchanges = fio.request("GET", "/exchange/station", cache='forever')
    exchanges = {}
    for rawexchange in rawexchanges:
        exchanges[rawexchange['ComexCode']] = Exchange(rawexchange)
    return exchanges

# Initialize global lists
exchanges = get_all_exchanges()


def main():
    planets = get_all_planets()
    print(json.dumps(planets['Montem'].rawdata, indent=2))
    #print(json.dumps(planets['Montem'].rawdata, indent=2))

    #exchanges = get_all_exchanges()
    #print(json.dumps(exchanges['NC1'].get_good('AMM'), indent=2))

    #systems = get_all_systems()
    


if __name__ == "__main__":
    main()