import prunpy as prun
import sys
import math

MIN_DAYS_SUPPLY_AVAILABLE = 30 # days worth per building
MIN_DAYS_DEMAND_AVAILABLE = 0 # days worth per building
MIN_DAILY_SOLD = 50

def main():
    planet_name = ''
    if len(sys.argv) > 1:
        planet_name = sys.argv[1]
    else:
        print("Usage: python manufacture_ranker.py <planet_name>")
        sys.exit(1)

    planet = prun.loader.get_planet(planet_name)
    exchange_code, exchange_distance = planet.get_nearest_exchange()

    exchange = prun.loader.get_exchange(exchange_code)
    all_recipes = prun.loader.get_all_recipes()

    hits = []
    for recipe in all_recipes:
        base_area = 500
        building = prun.Building(recipe.building, planet)
    
        bonus = building.get_cogc_bonus(planet.cogc)
        # Optionally add expert bonus later
        recipe.duration /= bonus
        #recipe.inputs += recipe.get_worker_upkeep_per_craft()

        max_count = base_area // building.area
        if max_count <= 0: continue

        upkeep_cost = recipe.get_worker_upkeep_per_craft().get_total_value(exchange.code, 'buy')

        daily_profit_per_building = recipe.get_profit_per_day(exchange.code)
        profit_ratio = recipe.get_profit_ratio(exchange.code)
        max_daily_profit = max_count * daily_profit_per_building
        if daily_profit_per_building <= 0: continue

        building_cost = building.get_cost(exchange.code)
        roi = building_cost / daily_profit_per_building
        if roi <= 0: continue

        #recipe.inputs -= recipe.get_worker_upkeep_per_craft()*2
        #recipe.inputs = recipe.inputs.prune_negatives()

        for ticker, count in recipe.inputs.resources.items():
            supply = exchange.get_good(ticker).supply
            daily_need = recipe.inputs.resources[ticker] * 24 / recipe.duration
            days_available = supply / daily_need
            if days_available < MIN_DAYS_SUPPLY_AVAILABLE: remove = True
        
        daily_input_cost = recipe.daily.inputs.get_total_value(exchange.code, 'buy')

        DAYS_BURN = 5
        burn_cost = daily_input_cost*DAYS_BURN
        true_roi = (building_cost + burn_cost) / daily_profit_per_building

        outputs = []
        for ticker, count in recipe.outputs.resources.items():
            good = exchange.get_good(ticker)
            daily_sold = good.daily_sold

            daily_produced = recipe.daily.outputs.resources[ticker]

            output_data = { # Per building
                'ticker': ticker,
                'instant_sell_price': good.sell_price,
                'patient_sell_price': good.buy_price,
                'daily_produced': daily_produced,
                'daily_sold': daily_sold,
                'sell_saturation_per_building': daily_produced / daily_sold,
                'good': good
            }
            outputs.append(output_data)


        hit = {
            'recipe': recipe,
            'profit_ratio': profit_ratio,
            'daily_profit': daily_profit_per_building,
            'max_daily_profit': max_daily_profit,
            'daily_input_cost': daily_input_cost,
            'max_count': max_count,
            'building_cost': building_cost,
            'roi': roi,
            'true_roi': true_roi,
            'outputs': outputs,
        }

        hits.append(hit)
    
    # Sort hits by lowest roi
    hits.sort(key=lambda x: x['daily_profit'], reverse=False)

    # Further filtering
    filtered_hits = []
    for hit in hits:
        #print(hit['recipe'])
        remove = False
        for ingredient, count in hit['recipe'].inputs.resources.items():
            #print(f"  {ingredient}: {count}")
            supply = exchange.get_good(ingredient).supply
            daily_need = hit['recipe'].inputs.resources[ingredient] * 24 / hit['recipe'].duration
            days_available = supply / daily_need
            if days_available < MIN_DAYS_SUPPLY_AVAILABLE:
                print(f"Removed {hit['recipe']} due to low input supply")
                remove = True
        
        for product, count in hit['recipe'].outputs.resources.items():
            good = exchange.get_good(product)
            daily_made = hit['recipe'].outputs.resources[product] * 24 / hit['recipe'].duration
            days_available = good.demand / daily_made

            has_market_maker = False

            if days_available < MIN_DAYS_DEMAND_AVAILABLE:
                print(f"Removed {hit['recipe']} due to low output demand")
                remove = True
            if good.daily_sold < MIN_DAILY_SOLD:
                print(f"Removed {hit['recipe']} due to low output daily sold")
                remove = True

        if remove: continue
        filtered_hits.append(hit)

    hits = filtered_hits

    for hit in hits:
        print(
            f"{str(hit['recipe'])+':':<50}"
            f"    ROI: {hit['roi']:>6.1f}d / {hit['true_roi']:>6.1f}d"
            f"    II: {hit['building_cost']:.0f} building + {hit['daily_input_cost']*DAYS_BURN:.0f} for {DAYS_BURN} days inputs"
            f"    Daily profit / building: {hit['daily_profit']:.2f}"
            #f"   Max DP: {hit['max_daily_profit']:.2f} "
        )

        # for ingredient, count in hit['recipe'].inputs.resources.items():
        #     good = exchange.get_good(ingredient)
        #     price = good.buy_price
        #     print(f"  Buy  {ingredient:<3}: {count:>3}, {price:>5.0f}/u ({price*count:>5.0f}/recipe) with {good.daily_sold:<6.1f} sold daily")

        for output in hit['outputs']:
            print(
                f"Sell: {output['daily_produced']:>5.1f} "
                f" {output['ticker']:>3}/day "
                f"@{output['instant_sell_price']:>5.0f} <-> {output['patient_sell_price']:>5.0f} /u.    "
                f"{output['good'].daily_sold:>6.1f} sold daily "
                f"({output['sell_saturation_per_building']:.1%} market saturation / building)"
            )
        
        daily_burn = hit['recipe'].daily.inputs.ceil()
        print(f"Buy: {daily_burn} daily for {daily_burn.get_total_value(exchange.code, 'buy'):.2f}")

        print()
            #print(f"  Sell {product:<3}: {count:>3}, {price:>5.0f}/u ({price*count:>5.0f}/recipe) with {good.daily_sold:<6.1f} sold daily ({output['sell_saturation_per_building']:.1%} per building)")

        # for product, count in hit['recipe'].outputs.resources.items():
        #     good = exchange.get_good(product)
        #     price = good.sell_price
        #     print(f"  Sell {product:<3}: {count:>3}, {price:>5.0f}/u ({price*count:>5.0f}/recipe) with {good.daily_sold:<6.1f} sold daily")
    print(f"Good manufacture goals for {planet.name}, sorted by ROI with the best at the bottom.\n")

if __name__ == "__main__":
    main()