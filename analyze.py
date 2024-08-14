#!/usr/bin/env python3

import json
import math
from fio_api import fio

# Global variables
USERNAME = "fishmodem"

class Planet:
    def __init__(self, planet_id):
        self.rawdata = fio.request("GET", f"/planet/{planet_id}")
        self.name = self.rawdata.get('PlanetName')
        self.id = self.rawdata.get('PlanetId')
        self.identifier = self.rawdata.get('PlanetIdentifier')

        # Init resources
        allmaterials = fio.request("GET", "/material/allmaterials", cache=60*60*24)
        self.resources = {}

        # Create a lookup dictionary for all materials by MaterialId
        material_lookup = {material['MaterialId']: material for material in allmaterials}

        # Process the resources in rawdata
        for resource in self.rawdata.get('Resources', []):
            material_id = resource.get('MaterialId')
            material_data = material_lookup.get(material_id)

            if material_data:
                ticker = material_data['Ticker']
                resource_type = resource.get('ResourceType')
                factor = threshold_round(resource.get('Factor', 0))
                
                extractor_type = self.get_extractor_type(resource_type)
                daily_amount = self.calculate_daily_amount(resource_type, factor)
                process_hours, process_amount = self.calculate_process_time_and_amount(extractor_type, daily_amount)

                self.resources[ticker] = {
                    'name': material_data['Name'],
                    'ticker': ticker,
                    'category': material_data['CategoryName'],
                    'weight': threshold_round(material_data['Weight']),
                    'volume': threshold_round(material_data['Volume']),
                    'type': resource_type,
                    'factor': factor,
                    'extractor_type': extractor_type,
                    'daily_amount': daily_amount,
                    'process_amount': process_amount,
                    'process_hours': process_hours
                }

    def get_extractor_type(self, resource_type):
        """Determine the extractor type based on the resource type."""
        if resource_type == 'GASEOUS':
            return 'COL'
        elif resource_type == 'LIQUID':
            return 'RIG'
        elif resource_type == 'MINERAL':
            return 'EXT'
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

    def calculate_daily_amount(self, resource_type, factor):
        """Calculate the daily extraction amount based on resource type and factor."""
        if resource_type == 'GASEOUS':
            return (factor * 100) * 0.6
        else:  # LIQUID or MINERAL
            return (factor * 100) * 0.7

    def calculate_process_time_and_amount(self, extractor_type, daily_amount):
        """Calculate the process hours and process amount based on the extractor type."""
        if extractor_type == 'COL':
            base_cycle_time = 6  # hours per cycle
        elif extractor_type == 'RIG':
            base_cycle_time = 4.8  # hours per cycle
        elif extractor_type == 'EXT':
            base_cycle_time = 12  # hours per cycle

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
        return self.name

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
            if resource["extractor_type"] == building_ticker:
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


# Rounds a given value to a specified threshold.
def threshold_round(val, threshold=1e-5):
    for decimal_places in range(15):  # Check rounding from 0 to 14 decimal places
        rounded_value = round(val, decimal_places)
        if abs(val - rounded_value) < threshold:
            return rounded_value
    return val


def main():
    sites = fio.request("GET", f"/sites/{USERNAME}")

    # Create Base objects
    bases = []
    for site_data in sites:
        base = Base(site_data)
        bases.append(base)

    # For debugging: Print a summary of each base
    for base in bases:
        print(f"\n{base}\n")
        #print(json.dumps(base.planet.resources, indent=2))

if __name__ == "__main__":
    main()
