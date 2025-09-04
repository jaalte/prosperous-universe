import prunpy
import re
import pyperclip
import json
from prunpy import strip_terminal_formatting

def main():
    prompt_user()



def prompt_user():
    print("Enter the name or natural ID of the planet you're building on (Assumes terran world if blank):")
    planet_string = input("> ")
    if not planet_string:
        planet_string = prunpy.constants.DEFAULT_BUILDING_PLANET_NATURAL_ID 
    planet = prunpy.loader.get_planet(planet_string)
    
    buildings = prompt_buildings(planet)
    resources = prompt_resources()

    total = resources + buildings.get_total_materials()

    print("Enter the code of the exchange you want to use (Blank for nearest):")
    exchange_code = input("> ")
    if exchange_code not in ["NC1", "AI1", "CI1", "IC1", "NC2", "CI2"]:
        exchange_code = planet.get_nearest_exchange()[0]
        print("Using nearest exchange: " + exchange_code)
    exchange = prunpy.loader.get_exchange(exchange_code)

    name = "Buy "
    if len(buildings.buildings):
        name += f"{buildings} "
    if len(resources.resources):
        name += f"{resources} "
    name += f"from {exchange_code}"
    # Remove commas and replace spaces with dashes
    name = re.sub(r',', '', name).replace(' ', '-')
    name = strip_terminal_formatting(name)

    action = prunpy.XITAction(name, total, exchange_code, True)
    output = json.dumps(action.json, indent=4)

    pyperclip.copy(output)

    print("Action copied to clipboard! Ensure you have a warehouse at the specified exchange before running.")

    print(
        f"Total cost estimated at \n{total.get_total_value(exchange_code, 'buy'):.0f} {exchange.currency},\n"
        f"{total.weight:.2f} weight, and\n"
        f"{total.volume:.2f} volume."
    )





def prompt_buildings(planet):
    success = False
    
    # Get all valid building tickers from the prunpy loader
    all_building_tickers = prunpy.loader.get_all_buildings(planet).keys()
    
    while not success:
        print("Enter a list of building codes, eg \"HB2, 2 CHP, 3 CLF\" (Blank for none)")
        building_string = input("> ")
        if not building_string:
            buildings = prunpy.BuildingList({}, planet)
            success = True
            break
        try:
            building_dict = parse_building_string(building_string, all_building_tickers)
            success = True
            buildings = prunpy.BuildingList(building_dict, planet)
            print(f"Parsed buildings: {buildings}")
            print(f"Materials needed: {buildings.get_total_materials()}")
        except ValueError as e:
            print(f"Error: {e}")
    
    return prunpy.BuildingList(buildings, planet)



def parse_building_string(building_string, valid_tickers):
    building_dict = {}
    pattern = '|'.join(re.escape(ticker) for ticker in sorted(valid_tickers, key=len, reverse=True))
    matches = list(re.finditer(f'({pattern})', building_string))
    
    if not matches:
        raise ValueError("No valid building tickers found in input.")
    
    last_index = 0
    for match in matches:
        ticker = match.group(1)
        start, end = match.span()
        count_str = building_string[last_index:start].strip()
        
        # Determine the count, default to 1 if no count is specified
        count = 1
        if count_str:
            count_digits = ''.join([char for char in count_str if char.isdigit()])
            count = int(count_digits) if count_digits else 1
        
        # Add the ticker and its count to the dictionary
        if ticker in building_dict:
            building_dict[ticker] += count
        else:
            building_dict[ticker] = count
        
        last_index = end
    
    # Handle any remaining part of the string after the last ticker
    count_str = building_string[last_index:].strip()
    if count_str:
        raise ValueError(f"Unexpected input after last ticker: '{count_str}'")
    
    # Validate tickers
    for ticker in building_dict.keys():
        if ticker not in valid_tickers:
            raise ValueError(f"Invalid building ticker: '{ticker}'")
    
    return building_dict

def prompt_resources():
    success = False
    
    # Get all valid material tickers from the prunpy loader
    all_material_tickers = prunpy.loader.material_ticker_list
    
    while not success:
        print("Enter a list of material codes, eg \"ALU, 2 FE, 3 H2O\" (Blank for none)")
        resource_string = input("> ")
        if not resource_string:
            resources = prunpy.ResourceList({})
            success = True
            break
        try:
            resource_dict = parse_resource_string(resource_string, all_material_tickers)
            success = True
            resources = prunpy.ResourceList(resource_dict)
            print(f"Parsed resources: {resources}")
        except ValueError as e:
            print(f"Error: {e}")
    
    return resources

def parse_resource_string(resource_string, valid_tickers):
    resource_dict = {}
    pattern = '|'.join(re.escape(ticker) for ticker in sorted(valid_tickers, key=len, reverse=True))
    matches = list(re.finditer(f'({pattern})', resource_string))
    
    if not matches:
        raise ValueError("No valid material tickers found in input.")
    
    last_index = 0
    for match in matches:
        ticker = match.group(1)
        start, end = match.span()
        count_str = resource_string[last_index:start].strip()
        
        # Determine the count, default to 1 if no count is specified
        count = 1
        if count_str:
            count_digits = ''.join([char for char in count_str if char.isdigit()])
            count = int(count_digits) if count_digits else 1
        
        # Add the ticker and its count to the dictionary
        if ticker in resource_dict:
            resource_dict[ticker] += count
        else:
            resource_dict[ticker] = count
        
        last_index = end
    
    # Handle any remaining part of the string after the last ticker
    count_str = resource_string[last_index:].strip()
    if count_str:
        raise ValueError(f"Unexpected input after last ticker: '{count_str}'")
    
    # Validate tickers
    for ticker in resource_dict.keys():
        if ticker not in valid_tickers:
            raise ValueError(f"Invalid material ticker: '{ticker}'")
    
    return resource_dict

if __name__ == "__main__":
    main()