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
MIN_PIONEERS = 1000
MAX_COLONIZATION_COST = 999999999999 # Large but not infinite

GASSES = ['AMM', 'AR', 'F', 'H', 'HE', 'HE3', 'N', 'NE', 'O']

INITIAL_BASE_BUILDINGS = {
    'COL': {'HB1': 2,'COL': 4},
    'RIG': {'HB1': 2,'RIG': 6},
    'EXT': {'HB1': 2,'EXT': 3},
}

MAX_BASE_BUILDINGS = {
    'COL': {'HB1': 12,'COL': 23},
    'RIG': {'HB1': 11,'RIG': 36},
    'EXT': {'HB1': 9,'EXT': 15},
}

def fetch_sites(name, planet):
    return name, planet.get_sites()

def main():
    planets = utils.get_all_planets()

    # First pass: filter to only profitable routes
    hits = []
    for name, planet in planets.items():
        for ticker in planet.resources:
            resource = planet.resources[ticker]
            if resource['factor'] > 0:
                hit = {
                    'planet': planet,
                    'resource': resource,
                }
                hits.append(hit)

    # Populate price-based properties
    for hit in hits:
        exchange = hit['planet'].get_nearest_exchange()

        if hit['planet'].cogc == "ADVERTISING_RESOURCE_EXTRACTION":
            hit['resource']['daily_amount'] *= 1.25
            hit['resource']['process_hours'] /= 1.25
            hit['cogc_boost'] = True
        else:
            hit['cogc_boost'] = False

        hit['price'] = exchange.goods[hit['resource']['ticker']]['Bid'] or 0
        hit['demand'] = exchange.goods[hit['resource']['ticker']]['Demand'] or 0

        initial_base = utils.Base(hit['planet'].natural_id,INITIAL_BASE_BUILDINGS[hit['resource']['extractor_building']])
        
        # Anything in initial_base.buildings (a list) with .is_extractor()
        extractor_count = sum(1 for b in initial_base.buildings if b.is_extractor())
        hit['daily_income_per_extractor'] = hit['resource']['daily_amount'] * hit['price']
        hit['daily_income'] = hit['daily_income_per_extractor'] * extractor_count

        max_base = utils.Base(hit['planet'].natural_id,MAX_BASE_BUILDINGS[hit['resource']['extractor_building']])
        extractor_count_max = sum(1 for b in max_base.buildings if b.is_extractor())
        hit['extractor_count_max'] = extractor_count_max
        max_daily_units = hit['resource']['daily_amount']*extractor_count_max
        hit['max_daily_units'] = max_daily_units
        hit['max_daily_income'] = max_daily_units * hit['price']

        #material = utils.loader.materials_by_ticker[hit['resource']['ticker']]

        ship_storage = utils.Container(500,500)
        max_shipment_units = ship_storage.get_max_capacity_for(hit['resource']['ticker'])
        # 3h per jump, 6h average STL, 4h for user availability
        appx_travel_time = hit['planet'].exchange_distance*3+6+4
        max_throughput_per_hour = max_shipment_units / appx_travel_time/2
        max_throughput_per_day = max_throughput_per_hour*24
        hit['max_ship_saturation'] = max_daily_units / max_throughput_per_day
        hit['initial_ship_saturation'] = hit['resource']['daily_amount']*extractor_count / max_throughput_per_day
        
        #print(f"{hit['planet'].natural_id}-{hit['resource']['ticker']}: {max_shipment_units}, {appx_travel_time}, {max_throughput_per_hour}, {hit['max_ship_saturation']}, {hit['initial_ship_saturation']}")

        expandability = 1/hit['initial_ship_saturation']
        hit['max_extractors_per_ship'] = math.floor(expandability*extractor_count)
        hit['max_income_per_ship'] = hit['max_extractors_per_ship'] * hit['daily_income_per_extractor']
        hit ['max_income_per_ship'] = min(hit['max_income_per_ship'],hit['max_daily_income'])

        colony_resource_cost = initial_base.get_construction_materials()
        hit['colonization_cost'] = colony_resource_cost.get_total_value(exchange,'buy')
        if hit['daily_income'] <= 0:
            hit['roi'] = float('inf')
        else:
            hit['roi'] = hit['colonization_cost'] / hit['daily_income']

        

    # Sort all hits by daily profit
    hits.sort(key=lambda x: x['roi'])

    # The great filtering
    # Price == 0
    # (Should also include ones with 0 daily income and infinite roi)
    prior_count = len(hits)
    hits = [hit for hit in hits if hit['price'] > 0]
    print(f"Removed {prior_count-len(hits)} hits with no sell orders for their resource")
    
    # Demand < min demand
    prior_count = len(hits)
    hits = [hit for hit in hits if hit['demand'] > MIN_DEMAND]
    print(f"Removed {prior_count-len(hits)} planets with demand < {MIN_DEMAND}")
    
    # Exchange distance > max jumps
    prior_count = len(hits)
    hits = [hit for hit in hits if hit['planet'].exchange_distance <= MAX_JUMPS]
    print(f"Removed {prior_count-len(hits)} planets with exchange distance > {MAX_JUMPS}")
    
    # Daily income < min daily income
    prior_count = len(hits)
    hits = [hit for hit in hits if hit['daily_income'] > MIN_DAILY_INCOME]
    print(f"Removed {prior_count-len(hits)} planets with projected daily income < {MIN_DAILY_INCOME}")
    
    # Colonization cost > max colonization cost
    prior_count = len(hits)
    hits = [hit for hit in hits if hit['colonization_cost'] <= MAX_COLONIZATION_COST]
    print(f"Removed {prior_count-len(hits)} planets with colonization cost > {MAX_COLONIZATION_COST}")

    # No pioneers
    # Do last cause it's sloooow
    prior_count = len(hits)
    hits = [hit for hit in hits if hit['planet'].get_population_data()['pioneers']['count'] > 1000]
    print(f"Removed {prior_count-len(hits)} planets with < {MIN_PIONEERS} pioneers")
    

    longest_name = max([len(hit['planet'].name) for hit in hits])

    for hit in hits:
        exchange = hit['planet'].get_nearest_exchange()

        name_string = f"{hit['planet'].natural_id}"
        shortened_name = ''
        if hit['planet'].natural_id != hit['planet'].name:
            MAX_NAME_LENGTH = 9
            if len(hit['planet'].name) > MAX_NAME_LENGTH:
                shortened_name = (hit['planet'].name+" "*MAX_NAME_LENGTH)[:MAX_NAME_LENGTH].strip()+'…'
            else:
                shortened_name = hit['planet'].name

        if shortened_name:
            name_string = f"{name_string} ({shortened_name+')':<10}"

        price_range = [0,0]
        for code, exchange_object in utils.get_all_exchanges().items():
            if hit['resource']['ticker'] in exchange_object.goods:
                bid = exchange_object.goods[hit['resource']['ticker']]['Bid']
                if not bid or bid == 0: continue
                if bid < price_range[0]:
                    price_range[0] = bid
                if bid > price_range[1]:
                    price_range[1] = bid

        factor_range = hit['resource']['factor_range']

        env_complications = len(hit['planet'].get_environment_string().replace(" ", ""))
        env_section = '['+f"{hit['planet'].get_environment_string():<4}"+']'
        cogc_string = 'E' if hit['cogc_boost'] else ''


        max_extractors = min(hit['max_extractors_per_ship'], hit['extractor_count_max'])
        max_extractor_fulfilment = max_extractors / hit['extractor_count_max']

        message = (
            f"{color(hit['resource']['factor'], factor_range[0], factor_range[1], '>4.1f', value_override=hit['resource']['daily_amount'])} "
            f"{hit['resource']['ticker']:<3}/d/{hit['resource']['extractor_building']} @ "
            f"{name_string:<21}"
            f"{color(1,0,1,'<1',value_override=cogc_string)} "
            f"{color(env_complications,0,4,'',value_override=env_section,inverse=True)} "
            f"{color(hit['planet'].exchange_distance,0,6,'>2.0f', inverse=True)}j"
            f"->{exchange.ticker} "
            f"{color(hit['price'], price_range[0], price_range[1], '>3.0f')}{exchange.currency}/u"
            f" ({color(hit['demand'],3,5,'>6.0f', logarithmic=True)} demand), "
            f"{color(hit['daily_income'],0,5000,'>5.0f')}"
            f"{exchange.currency}/day. "
            f"{color(hit['colonization_cost'],200000,500000, '>5.0f', inverse=True)}{exchange.currency} investment,"
            f"{color(hit['roi'],1,4,'>5.1f', logarithmic=True, inverse=True)}d ROI, "
            #f"{color(hit['max_daily_units'],0,300,'>4.0f')} max units,"
            f"{color(hit['initial_ship_saturation']*100,0,100,'>2.0f', inverse=True)}% ship saturation, "
            f"max {color(max_extractor_fulfilment, 0,1,'>2.0f', value_override=max_extractors)}{hit['resource']['extractor_building']}"
            f"@{color(hit['max_income_per_ship'],0,100000,'>6.0f')}{exchange.currency}/day/ship"
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

    # print(abbreviate(106292))      # "106K"
    # print(abbreviate(1251))        # "1.2K"
    # print(abbreviate(151))         # "151"
    # print(abbreviate(123456789))   # "123M"
    # print(abbreviate(23456789))    # "23M"
    # print(abbreviate(3456789))     # "3.4M"
    main()

    # span = (0, 50)
    # diff = span[1] - span[0]
    # for i in range(span[0]-2*diff, span[1]+2*diff):
    #     formatted_amount = color(i, span[0], span[1], '<2.1f')
    #     print(formatted_amount)
