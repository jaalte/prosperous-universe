from prunpy.data_loader import loader
from prunpy.models.planet import Planet
from prunpy.models.population import Population
from prunpy.models.recipe import Recipe
from prunpy.utils.resource_list import ResourceList

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
    def get_cost(self, exchange=None):
        exchange = exchange or self.planet.get_nearest_exchange()[0]
        return self.construction_materials.get_total_value(exchange, "buy")
    
    def get_daily_maintenance(self):
        return self.construction_materials/180

    def get_daily_maintenance_cost(self, exchange=None):
        exchange = exchange or self.planet.get_nearest_exchange()[0]
        return self.get_daily_maintenance.get_total_value(exchange, "buy")

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
