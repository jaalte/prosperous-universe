#!/usr/bin/env python3

import json
import math
from fio_api import fio

# Editable global variables
username = "fishmodem"

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

# Create a lookup dictionary for all materials by MaterialId
allmaterials = fio.request("GET", "/material/allmaterials", cache=60*60*24)
material_lookup = {material['MaterialId']: material for material in allmaterials}

allplanets = fio.request("GET", f"/planet/allplanets/full", cache=-1)

class Planet:
    def __init__(self, planet_id):
        self.rawdata = next((planet for planet in allplanets if planet['PlanetId'] == planet_id), {})
        self.name = self.rawdata.get('PlanetName')
        self.id = self.rawdata.get('PlanetId')
        self.identifier = self.rawdata.get('PlanetIdentifier')
        self.resources = {}

        # Process the resources in rawdata
        for resource in self.rawdata.get('Resources', []):
            material_id = resource.get('MaterialId')
            material_data = material_lookup.get(material_id)

            if material_data:
                ticker = material_data['Ticker']
                resource_type = resource.get('ResourceType')
                factor = resource.get('Factor', 0)
                
                for building, info in EXTRACTORS.items():
                    if info["type"] == resource_type:
                        extractor_building = building
                        break
                
                daily_amount = factor * 100 * EXTRACTORS[extractor_building]["multiplier"]
                process_hours, process_amount = self.calculate_process_time_and_amount(extractor_building, daily_amount)

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

    def calculate_process_time_and_amount(self, extractor_building, daily_amount):
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

def threshold_round(value):
    return value


def main():
    

    planets = []
    for planet in allplanets:
        planets.append(Planet(planet_id=planet.get('PlanetId')))
    
    gasses = ['AMM', 'AR', 'F', 'H', 'HE', 'HE3', 'N', 'NE', 'O']

    hits = []
    for planet in planets:
        for ticker in planet.resources:
            resource = planet.resources[ticker]
            if ticker in gasses:
                if resource['type'] == 'LIQUID':
                    if resource['factor'] > 0:
                        hit = {
                            'planet': planet,
                            'resource': resource,
                        }
                        print(f"Liquid {hit['resource']['ticker']:<3} at {hit['resource']['factor']*100:<5.2f} on {hit['planet'].name}")
                        hits.append(hit)
    
    # Sort hits into groups based on resource ticker
    groups = {}
    for hit in hits:
        if hit['resource']['ticker'] not in groups:
            groups[hit['resource']['ticker']] = []
        groups[hit['resource']['ticker']].append(hit)

    # Sort groups by resource factor
    for ticker in groups:
        groups[ticker].sort(key=lambda x: x['resource']['factor'], reverse=True)
    
    # Print groups
    for ticker in groups:
        print(f"\n{ticker} ({groups[ticker][0]['resource']['name']})")
        for hit in groups[ticker]:
            colonized = 'Colonized' if hit['planet'].rawdata['HasAdministrationCenter'] else 'Uncolonized'
            print(f"  {hit['resource']['factor']*100:<5.2f} {hit['planet'].name:<15} {colonized:<10}")
    


if __name__ == "__main__":
    main()
