import prunpy as prun
from prunpy import ResourceList
from prunpy import loader
import json
import math
import requests

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

def main():

    buildings = prun.BuildingList({
        #"POL": 4,
        "BMP": 2,
        "CHP": 4,
        "CLF": 4,
        "EXT": 3,
        "FP": 1,
        "PP1": 2,
        "PP3": 5,
    })

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


    for ticker in ['RSE', 'RBH', 'HMS', 'HSS', 'MED', 'TIO']:
        spread = prun.loader.get_exchange('NC1').get_good(ticker).spread_ratio
        print(f"{ticker}: {spread-1:.2%}")

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

if __name__ == "__main__":
    main()