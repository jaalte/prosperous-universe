import prunpy as prun
import sys
import re

EXCHANGE='NC1'
PRIORITY_MODE = 'profit_amount' or 'throughput'

def get_input_ticker():
    # Merge arguments into one string
    input_string = " ".join(sys.argv[1:])
    material_tickers = prun.loader.material_ticker_list

    # Find material_ticker that occurs first in the input string
    target_ticker = None
    for ticker in material_tickers:
        # Use word boundary to ensure ticker is matched as a whole word
        if re.search(rf'\b{ticker}\b', input_string):
            target_ticker = ticker
            break

    if target_ticker is None:
        print("No material ticker found in arguments")
        return

    return target_ticker

def get_recipe_string(recipe):
    out = f"{recipe.outputs} <= {recipe.inputs} in {recipe.duration:.1f}h @{recipe.building}"
    if recipe.multiplier != 1:
        out += f" x{recipe.multiplier}"
    return out

def display_recipe_tree(recipe, indent=0, parent=None):

    if not 'multiplier' in vars(recipe):
        recipe.multiplier = 1

    # recipe.multiplier = 1
    # if parent:
    #     parent_amount = parent.inputs.resources[recipe.inputs.tickers[0]]


    print("| " * indent + get_recipe_string(recipe))

    # Check the inputs of the current recipe
    for input_ticker in recipe.inputs.resources.keys():
        # Fetch the recipe for the input material
        input_recipe = prun.importer.get_best_recipe(input_ticker, PRIORITY_MODE)

        if input_recipe:
            amount_needed = recipe.inputs.resources[input_ticker]
            amount_gained = input_recipe.outputs.resources[input_ticker]
            input_recipe.multiplier = amount_needed / amount_gained
            input_recipe.inputs *= input_recipe.multiplier
            input_recipe.outputs *= input_recipe.multiplier
            # Recursively display the input recipe with increased indentation
            display_recipe_tree(input_recipe, indent + 1, parent = recipe)

def main():
    target_ticker = get_input_ticker()
    recipe = prun.importer.get_best_recipe(target_ticker, PRIORITY_MODE)
    
    exchanges = prun.importer.get_all_exchanges()

    if recipe:
        display_recipe_tree(recipe)

    

    

    







if __name__ == "__main__":
    main()