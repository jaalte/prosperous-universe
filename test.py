import prunpy
import prunpy as prun
from prunpy import ResourceList
from prunpy import loader
import json
import math
import requests
import numpy as np
from prunpy import RecipeQueue, RecipeQueueItem

NUM_SLOTS = 5
MAX_RECIPE_SLOT_MULTIPLIER = 3

def radius_crunch(loader, planet_sizes):
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.cluster import KMeans

    # Collect data dynamically
    radii = []
    masses = []
    gravities = []
    temperatures = []
    pressures = []
    slots = []

    for planet, slot_count in planet_sizes.items():
        planet_data = loader.get_planet(planet)
        radii.append(planet_data.rawdata["Radius"])
        masses.append(planet_data.rawdata["MassEarth"])
        gravities.append(planet_data.rawdata["Gravity"])
        temperatures.append(planet_data.rawdata["Temperature"])
        pressures.append(planet_data.rawdata["Pressure"])
        slots.append(slot_count)

    # Convert to numpy arrays
    features = np.array(list(zip(radii, masses, gravities, temperatures, pressures)))
    slots = np.array(slots).reshape(-1, 1)

    # Function to evaluate models and print results
    def evaluate_model(name, predictions, coefficients=None, intercept=None):
        errors = predictions.flatten() - slots.flatten()
        absolute_errors = np.abs(errors)
        percentage_errors = 100 * absolute_errors / slots.flatten()
        print(f"\n{name} Model:")
        if coefficients is not None:
            equation = " + ".join(
                [f"{coeff:.4e}*x{i}" for i, coeff in enumerate(coefficients.flatten())]
            )
            print(f"Equation: y = {equation} + {intercept[0]:.4f}")
        print("Radius | Mass | Gravity | Temp | Pressure | Predicted | Actual | Abs Error | % Error")
        for r, m, g, t, p, pred, actual, ae, pe in zip(
            radii, masses, gravities, temperatures, pressures, predictions.flatten(), slots.flatten(), absolute_errors, percentage_errors
        ):
            print(f"{r:.1f} | {m:.2e} | {g:.1f} | {t:.1f} | {p:.1f} | {pred:.1f} | {actual} | {ae:.1f} | {pe:.2f}%")

    # Linear model with all features
    linear_model = LinearRegression()
    linear_model.fit(features, slots)
    linear_pred = linear_model.predict(features)
    evaluate_model("Linear with Multiple Features", linear_pred, coefficients=linear_model.coef_, intercept=linear_model.intercept_)

    # Polynomial models (degree 2) with all features
    poly = PolynomialFeatures(2)
    features_poly = poly.fit_transform(features)
    poly_model = LinearRegression()
    poly_model.fit(features_poly, slots)
    poly_pred = poly_model.predict(features_poly)
    evaluate_model(
        "Polynomial (degree 2) with Multiple Features",
        poly_pred,
        coefficients=poly_model.coef_,
        intercept=poly_model.intercept_,
    )

    # Cluster analysis (optional, to group planets based on features)
    def fit_clusters(features, slots, n_clusters=2):
        print("\nPerforming clustering analysis:")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(features)
        for cluster in range(n_clusters):
            print(f"\nCluster {cluster + 1}:")
            for i, label in enumerate(labels):
                if label == cluster:
                    print(
                        f"  Radius: {radii[i]:.1f}, Mass: {masses[i]:.2e}, Gravity: {gravities[i]:.1f}, "
                        f"Temp: {temperatures[i]:.1f}, Pressure: {pressures[i]:.1f}, Slots: {slots[i][0]}"
                    )
        return labels

    # Perform clustering analysis
    fit_clusters(features, slots, n_clusters=2)





def main():

    planet_sizes = {
        'Vallis': 387,
        'Montem': 418,
        'OT-580a': 393,
        'OT-580d': 412,
        "UV-351a": 387,
        "UV-351b": 399,
        "UV-351c": 386,
        "OF-208a": 356,
        "OF-208b": 389,
        "OF-208c": 449,
        "OF-208d": 551,
        "UV-062a": 409,
        "UV-062b": 425,
        "UV-062c": 400,
        "UV-062d": 442,
        "UV-062e": 389,
        "UV-062f": 521,
    }

    planet_sizes_gas_giants = {
        'OT-580e': 490,
        "UV-351d": 635,
        "UV-351e": 694,
        "OF-208e": 443,
        "OF-208f": 627,
        "OF-208g": 690,
        "UV-062g": 623,
        "UV-062h": 713,
    }


    radius_crunch(loader, planet_sizes)
    #return
    
    #print_spread_cba()
    #print_fertile_planets()

    planets = loader.planets

    for planet, slots in planet_sizes.items():
        planet = loader.get_planet(planet)
        print(f"{planet.name}: {planet.rawdata['Radius']}m, {slots} slots")

    planet = loader.get_planet('Vallis')
    #print(json.dumps(planet.rawdata, indent=2))

    rawsites = prun.fio.request("GET", f"/planet/sites/{planet.natural_id}")
    print(len(rawsites))

    return

    g_range = (0.999, 1.001)

    candidates = []
    for name, planet in planets.items():
        if planet.environment['gravity'] > g_range[0]:
            if planet.environment['gravity'] < g_range[1]:
                candidates.append(planet)
            
    candidates.sort(key = lambda p: p.environment['gravity'])

    for planet in candidates:
        exchange, distance = planet.get_nearest_exchange()
        print(f"{planet.name}: {planet.environment['gravity']:0.3f}g, {planet.population.total} workers, {distance:>2}j->{exchange}, Environment: {planet.get_environment_string()}")


    return








    planets = list(loader.planets.values())
    #print(json.dumps(planets[0].rawdata, indent=4))

    planets = [planet for planet in planets if not planet.rawdata['HasAdministrationCenter']]

    open_planets = []
    for planet in planets:
        exchange, distance = planet.get_nearest_exchange()
        if exchange in ['NC2', 'CI2']:
            open_planets.append(planet)
        else:
            if distance > 3:
                open_planets.append(planet)
    planets = open_planets

    planets = [planet for planet in planets if planet.get_nearest_exchange()[1] > 0]
    planets = [planet for planet in planets if planet.population.total > 1000]
    
    planets.sort(key=lambda planet: planet.population.total, reverse=True)



    for planet in planets:
        print(f"{planet.shorten_name(10):<10}:    Population {planet.population.total:<4}, {planet.population.pioneers:<4} pioneers.    {planet.exchange_distance:>2}j->{planet.exchange_code}    COGC: {planet.cogc:<30}")

    #for planet in planets:
    #    system = prun.System(planet.system_natural_id)


    return

    building = prun.Building('CLF', 'Montem')
    exchange_code = building.planet.get_nearest_exchange()[0]
    exchange = prun.loader.get_exchange(exchange_code)

    # Later substitute with a building's recipe queue
    recipes = [
        loader.get_best_recipe('HMS'),
        loader.get_best_recipe('HSS'),
        loader.get_best_recipe('LC'),
    ]

    # Note: Doesn't have COGC bonus

    for recipe in recipes:
        building.queue_recipe(recipe, order_size=1)

    building.recipe_queue.balance()

    print(building.recipe_queue)

    

    return

    recipes = list(target_ratios.resources.keys())
    target_recipe_multipliers = target_recipe_multipliers.resources

    final_recipe_queue = generate_recipe_queue(recipes, target_recipe_multipliers)

    print("\nFinal recipe queue:")
    for slot in final_recipe_queue:
        print(f"{slot['recipe']}: {slot['multiplier']}")
    print()

    # Pretty print the final recipe_queue
    #print(json.dumps(final_recipe_queue, indent=4))


    return















def old():
    base_area = 750
    buildings = prun.BuildingList({
        "BMP": 2,
        "CHP": 4,
        "CLF": 4,
        "EXT": 3,
        "FP": 1,
        "PP1": 2,
        "PP3": 5,
    }, "Montem")

    # Cost
    cost_buildings = buildings.include_housing('cost')
    cost_cost = cost_buildings.cost
    cost_area = cost_buildings.area

    # Area
    area_buildings = buildings.include_housing('area')
    area_cost = area_buildings.cost
    area_area = area_buildings.area

    print(f"Cost-focused: {cost_buildings}\n  {cost_cost:.2f} NCC, {cost_area:.2f} area, {cost_cost/cost_area:.2f} per area")
    print(f"Area-focused: {area_buildings}\n  {area_cost:.2f} NCC, {area_area:.2f} area, {area_cost/area_area:.2f} per area")

    cost_added = area_cost - cost_cost
    area_added = cost_area - area_area
    opportunity_cost = cost_added / area_added

    print(f"Cost per extra area: {opportunity_cost:.2f}")


    full_base = buildings.include_housing('cost').expand_to_area(base_area-25)
    print(full_base)
    print(full_base.area)
    print(full_base.get_population_demand())
    

    return


    #find_largest_pop()

    buildings = prun.loader.get_all_buildings()

    # for ticker, building in buildings.items():
    #     print(f"{ticker}: {building.planet.name}: {building.get_daily_maintenance()}")

    exchange = loader.get_exchange('NC1')

    materials = []

    for ticker in loader.material_ticker_list:
        history = prun.PriceHistory(ticker, exchange.code)
        traded = history.average_traded_daily

        price = exchange.get_good(ticker).sell_price
        traded_value = traded * price

        materials.append({
            'ticker': ticker,
            'good': exchange.get_good(ticker),
            'price': price,
            'traded': traded,
            'traded_value': traded_value
        })
        print(f"{ticker}: {traded_value:.2f}")


    materials = sorted(materials, key=lambda x: x['traded_value'], reverse=True)

    total_mm = 0
    total_non_mm = 0
    for material in materials:
        if material['good'].mm_buys:
            total_mm += material['traded_value']
        else:
            total_non_mm += material['traded_value']

    for material in materials:
        print(f"{material['ticker']}: {material['traded_value']:.2f}")

    print(f"Total MM: {total_mm:.2f}")
    print(f"Total non-MM: {total_non_mm:.2f}")
    print(f"MM-nMM: {total_mm - total_non_mm:.2f}")

    ##########


    from prunpy.models.recipe_tree import RecipeTreeNode

    recipe = prun.loader.get_best_recipe('HMS')

    root_node = RecipeTreeNode(
        recipe=recipe.daily,
        priority_mode='profit_ratio',
        include_worker_upkeep=True,
        multiplier=1,
        terminals = ['SIO', 'FE', 'C', 'O', 'AL', 'PG', 'PE', 'CU', 'AU', 'SI', 'GC', 'NL', 'MG', 'S'],
    )

    planet = prun.loader.get_planet('Montem')

    print(root_node)

    building_days = root_node.get_total_building_days()

    for building, amount in building_days.items():
        building_days[building] = math.ceil(amount)

    print(json.dumps(building_days, indent=2))

    base = prun.Base(planet.natural_id, building_days)

    print(base)
    print(f"Area: {base.get_area()}")
    print(f"Population: {base.population_demand}")


    # materials = prun.ResourceList("8 COF, 7 CU, 17 FE, 46 GC, 114 H2O, 2 KOM, 13 LST, 7 MG, 8 NL, 3 PWO, 79 RAT, 7 S, 55 SIO")
    # materials += prun.ResourceList("5 COF, 34 DW, 5 OVE, 2 PWO, 34 RAT")
    # print(materials)

    # planets = prun.loader.get_all_planets()
    # minable_resources = set()
    # for name, planet in planets.items():
    #     for ticker, resource in planet.resources.items():
    #         minable_resources.add(ticker)
    
    # print(minable_resources)

    # #storage = prun.Storage(500,500)

    # #print(prun.loader.materials_by_ticker['MCG'])

    # #for resource in minable_resources:

    # value = 0.23999999463558197
    # print(round(value, 2))


    # for ticker, material in prun.loader.materials.items():
    #     print(f"{ticker}: {material.name}, Weight: {material.weight}, Volume: {material.volume}, Category: {material.category_name}")

    #count_pops_in_area()
    daily_count = 2
    ppu = 61000

    mats = prun.ResourceList({
        "MGS": 0.1,
        "LST": 0.01,
        "FEO": 0.81,
        "AUO": 0.96,
        "O": 6.54,
        "H2O": 1.36,
        "HAL": 4.0,
        "LIO": 10.0,
        "ALO": 20.39,
        "SIO": 6.75,
        "CUO": 1.27,
        "HE": 1.0
    }) * daily_count

    pop = prun.Population({
        "engineers": 70,
        "pioneers": 790,
        "settlers": 575,
        "technicians": 340
    })
    mats += pop.get_upkeep()

    cost = mats.get_total_value('NC1', 'buy')
    revenue = ppu * daily_count
    profit = revenue - cost

    print(f"Cost: {cost}, Revenue: {revenue}, Profit: {profit}")

    ll = estimate_company_value("Lumber Liquidators")
    print(f"Lumber Liquidators: ~{ll} credits in the market")


    #all_values = estimate_all_companies_value()
    #for company in all_values:
    #    print(f"Company {company['company_name']} has {company['buy_order_capital']:.0f} credits in buy orders and {company['sell_order_capital']:.0f} credits in sell orders ({company['sell_order_capital_optimistic']:.0f} at listed price), for a total of ~{company['total_capital']:.0f} credits")
        
    burn = ResourceList({
        'DW': 14.4,
        'OVE': 1.8,
        'RAT': 14.4,
        'COF': 1.8,
        'PWO': 0.72
    })

    print(burn.get_total_value('NC1', 'buy'))

    pop = prun.Population({
        "technicians": 40
    })
    upkeep = pop.upkeep * 5
    print(upkeep)
    print(upkeep.cost)

    recipe = prun.loader.get_best_recipe('RSE')
    burn = recipe.inputs*3
    print(f"Burn: {burn}: {burn.cost}, {burn.weight}t, {burn.volume}m3")

    print()

    # materials = prun.loader.materials
    # materials = dict(sorted(materials.items(), key=lambda item: item[1].storage_ratio))

    # counts = {}

    # for ticker, material in materials.items():
    #     target = 35/500
        
    #     if material.storage_ratio not in counts:
    #         counts[material.storage_ratio] = []
    #     counts[material.storage_ratio].append(ticker)


    # lengths = {}

    # for ratio, tickers in counts.items():
    #     lengths[ratio] = len(tickers)

    # length_counts = {}

    # for ratio, count in lengths.items():
    #     count = int(count)
    #     if count not in length_counts:
    #         length_counts[count] = 0
    #     length_counts[count] += lengths[ratio]

    # unique = length_counts[1]
    # non_unique = sum(length_counts.values()) - unique


    # print(json.dumps(length_counts, indent=4))

    # print(f"Unique: {unique}, Non-unique: {non_unique}")

    # print(len(materials.keys()))




    #print(match_storage_ratio(499.5, 185))

    #analyze_local_markets()


    # from prunpy.models.material import Material
    # c = Material('C')
    # print(c.get_value())






# Helper function to calculate the difference between trial queue ratios and target multipliers
def calc_trial_queue_difference(trial_queue, target_multipliers):
    total_multipliers = np.array([entry['total_multiplier'] for entry in trial_queue])
    current_ratios = total_multipliers / total_multipliers.sum()

    target_ratios = np.array([target_multipliers[entry['recipe']] for entry in trial_queue])
    
    # Return the sum of squared differences (a simple distance measure)
    return np.sum((current_ratios - target_ratios) ** 2)

# Function to generate the trial queue based on recipes and target multipliers
def generate_recipe_queue(recipes, target_recipe_multipliers):
    # Initialize the trial queue
    trial_queue = []
    for recipe in recipes:
        trial_queue.append({
            'recipe': recipe,
            'total_multiplier': 1,  # Start with 1 as each recipe must take up at least 1 slot
            'max_multiplier': MAX_RECIPE_SLOT_MULTIPLIER,
            'remaining_slots': NUM_SLOTS - len(recipes)
        })
    print("Initialized trial_queue:")
    for entry in trial_queue:
        print(f"{entry['recipe']}: total_multiplier={entry['total_multiplier']}, max_multiplier={entry['max_multiplier']}")

    # Try to allocate multipliers to recipes based on the distance from target multipliers
    iteration = 1
    while True:
        print(f"\n--- Iteration {iteration} ---")
        best_queue = None
        best_difference = float('inf')

        for entry in trial_queue:
            if entry['total_multiplier'] < entry['max_multiplier']:
                # Temporarily increase the multiplier for testing
                entry['total_multiplier'] += 1
                print(f"Testing by increasing {entry['recipe']} multiplier to {entry['total_multiplier']}")

                # Calculate the difference from target multipliers
                current_difference = calc_trial_queue_difference(trial_queue, target_recipe_multipliers)
                print(f"Difference score: {current_difference}")

                # Keep track of the best trial queue so far
                if current_difference < best_difference:
                    best_difference = current_difference
                    best_queue = [dict(e) for e in trial_queue]
                    print(f"Best queue so far with {entry['recipe']} multiplier increased.")

                # Undo the increment for the next test
                entry['total_multiplier'] -= 1
        
        if best_queue:
            # Update the trial queue with the best queue found
            trial_queue = best_queue
            print(f"Updated trial_queue at the end of iteration {iteration}:")
            for entry in trial_queue:
                print(f"{entry['recipe']}: total_multiplier={entry['total_multiplier']}, max_multiplier={entry['max_multiplier']}")

            # Check if any recipe has reached its max and adjust accordingly
            for entry in trial_queue:
                if entry['total_multiplier'] >= entry['max_multiplier']:
                    # If a recipe reached its max, increase its max and reduce remaining slots
                    entry['max_multiplier'] += MAX_RECIPE_SLOT_MULTIPLIER
                    entry['remaining_slots'] -= 1
                    print(f"{entry['recipe']} reached its max. Increasing max_multiplier to {entry['max_multiplier']} and remaining_slots to {entry['remaining_slots']}")
                    
                    if entry['remaining_slots'] < 0:
                        # No more slots left to allocate
                        print("No more slots available. Stopping allocation.")
                        break
        else:
            # No improvements, stop the loop
            print("No further improvements found. Ending allocation process.")
            break

        iteration += 1

    # Print the final trial queue before distribution
    print("\nFinal trial_queue before distribution:")
    for entry in trial_queue:
        print(f"{entry['recipe']}: total_multiplier={entry['total_multiplier']}, max_multiplier={entry['max_multiplier']}")

    # Now distribute the trial queue into slots
    recipe_queue = []
    for entry in trial_queue:
        remaining_multiplier = entry['total_multiplier']
        while remaining_multiplier > 0:
            multiplier_to_assign = min(remaining_multiplier, MAX_RECIPE_SLOT_MULTIPLIER)
            recipe_queue.append({
                'recipe': entry['recipe'],
                'multiplier': multiplier_to_assign
            })
            remaining_multiplier -= multiplier_to_assign

    return recipe_queue

# Function to pretty print the final recipe queue
def print_recipe_queue(recipe_queue):
    print("\nFinal Recipe Queue:")
    for slot in recipe_queue:
        print(f"{slot['recipe']}: {slot['multiplier']}")




def print_spread_cba():
    sell_run = prun.ResourceList({
        'RSE': 10,
        'RBH': 10,
        'HMS': 60,
        'HSS': 20,
        'MED': 60,
        'TIO': 300,
    })

    for ticker, count in sell_run.resources.items():
        spreadp = prun.loader.get_exchange('NC1').get_good(ticker).spread_percent
        spreada = prun.loader.get_exchange('NC1').get_good(ticker).spread_amount
        total_difference = spreada * count
        print(f"{ticker}: {spreadp:.2f} ({spreada:.2f}), Total for {count} = {total_difference:.2f}")

def find_largest_pop():
    max_pop = {dem: 0 for dem in prun.constants.DEMOGRAPHICS}
    planets = prun.loader.get_all_planets()

    print("Start:")
    for name, planet in planets.items():
        population = planet.get_population_count().population
        for dem, count in population.items():
            if max_pop[dem] < count:
                max_pop[dem] = count
                print(f"New best {dem} on {planet.name}")

    print(max_pop)

def count_pops_in_area():
    planets = prun.loader.get_all_planets()

    # filters out planets whose Planet.get_nearest_exchange() isn't NC1
    planets = {name: planet for name, planet in planets.items() if planet.get_nearest_exchange()[0] == 'NC1'}

    #for name, planet in planets.items():
        #print(f"{planet.name}: {planet.get_population_count().technicians}")

    total = sum([planet.get_population_count().technicians for name, planet in planets.items()])

    technician_upkeep = prun.ResourceList({'HMS': 0.005})*total

    print(f"Total technicians of all planets: {total}, need {technician_upkeep} upkeep daily")

def estimate_company_value(company_name):
    company = prun.Company(company_name)
    
    _ = prun.loader.rawexchangedata
    
    for code, exchange in prun.loader.exchanges.items():
        goods = exchange.goods
        
        own_buy_orders = []
        own_sell_orders = []
        for ticker, good in goods.items():
            for buy_order in good.buy_orders:
                if buy_order['company_name'] == company.name:
                    buy_order = buy_order.copy()
                    buy_order['ticker'] = ticker
                    buy_order['exchange'] = exchange.code
                    own_buy_orders.append(buy_order)

            for sell_order in good.sell_orders:
                if sell_order['company_name'] == company.name:
                    sell_order = sell_order.copy()
                    sell_order['ticker'] = ticker
                    sell_order['exchange'] = exchange.code
                    own_sell_orders.append(sell_order)
    
    total_buy = 0
    for order in own_buy_orders:
        total_buy += order['cost'] * order['count']
    
    total_sell = 0
    for order in own_sell_orders:
        exchange = prun.loader.exchanges[order['exchange']]
        actual_sell_cost = exchange.get_good(order['ticker']).sell_price_for_amount(order['count'])
        total_sell += actual_sell_cost # * order['count']

    total = total_buy + total_sell
    print(f"Company {company.name} has {total_buy} credits in buy orders and {total_sell} credits in sell orders")

    return total

def estimate_all_companies_value():
    companies = {}

    for exchange in prun.loader.exchanges.values():
        goods = exchange.goods

        for ticker, good in goods.items():
            # Process buy orders
            for buy_order in good.buy_orders:
                company_name = buy_order['company_name']
                if company_name not in companies:
                    companies[company_name] = {
                        'buy_order_capital': 0,
                        'sell_order_capital': 0,
                        'sell_order_capital_optimistic': 0,
                        'company_name': company_name
                    }

                buy_order_capital = buy_order['cost'] * buy_order['count']
                companies[company_name]['buy_order_capital'] += buy_order_capital

            # Process sell orders
            for sell_order in good.sell_orders:
                company_name = sell_order['company_name']
                if company_name not in companies:
                    companies[company_name] = {
                        'buy_order_capital': 0,
                        'sell_order_capital': 0,
                        'sell_order_capital_optimistic': 0,
                        'company_name': company_name
                    }

                # Actual sell cost based on the exchange's pricing
                actual_sell_cost = exchange.get_good(ticker).sell_price_for_amount(sell_order['count'])
                companies[company_name]['sell_order_capital'] += actual_sell_cost

                # Optimistic sell cost using the listed cost
                sell_order_capital_optimistic = sell_order['cost'] * sell_order['count']
                companies[company_name]['sell_order_capital_optimistic'] += sell_order_capital_optimistic

    # Calculate total capital for each company
    for company in companies.values():
        company['total_capital'] = company['buy_order_capital'] + company['sell_order_capital']

    # Sort by descending total capital
    companies = sorted(companies.values(), key=lambda x: x['total_capital'], reverse=False)

    return companies

def match_storage_ratio(weight_or_ratio, volume=None):
    if volume is not None:
        target_ratio = weight_or_ratio / volume
    else:
        target_ratio = weight_or_ratio

    tolerance = 0.005

    results = []
    for ticker, material in prun.loader.materials.items():
        if math.isclose(material.storage_ratio, target_ratio, rel_tol=tolerance):
            results.append(ticker)
    return results
    

def analyze_local_markets():
    # market_data = {}

    # for name, planet in prun.loader.planets.items():
    #     if planet.rawdata.get('HasLocalMarket') == True:
    #         print(name)
    #         try:
    #             rawdata = prun.fio.request("GET", f"/localmarket/planet/{planet.name}")
    #             market_data[name] = rawdata
    #         except:
    #             print(f"Failed to get market data for {planet.name}")
    #             pass

    # # Save market data to market_data.json
    # with open('market_data.json', 'w') as f:
    #     json.dump(market_data, f)

    # Load it again
    with open('market_data.json', 'r') as f:
        market_data = json.load(f)

    # for name, exchange in prun.loader.exchanges.items():
    #     market_data[name] = exchange.get_raw_local_market_data()

    exchange_market_data = {}
    exchange_names = []
    for code, exchange in prun.loader.exchanges.items():
        market_name = exchange.name.replace(" Commodity Exchange", "")
        if not market_name.endswith(" Station"):
            market_name += " Station"
        #market_name = market_name.replace(" ", "%20")
        exchange_names.append(market_name)

        try:
            response = requests.get(f"https://rest.fnar.net/localmarket/planet/{market_name}", headers={"accept": "application/json"})

            if response.status_code == 200:
                rawdata = response.json()
                market_data[market_name] = rawdata
        except:
            print(f"Failed to get market data for {market_name}")
    


    shipping_ads = []

    for name, rawdata in market_data.items():
        shipping_ads += rawdata.get('ShippingAds', [])
    


    #print(json.dumps(shipping_ads, indent=4))
    for ad in shipping_ads:
        origin = ad.get('OriginPlanetName')
        destination = ad.get('DestinationPlanetName')
        ratio = ad.get('CargoWeight') / ad.get('CargoVolume')
        materials = match_storage_ratio(ratio)
        company = ad.get('CreatorCompanyName')
        company_code = ad.get('CreatorCompanyCode')

        if len(materials) > 4:
            materials = f"[{len(materials)} possible materials]"

        if len(materials) == 0:
            #print(ad)
            materials = "[Unknown]"
            pass

        if len(materials) == 1:
            materials = materials[0]

            material_class = prun.loader.materials[materials]
            count = round(ad.get('CargoWeight') / material_class.weight, 0)
            materials = f"{count:.0f} {materials}"

        print(f" {materials} from {origin} -> {destination} by {company} ({company_code})")

def print_fertile_planets():
    planets = loader.get_all_planets()

    fertile_planets = {code: [] for code in loader.exchanges.keys()}

    for name, planet in planets.items():
        if planet.environment['fertility'] > -1:
            exchange, _ = planet.get_nearest_exchange()
            fertile_planets[exchange].append(planet)

    print()
    for exchange_code, exchange_planets in fertile_planets.items():
        print(f"  {exchange_code} fertile planets:")
        exchange_planets.sort(key=lambda planet: planet.environment['fertility'], reverse=True)
        for planet in exchange_planets:
            print(f"    {planet.shorten_name(10):<10}: {planet.environment['fertility']:<8.2%} {planet.population} {planet.exchange_distance}j->{exchange_code}")
        print()

if __name__ == "__main__":
    main()