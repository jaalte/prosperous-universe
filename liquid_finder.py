#!/usr/bin/env python3

import json
import math
from fio_api import fio
from pathfinding import jump_distance
import fio_utils as utils

def main():

    
    gasses = ['AMM', 'AR', 'F', 'H', 'HE', 'HE3', 'N', 'NE', 'O']

    hits = []
    planets = utils.get_all_planets()
    for name in planets:
        planet = planets[name]
        for ticker in planet.resources:
            resource = planet.resources[ticker]
            if ticker in gasses:
                if resource['type'] == 'LIQUID':
                    if resource['factor'] > 0:
                        hit = {
                            'planet': planet,
                            'resource': resource,
                        }
                        #print(f"Liquid {hit['resource']['ticker']:<3} at {hit['resource']['factor']*100:<5.2f} on {hit['planet'].name}")
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
            exchange = hit['planet'].get_nearest_exchange()
            print(f"  {hit['resource']['factor']*100:<5.2f} {hit['planet'].name:<15} {colonized:<11}: {exchange['Distance']:<2} jumps from {exchange['Ticker']}")
    
if __name__ == "__main__":
    main()
