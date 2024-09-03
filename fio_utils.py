import json
import math
import re
import time
from fio_api import fio
from pathfinding import jump_distance

USERNAME = 'fishmodem'

# Migrated
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

DISTANCE_PER_PARSEC = 12
STL_FUEL_FLOW_RATE = 0.015 # Unknown what it means but it's from /ship/ships/fishmodem
# Pretty sure its a factor of distance, not time:
# - Cause even in close STL transfers in Montem, fuel cost is ~107

DEMOGRAPHICS: ["pioneers", "settlers", "technicians", "engineers", "scientists"]

# Tacotopia, no resources, no harsh environment, no fertility, has surface (MCG)
#   also has population and resource_extraction cogc lol
DEFAULT_BUILDING_PLANET_NATURAL_ID = "CB-045b"

BOGUS_ORDER_THRESHOLD = 5

# Migrated
class DataLoader:
    def __init__(self):
        self._cache = {}
        self.planet_dicts = {}

    def _get_cached_data(self, key):
        """Retrieve data from cache if available."""
        return self._cache.get(key)

    def _set_cache(self, key, data):
        """Store data in cache."""
        self._cache[key] = data
        return data

    @property
    def allplanets(self):
        cache_key = 'allplanets'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        allplanets = fio.request("GET", f"/planet/allplanets/full")
        return self._set_cache(cache_key, allplanets)

    @property
    def planet_lookup(self):
        cache_key = 'planet_lookup'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        planet_lookup = {planet['PlanetNaturalId']: planet for planet in self.allplanets}
        return self._set_cache(cache_key, planet_lookup)

    @property
    def system_planet_lookup(self):
        cache_key = 'system_planet_lookup'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        system_planet_lookup = {}
        for planet in self.allplanets:
            if planet['SystemId'] not in system_planet_lookup:
                system_planet_lookup[planet['SystemId']] = []
            system_planet_lookup[planet['SystemId']].append(planet['PlanetName'])
        return self._set_cache(cache_key, system_planet_lookup)
    
    @property
    def rawsystemstars(self):
        cache_key = 'rawsystemstars'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data
        
        rawsystemstars = fio.request("GET", f"/systemstars")
        return self._set_cache(cache_key, rawsystemstars)

    @property
    def systemstars_lookup(self):
        cache_key = 'systemstars_lookup'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        systemstars_lookup = {system["SystemId"]: system for system in self.rawsystemstars}
        return self._set_cache(cache_key, systemstars_lookup)
    
    @property
    def allmaterials(self):
        cache_key = 'allmaterials'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data
        
        allmaterials = fio.request("GET", "/material/allmaterials")
        # Remove the entry with ticker "CMK", as it's not craftable
        for i in range(len(allmaterials)):
            if allmaterials[i]['Ticker'] == 'CMK':
                del allmaterials[i]
                break
        return self._set_cache(cache_key, allmaterials)

    @property
    def materials_by_ticker(self):
        cache_key = 'materials_by_ticker'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_by_ticker = {material['Ticker']: material for material in self.allmaterials}
        return self._set_cache(cache_key, materials_by_ticker)

    @property
    def material_ticker_list(self):
        cache_key = 'material_ticker_list'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        return self._set_cache(cache_key, self.materials_by_ticker.keys())

    def get_material(self, ticker):
        cache_key = 'get_material_' + str(ticker)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        material = self.materials_by_ticker[ticker]
        return self._set_cache(cache_key, material)

    @property
    def materials_by_hash(self):
        cache_key = 'material_by_hash'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_by_hash = {material['MaterialId']: material for material in self.allmaterials}
        return self._set_cache(cache_key, materials_by_hash)

    @property
    def allbuildings_raw(self):
        cache_key = 'allbuildings_raw'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        allbuildings_raw = fio.request("GET", f"/building/allbuildings", cache=-1)
        return self._set_cache(cache_key, allbuildings_raw)

    @property
    def rawexchangedata(self):
        cache_key = 'rawexchangedata'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawexchangedata = fio.request("GET", f"/exchange/full", message="Fetching exchange data...")
        return self._set_cache(cache_key, rawexchangedata)

    @property
    def exchange_goods(self):
        cache_key = 'exchange_goods'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        exchange_goods = {}
        for good in self.rawexchangedata:
            # Initialize all exchanges
            if good['ExchangeCode'] not in exchange_goods:
                exchange_goods[good['ExchangeCode']] = {}
            exchange_goods[good['ExchangeCode']][good['MaterialTicker']] = ExchangeGood(good)

        return self._set_cache(cache_key, exchange_goods)

    @property
    def exchanges(self):
        return self.get_all_exchanges()

    @property
    def all_population_reports(self):
        cache_key = 'all_population_reports'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        all_population_reports_raw = fio.request("GET", "/csv/infrastructure/allreports", cache=60*60*24)
        all_population_reports = {}
        for report in all_population_reports_raw:
            planet_id = report["PlanetNaturalId"]
            # Initialize the list for this planet if it doesn't exist
            if planet_id not in all_population_reports:
                all_population_reports[planet_id] = []
            all_population_reports[planet_id].append(report)
        return self._set_cache(cache_key, all_population_reports)

    @property
    def planets(self):
        return self.get_all_planets('name')

    @property
    def systems(self):
        return self.get_all_systems()

    def get_all_planets(self, key='name'):
        if key in self.planet_dicts:
            return self.planet_dicts[key]

        planets = {}
        total = len(self.allplanets)
        for i, planet in enumerate(self.allplanets):
            planet_class = Planet(natural_id=planet.get('PlanetNaturalId'))
            planet_key_value = getattr(planet_class, key, None)
            if planet_key_value is not None:
                planets[planet_key_value] = planet_class
            else:
                print(f"Warning: Planet {planet_class.name} does not have the attribute '{key}'")
            print(f"\rLoading all planets: {i+1}/{total}", end="")
        print("\n")

        factor_ranges = {}
        # Determine range of factors for all resources
        for name, planet in planets.items():
            for ticker, resource in planet.resources.items():
                if ticker not in factor_ranges:
                    factor_ranges[ticker] = (resource['factor'],resource['factor'])
                else:
                    if resource['factor'] < factor_ranges[ticker][0]:
                        factor_ranges[ticker] = (resource['factor'],factor_ranges[ticker][1])
                    if resource['factor'] > factor_ranges[ticker][1]:
                        factor_ranges[ticker] = (factor_ranges[ticker][0],resource['factor'])
        
        for name, planet in planets.items():
            for ticker, resource in planet.resources.items():
                resource['factor_range'] = factor_ranges[ticker]

        self.planet_dicts[key] = planets

        return planets


    def get_all_systems(self):
        systems = {}
        total = len(self.systemstars_lookup)
        for system_hash in self.systemstars_lookup.keys():
            system_class = System(system_hash)
            systems[system_class.name] = system_class
        return systems

    def get_all_exchanges(self):
        cache_key = 'all_exchanges'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawexchanges = fio.request("GET", "/exchange/station", cache='forever')
        exchanges = {}
        for rawexchange in rawexchanges:
            exchanges[rawexchange['ComexCode']] = Exchange(rawexchange)
        return self._set_cache(cache_key, exchanges)

    def get_exchange(self, code):
        cache_key = 'exchange_' + str(code)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        exchange = self.exchanges[code]
        return self._set_cache(cache_key, exchange)


    def exchange(self, code):
        return self.get_exchange(code)

    def get_all_buildings(self):
        cache_key = 'buildings'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        buildings = {}
        for rawbuilding in self.allbuildings_raw:
            ticker = rawbuilding.get('Ticker')
            planet = Planet(natural_id=DEFAULT_BUILDING_PLANET_NATURAL_ID)
            buildings[ticker] = Building(ticker, planet)

        return self._set_cache(cache_key, buildings)

loader = DataLoader()

        
# Migrated
class Planet:
    # Constructor
    # CHOOSE ONE: id (hash), planet name, or planet natural id
    def __init__(self, hash='', name='', natural_id=''):

        self.rawdata = loader.planet_lookup.get(natural_id)
        self.name = self.rawdata.get('PlanetName')
        self.id = self.rawdata.get('PlanetId')
        self.natural_id = self.rawdata.get('PlanetNaturalId')
        self.system_natural_id = self.rawdata.get('PlanetNaturalId')[:-1]
        self.resources = {}
        #self.exchange = self.get_nearest_exchange()

        # Set current COGC program
        self.cogc = ""
        if len(self.rawdata.get('COGCPrograms', [])) > 0 and self.rawdata.get("COGCProgramStatus") == "ACTIVE":
            current_time_ms = int(time.time() * 1000)
            for period in self.rawdata.get("COGCPrograms", []):
                if period["StartEpochMs"] <= current_time_ms <= period["EndEpochMs"]:
                    if period["ProgramType"]:
                        raw_cogc = period["ProgramType"]

                        # Remove "ADVERTISING_" or "WORKFORCE_" from the start if present
                        if raw_cogc.startswith("ADVERTISING_"):
                            self.cogc = raw_cogc[len("ADVERTISING_"):]
                        elif raw_cogc.startswith("WORKFORCE_"):
                            self.cogc = raw_cogc[len("WORKFORCE_"):]
                        else:
                            self.cogc = raw_cogc
                    break


        # Process the resources in rawdata
        for resource in self.rawdata.get('Resources', []):
            material_hash = resource.get('MaterialId')
            material_data = loader.materials_by_hash[material_hash]

            if not material_data:
                print(f"Warning: Material {material_hash} not found in material lookup")
                continue

            ticker = material_data['Ticker']
            resource_type = resource.get('ResourceType')
            factor = threshold_round(resource.get('Factor', 0))
            
            for building, info in EXTRACTORS.items():
                if info["type"] == resource_type:
                    extractor_building = building
                    break
            
            daily_amount = factor * 100 * EXTRACTORS[extractor_building]["multiplier"]
            process_hours, process_amount = self._calculate_process_time_and_amount(extractor_building, daily_amount)

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
        self.environment['fertility'] = threshold_round(self.rawdata.get('Fertility'))
        
        self.environment_class = {}
        for prop in ['temperature', 'pressure', 'gravity']:
            if self.environment[prop] < PLANET_THRESHOLDS[prop][0]:
                self.environment_class[prop] = 'low'
            elif self.environment[prop] > PLANET_THRESHOLDS[prop][1]:
                self.environment_class[prop] = 'high'
            else:
                self.environment_class[prop] = 'normal'
        self.environment_class['surface'] = threshold_round(self.rawdata.get('Surface'))




    def _calculate_process_time_and_amount(self, extractor_building, daily_amount):
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

    def get_population_data(self):
        all_population_reports = loader.all_population_reports
        if not self.natural_id in all_population_reports \
        or len(all_population_reports[self.natural_id]) < 2:
            # Generate an empty population dict
            categories = ["pioneers", "settlers", "technicians", "engineers", "scientists"]
            keys = [
                "count",
                "next",
                "difference",
                "average_happiness",
                "unemployment_rate",
                "unemployment_amount",
                "open_jobs",
            ]

            population = {category: {key: 0 for key in keys} for category in categories}
            return population

        reports = all_population_reports[self.natural_id]

        latest_report = reports[-1]
        previous_report = reports[-2]
        
        # Function to generate the cleaned-up report
        def _generate_population_data(prefix):
            return {
                "count": previous_report[f"NextPopulation{prefix}"],
                # Oddly next is always "2" for pioneers on unpopulated planets
                "next": latest_report[f"NextPopulation{prefix}"] if latest_report[f"NextPopulation{prefix}"] >= 10 else 0,
                "difference": latest_report[f"PopulationDifference{prefix}"],
                "average_happiness": latest_report[f"AverageHappiness{prefix}"],
                "unemployment_rate": latest_report[f"UnemploymentRate{prefix}"],
                "unemployment_amount": math.floor(previous_report[f"NextPopulation{prefix}"] * latest_report[f"UnemploymentRate{prefix}"]),
                "open_jobs": int(latest_report[f"OpenJobs{prefix}"])
            }

        # Population categories
        categories = ["Pioneer", "Settler", "Technician", "Engineer", "Scientist"]

        # Create the new structure
        population = {category.lower()+'s': _generate_population_data(category) for category in categories}

        # Return the new structure
        return population

    def get_population_count(self):
        # A dict of {demographic: count}
        data = self.get_population_data()
        counts = {key: value['count'] for key, value in data.items()}
        return Population(counts)
        


    def get_building_environment_cost(self, area):
        cost = ResourceList({})

        if self.environment_class['temperature'] == 'low':
            cost += ResourceList({'INS': 10*area})
        elif self.environment_class['temperature'] == 'high':
            cost += ResourceList({'TSH': 1})

        if self.environment_class['pressure'] == 'low':
            cost += ResourceList({'SEA': area})
        elif self.environment_class['pressure'] == 'high':
            cost += ResourceList({'HSE': 1})

        if self.environment_class['gravity'] == 'low':
            cost += ResourceList({'MGC': 1})
        elif self.environment_class['gravity'] == 'high':
            cost += ResourceList({'BL': 1})

        if self.environment_class['surface']:
            cost += ResourceList({'MCG': 4*area})
        else: 
            cost += ResourceList({'AEF': math.ceil(area/3)})

        return cost


    def get_environment_string(self):
        text = ""

        # Define the mapping for each property
        property_mapping = {
            'temperature': 'T',
            'pressure': 'P',
            'gravity': 'G',
        }

        # Loop through each property and build the string
        for prop in property_mapping.keys():
            if self.environment_class[prop] == 'high':
                text += property_mapping[prop]
            elif self.environment_class[prop] == 'low':
                text += property_mapping[prop].lower()
            else:
                text += ' '  # For normal values, add a space

        # Add ^ if surface is false, otherwise add space
        text += '^' if not self.environment_class['surface'] else ' '
        text += ' ' if self.environment['fertility'] == -1.0 else 'F'
        

        return text



    # Make Planet printable
    def __str__(self):
        # Note: Reimplement once Planet.system class is added
        return f"(Planet {self.name} ({self.natural_id}) in the {self.system_natural_id} system)"

# Migrated
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
# Migrated
# A single building of a particular ticker. Not a particular one though.
class Building:
    def __init__(self, ticker, planet=None):

        self.ticker = ticker
        if isinstance(planet, str):
            self.planet = Planet(natural_id=planet)
        elif isinstance(planet, Planet):
            self.planet = planet
        elif planet is None:
            self.planet = Planet(natural_id=DEFAULT_PLANET_NATURAL_ID)
        else:
            raise Exception(f"Invalid planet type: {type(planet)}")

        for building in loader.allbuildings_raw:
            if building['Ticker'] == ticker:
                self.rawdata = building
                break
        
        self.area = self.rawdata.get('AreaCost')
        self.population_demand = Population({
            'pioneers': self.rawdata.get('Pioneers'),
            'colonists': self.rawdata.get('Colonists'),
            'technicians': self.rawdata.get('Technicians'),
            'engineers': self.rawdata.get('Engineers'),
            'researchers': self.rawdata.get('Researchers'),
        })
        self.cogc_type = self.rawdata.get('Expertise')

        is_extractor = self.ticker in ['COL', 'RIG', 'EXT']
        self.type = 'extractor' if is_extractor else 'crafter'
        if self.type == 'extractor':
            self._init_extractor_recipes(self.ticker)
        else:
            self._init_crafter_recipes(self.ticker)

        if len(self.recipes) == 0:
            self.type = 'other'

        self.min_construction_materials = ResourceList(self.rawdata.get('BuildingCosts'))
        extra_materials = self.planet.get_building_environment_cost(self.area)
        self.construction_materials = self.min_construction_materials + extra_materials
    
    def _init_crafter_recipes(self, building_ticker):
        for building in loader.allbuildings_raw:
            if building['Ticker'] == building_ticker:
                rawrecipes = building.get('Recipes', [])
                self.recipes = []
                for rawrecipe in rawrecipes:
                    recipe = Recipe(rawrecipe)
                    self.recipes.append(recipe)

    def _init_extractor_recipes(self, building_ticker):
        self.recipes = []
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
                self.recipes.append(Recipe(recipedata))

    # function to get total cost of building by resourcelist
    def get_cost(self, exchange='NC1'):
        return self.construction_materials.get_total_value(exchange, "buy")

    def is_extractor(self):
        return self.ticker in ['COL', 'RIG', 'EXT']

    def get_cogc_bonus(self, cogc=None):
        if not cogc: return 1.0

        if cogc == self.cogc_type:
            return 1.25

        if cogc in ['PIONEERS', 'SETTLERS', 'TECHNICIANS', 'ENGINEERS', 'SCIENTISTS']:
            if self.population_demand[cogc.lower()] > 0:
                return 1.1
            else:
                return 1.0

        return 1.0

    def __str__(self):
        return f"{self.ticker}"

# Migrated
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

    def __str__(self):
        return f"[{self.building:<3} Recipe: {self.inputs} => {self.outputs} in {self.duration}h]"

# Migrated
class Population:
    def __init__(self, population_dict):
        # TODO: Implement parsing of multiple rawdata types to clean up code elsewhere
        self.population = population_dict

    def get_upkeep(self):
        # Population is a dict of {demographic: amount}
        needs = ResourceList()
        for demographic in self.population:
            needs += self.population[demographic]/100 * POPULATION_UPKEEP_PER_100_PER_DAY[demographic]
        return needs

    @property
    def pioneers(self):
        return self.population.get('pioneers', 0)

    @property
    def settlers(self):
        return self.population.get('settlers', 0)

    @property
    def technicians(self):
        return self.population.get('technicians', 0)

    @property
    def engineers(self):
        return self.population.get('engineers', 0)

    @property
    def scientists(self):
        return self.population.get('scientists', 0)

    def __getitem__(self, demographic):
        return self.population.get(demographic.lower(), 0)

    def __add__(self, other):
        if not isinstance(other, Population):
            return NotImplemented
        result_population = {}
        for demographic, amount in self.population.items():
            result_population[demographic] = amount + other.population.get(demographic, 0)
        for demographic, amount in other.population.items():
            if demographic not in result_population:
                result_population[demographic] = amount
        return Population(result_population)

    def __sub__(self, other):
        if not isinstance(other, Population):
            return NotImplemented
        result_population = {}
        for demographic, amount in self.population.items():
            result_population[demographic] = amount - other.population.get(demographic, 0)
        return Population(result_population)

    def __mul__(self, factor):
        if not isinstance(factor, (int, float)):
            return NotImplemented
        result_population = {demographic: amount * factor for demographic, amount in self.population.items()}
        return Population(result_population)

    __rmul__ = __mul__  # Allows multiplication with a float on the left-hand side

    def __str__(self):
        return str(self.population)


class Exchange:
    def __init__(self, rawdata):
        if isinstance(rawdata, str):
            rawexchanges = fio.request("GET", "/exchange/station", cache='forever')
            for rawexchange in rawexchanges:
                if rawexchange['ComexCode'] == rawdata:
                    rawdata = rawexchange 

        self.rawdata = rawdata
        self.ticker = rawdata.get('ComexCode')
        self.code = self.ticker
        self.name = rawdata.get('ComexName')
        self.currency = rawdata.get('CurrencyCode')
        self.country = rawdata.get('CountryCode')
        self.system_natural_id = rawdata.get('SystemNaturalId')

        goods = {}
        
        self.goods = loader.exchange_goods[self.ticker]
    
    def get_good(self, material_ticker):
        return self.goods.get(material_ticker, None)

    def get_average_price(self, material_ticker, buy_or_sell, amount):
        good = self.goods[material_ticker]
        if buy_or_sell == "Buy":
            pass

    def get_availability(self, material_ticker, buy_or_sell):
        good = self.goods[material_ticker]


    def __str__(self):
        return f"[Exchange {self.ticker}]"

# A single good on an exchange
# Will contain price prediction logic later
# Migrated with Exchange
class ExchangeGood:
    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.ticker = rawdata['MaterialTicker']
        self.name = rawdata['MaterialName']
        self.currency = rawdata['Currency']

        self._init_buy_orders() # AKA Bid
        self._init_sell_orders() # AKA Ask


    def _init_buy_orders(self):
        raw_orders = self.rawdata['BuyingOrders'] # AKA Bid
        # Remap ItemCount to count and ItemCost to cost
        self.buy_orders = [{'cost': order['ItemCost'], 'count': order['ItemCount']} for order in raw_orders]
        self.buy_orders = sorted(self.buy_orders, key=lambda k: k['cost'], reverse=True)

        # Fixes values for nation orders with no count limit
        for order in self.buy_orders:
            if not order['count']:
                order['count'] = float('inf')

        # Filter bogus orders
        if len(self.buy_orders) > 0:
            filtered_orders = []
            buy_min = self.buy_orders[0]['cost'] / BOGUS_ORDER_THRESHOLD
            for i in range(len(self.buy_orders)):
                order = self.buy_orders[i]
                if order['cost'] >= buy_min:
                    filtered_orders.append(order)
            self.buy_orders = filtered_orders

    def _init_sell_orders(self):
        raw_orders = self.rawdata['SellingOrders']  # AKA Ask
        # Remap ItemCount to count and ItemCost to cost
        self.sell_orders = [{'cost': order['ItemCost'], 'count': order['ItemCount']} for order in raw_orders]
        self.sell_orders = sorted(self.sell_orders, key=lambda k: k['cost'])

        # Fixes values for nation orders with no count limit
        for order in self.sell_orders:
            if not order['count']:
                order['count'] = float('inf')

        # Filter bogus orders
        if len(self.sell_orders) > 0:
            filtered_orders = []
            sell_max = self.sell_orders[0]['cost'] * BOGUS_ORDER_THRESHOLD
            for i in range(len(self.sell_orders)):
                order  = self.sell_orders[i]
                if order['cost'] <= sell_max:
                    filtered_orders.append(order)
            self.sell_orders  = filtered_orders


    @property
    def buy_price(self):
        if len(self.sell_orders) > 0:
            return self.sell_orders[0]['cost']
        else:  
            return float('inf')

    @property
    def sell_price(self):
        if len(self.buy_orders) > 0:
            return self.buy_orders[0]['cost']
        else:  
            return 0

    def buy_price_for_amount(self, amount):
        met = 0
        spent = 0
        for order in self.sell_orders:
            needed = amount - met
            if order['count'] >= needed:
                bought = needed
                spent += bought * order['cost']
                met = amount
                break
            else:
                bought = order['count']
                met += bought
                spent += bought * order['cost']
        
        if met < amount:
            return float('inf')
        else:
            return spent

    def sell_price_for_amount(self, amount):
        met = 0
        earned = 0
        for order in self.buy_orders:
            needed = amount - met
            if order['count'] >= needed:
                sold = needed
                earned += sold * order['cost']
                met = amount
                break
            else:
                sold = order['count']
                met += sold
                earned += sold * order['cost']
        
        if met < amount:
            return 0
        else:
            return earned

    @property
    def supply(self):
        # Get average price for all orders
        #total_cost = sum([i['cost'] * i['count'] for i in self.sell_orders])
        if len(self.sell_orders) == 0:
            return 0

        total_count = 0
        for order in self.sell_orders: 
            total_count += order['count']

        
        return total_count#, total_cost/total_count
 
    @property
    def demand(self):
        # Get average price for all orders
        #total_cost = sum([i['cost'] * i['count'] for i in self.buy_orders])
        if len(self.buy_orders) == 0:
            return 0
        
        total_count = 0
        for order in self.buy_orders:
            total_count += order['count']
        
        return total_count#, total_cost/total_count



# # WIP
# class Material:
#     def __init__(self, ticker):
#         self.ticker  = ticker
#         self.rawdata = loader.get_material(ticker)

#         print(self.rawdata)

class System:
    def __init__(self, hashid):
        rawdata = loader.systemstars_lookup[hashid]

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
            other_system = loader.systemstars_lookup[system_hash]
            connection_name = other_system.get('Name')
            connection_pos = {
                'x': other_system.get('PositionX'),
                'y': other_system.get('PositionY'),
                'z': other_system.get('PositionZ')
            }
            self.connections[connection_name] = {
                'system': connection_name,
                'distance': distance(self.pos, connection_pos)/DISTANCE_PER_PARSEC,
            }
        
        self.planets = loader.system_planet_lookup.get(hashid, [])  

    def get_route_to(self, system_natural_id):
        
        # mockup, not init
        route = {
            'systems': [],
            'total_parsecs': 0,
            'total_jumps': 0,
        }

        distance = 0 # in parsecs
        
        
        return route


    def __str__(self):
        return f"[System {self.name} ({self.natural_id}), {len(self.connections)} connections, {len(self.planets)} planets]"

class Container:
    def __init__(self, mass_capacity, volume_capacity):
        self.mass_capacity = mass_capacity
        self.volume_capacity = volume_capacity
    
    def get_max_capacity_for(self, resource_ticker):
        material = loader.materials_by_ticker[resource_ticker]
        #print(json.dumps(material, indent=4))
        max_by_volume = int(self.volume_capacity / material['Volume'])
        max_by_mass = int(self.mass_capacity / material['Weight'])

        return min(max_by_volume, max_by_mass)


class Ship:
    def __init__(self, id):
        ships = fio.request("GET", f"/ship/ships/{USERNAME}", cache=60*60*24)
        #print(json.dumps(ships, indent=4))

        self.rawdata = next((ship for ship in ships if ship.get('Registration') == id), None)

    def get_time_to(self, system_natural_id, reactor):
        distance = self.get_parsecs_to(system_natural_id)
        hours = 0.0318*reactor+0.7763
        
    def get_fuel_to(self, system_natural_id, reactor):
        distance = self.get_parsecs_to(system_natural_id)
        fuel = 0.0721*reactor-0.0730

class ResourceList:
    def __init__(self, rawdata={}):
        if len(rawdata) == 0:
            self.resources = {}
            return

        if isinstance(rawdata, dict):
            self.resources = rawdata
        elif isinstance(rawdata, list):

            key_mapping = {
                'CommodityTicker': 'Ticker',
                'MaterialTicker': 'Ticker',
                'Ticker': 'Ticker',
                'MaterialAmount': 'Amount',
                'DailyConsumption': 'Amount',
                'Amount': 'Amount',
            }

            # Initialize ticker_key and amount_key with None
            ticker_key = None
            amount_key = None

            # Find the correct keys
            for key in key_mapping:
                if key in rawdata[0]:
                    if key_mapping[key] == 'Ticker' and ticker_key is None:
                        ticker_key = key
                    elif key_mapping[key] == 'Amount' and amount_key is None:
                        amount_key = key

            # Default to 'Ticker' and 'Amount' if no specific key found
            ticker_key = ticker_key or 'Ticker'
            amount_key = amount_key or 'Amount'

            self.resources = {}
            for resource in rawdata:
                ticker = resource[ticker_key]
                amount = resource[amount_key]
                self.resources[ticker] = amount
        elif isinstance(rawdata, str):
            tickers = sorted(loader.materials_by_ticker.keys())

            pattern = r'\b(\d+)\s*x?\s*({})\b'.format('|'.join(re.escape(ticker) for ticker in tickers))
            matches = re.findall(pattern, rawdata)
            recognized_tickers = {ticker for _, ticker in matches}

            # Check for unrecognized tickers
            unrecognized = re.findall(r'(\d+\s*x?\s*[A-Z0-9]+)', rawdata)
            for item in unrecognized:
                quantity, ticker = re.findall(r'(\d+)\s*x?\s*([A-Z0-9]+)', item)[0]
                if ticker not in recognized_tickers:
                    print(f"Unrecognized material ticker: {ticker}")

            self.resources = {ticker: int(quantity) for quantity, ticker in matches}
        else:
            raise TypeError("Unsupported data type for ResourceList initialization")
        
        self.resources = dict(sorted(self.resources.items()))

    def get_material_properties(self):
        return {ticker: loader.materials_by_ticker[ticker] for ticker in self.resources}

    def get_total_weight(self):
        total = 0
        for ticker, amount in self.resources.items():
            total += loader.materials_by_ticker[ticker]['Weight'] * amount
        return total

    def get_total_volume(self):
        total = 0
        for ticker, amount in self.resources.items():
            total += loader.materials_by_ticker[ticker]['Volume'] * amount
        return total

    def get_total_value(self, exchange="NC1", trade_type="buy"):
        if isinstance(exchange, str):
            exchange = Exchange(exchange)

        if not isinstance(trade_type, str):
            return NotImplemented
        trade_type = trade_type.lower()

        total = 0
        for ticker, amount in self.resources.items():
            if trade_type == "buy":
                total += exchange.get_good(ticker).buy_price * amount
            else: # trade_type == "sell" or other:
                total += exchange.get_good(ticker).sell_price * amount
        return total

    def get_amount(self, ticker):
        return self.resources.get(ticker, 0)

    def contains(self, ticker):
        return ticker in self.resources.keys() and self.resources[ticker] > 0

    def remove(self, ticker):
        if ticker in self.resources:
            amount = self.resources[ticker]
            del self.resources[ticker]
            return amount
        else:
            raise KeyError(f"Resource '{ticker}' does not exist in the ResourceList.")

    def invert(self):
        new_resources = {ticker: -amount for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def prune_negatives(self):
        new_resources = {ticker: amount for ticker, amount in self.resources.items() if amount > 0}
        return ResourceList(new_resources)

    def floor(self):
        new_resources = {ticker: math.floor(amount) for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def ceil(self):
        new_resources = {ticker: math.ceil(amount) for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def round(self):
        new_resources = {ticker: round(amount) for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)
    
    def add(self, ticker, amount):
        add_list = None
        if isinstance(ticker, dict):
            add_list = ResourceList(ticker)
        if isinstance(ticker, ResourceList):
            add_list = ticker
        
        if add_list is not None:
            add_list = ResourceList(add_list)
            self += add_list
            return
        
        if ticker in self.resources:
            self.resources[ticker] += amount
        else:
            self.resources[ticker] = amount

    def subtract(self, ticker, amount):
        sub_list = None
        if isinstance(ticker, dict):
            sub_list = ResourceList(ticker)
        if isinstance(ticker, ResourceList):
            sub_list = ticker
        
        if sub_list is not None:
            sub_list = ResourceList(add_list)
            self -= add_list
            return
        
        if ticker in self.resources:
            self.resources[ticker] += amount
        else:
            self.resources[ticker] = amount

    def split(self):
        single_resources = []
        for ticker, amount in self.resources.items():
            single_resources.append(ResourceList({ticker: amount}))
        return single_resources

    def __add__(self, other):
        if not isinstance(other, ResourceList):
            return NotImplemented
        new_resources = self.resources.copy()
        for ticker, amount in other.resources.items():
            if ticker in new_resources:
                new_resources[ticker] += amount
            else:
                new_resources[ticker] = amount
        return ResourceList(new_resources)

    def __sub__(self, other):
        if not isinstance(other, ResourceList):
            return NotImplemented
        new_resources = self.resources.copy()

        for ticker, amount in other.resources.items():
            if ticker in new_resources:
                new_resources[ticker] -= amount
            else:
                new_resources[ticker] = -amount

        return ResourceList(new_resources)

    def __mul__(self, multiplier):
        if not isinstance(multiplier, int) and not isinstance(multiplier, float):
            return NotImplemented
        new_resources = {ticker: amount * multiplier for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def __rmul__(self, multiplier):
        return self.__mul__(multiplier)

    def __len__(self):
        return len(self.resources)

    def json(self):
        return json.dumps(self.resources, indent=2)

    def __str__(self):
        formatted_resources = []
        for name, count in self.resources.items():
            if abs(count - round(count)) < 0.0001:  # Check if count is within 4 decimal places of an integer
                formatted_resources.append(f"{int(round(count))} {name}")  # Display as an integer
            else:
                formatted_resources.append(f"{count:.2f} {name}")  # Display with 2 decimal places

        return ', '.join(formatted_resources)

# Global functions

# Rounds a given value to a specified threshold.
def threshold_round(val, threshold=1e-5):
    for decimal_places in range(15):  # Check rounding from 0 to 14 decimal places
        rounded_value = round(val, decimal_places)
        if abs(val - rounded_value) < threshold:
            return rounded_value
    return val

def distance(pos1, pos2):
    return math.sqrt((pos1['x'] - pos2['x'])**2 + (pos1['y'] - pos2['y'])**2 + (pos1['z'] - pos2['z'])**2)

POPULATION_UPKEEP_PER_100_PER_DAY = {
    'pioneers':    ResourceList({'RAT': 4, 'DW': 4,   'OVE': 0.5,                         'PWO': 0.2, 'COF': 0.5}),
    'settlers':    ResourceList({'RAT': 6, 'DW': 5,   'EXO': 0.5, 'PT':  0.5,             'REP': 0.2, 'KOM': 1  }),
    'technicians': ResourceList({'RAT': 7, 'DW': 7.5, 'MED': 0.5, 'HMS': 0.5, 'SCN': 0.1, 'SC':  0.1, 'ALE': 1  }),
    'engineers':   ResourceList({'FIM': 7, 'DW': 10,  'MED': 0.5, 'HSS': 0.2, 'PDA': 0.1, 'VG':  0.2, 'GIN': 1  }),
    'scientists':  ResourceList({'MEA': 7, 'DW': 10,  'MED': 0.5, 'LC':  0.2, 'WS':  0.1, 'NS':  0.1, 'WIN': 1  }),
}

# Get a dict of all planets in the game keyed by name
# Also adds extra data that requires all planets to be loaded first
def get_all_planets(key='name'):
    return loader.get_all_planets(key)

# Get a dict of all systems in the game keyed by name
def get_all_systems():
    return loader.get_all_systems()

# Get a dict of all exchanges in the game keyed by ticker
def get_all_exchanges():
    return loader.get_all_exchanges()

def get_burn_rates():
    raw_burn_rates = fio.request("GET", f"/csv/burnrate?apikey={fio.api_key}&username={USERNAME}", cache=-1)
    burn_rates = {}
    for raw_burn_rate in raw_burn_rates:
        if not raw_burn_rate['PlanetName'] in burn_rates:
            burn_rates[raw_burn_rate['PlanetName']] = []
        burn_rates[raw_burn_rate['PlanetName']].append(raw_burn_rate)

    for planet, rate_list in burn_rates.items():
        burn_rates[planet] = ResourceList({rate['Ticker']: rate['DailyConsumption'] for rate in rate_list})

        #burn_rates[raw_burn_rate['PlanetName']][raw_burn_rate['Ticker']] = raw_burn_rate


    return burn_rates


# Make this public for importing scripts cause it's very fast
exchanges = get_all_exchanges()

def main():
    planets = loader.get_all_planets('name')
    montem = planets['Montem']
    tio_base = planets['XG-326a']

    burn_rates = get_burn_rates()
    #for planet, rate in burn_rates.items():
        #print(f"{planet}: {rate}")

    

    #print(json.dumps(tio_base.rawdata, indent=2))

    # ship = Ship("AVI-054C4")
    
    nc1 = loader.exchange('NC1')
    #print(json.dumps(nc1.goods, indent=2))

    for ticker, material in loader.materials_by_ticker.items():
        for code, exchange in loader.exchanges.items():
                if exchange.get_good(ticker) is None:
                    print(f"{exchange.code}: No {ticker} good.")


    good = loader.exchanges['NC1'].get_good('MCB')

if __name__ == "__main__":
    main()