from prunpy.api import fio
from prunpy.constants import DEFAULT_BUILDING_PLANET_NATURAL_ID, DEMOGRAPHICS

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

        materials_by_ticker = {material['Ticker']: Material(material) for material in self.materials_raw}
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
        cache_key = 'planets'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        planets = {}
        total = len(loader.allplanets)
        for i, planet in enumerate(loader.allplanets):
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

        return self._set_cache(cache_key, planets)

    def get_planet(self, name_string):
        planet_names = list(self.get_all_planets('name').keys())
        planet_ids   = list(self.get_all_planets('natural_id').keys())

        # Create lowercase mappings for case-insensitive lookup
        lc_names = {name.lower(): name for name in planet_names}
        lc_ids   = {planet_id.lower(): planet_id for planet_id in planet_ids}

        # Lowercase the input for case-insensitive comparison
        lc_name_string = name_string.lower()

        if lc_name_string in lc_names:
            original_name = lc_names[lc_name_string]
            return self.get_all_planets('name')[original_name]
        elif lc_name_string in lc_ids:
            original_id = lc_ids[lc_name_string]
            return self.get_all_planets('natural_id')[original_id]
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

    def get_exchange(self, code):
        cache_key = 'exchange_' + str(code)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        exchange = self.exchanges[code]
        return self._set_cache(cache_key, exchange)

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

    def get_all_recipes(self):
        cache_key = 'all_recipes'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        buildings = self.get_all_buildings()
        recipes = []
        for ticker, building in buildings.items():
            recipes += building.recipes
        
        return self._set_cache(cache_key, recipes)

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

loader = DataLoader()