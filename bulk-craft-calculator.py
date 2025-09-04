#!/usr/bin/env python3

import prunpy as prun
import sys
import math
import argparse

def get_material_ticker():
    if len(sys.argv) < 2:
        print("Usage: python bulk-craft-calculator.py <TICKER> [--batch-time HOURS] [--fab_count COUNT]")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    try:
        prun.loader.get_material(ticker)  # Validates ticker
        return ticker
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Calculate bulk crafting requirements')
    parser.add_argument('ticker', help='Material ticker symbol')
    parser.add_argument('planet', help='Planet identifier')
    parser.add_argument('days', nargs='?', type=float, default=14, help='Batch time in days (default: 14)')
    
    return parser.parse_args()

def get_colony_efficiency(base, building_ticker):
    # Get the full building name from rawdata to match production lines
    building_name = None
    for building in base.buildings:
        if building.ticker == building_ticker:
            building_name = building.rawdata.get('Name')
            break
    
    # Get colony efficiency (base-level) from production data
    colony_efficiency = 1.0
    if building_name:
        for production_line in base.raw_production:
            production_type = production_line.get('Type', '')
            if building_name.lower() == production_type.lower():
                colony_efficiency = production_line.get('Efficiency', 1.0)
                break
    
    return colony_efficiency

def select_recipe(ticker, base, building_ticker):
    recipes = prun.loader.get_material_recipes(ticker)
    
    if not recipes:
        print(f"No recipes found that produce {ticker}")
        return None
    
    # Filter recipes to only those available in the specified building
    available_recipes = [recipe for recipe in recipes if recipe.building == building_ticker]
    
    if not available_recipes:
        print(f"No recipes found that produce {ticker} in building {building_ticker}")
        print(f"Available recipes use these buildings: {[r.building for r in recipes]}")
        return None
    
    if len(available_recipes) == 1:
        print(f"\nAuto-selected recipe: {available_recipes[0]}")
        return available_recipes[0]
    
    print(f"\nRecipes that produce {ticker} in {building_ticker}:")
    for i, recipe in enumerate(available_recipes):
        print(f"{i + 1}. {recipe}")
    
    while True:
        try:
            choice = input(f"\nSelect recipe (1-{len(available_recipes)}): ")
            index = int(choice) - 1
            if 0 <= index < len(available_recipes):
                return available_recipes[index]
            else:
                print(f"Please enter a number between 1 and {len(available_recipes)}")
        except ValueError:
            print("Please enter a valid number")

def calculate_batch(recipe, requested_batch_time, fab_count):
    theoretical_batch_count = int(requested_batch_time / recipe.duration)
    
    # Cap batch size at 20 per fabricator
    actual_batch_count = min(theoretical_batch_count, 20)
    
    # Calculate actual batch time based on what we can craft
    actual_batch_time = actual_batch_count * recipe.duration
    
    craft_count = actual_batch_count * fab_count
    
    total_inputs = recipe.inputs * craft_count
    total_outputs = recipe.outputs * craft_count
    
    return actual_batch_count, craft_count, total_inputs, total_outputs, actual_batch_time

def analyze_shipping(resource_list, label):
    wcb_ship = prun.Container(3000, 1000)  # WCB capacity: 3000 weight, 1000 volume
    
    weight_loads = math.ceil(resource_list.weight / 3000)
    volume_loads = math.ceil(resource_list.volume / 1000)
    total_loads = max(weight_loads, volume_loads)
    
    print(f"\n{label} shipping analysis:")
    print(f"  Total weight: {resource_list.weight:.1f} t")
    print(f"  Total volume: {resource_list.volume:.1f} m3") 
    print(f"  WCB loads needed: {total_loads} ({weight_loads} by weight, {volume_loads} by volume)")
    
    return total_loads

def calculate_profit_margin(total_inputs, total_outputs, exchange):
    input_cost = total_inputs.get_total_value(exchange, 'buy')
    output_cost = total_outputs.get_total_value(exchange, 'sell')
    
    if input_cost == 0:
        return float('inf') if output_cost > 0 else 0
    
    profit = output_cost - input_cost
    margin = (profit / input_cost) * 100
    
    print(f"\nProfit Analysis (@ {exchange.code}):")
    print(f"  Input cost: {input_cost:.2f} {exchange.currency}")
    print(f"  Output value: {output_cost:.2f} {exchange.currency}") 
    print(f"  Profit: {profit:.2f} {exchange.currency}")
    print(f"  Profit margin: {margin:.1f}%")
    
    return margin

def main():
    args = parse_arguments()
    ticker = args.ticker.upper()
    
    # Validate ticker
    try:
        prun.loader.get_material(ticker)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Get planet and base
    try:
        planet = prun.loader.get_planet(args.planet)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Get username and real base
    username = prun.loader.get_username()
    try:
        base = prun.RealBase(planet.natural_id, username)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Find which building can produce the ticker
    available_buildings = set()
    for recipe in prun.loader.get_material_recipes(ticker):
        if recipe.building in base.building_counts:
            available_buildings.add(recipe.building)
    
    if not available_buildings:
        print(f"No buildings on {planet.name} can produce {ticker}")
        all_buildings = set(recipe.building for recipe in prun.loader.get_material_recipes(ticker))
        print(f"Required buildings: {', '.join(all_buildings)}")
        sys.exit(1)
    
    if len(available_buildings) > 1:
        print(f"Multiple buildings can produce {ticker}: {', '.join(available_buildings)}")
        building_ticker = input("Select building: ").upper()
        if building_ticker not in available_buildings:
            print(f"Invalid building. Choose from: {', '.join(available_buildings)}")
            sys.exit(1)
    else:
        building_ticker = list(available_buildings)[0]
        print(f"Using building: {building_ticker}")
    
    # Recipe selection
    recipe = select_recipe(ticker, base, building_ticker)
    if not recipe:
        return
    
    # Get building count and colony efficiency
    fab_count = base.building_counts.get(building_ticker, 0)
    colony_efficiency = get_colony_efficiency(base, building_ticker)
    
    # Get the building to check COGC details for display
    building = None
    for b in base.buildings:
        if b.ticker == building_ticker:
            building = b
            break
    
    # Copy recipe and apply both COGC and colony efficiency
    adjusted_recipe = recipe.copy()
    
    # Apply COGC bonus to recipe (like manufacture-ranker.py does)
    if building:
        cogc_bonus = building.get_cogc_bonus(base.planet.cogc)
        adjusted_recipe.multipliers['cogc'] = cogc_bonus
    
    # Apply colony efficiency on top of recipe multipliers
    total_efficiency = adjusted_recipe.multiplier * colony_efficiency
    adjusted_recipe.raw_duration = recipe.raw_duration / total_efficiency
    
    print(f"\nSelected recipe: {adjusted_recipe}")
    
    # Batch calculations
    requested_batch_time_hours = args.days * 24
    batch_count, craft_count, total_inputs, total_outputs, actual_batch_time_hours = calculate_batch(
        adjusted_recipe, requested_batch_time_hours, fab_count
    )
    
    # Get exchange for pricing
    exchange_code, exchange_distance = planet.get_nearest_exchange()
    exchange = prun.loader.get_exchange(exchange_code)
    
    print(f"\nBatch Configuration:")
    print(f"  Planet: {planet.name} ({planet.natural_id})")
    print(f"  Building: {building_ticker} (x{fab_count})")
    cogc_bonus = building.get_cogc_bonus(planet.cogc) if building else 1.0
    cogc_match = building.cogc_type == planet.cogc if building else False
    cogc_display = f"{cogc_bonus:.2f}x ({planet.cogc}" + (f" = {building.cogc_type})" if cogc_match else f" ≠ {building.cogc_type})" if building else ")")
    print(f"  COGC bonus: {cogc_display}")
    print(f"  Colony efficiency: {colony_efficiency:.2f}x")
    print(f"  Total efficiency: {total_efficiency:.2f}x")
    print(f"  Exchange: {exchange_code} ({exchange_distance} jumps)")
    print(f"  Requested batch time: {args.days:.1f} days ({requested_batch_time_hours:.1f} hours)")
    print(f"  Actual batch time: {actual_batch_time_hours/24:.1f} days ({actual_batch_time_hours:.1f} hours)")
    print(f"  Effective duration: {adjusted_recipe.duration:.1f} hours")
    print(f"  Batches per fabricator: {batch_count}")
    print(f"  Total craft count: {craft_count}")
    
    print(f"\nTotal Resources:")
    print(f"  Inputs: {total_inputs}")
    print(f"  Outputs: {total_outputs}")
    
    # Shipping analysis
    input_loads = analyze_shipping(total_inputs, "Input")
    output_loads = analyze_shipping(total_outputs, "Output")
    
    # Profit analysis using the planet's exchange
    calculate_profit_margin(total_inputs, total_outputs, exchange)

if __name__ == "__main__":
    main()