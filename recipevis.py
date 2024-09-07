import prunpy as prun
import sys
import re

EXCHANGE='NC1'
PRIORITY_MODE = 'profit' or 'throughput'

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

# Replace with Material.getRecipes() eventually 
def get_recipes(ticker):
    recipes = prun.importer.get_all_recipes()

    # Find recipes that use the material_ticker
    target_recipes = []
    for recipe in recipes:
        if ticker in recipe.outputs.resources.keys():
            target_recipes.append(recipe)

    if len(target_recipes) == 0:
        #print(f"No recipes found for material ticker {ticker}")
        return None

    # Pick recipe with highest profit per hour
    best_recipe = None
    for recipe in target_recipes:
        if best_recipe is None:
            best_recipe = recipe
        if PRIORITY_MODE == 'throughput':
            if recipe.throughput > best_recipe.throughput:
                best_recipe = recipe
        if PRIORITY_MODE == 'profit':
            if recipe.get_profit_per_hour('NC1') > best_recipe.get_profit_per_hour('NC1'):
                best_recipe = recipe
        

    return best_recipe

def get_recipe_string(recipe):
    return f"{recipe.outputs} <= {recipe.inputs} in {recipe.duration:.1f}h @ {recipe.building}"

def display_recipe_tree(recipe, indent=0):
    print("| " * indent + get_recipe_string(recipe))

    # Check the inputs of the current recipe
    for input_ticker in recipe.inputs.resources.keys():
        # Fetch the recipe for the input material
        input_recipe = get_recipes(input_ticker)
        
        if input_recipe:
            # Recursively display the input recipe with increased indentation
            display_recipe_tree(input_recipe, indent + 1)

def main():
    target_ticker = get_input_ticker()
    recipe = get_recipes(target_ticker)
    
    exchanges = prun.importer.get_all_exchanges()

    if recipe:
        display_recipe_tree(recipe)

    

    

    







if __name__ == "__main__":
    main()