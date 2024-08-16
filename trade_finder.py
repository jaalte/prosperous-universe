#!/usr/bin/env python3

import json
import math
from fio_api import fio
import fio_utils as utils
from pathfinding import jump_distance

origin = "NC1" # IC1
base_cost = 1000
cost_per_jump = 750
liquid_assets = 40000

ship_specs = {
    "weight": 500,
    "volume": 500,
}

def main():
    exchanges = utils.get_all_exchanges()

    allmaterials = fio.request("GET", "/material/allmaterials", cache=60*60*24)
    material_lookup = {material['Ticker']: material for material in allmaterials}

    oex = exchanges[origin]
    destinations = {}
    for code, exchange in exchanges.items():
        if code == origin: continue
        dex = exchange

        dex.distance = jump_distance(oex.system_natural_id, dex.system_natural_id)
        destinations[dex.ticker] = dex
        #print(f"{code}: {dex.name} at distance {dex.distance}")


    # First pass: filter to only profitable routes
    for code, dex in destinations.items():
        dex.profitable_routes = []
        # Check all materials
        for material_ticker in exchanges[origin].goods:
            og = oex.goods[material_ticker]
            dg = dex.goods[material_ticker]
            
            if og['Ask'] is None or og['Ask'] == 0: continue
            if dg['Bid'] is None or dg['Bid'] == 0: continue

            route = {
                "origin": oex,
                "destination": dex,
                "material": material_ticker,
                "profit_per_unit": dg['Bid'] - og['Ask'],
                "profit_ratio": dg['Bid'] / og['Ask'],
                "origin_good": og,
                "destination_good": dg,
            }

            if route['profit_per_unit'] > 0:
                dex.profitable_routes.append(route)

    # Optional: Check actual trades available to accurately tally bid/ask costs
     # Good to do now since far fewer viable routes

    # Sort profitable routes by decreasing profit
    for code, dex in destinations.items():
        dex.profitable_routes.sort(key=lambda x: x['profit_ratio'], reverse=True)

    #print(json.dumps(destinations['IC1'].profitable_routes, indent=4))

    for code, dex in destinations.items():
        trades = []
        for route in dex.profitable_routes:
            material = material_lookup[route['material']]

            buyable_orders = route['origin_good']['SellingOrders']
            sellable_orders = route['destination_good']['BuyingOrders']

            # Sort buyable orders from least to most expensive
            buyable_orders.sort(key=lambda x: x['ItemCost'])
            
            # Sort sellable orders from most to least expensive
            sellable_orders.sort(key=lambda x: x['ItemCost'], reverse=True)

            for buyable_order in buyable_orders:
                buyable_order['material'] = route['material']

            for sellable_order in sellable_orders:
                sellable_order['material'] = route['material']

            # loop until either is empty
            while len(buyable_orders) > 0 and len(sellable_orders) > 0:
                if buyable_orders[0]['ItemCost'] >= sellable_orders[0]['ItemCost']: break

                amount = min(buyable_orders[0]['ItemCount'], sellable_orders[0]['ItemCount'])
                profit_per_unit = sellable_orders[0]['ItemCost'] - buyable_orders[0]['ItemCost']
                profit_ratio = sellable_orders[0]['ItemCost'] / buyable_orders[0]['ItemCost']

                trades.append({
                    'buy': buyable_orders[0].copy(),  # copy to avoid reference issues
                    'sell': sellable_orders[0].copy(),  # copy to avoid reference issues
                    'material': route['material'],
                    'amount': amount,
                    'profit_per_unit': profit_per_unit,
                    'profit_ratio': profit_ratio,
                })

                if buyable_orders[0]['ItemCount'] > sellable_orders[0]['ItemCount']:
                    buyable_orders[0]['ItemCount'] -= amount
                    sellable_orders.pop(0)
                elif buyable_orders[0]['ItemCount'] < sellable_orders[0]['ItemCount']:
                    sellable_orders[0]['ItemCount'] -= amount
                    buyable_orders.pop(0)
                else:
                    buyable_orders.pop(0)
                    sellable_orders.pop(0)

                while len(buyable_orders) > 0 and buyable_orders[0]['ItemCount'] == None: buyable_orders.pop(0)
                while len(sellable_orders) > 0 and sellable_orders[0]['ItemCount'] == None: sellable_orders.pop(0)

        # sort trades by profit ratio in descending order
        trades.sort(key=lambda x: x['profit_ratio'], reverse=True)
        #print(json.dumps(trades, indent=4))

        remaining_volume = ship_specs['volume']
        remaining_weight = ship_specs['weight']
        remaining_credits = liquid_assets
        approved_trades = []

        for trade in trades:
            material = material_lookup[trade['buy']['material']]

            max_units = get_max_space_remaining(trade, material, remaining_weight, remaining_volume, remaining_credits)

            if max_units < trade['amount']:
                # Trade is too large, only take what can fit
                trade['amount'] = max_units
            
            remaining_volume -= trade['amount'] * material['Volume']
            remaining_weight -= trade['amount'] * material['Weight']
            remaining_credits -= trade['amount'] * trade['buy']['ItemCost']
            
            if trade['amount'] > 0:
                approved_trades.append(trade)
        
        

        cost = liquid_assets - remaining_credits
        weight = ship_specs['weight']
        volume = ship_specs['volume']

        total_profit = 0
        for trade in approved_trades:
            total_profit += trade['profit_per_unit'] * trade['amount']
        
        adjusted_profit = total_profit - get_fuel_cost(dex.distance)

        dex.trade_job = {
            'trades': approved_trades,
            'cost': cost,
            'weight': weight,
            'volume': volume,
            'distance': dex.distance,
            'total_profit': total_profit,
            'adjusted_profit': adjusted_profit
        }

    # Sort destinations by .trade_job.adjusted profit in descending order (it's a dict, not a list)
    destinations = dict(sorted(destinations.items(), key=lambda item: item[1].trade_job['adjusted_profit'], reverse=True))
    
    for code, dex in destinations.items():
        trade_job = dex.trade_job
        if trade_job['adjusted_profit'] > 0:
            print(f"{dex.ticker}: {trade_job['adjusted_profit']:.2f} profit, ({trade_job['distance']} jumps, {trade_job['weight']:.2f} kg, {trade_job['volume']:.2f} m3)")
            for trade in trade_job['trades']:
                print(f"{trade['amount']:>5} {trade['material']:<3}: {trade['buy']['ItemCost']:.2f} - {trade['sell']['ItemCost']:.2f} -> {trade['profit_per_unit']:.2f} ({trade['profit_ratio']*100:.2f}%)")
            print()

        

def get_max_space_remaining(trade, material, remaining_weight, remaining_volume, remaining_credits):
    max_by_volume = int(remaining_volume / material['Volume'])
    max_by_weight = int(remaining_weight / material['Weight'])
    max_by_cost   = int(remaining_credits / trade['buy']['ItemCost'])
    if material['Ticker'] == 'BWS':
        print(f"max_by_volume: {max_by_volume}, max_by_weight: {max_by_weight}, max_by_cost: {max_by_cost}, cost: {trade['buy']['ItemCost']}")
    max_units = min(max_by_volume, max_by_weight, max_by_cost)
    return max_units


def get_fuel_cost(jumps):
    return base_cost + cost_per_jump * jumps

if __name__ == "__main__":
    main()
