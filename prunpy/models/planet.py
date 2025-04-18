from prunpy.api import fio
from prunpy.data_loader import loader
from prunpy.models.population import Population
from prunpy.models.recipe import Recipe
from prunpy.utils.resource_list import ResourceList
from prunpy.constants import EXTRACTORS, PLANET_THRESHOLDS, DEMOGRAPHICS, DEFAULT_BUILDING_PLANET_NATURAL_ID, COGC_COLORS
from prunpy.models.pathfinding import jump_distance
from prunpy.utils.terminal_formatting import terminal_color_scale as color_scale
from prunpy.utils.terminal_formatting import terminal_format

import math
import time
import json

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
        if len(self.rawdata.get('COGCPrograms', [])) > 0:
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
            material = loader.materials_by_hash[material_hash]

            if not material:
                print(f"Warning: Material {material_hash} not found in material lookup")
                continue

            ticker = material.ticker
            resource_type = resource.get('ResourceType')
            factor = resource.get('Factor', 0)

            for building, info in EXTRACTORS.items():
                if info["type"] == resource_type:
                    extractor_building = building
                    break

            daily_amount = factor * 100 * EXTRACTORS[extractor_building]["multiplier"]
            process_hours, process_amount = self._calculate_process_time_and_amount(extractor_building, daily_amount)

            # Deprecated, replaced with Planet.mining_recipes
            self.resources[ticker] = {
                'name': material.name,
                'ticker': ticker,
                'category': material.category_name,
                'weight': material.weight,
                'volume': material.volume,
                'type': resource_type,
                'factor': factor, # Not in Recipe (Shouldn't be but should be accessible somehow)
                'extractor_building': extractor_building,
                'daily_amount': daily_amount, # Not in Recipe
                'process_amount': process_amount,
                'process_hours': process_hours
            }

            self.mining_recipes = []
            recipe_rawdata = {
                'building': extractor_building,
                'raw_duration': process_hours,
                'inputs': {},
                'outputs': {ticker: process_amount}
            }

            self.mining_recipes.append(Recipe(recipe_rawdata))

        # Process environmental properties
        self.environment = {}
        self.environment['temperature'] = self.rawdata.get('Temperature')
        self.environment['pressure'] = self.rawdata.get('Pressure')
        self.environment['gravity'] = self.rawdata.get('Gravity')
        self.environment['fertility'] = float(self.rawdata.get('Fertility'))
        if self.environment['fertility'] != -1.0:
            self.environment['fertility'] *= 10/33


        self.environment_class = {}
        for prop in ['temperature', 'pressure', 'gravity']:
            if self.environment[prop] < PLANET_THRESHOLDS[prop][0]:
                self.environment_class[prop] = 'low'
            elif self.environment[prop] > PLANET_THRESHOLDS[prop][1]:
                self.environment_class[prop] = 'high'
            else:
                self.environment_class[prop] = 'normal'
        self.environment_class['surface'] = self.rawdata.get('Surface')


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

        return process_hours, process_amount

    def get_nearest_exchange(self):
        nearest_distance = 99999999
        nearest_exchange_code = None

        rawexchanges = loader.rawexchanges
        exchanges = {exchange['ComexCode']: exchange['SystemNaturalId'] for exchange in rawexchanges}

        for code, systemid in exchanges.items():
            distance = jump_distance(systemid, self.system_natural_id)
            if distance < nearest_distance:
                nearest_exchange_code = code
                nearest_distance = distance
        self.exchange_code = nearest_exchange_code
        self.exchange_distance = nearest_distance
        return nearest_exchange_code, nearest_distance

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

    @property
    def population(self):
        return self.get_population_count()


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
    
    def get_resource_string(self, separator=', '):
        string = ""
        for ticker, resource in self.resources.items():
            factor_range = resource['factor_range']
            string += f"{color_scale(resource['factor'], factor_range[0], factor_range[1], '', value_override=resource['ticker'])} "
        return string

    def get_building_cost_factor(self):
        area = 25
        mats_here = self.get_building_environment_cost(area)
        mats_ideal = loader.get_planet(DEFAULT_BUILDING_PLANET_NATURAL_ID).get_building_environment_cost(area)

        exchange = self.get_nearest_exchange()[0]

        return mats_here.get_total_value(exchange) / mats_ideal.get_total_value(exchange)

    def shorten_name(self, max_length):
        if len(self.name) > max_length:
            shortened = self.name[:max_length-1].rstrip()
            return shortened + '…'
        else:
            return self.name

    def colorful_name(self, length, format_string):

        if self.cogc in COGC_COLORS:
            color = COGC_COLORS[self.cogc]
        else:
            color = "#888888"

        return terminal_format(self.shorten_name(length), bold=True, color=color, format_spec=format_string)

    def __eq__(self, other):
        return self.natural_id == other.natural_id

    # Make Planet printable
    def __str__(self):
        # Note: Reimplement once Planet.system class is added
        return f"(Planet {self.name} ({self.natural_id}) in the {self.system_natural_id} system)"
