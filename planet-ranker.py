#!/usr/bin/env python3

import json
import math
#from prunpy import loader, Base, Container
import prunpy as prun

color_scale = prun.terminal_color_scale
terminal_format = prun.terminal_format

MIN_DEMAND = 10000
MAX_JUMPS = 8
MIN_DAILY_INCOME = 4000
MAX_ROI = 100
MIN_PIONEERS = 1000
MAX_COLONIZATION_COST = float('inf') # No limit
PREFERRED_EXCHANGE = 'NC1'
MARKET_SATURATION_THRESHOLD = 0.5

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
    planets = prun.loader.get_all_planets()

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
        nearest_exchange_code, _ = hit['planet'].get_nearest_exchange()
        exchange = prun.loader.get_exchange(nearest_exchange_code)

        hit['exchange'] = exchange

        if hit['planet'].cogc == "RESOURCE_EXTRACTION":
            hit['resource']['daily_amount'] *= 1.25
            hit['resource']['process_hours'] /= 1.25
            hit['cogc_boost'] = True
        else:
            hit['cogc_boost'] = False

        ticker = hit['resource']['ticker']
        good = exchange.get_good(ticker)
        price_per_1000 = good.sell_price_for_amount(1000) or 0
        hit['price'] = price_per_1000 / 1000
        hit['demand'] = good.demand or 0
        hit['daily_traded'] = good.daily_traded

        initial_base = prun.Base(hit['planet'].natural_id,INITIAL_BASE_BUILDINGS[hit['resource']['extractor_building']])
        
        # Anything in initial_base.buildings (a list) with .is_extractor()
        extractor_count = sum(1 for b in initial_base.buildings if b.is_extractor())
        hit['daily_income_per_extractor'] = hit['resource']['daily_amount'] * hit['price']
        hit['daily_income'] = hit['daily_income_per_extractor'] * extractor_count
        hit['daily_units'] = hit['resource']['daily_amount']

        max_base = prun.Base(hit['planet'].natural_id,MAX_BASE_BUILDINGS[hit['resource']['extractor_building']])
        extractor_count_max = sum(1 for b in max_base.buildings if b.is_extractor())
        hit['extractor_count_max'] = extractor_count_max
        hit['max_daily_units'] = hit['resource']['daily_amount']*extractor_count_max
        hit['max_daily_income_area'] = hit['max_daily_units'] * hit['price']

        #material = prun.loader.materials_by_ticker[hit['resource']['ticker']]

        ship_storage = prun.Container(3000,1000)
        max_shipment_units = ship_storage.get_max_capacity_for(hit['resource']['ticker'])
        # 3h per jump, 6h average STL, 4h for user availability
        appx_travel_time = hit['planet'].exchange_distance*3+6+4
        max_throughput_per_hour = max_shipment_units / appx_travel_time/2
        max_throughput_per_day = max_throughput_per_hour*24
        hit['ship_saturation_per_extractor'] = hit['resource']['daily_amount'] / max_throughput_per_day
        hit['max_ship_saturation'] = extractor_count_max * hit['ship_saturation_per_extractor']
        hit['initial_ship_saturation'] = hit['ship_saturation_per_extractor'] *extractor_count

        hit['market_max'] = hit['daily_traded'] * MARKET_SATURATION_THRESHOLD
        if hit['market_max'] > 0:
            hit['market_saturation_per_extractor'] = hit['daily_units'] / hit['market_max']
        else:
            hit['market_saturation_per_extractor'] = float('inf')

        
        #print(f"{hit['planet'].natural_id}-{hit['resource']['ticker']}: {max_shipment_units}, {appx_travel_time}, {max_throughput_per_hour}, {hit['max_ship_saturation']}, {hit['initial_ship_saturation']}")

        expandability = 1/hit['initial_ship_saturation']
        hit['max_extractors_per_ship'] = math.floor(expandability*extractor_count)
        hit['max_income_per_ship'] = hit['max_extractors_per_ship'] * hit['daily_income_per_extractor']
        hit ['max_income_per_ship'] = min(hit['max_income_per_ship'],hit['max_daily_income_area'])

        colony_resource_cost = initial_base.get_construction_materials()
        hit['colonization_cost'] = colony_resource_cost.get_total_value(exchange,'buy')
        if hit['daily_income'] <= 0:
            hit['roi'] = float('inf')
        else:
            hit['roi'] = hit['colonization_cost'] / hit['daily_income']

        max_extractors_ship   = math.floor(100/hit['ship_saturation_per_extractor'])
        max_extractors_market = math.floor(100/hit['market_saturation_per_extractor'])
        max_extractors_area   = extractor_count_max
        max_extractors = min(max_extractors_market, max_extractors_ship, max_extractors_area)
        
        hit['max_extractors'] = max_extractors
        hit['max_income'] = hit['max_extractors'] * hit['daily_income_per_extractor']

        #print(max_extractors, max_extractors_ship, max_extractors_market, max_extractors_area)

        if max_extractors == max_extractors_market:
            hit['limiting_factor'] = "market"
        elif max_extractors == max_extractors_ship:
            hit['limiting_factor'] = "ship"
        else:
            hit['limiting_factor'] = "area"

        if max_extractors_market < 15:
            hit['planet'] = hit['planet'].name
            hit['exchange'] = hit['exchange'].code
            #print(json.dumps(hit, indent=2))


    # Sort all hits by max income per ship
    hits.sort(key=lambda hit: hit['max_income'], reverse=True)

    ### The great filtering

    # Price == 0
    # (Should also include ones with 0 daily income and infinite roi)
    hits = filter_hits(hits, lambda hit: hit['price'] > 0, "no sell orders for their resource")
    
    # Demand < min demand
    #hits = filter_hits(hits, lambda hit: hit['demand'] > MIN_DEMAND, f"demand < {MIN_DEMAND}")
    
    # Exchange != preferred exchange
    #hits = filter_hits(hits, lambda hit: hit['exchange'].ticker == PREFERRED_EXCHANGE, f"not near preferred exchange ({PREFERRED_EXCHANGE})")

    # Exchange distance > max jumps
    hits = filter_hits(hits, lambda hit: hit['planet'].exchange_distance <= MAX_JUMPS, f"exchange distance > {MAX_JUMPS}")
    
    hits = filter_hits(hits, lambda hit: hit['roi'] < MAX_ROI, f"ROI > {MAX_ROI} days")

    # Daily income < min daily income
    #hits = filter_hits(hits, lambda hit: hit['daily_income'] > MIN_DAILY_INCOME, f"projected daily income < {MIN_DAILY_INCOME}")
    
    # Colonization cost > max colonization cost
    #hits = filter_hits(hits, lambda hit: hit['colonization_cost'] <= MAX_COLONIZATION_COST, f"colonization cost > {MAX_COLONIZATION_COST}")

    # No pioneers
    # Do last cause it's sloooow
    hits = filter_hits(hits, lambda hit: hit['planet'].get_population_data()['pioneers']['count'] > MIN_PIONEERS, f"< {MIN_PIONEERS} pioneers")
    

    longest_name = max([len(hit['planet'].name) for hit in hits])

    for hit in hits:
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

        ticker = hit['resource']['ticker']
        price_range = [0,0]
        for code, exchange_object in prun.loader.exchanges.items():
            bid = exchange_object.get_good(ticker).sell_price
            if bid == 0: continue
            if bid < price_range[0]:
                price_range[0] = bid
            if bid > price_range[1]:
                price_range[1] = bid

        factor_range = hit['resource']['factor_range']

        env_complications = len(hit['planet'].get_environment_string().replace(" ", ""))
        env_section = '['+f"{hit['planet'].get_environment_string():<4}"+']'
        cogc_string = 'E' if hit['cogc_boost'] else ''

        exchange = hit['exchange']

        material = prun.loader.get_material(hit['resource']['ticker'])
        ticker_color = material.get_color()
        
        message = (
            f"{color_scale(hit['resource']['factor'], factor_range[0], factor_range[1], '>4.1f', value_override=hit['resource']['daily_amount'])} "
            f"{color_scale(0, 0, 1, '<3', value_override=hit['resource']['ticker'], color_override=ticker_color, bold=True)}/d/{hit['resource']['extractor_building']} @ "
            f"{name_string:<21}"
            f"{color_scale(1,0,1,'<1',value_override=cogc_string)} "
            f"{color_scale(env_complications,0,4,'',value_override=env_section,inverse=True)} "
            f"{hit['planet'].population} "
            f"{color_scale(hit['planet'].exchange_distance,0,6,'>2.0f', inverse=True)}j"
            f"->{exchange.ticker} "
            f"{color_scale(hit['price'], price_range[0], price_range[1], '>3.0f')}{exchange.currency}/u, "
            #f" ({color_scale(hit['demand'],3,5,'>6.0f', logarithmic=True)} demand), "
            f"{color_scale(hit['daily_income'],0,10000,'>5.0f')}"
            f"{exchange.currency}/day. "
            f"{color_scale(hit['colonization_cost'],200000,500000, '>5.0f', inverse=True)}{exchange.currency} investment,"
            f"{color_scale(hit['roi'],1,4,'>5.1f', logarithmic=True, inverse=True)}d ROI, "
            #f"{color_scale(hit['max_daily_units'],0,300,'>4.0f')} max units,"
            #f"{color_scale(hit['ship_saturation_per_extractor']*100,0,100,'>3.0f', inverse=True)}% ship saturation per {hit['resource']['extractor_building']}, "
            f"max {color_scale(max_extractors, 0,1,'>2.0f', value_override=max_extractors)}{hit['resource']['extractor_building']}"
            f"@{color_scale(hit['max_income'],0,50000,'>6.0f')}{exchange.currency}/day/ship, "
            f"limited by {hit['limiting_factor']}"
        )
        print(message)

        hit['planet'] = hit['planet'].name
        hit['exchange'] = hit['exchange'].code
        #print(json.dumps(hit, indent=2))

def filter_hits(hits, condition, message):
    """
    Filters the hits list based on a given condition and prints a summary message.

    Parameters:
    hits (list): The list of hits to be filtered.
    condition (function): A function that returns True for elements to keep.
    message (str): The message describing the filter being applied.

    Returns:
    list: The filtered list of hits.
    """
    prior_count = len(hits)
    hits = [hit for hit in hits if condition(hit)]
    diff = prior_count - len(hits)
    pct = diff / prior_count * 100
    print(f"Removed {diff} ({pct:>.0f}%) hits with {message}")
    return hits

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
    #     formatted_amount = color_scale(i, span[0], span[1], '<2.1f')
    #     print(formatted_amount)
