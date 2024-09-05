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

    def get_all_systems(self):
        cache_key = 'systems'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        systems = {}
        total = len(loader.systemstars_lookup)
        for system_hash in loader.systemstars_lookup.keys():
            system_class = System(system_hash)
            systems[system_class.name] = system_class
        return self._set_cache(cache_key, systems)

    def get_all_buildings(self):
        from prunpy.models.building import Building
        cache_key = 'systems'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        buildings = {}
        for rawbuilding in loader.allbuildings_raw:
            ticker = rawbuilding.get('Ticker')
            planet = Planet(natural_id=DEFAULT_BUILDING_PLANET_NATURAL_ID)
            buildings[ticker] = Building(ticker, planet)

        return self._set_cache(cache_key, buildings)

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

importer = GameImporter()
