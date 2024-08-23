#!/usr/bin/env python3

import json
import math
from fio_api import fio
from pathfinding import jump_distance
import fio_utils as utils

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

MIN_DEMAND = 10000
MAX_JUMPS = 4
MIN_DAILY_INCOME = 4000
MAX_COLONIZATION_COST = float('inf')
MIN_PIONEERS = 1000

GASSES = ['AMM', 'AR', 'F', 'H', 'HE', 'HE3', 'N', 'NE', 'O']

INITIAL_BASE_BUILDINGS = {
    'COL': {'HB1': 2,'COL': 4},
    'RIG': {'HB1': 2,'RIG': 6},
    'EXT': {'HB1': 2,'EXT': 3},
}

def fetch_sites(name, planet):
    return name, planet.get_sites()

def main():
    planets = utils.get_all_planets()

    # First pass: filter to only profitable routes
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
    
    count = len(hits)
    print(count)
    # Print groups
    for ticker in groups:
        #print(f"\n{ticker} ({groups[ticker][0]['resource']['name']})")
        for hit in groups[ticker]:
            #hit['colonized'] = hit['planet'].get_population()['pioneers']['count'] > 0
            
            exchange = hit['planet'].get_nearest_exchange()

            hit['price'] = exchange.goods[hit['resource']['ticker']]['Bid'] or 0
            hit['demand'] = exchange.goods[hit['resource']['ticker']]['Demand'] or 0

            hit['daily_income'] = hit['resource']['daily_amount'] * hit['price']
            if hit['daily_income'] <= 0: continue

            initial_base = utils.Base(hit['planet'].natural_id,INITIAL_BASE_BUILDINGS[hit['resource']['extractor_building']])
            colony_resource_cost = initial_base.get_construction_materials()
            hit['colonization_cost'] = colony_resource_cost.get_total_value(exchange,'buy')
            hit['roi'] = hit['colonization_cost'] / hit['daily_income']
    print(f"Removed {count-len(hits)} unprofitable planets")

    # Merge all groups items into a single list
    all_hits = []
    for ticker in groups:
        for hit in groups[ticker]:
            #if hit['price'] == 0: continue
            #if hit['demand'] <= MIN_DEMAND: continue
            #if hit['planet'].exchange_distance > MAX_JUMPS: continue
            #if hit['daily_income'] <= MIN_DAILY_INCOME: continue
            #if hit['colonization_cost'] >= MAX_COLONIZATION_COST: continue

            # Done after filtering to reduce api calls
            #hit['pioneers_available'] = hit['planet'].get_population()['pioneers']['unemployment_amount']
            #if hit['pioneers_available'] < MIN_PIONEERS: continue

            all_hits.append(hit)

    # Sort all hits by daily profit
    all_hits.sort(key=lambda x: x['roi'])

    # The great filtering
    # Price == 0
    prior_count = len(all_hits)
    all_hits = [hit for hit in all_hits if hit['price'] > 0]
    print(f"Removed {prior_count-len(all_hits)} planets with unavailable build materials")
    
    # Demand < min demand
    prior_count = len(all_hits)
    all_hits = [hit for hit in all_hits if hit['demand'] > MIN_DEMAND]
    print(f"Removed {prior_count-len(all_hits)} planets with demand < {MIN_DEMAND}")
    
    # Exchange distance > max jumps
    prior_count = len(all_hits)
    all_hits = [hit for hit in all_hits if hit['planet'].exchange_distance <= MAX_JUMPS]
    print(f"Removed {prior_count-len(all_hits)} planets with exchange distance > {MAX_JUMPS}")
    
    # Daily income < min daily income
    prior_count = len(all_hits)
    all_hits = [hit for hit in all_hits if hit['daily_income'] > MIN_DAILY_INCOME]
    print(f"Removed {prior_count-len(all_hits)} planets with daily income < {MIN_DAILY_INCOME}")
    
    # Colonization cost > max colonization cost
    prior_count = len(all_hits)
    all_hits = [hit for hit in all_hits if hit['colonization_cost'] <= MAX_COLONIZATION_COST]
    print(f"Removed {prior_count-len(all_hits)} planets with colonization cost > {MAX_COLONIZATION_COST}")

    # No pioneers
    prior_count = len(all_hits)
    all_hits = [hit for hit in all_hits if hit['planet'].get_population()['pioneers']['count'] > 1000]
    print(f"Removed {prior_count-len(all_hits)} planets with < {MIN_PIONEERS} pioneers")
    

    longest_name = max([len(hit['planet'].name) for hit in all_hits])

    for hit in all_hits:
        exchange = hit['planet'].get_nearest_exchange()

        price_range = [0,0]
        for code, exchange in utils.get_all_exchanges().items():
            if hit['resource']['ticker'] in exchange.goods:
                bid = exchange.goods[hit['resource']['ticker']]['Bid']
                if not bid or bid == 0: continue
                if bid < price_range[0]:
                    price_range[0] = bid
                if bid > price_range[1]:
                    price_range[1] = bid

        factor_range = hit['resource']['factor_range']

        env_complications = len(hit['planet'].get_environment_string().replace(" ", ""))
        env_section = '['+f"{hit['planet'].get_environment_string():<4}"+']'

        message = (
            f"{color(hit['resource']['factor'], factor_range[0], factor_range[1], '>4.1f', value_override=hit['resource']['daily_amount'])} "
            f"{hit['resource']['ticker']:<3}/d/e @ "
            f"{format(hit['planet'].name,'<'+str(longest_name))} "
            f"{color(env_complications,0,4,'',value_override=env_section,inverse=True)} "
            f"{color(hit['planet'].exchange_distance,0,6,'>2.0f', inverse=True)}j"
            f"->{exchange.ticker} "
            f"{color(hit['price'], price_range[0], price_range[1], '>3.0f')}{exchange.currency}/u"
            f" ({color(hit['demand'],3,5,'>5.0f', logarithmic=True)} demand), "
            f"{color(hit['daily_income'],0,5000,'>5.0f')}"
            f"{exchange.currency}/day/{hit['resource']['extractor_building']}. "
            f"{color(hit['colonization_cost'],200000,500000, '>5.0f', inverse=True)}{exchange.currency} investment, "
            f"{color(hit['roi'],1,4,'>4.1f', logarithmic=True, inverse=True)}d ROI"
        )
        print(message)

def color(value, min_value, max_value, format_spec, value_override=None, inverse=False, logarithmic=False):
    """
    Applies color to the formatted value based on the given range and color map.
    Supports coloration for values outside the min and max range.
    If 'inverse' is True or if min_value > max_value, the colors are applied in reverse.
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

    # Handle inverse logic by reversing the mapping
    if min_value > max_value:
        inverse = not inverse
    if inverse:
        min_value, max_value = min(max_value, min_value), max(max_value, min_value)
        color_map = {
            -1: color_map[2],     
            0: color_map[1],      
            0.25: color_map[0.75],
            0.5: color_map[0.5],  
            0.75: color_map[0.25],
            1: color_map[0],      
            2: color_map[-1],     
        }
    
    # Apply logarithmic scaling if requested
    placement_value = value
    if logarithmic:
        placement_value = math.log10(value)
    
    # Calculate the span and normalized value key
    span = max_value - min_value
    normalized_value = (placement_value - min_value) / span

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

    if value_override is not None:
        value = value_override

    # Format the value using the specified format
    formatted_value = format(value, format_spec)
    
    # Apply color using ANSI escape codes for RGB
    colored_value = f"\033[38;2;{r};{g};{b}m{formatted_value}\033[0m"
    
    return colored_value

def abbreviate(value):
    suffixes = {
        3: 'K',
        6: 'M',
        9: 'B',
        12: 'T',
        15: 'Q'
    }
    
    # Handle the case for values less than 1000
    if value < 1000:
        return str(value)
    
    magnitude = len(str(value)) - 1
    base_magnitude = (magnitude // 3) * 3
    suffix = suffixes.get(base_magnitude, '')

    scaled_value = value / 10**base_magnitude
    
    #print(f"Value: {value}, Magnitude: {magnitude}, Base Magnitude: {base_magnitude}, Suffix: {suffix}, Scaled Value: {scaled_value}")

    # Determine the correct format based on the magnitude
    if magnitude % 3 == 0:
        return f"{int(scaled_value)}{suffix}"
    elif magnitude % 3 == 1:
        return f"{scaled_value:.1f}{suffix}".rstrip('0').rstrip('.')
    else:
        return f"{int(scaled_value)}{suffix}"

if __name__ == "__main__":

    print(abbreviate(106292))      # "106K"
    print(abbreviate(1251))        # "1.2K"
    print(abbreviate(151))         # "151"
    print(abbreviate(123456789))   # "123M"
    print(abbreviate(23456789))    # "23M"
    print(abbreviate(3456789))     # "3.4M"
    main()

    # span = (0, 50)
    # diff = span[1] - span[0]
    # for i in range(span[0]-2*diff, span[1]+2*diff):
    #     formatted_amount = color(i, span[0], span[1], '<2.1f')
    #     print(formatted_amount)
