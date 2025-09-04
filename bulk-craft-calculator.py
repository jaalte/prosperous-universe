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
    parser.add_argument('--batch-time', type=float, default=168, help='Batch time in hours (default: 168 = 7 days)')
    parser.add_argument('--fab-count', type=int, default=1, help='Number of fabricators (default: 1)')
    parser.add_argument('--efficiency', type=float, default=100, help='Efficiency percentage (e.g. 175 for 1.75x speed, default: 100)')
    
    return parser.parse_args()

def apply_efficiency(recipe, efficiency):
    # Convert efficiency to multiplier (handle both percentage and decimal formats)
    if efficiency == int(efficiency):  # No decimal point, assume percentage (e.g. 175)
        efficiency_multiplier = efficiency / 100
    else:  # Has decimal point, assume multiplier (e.g. 1.75)
        efficiency_multiplier = efficiency
    
    # Create a copy and modify duration
    adjusted_recipe = recipe.copy()
    adjusted_recipe.raw_duration = recipe.raw_duration / efficiency_multiplier
    return adjusted_recipe, efficiency_multiplier

def select_recipe(ticker, efficiency):
    recipes = prun.loader.get_material_recipes(ticker)
    
    if not recipes:
        print(f"No recipes found that produce {ticker}")
        return None, None
    
    print(f"\nRecipes that produce {ticker} (efficiency: {efficiency}% applied):")
    adjusted_recipes = []
    for i, recipe in enumerate(recipes):
        adjusted_recipe, efficiency_multiplier = apply_efficiency(recipe, efficiency)
        adjusted_recipes.append((adjusted_recipe, efficiency_multiplier))
        print(f"{i + 1}. {adjusted_recipe}")
    
    while True:
        try:
            choice = input(f"\nSelect recipe (1-{len(recipes)}): ")
            index = int(choice) - 1
            if 0 <= index < len(recipes):
                return adjusted_recipes[index]
            else:
                print(f"Please enter a number between 1 and {len(recipes)}")
        except ValueError:
            print("Please enter a valid number")

def calculate_batch(recipe, batch_time, fab_count):
    batch_count = int(batch_time / recipe.duration)
    craft_count = batch_count * fab_count
    
    total_inputs = recipe.inputs * craft_count
    total_outputs = recipe.outputs * craft_count
    
    return batch_count, craft_count, total_inputs, total_outputs

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

def calculate_profit_margin(total_inputs, total_outputs):
    input_cost = total_inputs.cost
    output_cost = total_outputs.cost
    
    if input_cost == 0:
        return float('inf') if output_cost > 0 else 0
    
    profit = output_cost - input_cost
    margin = (profit / input_cost) * 100
    
    print(f"\nProfit Analysis:")
    print(f"  Input cost: {input_cost:.2f} ICA")
    print(f"  Output value: {output_cost:.2f} ICA") 
    print(f"  Profit: {profit:.2f} ICA")
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
    
    # Recipe selection
    recipe_result = select_recipe(ticker, args.efficiency)
    if not recipe_result or recipe_result[0] is None:
        return
    
    adjusted_recipe, efficiency_multiplier = recipe_result
    print(f"\nSelected recipe: {adjusted_recipe}")
    
    # Batch calculations
    batch_count, craft_count, total_inputs, total_outputs = calculate_batch(
        adjusted_recipe, args.batch_time, args.fab_count
    )
    
    print(f"\nBatch Configuration:")
    print(f"  Batch time: {args.batch_time:.1f} hours ({args.batch_time/24:.1f} days)")
    print(f"  Efficiency: {args.efficiency}% ({efficiency_multiplier:.2f}x)")
    print(f"  Effective duration: {adjusted_recipe.duration:.1f} hours")
    print(f"  Batches per fabricator: {batch_count}")
    print(f"  Number of fabricators: {args.fab_count}")
    print(f"  Total craft count: {craft_count}")
    
    print(f"\nTotal Resources:")
    print(f"  Inputs: {total_inputs}")
    print(f"  Outputs: {total_outputs}")
    
    # Shipping analysis
    input_loads = analyze_shipping(total_inputs, "Input")
    output_loads = analyze_shipping(total_outputs, "Output")
    
    # Profit analysis
    calculate_profit_margin(total_inputs, total_outputs)

if __name__ == "__main__":
    main()