from prunpy.data_loader import loader

from prunpy.models.planet import Planet
from prunpy.models.system import System
from prunpy.models.exchange import Exchange, ExchangeGood
from prunpy.constants import DEMOGRAPHICS, DEFAULT_BUILDING_PLANET_NATURAL_ID

class GameImporter:
    def __init__(self):
        self._cache = {}

    def _get_cached_data(self, key):
        """Retrieve data from cache if available."""
        return self._cache.get(key)

    def _set_cache(self, key, data):
        """Store data in cache."""
        self._cache[key] = data
        return data

    def get_all_planets(self, key='name'):
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

    def get_planet(self, name):
        return self.get_all_planets().get(name)

    def get_all_systems(self):
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

    

importer = GameImporter()
