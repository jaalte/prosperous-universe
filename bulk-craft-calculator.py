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

def prepare_recipe_with_efficiency(recipe, base, building_ticker):
    """Apply COGC and colony efficiency to recipe, return adjusted recipe and efficiency details"""
    # Get building for COGC bonus
    building = None
    for b in base.buildings:
        if b.ticker == building_ticker:
            building = b
            break
    
    # Get colony efficiency
    colony_efficiency = get_colony_efficiency(base, building_ticker)
    
    # Copy recipe and apply both COGC and colony efficiency
    adjusted_recipe = recipe.copy()
    
    # Apply COGC bonus to recipe (like manufacture-ranker.py does)
    if building:
        cogc_bonus = building.get_cogc_bonus(base.planet.cogc)
        adjusted_recipe.multipliers['cogc'] = cogc_bonus
    
    # Apply colony efficiency on top of recipe multipliers
    total_efficiency = adjusted_recipe.multiplier * colony_efficiency
    adjusted_recipe.raw_duration = recipe.raw_duration / total_efficiency
    
    # Return efficiency details for display
    efficiency_details = {
        'cogc_bonus': building.get_cogc_bonus(base.planet.cogc) if building else 1.0,
        'cogc_match': building.cogc_type == base.planet.cogc if building else False,
        'cogc_type': building.cogc_type if building else None,
        'colony_efficiency': colony_efficiency,
        'total_efficiency': total_efficiency,
        'building': building
    }
    
    return adjusted_recipe, efficiency_details

def select_recipe(ticker):
    """Select a recipe for the given ticker"""
    recipes = prun.loader.get_material_recipes(ticker)
    
    if not recipes:
        print(f"No recipes found that produce {ticker}")
        return None
    
    if len(recipes) == 1:
        print(f"\nAuto-selected recipe: {recipes[0]}")
        return recipes[0]
    
    print(f"\nRecipes that produce {ticker}:")
    for i, recipe in enumerate(recipes):
        print(f"{i + 1}. {recipe}")
    
    while True:
        try:
            choice = input(f"\nSelect recipe (1-{len(recipes)}): ")
            index = int(choice) - 1
            if 0 <= index < len(recipes):
                return recipes[index]
            else:
                print(f"Please enter a number between 1 and {len(recipes)}")
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

def calculate_profit_margin(total_inputs, total_outputs, exchange, actual_batch_time_hours):
    input_cost = total_inputs.get_total_value(exchange, 'buy')
    output_cost = total_outputs.get_total_value(exchange, 'sell')
    
    if input_cost == 0:
        return float('inf') if output_cost > 0 else 0
    
    profit = output_cost - input_cost
    margin = (profit / input_cost) * 100
    
    # Calculate daily profit rate
    batch_time_days = actual_batch_time_hours / 24
    daily_profit = profit / batch_time_days if batch_time_days > 0 else 0
    
    print(f"\nProfit Analysis (@ {exchange.code}):")
    print(f"  Input cost: {input_cost:.2f} {exchange.currency}")
    print(f"  Output value: {output_cost:.2f} {exchange.currency}") 
    print(f"  Profit: {profit:.2f} {exchange.currency}")
    print(f"  Profit margin: {margin:.1f}%")
    print(f"  Daily profit rate: {daily_profit:.2f} {exchange.currency}/day")
    
    return margin

def prompt_building_count(building_ticker, base):
    """Prompt user for building count if they don't own any"""
    fab_count = base.building_counts.get(building_ticker, 0)
    
    if fab_count == 0:
        print(f"You don't own any {building_ticker} buildings on {base.planet.name}")
        while True:
            try:
                fab_count = int(input(f"How many {building_ticker} buildings to simulate? "))
                if fab_count > 0:
                    break
                else:
                    print("Please enter a positive number")
            except ValueError:
                print("Please enter a valid number")
    
    return fab_count

def display_results(args, base, recipe, efficiency_details, batch_count, craft_count, 
                   total_inputs, total_outputs, actual_batch_time_hours, requested_batch_time_hours, 
                   fab_count, building_ticker, exchange, exchange_distance):
    """Display all results and analysis"""
    print(f"\nBatch Configuration:")
    print(f"  Planet: {base.planet.name} ({base.planet.natural_id})")
    print(f"  Building: {building_ticker} (x{fab_count})")
    
    # COGC display
    cogc_display = f"{efficiency_details['cogc_bonus']:.2f}x ({base.planet.cogc}"
    if efficiency_details['cogc_type']:
        cogc_display += f" = {efficiency_details['cogc_type']})" if efficiency_details['cogc_match'] else f" ≠ {efficiency_details['cogc_type']})"
    else:
        cogc_display += ")"
    print(f"  COGC bonus: {cogc_display}")
    
    print(f"  Colony efficiency: {efficiency_details['colony_efficiency']:.2f}x")
    print(f"  Total efficiency: {efficiency_details['total_efficiency']:.2f}x")
    print(f"  Exchange: {exchange.code} ({exchange_distance} jumps)")
    print(f"  Requested batch time: {args.days:.1f} days ({requested_batch_time_hours:.1f} hours)")
    print(f"  Actual batch time: {actual_batch_time_hours/24:.1f} days ({actual_batch_time_hours:.1f} hours)")
    print(f"  Effective duration: {recipe.duration:.1f} hours")
    print(f"  Batches per fabricator: {batch_count}")
    print(f"  Total craft count: {craft_count}")
    
    # Resource display
    print(f"\nTotal Resources:")
    print(f"  Inputs: {total_inputs}")
    print(f"  Outputs: {total_outputs}")
    
    # Shipping analysis
    input_loads = analyze_shipping(total_inputs, "Input")
    output_loads = analyze_shipping(total_outputs, "Output")
    
    # Profit analysis
    calculate_profit_margin(total_inputs, total_outputs, exchange, actual_batch_time_hours)

def main():
    args = parse_arguments()
    
    # Setup base and recipe
    ticker = args.ticker.upper()
    prun.loader.get_material(ticker)  # Validates ticker
    
    planet = prun.loader.get_planet(args.planet)
    username = prun.loader.get_username()
    base = prun.RealBase(planet.natural_id, username)
    
    recipe = select_recipe(ticker)
    if not recipe:
        return
    
    building_ticker = recipe.building
    
    # Apply efficiency and calculate batch
    adjusted_recipe, efficiency_details = prepare_recipe_with_efficiency(recipe, base, building_ticker)
    print(f"\nSelected recipe: {adjusted_recipe}")
    
    requested_batch_time_hours = args.days * 24
    fab_count = prompt_building_count(building_ticker, base)
    
    batch_count, craft_count, total_inputs, total_outputs, actual_batch_time_hours = calculate_batch(
        adjusted_recipe, requested_batch_time_hours, fab_count
    )
    
    # Get exchange for pricing
    exchange_code, exchange_distance = base.planet.get_nearest_exchange()
    exchange = prun.loader.get_exchange(exchange_code)
    
    # Display results
    display_results(args, base, adjusted_recipe, efficiency_details, batch_count, craft_count,
                   total_inputs, total_outputs, actual_batch_time_hours, requested_batch_time_hours,
                   fab_count, building_ticker, exchange, exchange_distance)

if __name__ == "__main__":
    main()