import prunpy as prun
import sys
import math

MIN_DAYS_SUPPLY_AVAILABLE = 500 # 100d worth per building
MIN_DAYS_DEMAND_AVAILABLE = 500 # 100d worth per building

def main():
    planet_name = ''
    if len(sys.argv) > 1:
        planet_name = sys.argv[1]
    else:
        print("Usage: python manufacture_ranker.py <planet_name>")
        sys.exit(1)

    planet = prun.importer.get_planet(planet_name)
    exchange_code, exchange_distance = planet.get_nearest_exchange()

    exchange = prun.importer.get_exchange(exchange_code)
    all_recipes = prun.importer.get_all_recipes()

    hits = []
    for recipe in all_recipes:
        base_area = 500
        building = prun.Building(recipe.building, planet)
    
        bonus = building.get_cogc_bonus(planet.cogc)
        # Optionally add expert bonus later
        recipe.duration /= bonus
        recipe.inputs += recipe.get_worker_upkeep_per_craft()

        max_count = base_area // building.area
        if max_count <= 0: continue

        daily_profit_per_building = recipe.get_profit_per_day(exchange.code)
        profit_ratio = recipe.get_profit_ratio(exchange.code)
        max_daily_profit = max_count * daily_profit_per_building
        if daily_profit_per_building <= 0: continue

        building_cost = building.get_cost(exchange.code)
        roi = building_cost / daily_profit_per_building
        if roi <= 0: continue

        recipe.inputs -= recipe.get_worker_upkeep_per_craft()*2
        recipe.inputs = recipe.inputs.prune_negatives()

        hit = {
            'recipe': recipe,
            'profit_ratio': profit_ratio,
            'daily_profit': daily_profit_per_building,
            'max_daily_profit': max_daily_profit,
            'max_count': max_count,
            'building_cost': building_cost,
            'roi': roi,
        }

        hits.append(hit)
    
    # Sort hits by lowest roi
    hits.sort(key=lambda x: x['roi'], reverse=False)

    # Further filtering
    filtered_hits = []
    for hit in hits:
        remove = False
        for ingredient in hit['recipe'].inputs.resources:
            supply = exchange.get_good(ingredient).supply
            daily_need = hit['recipe'].inputs.resources[ingredient] * 24 / hit['recipe'].duration
            days_available = supply / daily_need
            if days_available < MIN_DAYS_SUPPLY_AVAILABLE: remove = True
        
        for result in hit['recipe'].outputs.resources:
            demand = exchange.get_good(result).demand
            daily_made = hit['recipe'].outputs.resources[result] * 24 / hit['recipe'].duration
            days_available = demand / daily_made
            if days_available < MIN_DAYS_DEMAND_AVAILABLE: remove = True

        if remove: continue
        filtered_hits.append(hit)

    hits = filtered_hits

    for hit in hits:
        print(
            f"{hit['recipe']}: ".ljust(80) +
            f"ROI: {hit['roi']:>6.2f}d "
            f"  Building cost: {hit['building_cost']:.2f} "
            f"  DPPB: {hit['daily_profit']:.2f} "
            f"  Max DP: {hit['max_daily_profit']:.2f} "
        )

if __name__ == "__main__":
    main()