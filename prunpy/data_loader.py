from prunpy.api import fio
from prunpy.constants import DEFAULT_BUILDING_PLANET_NATURAL_ID, DEMOGRAPHICS
import os

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
    def materials_raw(self):
        cache_key = 'materials_raw'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_raw = fio.request("GET", "/material/allmaterials")
        # Remove the entry with ticker "CMK", as it's not craftable
        # Note: This will break things when reading ships of new players
        for i in range(len(materials_raw)):
            if materials_raw[i]['Ticker'] == 'CMK':
                del materials_raw[i]
                break
        return self._set_cache(cache_key, materials_raw)

    @property
    def materials_by_ticker(self):
        from prunpy.models.material import Material
        cache_key = 'materials_by_ticker'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_by_ticker = {rawmaterial['Ticker']: Material(rawmaterial) for rawmaterial in self.materials_raw}
        return self._set_cache(cache_key, materials_by_ticker)

    @property
    def materials(self):
        return self.materials_by_ticker

    @property
    def materials_by_hash(self):
        from prunpy.models.material import Material
        cache_key = 'material_by_hash'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_by_hash = {material['MaterialId']: Material(material) for material in self.materials_raw}
        return self._set_cache(cache_key, materials_by_hash)

    @property
    def material_ticker_list(self):
        cache_key = 'material_ticker_list'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        return self._set_cache(cache_key, sorted(self.materials_by_ticker.keys()))

    def get_material(self, ticker):
        cache_key = 'get_material_' + str(ticker)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        if ticker not in self.materials_by_ticker:
            raise ValueError(f"Material with ticker {ticker} not found")

        material = self.materials_by_ticker[ticker]
        return self._set_cache(cache_key, material)

    def material(self, ticker):
        return self.get_material(ticker)

    @property
    def allbuildings_raw(self):
        cache_key = 'allbuildings_raw'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        allbuildings_raw = fio.request("GET", f"/building/allbuildings", cache=-1)
        return self._set_cache(cache_key, allbuildings_raw)

    @property
    def all_building_tickers(self):
        cache_key = 'all_building_tickers'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        return self._set_cache(cache_key, [building['Ticker'] for building in self.allbuildings_raw])

    @property
    def rawexchangedata(self):
        cache_key = 'rawexchangedata'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawexchangedata = fio.request("GET", f"/exchange/full", message="Fetching exchange data...")
        return self._set_cache(cache_key, rawexchangedata)

    @property
    def rawexchanges(self):
        cache_key = 'rawexchanges'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawexchanges = fio.request("GET", "/exchange/station", cache='forever')
        return self._set_cache(cache_key, rawexchanges)

    def get_raw_exchange_price_history(self, exchange_ticker, material_ticker):
        cache_key = f'get_raw_exchange_price_history_{exchange_ticker}.{material_ticker}'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        history = fio.request("GET", f"/exchange/cxpc/{material_ticker}.{exchange_ticker}", cache=60*60*24*3)
        
        return self._set_cache(cache_key, history)

    def get_price_history(self, exchange_ticker, material_ticker):
        cache_key = f'get_price_history_{exchange_ticker}.{material_ticker}'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        from prunpy.models.price_history import PriceHistory
        history = PriceHistory(material_ticker, exchange_ticker)
        
        return self._set_cache(cache_key, history)

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


    ##### Methods that depend on external classes which depend on loader
    ##### Modules must be lazy-imported within them
    ##### Generally they are methods, not properties
    ##### Also includes getters that depend on methods that require imports

    def get_all_planets(self, key='name'):
        from prunpy.models.planet import Planet
        cache_key = f"all_planets_by_{key}"
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        planets = {}
        total = len(loader.allplanets)
        for i, planet in enumerate(loader.allplanets):
            planet_instance = Planet(natural_id=planet.get('PlanetNaturalId'))

            if key in ['name', '', 'PlanetName']:
                planets[planet_instance.name] = planet_instance
            elif key in ['natural_id', 'id', 'PlanetNaturalId']:
                planets[planet_instance.natural_id] = planet_instance
            else:
                raise ValueError(f"Invalid key: {key}")

            #print(f"\rLoading all planets: {i+1}/{total}", end="")
        #print("\n")

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

        return self._set_cache(cache_key, planets)

    @property
    def planets(self):
        return self.get_all_planets()

    def get_all_planet_names(self):
        cache_key = 'get_all_planet_names'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        names = list(self.get_all_planets('name').keys())

        return self._set_cache(cache_key, names)

    def get_all_planet_ids(self):
        cache_key = 'get_all_planet_ids'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        ids = []
        for planet in loader.allplanets:
            ids.append(planet['PlanetNaturalId'])

        return self._set_cache(cache_key, ids)

    def get_planet(self, name_string):
        from prunpy.models.planet import Planet
        if isinstance(name_string, Planet):
            return self.get_all_planets(key='natural_id')[name_string.natural_id]
        
        planet_names = self.get_all_planet_names()
        planet_ids   = self.get_all_planet_ids()

        # Create lowercase mappings for case-insensitive lookup
        lc_names = {name.lower(): name for name in planet_names}
        lc_ids   = {planet_id.lower(): planet_id for planet_id in planet_ids}

        # Lowercase the input for case-insensitive comparison
        lc_name_string = name_string.lower()

        if lc_name_string in lc_names:
            original_name = lc_names[lc_name_string]
            return self.get_all_planets(key='name')[original_name]
        elif lc_name_string in lc_ids:
            original_id = lc_ids[lc_name_string]
            return self.get_all_planets(key='natural_id')[original_id]
        else:
            # Raise error
            raise Exception(f"Could not find planet '{name_string}'")

    def get_all_systems(self):
        from prunpy.models.system import System
        cache_key = 'systems'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        systems = {}
        total = len(loader.systemstars_lookup)
        for system_hash in loader.systemstars_lookup.keys():
            system_class = System(system_hash)
            systems[system_class.name] = system_class
        return self._set_cache(cache_key, systems)

    def get_all_buildings(self, planet_id=DEFAULT_BUILDING_PLANET_NATURAL_ID):
        from prunpy.models.building import Building
        from prunpy.models.planet import Planet
        cache_key = 'all_buildings_' + str(planet_id)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        buildings = {}
        for rawbuilding in loader.allbuildings_raw:
            ticker = rawbuilding.get('Ticker')
            planet = Planet(natural_id=DEFAULT_BUILDING_PLANET_NATURAL_ID)
            buildings[ticker] = Building(ticker, planet)

        return self._set_cache(cache_key, buildings)

    def get_building(self, ticker, planet_id=DEFAULT_BUILDING_PLANET_NATURAL_ID):
        return self.get_all_buildings().get(ticker, planet_id)

    def get_all_exchanges(self):
        from prunpy.models.exchange import Exchange
        cache_key = 'all_exchanges'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        exchanges = {}
        exchange_goods = self.get_exchange_goods()
        for rawexchange in loader.rawexchanges:
            ticker = rawexchange['ComexCode']
            exchanges[ticker] = Exchange(rawexchange, exchange_goods[ticker])
        return self._set_cache(cache_key, exchanges)

    @property
    def exchanges(self):
        return self.get_all_exchanges()

    def get_exchange(self, identifier):
        from prunpy.models.exchange import Exchange

        cache_key = 'exchange_' + str(identifier)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        if isinstance(identifier, Exchange):
            return self._set_cache(cache_key, identifier)

        exchanges = self.get_all_exchanges()

        if identifier in exchanges.keys():
            return self._set_cache(cache_key, exchanges[identifier])
        
        if not identifier:
            exchange = exchanges[self.get_preferred_exchange_code()]
            return self._set_cache(cache_key, exchange)

        raise Exception(f"Could not find exchange '{identifier}'")

    def get_exchange_goods(self):
        from prunpy.models.exchange import ExchangeGood
        cache_key = 'exchange_goods'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        exchange_goods = {}
        for good in loader.rawexchangedata:
            # Initialize all exchanges
            if good['ExchangeCode'] not in exchange_goods:
                exchange_goods[good['ExchangeCode']] = {}
            exchange_goods[good['ExchangeCode']][good['MaterialTicker']] = ExchangeGood(good)

        return self._set_cache(cache_key, exchange_goods)

    def get_max_population(self):
        cache_key = 'max_pops'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        max_pop = {dem: 0 for dem in DEMOGRAPHICS}
        for name, planet in self.get_all_planets().items():
            population = planet.get_population_count().population
            for dem, count in population.items():
                if max_pop[dem] < count:
                    max_pop[dem] = count

        return self._set_cache(cache_key, max_pop)

    def get_population_upkeep(self):
        cache_key = 'population_upkeep'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        from prunpy.utils.resource_list import ResourceList
        rawdata = fio.request("GET", "/global/workforceneeds", cache=60*60*24)
        needs = {entry['WorkforceType'].lower()+'s': ResourceList(entry['Needs']) for entry in rawdata}

        return self._set_cache(cache_key, needs)

    def get_all_recipes(self):
        cache_key = 'all_recipes'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        buildings = self.get_all_buildings()
        recipes = []
        for ticker, building in buildings.items():
            recipes += building.recipes
        
        return self._set_cache(cache_key, recipes)

    # id = "StandardRecipeName" in rawdata
    def get_recipe(self, id):
        cache_key = 'recipe_' + str(id)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        for recipe in self.get_all_recipes():
            if recipe.id == id:
                return self._set_cache(cache_key, recipe)

        # Raise error
        raise Exception(f"Could not find recipe '{id}'")

    def get_material_recipes(self, ticker, include_mining_from_planet_id=None, include_purchase_from=None):
        from prunpy.models.recipe import Recipe
        cache_key = f"material_recipes_{ticker}_mining-{include_mining_from_planet_id}_purchase-{include_purchase_from}"
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        # Find recipes that use the material_ticker
        target_recipes = []
        for recipe in self.get_all_recipes():
            if ticker in recipe.outputs.resources.keys():
                target_recipes.append(recipe)

        if include_mining_from_planet_id:
            planet = self.get_planet(include_mining_from_planet_id)
            for recipe in planet.mining_recipes:
                if ticker in recipe.outputs.resources.keys():
                    target_recipes.append(recipe)
                    break

        if include_purchase_from:
            exchange = self.get_exchange(include_purchase_from)
            buy_price = exchange.get_good(ticker).buy_price
            mult = 100
            purchase_recipe_rawdata = {
                'building': exchange.code,
                'duration': 12,
                'inputs': {exchange.currency: buy_price*mult},
                'outputs': {ticker: 1*mult},
            }
            target_recipes.append(Recipe(purchase_recipe_rawdata))

        return self._set_cache(cache_key, target_recipes)
    
    def get_best_recipe(self, ticker, priority_mode='profit_ratio'):
        cache_key = 'best_recipe_' + str(ticker) + '_' + str(priority_mode)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        target_recipes = self.get_material_recipes(ticker)

        # Pick recipe with highest profit per hour
        best_recipe = None
        for recipe in target_recipes:
            if best_recipe is None:
                best_recipe = recipe

            if priority_mode == 'throughput':
                if recipe.throughput > best_recipe.throughput:
                    best_recipe = recipe
            elif priority_mode == 'profit_amount':
                if recipe.get_profit_per_hour('NC1') > best_recipe.get_profit_per_hour('NC1'):
                    best_recipe = recipe
            elif priority_mode == 'profit_ratio':
                if recipe.get_profit_ratio('NC1') > best_recipe.get_profit_ratio('NC1'):
                    best_recipe = recipe
            else:
                raise ValueError(f"Invalid priority mode: {priority_mode}")

        return self._set_cache(cache_key, best_recipe)

    # Special function to load, prompt, and cache username
    def get_username(self):
        # Load data from ./username.txt, no caching

        exists = os.path.exists('./username.txt')
        # If it exists
        if exists:
            with open('./username.txt', 'r') as f:
                username = f.read().strip()
                if username:
                    return username
                else:
                    pass # Remake file as below if invalid

        # If it doesn't exist
        username = input("Enter your username: ")

        # Prompt to remember username
        remember = input(f"Remember username \"{username}\"? (y/N): ")
        if remember.lower() == 'y':
            with open('./username.txt', 'w') as f:
                f.write(username)
                print(f"Saved username to ./username.txt. Delete that file if you want to reset it.")

        return username

    @property
    def username(self):
        return self.get_username()

    def get_preferred_exchange_code(self):
        # Load data from ./preferred_exchange.txt, no caching

        exists = os.path.exists('./preferred_exchange.txt')
        # If it exists
        if exists:
            with open('./preferred_exchange.txt', 'r') as f:
                preferred_exchange = f.read().strip()
                if preferred_exchange:
                    return preferred_exchange
                else:
                    pass # Remake file as below if invalid

        # If it doesn't exist or otherwise fails to parse
        valid = False
        while not valid:
            preferred_exchange = input("Enter your preferred exchange's code (e.g. NC1): ")
            if preferred_exchange in loader.exchanges.keys():
                valid = True
            else:
                print("Unrecognized exchange code. Please try again.")

        

        # Prompt to remember preferred_exchange
        remember = input(f"Remember preferred exchange \"{preferred_exchange}\"? (y/N): ")
        if remember.lower() == 'y':
            with open('./preferred_exchange.txt', 'w') as f:
                f.write(preferred_exchange)
                print(f"Saved preferred_exchange to ./preferred_exchange.txt. Delete that file if you want to reset it.")

        return preferred_exchange
    
    @property
    def preferred_exchange(self):
        return self.get_exchange(self.get_preferred_exchange_code())
    @property
    def preferred_exchange_code(self):
        return self.get_preferred_exchange_code()

loader = DataLoader()
