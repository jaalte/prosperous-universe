import prunpy as prun
import sys
import math
from prunpy.data_loader import loader

MIN_DAYS_SUPPLY_AVAILABLE = 30 # days worth per building
MIN_DAYS_DEMAND_AVAILABLE = 0 # days worth per building
MIN_DAILY_SOLD = 50
MAX_MARKET_SATURATION_PER_BUILDING = 0.25

DAYS_BURN = 3

SORT_KEY = 'true_roi'
REVERSE_SORT = True

def main():
    planet_names = get_planet_names()

    all_hits = []
    for planet_name in planet_names:
        all_hits += analyze_planet(planet_name)

    leng = len(all_hits)
    all_hits = filter_hits(all_hits)

    # Sort hits by lowest roi
    all_hits.sort(key=lambda x: x[SORT_KEY], reverse=REVERSE_SORT)

    display_hits(all_hits)

def get_planet_names():
    planet_name = ''
    if len(sys.argv) > 1:
        planet_name = sys.argv[1]
    else:
        print("Usage: python manufacture_ranker.py <planet_name>")
        sys.exit(1)

    # If "all", pick a representative set of planets with each COGC
    if planet_name.lower() == 'all':
        best_per_cogc = {}
        exchange = loader.preferred_exchange.code
        for name, planet in prun.loader.get_all_planets().items():
            nearest_exchange, distance = planet.get_nearest_exchange()
            if nearest_exchange != exchange: continue
            if planet.cogc not in best_per_cogc:
                best_per_cogc[planet.cogc] = planet
            else:
                if distance < best_per_cogc[planet.cogc].exchange_distance:
                    best_per_cogc[planet.cogc] = planet
                elif distance == best_per_cogc[planet.cogc].exchange_distance:
                    if planet.population.total > best_per_cogc[planet.cogc].population.total:
                        best_per_cogc[planet.cogc] = planet
        planet_names = [planet.name for planet in best_per_cogc.values()]
    else:
        planet_names = [planet_name]

    print(f"DEBUG: Picked planets {", ".join(planet_names)}")

    return planet_names

def analyze_planet(planet_name):
    planet = prun.loader.get_planet(planet_name)
    exchange_code, exchange_distance = planet.get_nearest_exchange()

    exchange = prun.loader.get_exchange(exchange_code)
    all_recipes = prun.loader.get_all_recipes()

    hits = []
    for recipe in all_recipes:
        base_area = 500-25
        building = prun.Building(recipe.building, planet)
    
        base_seed = prun.BuildingList({recipe.building: 1}, planet=planet)
        base_seed = base_seed.include_housing('cost')

        bonus = building.get_cogc_bonus(planet.cogc)
        recipe.multipliers['cogc'] = bonus
        # Optionally add expert bonus later

        max_count = base_area // base_seed.area
        if max_count <= 0: continue

        upkeep_cost = recipe.get_worker_upkeep_per_craft().get_total_value(exchange.code, 'buy')

        daily_profit_per_building = recipe.get_profit_per_day(exchange.code)
        profit_ratio = recipe.get_profit_ratio(exchange.code)
        max_daily_profit = max_count * daily_profit_per_building
        if daily_profit_per_building <= 0: continue

        building_cost = building.get_cost(exchange.code) 
        seed_cost = base_seed.get_total_cost(exchange)
        housing_cost = seed_cost-building_cost

        daily_profit_per_area = daily_profit_per_building / base_seed.area
        
        roi = seed_cost / daily_profit_per_building
        if roi <= 0: continue

        #recipe.inputs -= recipe.get_worker_upkeep_per_craft()*2
        #recipe.inputs = recipe.inputs.prune_negatives()

        for ticker, count in recipe.inputs.resources.items():
            supply = exchange.get_good(ticker).supply
            daily_need = recipe.daily.inputs.resources[ticker]
            days_available = supply / daily_need
            if days_available < MIN_DAYS_SUPPLY_AVAILABLE: remove = True
        
        daily_input_cost = recipe.daily.inputs.get_total_value(exchange.code, 'buy')

        burn_cost = daily_input_cost*DAYS_BURN
        total_cost = seed_cost + daily_input_cost*DAYS_BURN
        true_roi = (seed_cost + burn_cost) / daily_profit_per_building

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
            'outputs': outputs,
            'max_count': max_count,
            
            'profit_ratio': profit_ratio,
            'daily_profit': daily_profit_per_building,
            'dppa': daily_profit_per_area,
            'max_daily_profit': max_daily_profit,
            'daily_input_cost': daily_input_cost,

            'building_cost': building_cost,
            'seed_cost': seed_cost,
            'housing_cost': housing_cost,
            'total_cost': total_cost,

            'roi': roi,
            'true_roi': true_roi,

            'exchange': exchange,
            'exchange_distance': exchange_distance,
            'planet': planet
        }

        hits.append(hit)

    return hits
    
def filter_hits(hits):

    # Further filtering
    filtered_hits = []
    for hit in hits:
        exchange = loader.get_exchange(hit['exchange'])
        #print(hit['recipe'])
        remove = False
        for ingredient, count in hit['recipe'].inputs.resources.items():
            #print(f"  {ingredient}: {count}")
            supply = exchange.get_good(ingredient).supply
            daily_need = hit['recipe'].inputs.resources[ingredient] * 24 / hit['recipe'].duration
            days_available = supply / daily_need
            if days_available < MIN_DAYS_SUPPLY_AVAILABLE:
                print(f"Removing {hit['recipe']} due to low input supply")
                remove = True
        
        for product, count in hit['recipe'].outputs.resources.items():
            good = exchange.get_good(product)
            daily_made = hit['recipe'].outputs.resources[product] * 24 / hit['recipe'].duration
            days_available = good.demand / daily_made

            has_market_maker = False

            #if days_available < MIN_DAYS_DEMAND_AVAILABLE:
            #    print(f"Removing {hit['recipe']} due to low output demand")
            #    remove = True
            #if good.daily_sold < MIN_DAILY_SOLD:
            #    print(f"Removing {hit['recipe']} due to low output daily sold")
            #    remove = True

        for output in hit['outputs']:
            if output['sell_saturation_per_building'] > MAX_MARKET_SATURATION_PER_BUILDING:
                print(f"Removing {hit['recipe']} due to high per-building market saturation of {output['sell_saturation_per_building']:.2%}")
                remove = True

        if remove: continue
        filtered_hits.append(hit)

    return filtered_hits

def display_hits(hits):
    MAX_NAME_LENGTH = 10
    padding = " "*20

    for hit in hits:
        exchange = loader.get_exchange(hit['exchange'].code)
        planet = hit['planet']

        print(
            f"{planet.shorten_name(10):<{MAX_NAME_LENGTH}}"
            f"({planet.natural_id}) "
            f"{str(hit['recipe'])+':':<40}"
        )

        print(
            f"{padding}ROI: {hit['roi']:>6.1f}d / {hit['true_roi']:>6.1f}d"
            f"    Daily profit / building: {hit['daily_profit']:.0f}"
            f"    Daily profit / area: {hit['dppa']:.0f}"
            #f"{padding}Max DP: {hit['max_daily_profit']:.2f} "
        )

        print(
            f"{padding}Investment cost: {hit['total_cost']:.0f} = "
            f"{hit['building_cost']:.0f} for building + "
            f"{hit['housing_cost']:.0f} for housing + "
            f"{hit['daily_input_cost']*DAYS_BURN:.0f} for {DAYS_BURN}d inputs"
        )

        # for ingredient, count in hit['recipe'].inputs.resources.items():
        #     good = exchange.get_good(ingredient)
        #     price = good.buy_price
        #     print(f"  Buy  {ingredient:<3}: {count:>3}, {price:>5.0f}/u ({price*count:>5.0f}/recipe) with {good.daily_sold:<6.1f} sold daily")

        print(f"{padding}Sell:")
        for output in hit['outputs']:
            print(
                f"{padding}- {output['daily_produced']:>5.1f} "
                f" {output['ticker']:>3}/day "
                f"@{output['instant_sell_price']:>5.0f} <-> {output['patient_sell_price']:>5.0f} /u.    "
                f"{output['good'].daily_sold:>6.1f} sold daily "
                f"({output['sell_saturation_per_building']:.1%} market saturation / building)"
            )
        
        daily_burn = hit['recipe'].daily.inputs.ceil()
        print(f"{padding}Buy: {daily_burn} daily for {daily_burn.get_total_value(exchange.code, 'buy'):.2f}")

        print()
            #print(f"  Sell {product:<3}: {count:>3}, {price:>5.0f}/u ({price*count:>5.0f}/recipe) with {good.daily_sold:<6.1f} sold daily ({output['sell_saturation_per_building']:.1%} per building)")

        # for product, count in hit['recipe'].outputs.resources.items():
        #     good = exchange.get_good(product)
        #     price = good.sell_price
        #     print(f"  Sell {product:<3}: {count:>3}, {price:>5.0f}/u ({price*count:>5.0f}/recipe) with {good.daily_sold:<6.1f} sold daily")
    print(f"Good manufacture goals for {planet.name}, sorted by ROI with the best at the bottom.\n")

if __name__ == "__main__":
    main()