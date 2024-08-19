#!/usr/bin/env python3

import json
import math
from fio_api import fio
from pathfinding import jump_distance
import fio_utils as utils

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

INITIAL_BASES = {
    'COL':
        {
            # Core, 2 HB1, 4 COL
            'materials': '8 BBH, 4 BDE, 68 BSE, 1 BTA, 4 LDE, 4 LSE, 4 LTA, 12 PSL, 8 TRU',
            'area': 105,
            'building_count': 7,
            'population': 200,
        },
    'RIG':
        {
            # Core, 2 HB1, 6 RIG
            'materials': '8 BBH, 4 BDE, 76 BSE, 2 BTA, 4 LDE, 4 LSE, 4 LTA, 12 PSL, 8 TRU',
            'area': 105,
            'building_count': 9,
            'population': 180,
        },
    'EXT':
        {
            # Core, 2 HB1, 3 EXT
            'materials': '8 BBH, 4 BDE, 52 BSE, 2 BTA, 4 LDE, 4 LSE, 4 LTA, 12 PSL, 8 TRU',
            'area': 120,
            'building_count': 6,
            'population': 180
        },
}

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
            if hit['daily_income'] == 0: continue

            #normal_base_resources = utils.ResourceList(utils.BASE_CORE_MIN_RESOURCES)
            #base_resources = utils.ResourceList(hit['planet'].rawdata['BuildRequirements'])
            #extra_resources = base_resources - normal_base_resources

            initial_base = INITIAL_BASES[hit['resource']['extractor_building']]
            colony_resource_cost = utils.ResourceList(initial_base['materials'])

            colony_resource_cost += hit['planet'].get_building_environment_cost(initial_base['area'])
            for i in range(1, initial_base['building_count']-1):
                colony_resource_cost += hit['planet'].get_building_environment_cost(0)

            hit['colonization_cost'] = colony_resource_cost.get_total_value(exchange,'buy')
            hit['roi'] = hit['colonization_cost'] / hit['daily_income']

    # Merge all groups items into a single list
    all_hits = []
    for ticker in groups:
        for hit in groups[ticker]:
            if hit['price'] == 0: continue
            if hit['demand'] < 10000: continue
            if hit['planet'].exchange_distance > 4: continue
            if hit['daily_income'] < 4000: continue
            if hit['colonization_cost'] == float('inf'): continue

            hit['pioneers_available'] = hit['planet'].get_population()['pioneer']['unemployment_amount']
            if hit['pioneers_available'] < 1000: continue

            all_hits.append(hit)

    # Sort all hits by daily profit
    all_hits.sort(key=lambda x: x['roi'])

    for hit in all_hits:
        exchange = hit['planet'].get_nearest_exchange()

        message = (
            f"{color(hit['resource']['daily_amount'], 0, 50, '<2.1f')} "
            f"{hit['resource']['ticker']:<3}/d @ "
            f"{hit['planet'].name:<15} {hit['colonized']:<10} {hit['planet'].get_environment_string():<7} "
            f"{hit['planet'].exchange_distance:>2} jumps from {exchange.ticker} with "
            f"{hit['price']:>3.0f} {exchange.currency} bid price ({hit['demand']:>7} demand), "
            f"{hit['daily_income']:>5.0f} {exchange.currency}/day/{hit['resource']['extractor_building']}. "
            f"{hit['colonization_cost']:>5.0f} {exchange.currency} investment, {hit['roi']:>4.1f}d ROI"
        )
        print(message)

        #print(f"{hit['resource']['daily_amount']:<2.1f} {hit['resource']['ticker']:<3}/d @ {hit['planet'].name:<15} {hit['colonized']:<10} {hit['planet'].get_environment_string():<7} {hit['planet'].exchange_distance:>2} jumps from {exchange.ticker} with {hit['price']:>3.0f} {exchange.currency} bid price ({hit['demand']:>7} demand), {hit['daily_income']:>5.0f} {exchange.currency}/day/{hit['resource']['extractor_building']}. {hit["colonization_cost"]:>5.0f} {exchange.currency} investment, {hit['roi']:>4.1f}d ROI")

def color(value, min_value, max_value, format_spec):
    """
    Applies color to the formatted value based on the given range and color map.
    Supports coloration for values outside the min and max range.
    """
    # Define the color map with positions and corresponding colors
    color_map = {
        -1: (40, 40, 40),           # Dark gray for values far below min
        0: (255, 0, 0),             # Red at min
        0.25: (255, 165, 0),        # Orange
        0.5: (255, 255, 0),         # Yellow
        0.75: (0, 255, 0),          # Green
        1: (0, 255, 255),           # Cyan at max
        2: (255, 0, 255),           # Magenta for values far above max
    }

    # Calculate the span and normalized value key
    span = max_value - min_value
    normalized_value = (value - min_value) / span

    # Clamp normalized_value to the min and max keys in color_map
    min_key = min(color_map.keys())
    max_key = max(color_map.keys())

    if normalized_value < min_key:
        normalized_value = min_key
    elif normalized_value > max_key:
        normalized_value = max_key

    # Get the two keys to interpolate between
    sorted_keys = sorted(color_map.keys())
    
    lower_key = max(k for k in sorted_keys if k <= normalized_value)
    upper_key = min(k for k in sorted_keys if k >= normalized_value)

    if lower_key == upper_key:
        r, g, b = color_map[lower_key]
    else:
        # Interpolate between the lower and upper color
        lower_color = color_map[lower_key]
        upper_color = color_map[upper_key]
        segment_ratio = (normalized_value - lower_key) / (upper_key - lower_key)
        
        r = int(lower_color[0] + (upper_color[0] - lower_color[0]) * segment_ratio)
        g = int(lower_color[1] + (upper_color[1] - lower_color[1]) * segment_ratio)
        b = int(lower_color[2] + (upper_color[2] - lower_color[2]) * segment_ratio)

    # Format the value using the specified format
    formatted_value = format(value, format_spec)
    
    # Apply color using ANSI escape codes for RGB
    colored_value = f"\033[38;2;{r};{g};{b}m{formatted_value}\033[0m"
    
    return colored_value

if __name__ == "__main__":
    main()

    # span = (0, 50)
    # diff = span[1] - span[0]
    # for i in range(span[0]-2*diff, span[1]+2*diff):
    #     formatted_amount = color(i, span[0], span[1], '<2.1f')
    #     print(formatted_amount)
