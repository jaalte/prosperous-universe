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
        return loader.get_all_planets(key)

    def get_planet(self, name_string):
        return loader.get_planet(name_string)


    def get_all_systems(self):
        return loader.get_all_systems()

    def get_all_buildings(self, planet_id=DEFAULT_BUILDING_PLANET_NATURAL_ID):
        return loader.get_all_buildings(planet_id)

    def get_building(self, ticker, planet_id=DEFAULT_BUILDING_PLANET_NATURAL_ID):
        return loader.get_building(ticker, planet_id)

    def get_all_exchanges(self):
        return loader.get_all_exchanges()

    @property
    def exchanges(self):
        return loader.get_all_exchanges()

    def get_exchange_goods(self):
        return loader.get_exchange_goods()

    def get_exchange(self, code):
        return loader.get_exchange(code)

    def get_max_population(self):
        return loader.get_max_population()

    def get_all_recipes(self):
        return loader.get_all_recipes()

    def get_material_recipes(self, ticker, include_mining_from_planet_id=None, include_purchase_from=None):
        return loader.get_material_recipes(ticker, include_mining_from_planet_id, include_purchase_from)
    
    def get_best_recipe(self, ticker, priority_mode='profit_ratio'):
        return loader.get_best_recipe(ticker, priority_mode)

    

importer = GameImporter()
