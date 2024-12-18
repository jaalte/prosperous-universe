from prunpy.data_loader import loader
from prunpy.models.planet import Planet
from prunpy.models.population import Population
from prunpy.models.recipe import Recipe
from prunpy.models.recipe_queue import RecipeQueue, RecipeQueueItem
from prunpy.utils.resource_list import ResourceList
from prunpy.constants import DEFAULT_BUILDING_PLANET_NATURAL_ID, HOUSING_SIZES

# A single building of a particular ticker. Not a particular one though.
class Building:
    def __init__(self, ticker, planet=None):

        self.ticker = ticker
        if isinstance(planet, str):
            self.planet = loader.get_planet(planet)
        elif isinstance(planet, Planet):
            self.planet = planet
        elif planet is None:
            self.planet = loader.get_planet(DEFAULT_PLANET_NATURAL_ID)
        else:
            raise Exception(f"Invalid planet type: {type(planet)}")

        for building in loader.allbuildings_raw:
            if building['Ticker'] == ticker:
                self.rawdata = building
                break

        self.area = self.rawdata.get('AreaCost')

        
        if self.ticker in HOUSING_SIZES.keys():
            self.population_demand = Population(HOUSING_SIZES[self.ticker]).invert()
        else:
            self.population_demand = Population({
                'pioneers': self.rawdata.get('Pioneers'),
                'settlers': self.rawdata.get('Settlers'),
                'technicians': self.rawdata.get('Technicians'),
                'engineers': self.rawdata.get('Engineers'),
                'scientists': self.rawdata.get('Scientists'),
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

        self.recipe_queue = RecipeQueue(5)

    def _init_crafter_recipes(self, building_ticker):
        for building in loader.allbuildings_raw:
            if building['Ticker'] == building_ticker:
                rawrecipes = building.get('Recipes', [])
                self.recipes = []
                for rawrecipe in rawrecipes:
                    recipe = Recipe(rawrecipe)
                    self.recipes.append(recipe)

        if self.ticker in ['FRM', 'ORC']:
            if self.planet.environment['fertility'] < 0:
                self.recipes = []
                return
            else:
                for recipe in self.recipes:
                    fertility = self.planet.environment['fertility']
                    recipe.multipliers['fertility'] = fertility


    def _init_extractor_recipes(self, building_ticker):
        self.recipes = []
        for ticker in self.planet.resources:
            resource = self.planet.resources[ticker]

            # Skip resources that aren't for this extractor
            if resource["extractor_building"] == building_ticker:
                recipedata = {
                    'building': building_ticker,
                    'name': f"@{building_ticker}=>{resource['process_amount']}x{ticker}",
                    'raw_duration': resource["process_hours"],
                    'inputs': {},
                    'outputs': {
                        ticker: resource["process_amount"]
                    }
                }
                self.recipes.append(Recipe(recipedata))

    def queue_recipe(self, recipe, order_size=1):
        if not isinstance(recipe, Recipe):
            raise TypeError
        if not isinstance(order_size, int) and not isinstance(order_size, float):
            raise TypeError
        self.recipe_queue.queue_recipe(recipe, order_size)

    # function to get total cost of building by resourcelist
    def get_cost(self, exchange_override=None, include_housing=False):
        from prunpy.data_loader import loader

        materials = self.construction_materials

        if include_housing:
            materials += self.get_population_housing('cost').get_total_materials()

        if exchange_override:
            exchange = loader.get_exchange(exchange_override)
            return materials.get_total_value(exchange_override, "buy")
        else:
            exchange = self.planet.get_nearest_exchange()[0]
            return materials.get_total_value(exchange, "buy")
    
    def get_daily_maintenance(self):
        return self.construction_materials/180

    def get_daily_maintenance_cost(self, exchange=None):
        exchange = exchange or self.planet.get_nearest_exchange()[0]
        return self.get_daily_maintenance.get_total_value(exchange, "buy")

    def get_population_housing(self, priority='cost'):
        return self.population_demand.get_housing_needs(priority)
    def get_housing_needs(self, priority='cost'):
        return self.population_demand.get_housing_needs(priority)

    def is_extractor(self):
        return self.ticker in ['COL', 'RIG', 'EXT']

    def get_cogc_bonus(self, cogc=None):
        if not cogc: return 1.0

        if cogc == self.cogc_type:
            return 1.25

        if cogc.upper() in ['PIONEERS', 'SETTLERS', 'TECHNICIANS', 'ENGINEERS', 'SCIENTISTS']:
            if self.population_demand.get_demographic(cogc.lower()) > 0:
                return 1.1
            else:
                return 1.0

        return 1.0

    def filter_recipes(self, output_tickers=None, input_tickers=None):
        if isinstance(output_tickers, str):
            output_tickers = [output_tickers]
        if isinstance(input_tickers, str):
            input_tickers = [input_tickers]
        if not output_tickers: output_tickers = []
        if not input_tickers: input_tickers = []
        
        matched_recipes = []
        # Filter to recipes whose outputs contain output_tickers wth resourcelist.contains, which accepts a single ticker

        for recipe in self.recipes:
            keep = True
            for ticker in output_tickers:
                if not recipe.outputs.contains(ticker):
                    keep = False
                    continue
            for ticker in input_tickers:
                if not recipe.inputs.contains(ticker):
                    keep = False
                    continue
            if keep:
                matched_recipes.append(recipe)

        return matched_recipes

    def __str__(self):
        return f"{self.ticker}"


class RealBuilding(Building):
    def __init__(self, ticker, planet):
        super().__init__(ticker, planet)