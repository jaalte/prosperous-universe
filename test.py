import prunpy as prun
import json
import math

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


def main():
    #find_largest_pop()

    buildings = prun.loader.get_all_buildings()

    # for ticker, building in buildings.items():
    #     print(f"{ticker}: {building.planet.name}: {building.get_daily_maintenance()}")

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


    all_values = estimate_all_companies_value()
    for company in all_values:
        print(f"Company {company['company_name']} has {company['buy_order_capital']:.0f} credits in buy orders and {company['sell_order_capital']:.0f} credits in sell orders ({company['sell_order_capital_optimistic']:.0f} at listed price), for a total of ~{company['total_capital']:.0f} credits")
        

if __name__ == "__main__":
    main()