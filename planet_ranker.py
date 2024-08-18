#!/usr/bin/env python3

import json
import math
from fio_api import fio
from pathfinding import jump_distance
import fio_utils as utils

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def fetch_sites(name, planet):
    return name, planet.get_sites()

def main():

    
    gasses = ['AMM', 'AR', 'F', 'H', 'HE', 'HE3', 'N', 'NE', 'O']

    hits = []
    planets = utils.get_all_planets()
    #print(json.dumps(planets["Montem"].rawdata, indent=2))

    # Fetch all planet sites
    # threads = 1
    # with ThreadPoolExecutor(max_workers=threads) as executor:
    #     futures = {executor.submit(fetch_sites, name, planet): name for name, planet in planets.items()}
        
    #     with tqdm(total=len(futures), desc="Fetching planet sites") as pbar:
    #         for future in as_completed(futures):
    #             name, sites = future.result()
    #             # Do something with the result, e.g., storing the sites
    #             pbar.update(1)

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

    hits = []
    for name in planets:
        planet = planets[name]
        for ticker in planet.resources:
            resource = planet.resources[ticker]
            if resource['factor'] > 0:
                hit = {
                    'planet': planet,
                    'resource': resource,
                }
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
        #print(f"\n{ticker} ({groups[ticker][0]['resource']['name']})")
        for hit in groups[ticker]:
            hit['colonized'] = 'Colonized' if hit['planet'].has_infrastructure() else ''
            
            exchange = hit['planet'].get_nearest_exchange()

            hit['price'] = exchange.goods[hit['resource']['ticker']]['Bid'] or 0
            hit['demand'] = exchange.goods[hit['resource']['ticker']]['Demand'] or 0

            hit['daily_income'] = hit['resource']['daily_amount'] * hit['price']

    # Merge all groups items into a single list
    all_hits = []
    for ticker in groups:
        for hit in groups[ticker]:
            if hit['price'] == 0: continue
            if hit['demand'] < 10000: continue
            if hit['planet'].exchange_distance > 4: continue
            if hit['daily_income'] < 4000: continue

            hit['pioneers_available'] = hit['planet'].get_population()['pioneer']['unemployment_amount']
            if hit['pioneers_available'] < 1000: continue

            all_hits.append(hit)

    # Sort all hits by daily profit
    all_hits.sort(key=lambda x: x['daily_income'], reverse=True)

    for hit in all_hits:
        exchange = hit['planet'].get_nearest_exchange()

        print(f"  {hit['resource']['factor']*100:<5.2f} {hit['resource']['ticker']:<3} @ {hit['planet'].name:<15} {hit['colonized']:<10} {hit['planet'].get_environment_string():<7} {hit['planet'].exchange_distance:>2} jumps from {exchange.ticker} with {hit['price']:>3.0f} {exchange.currency} bid price ({hit['demand']:>7} demand), {hit['daily_income']:>5.0f} {exchange.currency}/day/{hit['resource']['extractor_building']}")

if __name__ == "__main__":
    main()
