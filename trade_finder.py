#!/usr/bin/env python3

import sys
import json
import math

import prunpy as prun

base_cost = 1000
cost_per_jump = 750
liquid_assets = 60000

min_demand = 500
# Expected trade volume in n weeks
min_volume_demand_ratio = 1

ship_specs = {
    "weight": 500,
    "volume": 500,
}

def find_trades(origin):

    exchanges = prun.loader.get_all_exchanges()

    oex = exchanges[origin]
    destinations = {}
    for code, exchange in exchanges.items():
        if code == origin: continue
        dex = exchange

        dex.distance = prun.pathfinding.jump_distance(oex.system_natural_id, dex.system_natural_id)
        destinations[dex.ticker] = dex
        #print(f"{code}: {dex.name} at distance {dex.distance}")


    # First pass: filter to only profitable routes
    for code, dex in destinations.items():
        dex.profitable_routes = []
        # Check all materials
        for material_ticker in exchanges[origin].goods:
            og = oex.get_good(material_ticker)
            dg = dex.get_good(material_ticker)
            
            if og.buy_price == 0: continue
            if dg.sell_price == 0: continue
            if dg.demand < min_demand: continue
            if dg.demand < dg.rawdata['Traded']*min_volume_demand_ratio: continue

            route = {
                "origin": oex,
                "destination": dex,
                "material": material_ticker,
                "profit_per_unit": dg.sell_price - og.buy_price,
                "profit_ratio": dg.sell_price / og.buy_price,
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
            material = prun.loader.get_material(route['material'])

            buyable_orders = route['origin_good'].sell_orders.copy()
            sellable_orders = route['destination_good'].buy_orders.copy()

            for buyable_order in buyable_orders:
                buyable_order['material'] = route['material']

            for sellable_order in sellable_orders:
                sellable_order['material'] = route['material']

            # Pop off orders with too low buy volume to be reliable
            if sellable_orders:
                while route['destination_good'].rawdata['Traded']*min_volume_demand_ratio < (sellable_orders[0]['count'] or 0):
                    sellable_orders.pop(0)
                    if not sellable_orders: break

            # loop until either is empty
            while len(buyable_orders) > 0 and len(sellable_orders) > 0:
                if buyable_orders[0]['cost'] >= sellable_orders[0]['cost']: break

                amount = min(buyable_orders[0]['count'], sellable_orders[0]['count'])
                profit_per_unit = sellable_orders[0]['cost'] - buyable_orders[0]['cost']
                profit_ratio = sellable_orders[0]['cost'] / buyable_orders[0]['cost']

                trades.append({
                    'buy': buyable_orders[0].copy(),  # copy to avoid reference issues
                    'sell': sellable_orders[0].copy(),  # copy to avoid reference issues
                    'material': route['material'],
                    'amount': amount,
                    'profit_per_unit': profit_per_unit,
                    'profit_ratio': profit_ratio,
                })

                if buyable_orders[0]['count'] > sellable_orders[0]['count']:
                    buyable_orders[0]['count'] -= amount
                    sellable_orders.pop(0)
                elif buyable_orders[0]['count'] < sellable_orders[0]['count']:
                    sellable_orders[0]['count'] -= amount
                    buyable_orders.pop(0)
                else:
                    buyable_orders.pop(0)
                    sellable_orders.pop(0)

                while len(buyable_orders) > 0 and buyable_orders[0]['count'] == None: buyable_orders.pop(0)
                while len(sellable_orders) > 0 and sellable_orders[0]['count'] == None: sellable_orders.pop(0)

        # sort trades by profit ratio in descending order
        trades.sort(key=lambda x: x['profit_ratio'], reverse=True)
        #print(json.dumps(trades, indent=4))

        remaining_volume = ship_specs['volume']
        remaining_weight = ship_specs['weight']
        remaining_credits = liquid_assets
        approved_trades = []

        for trade in trades:
            material = prun.loader.get_material(trade['buy']['material'])

            max_units = get_max_space_remaining(trade, material, remaining_weight, remaining_volume, remaining_credits)

            if max_units < trade['amount']:
                # Trade is too large, only take what can fit
                trade['amount'] = max_units
            
            remaining_volume -= trade['amount'] * material.volume
            remaining_weight -= trade['amount'] * material.weight
            remaining_credits -= trade['amount'] * trade['buy']['count']
            
            if trade['amount'] > 0:
                approved_trades.append(trade)
        
        

        cost = liquid_assets - remaining_credits
        weight = ship_specs['weight'] - remaining_weight
        volume = ship_specs['volume'] - remaining_volume

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
            total_profit_ratio = (trade_job['adjusted_profit']+trade_job['cost']) / trade_job['cost']
            print(f"{origin}->{dex.ticker}: {trade_job['adjusted_profit']:.0f}c ({total_profit_ratio*100:.2f}%) profit, ({trade_job['distance']} jumps, {trade_job['cost']:.0f}c, {trade_job['weight']:.2f} kg, {trade_job['volume']:.2f} m3)")
            for trade in trade_job['trades']:
                print(f"{trade['amount']:>5} {trade['material']:<3}: {trade['buy']['count']:.2f} - {trade['sell']['count']:.2f} -> {trade['profit_per_unit']:.2f} ({trade['profit_ratio']*100:.2f}% profit, {dex.goods[trade['material']].demand} demand, {dex.goods[trade['material']].rawdata['Traded']} volume)")
            print()

        

def get_max_space_remaining(trade, material, remaining_weight, remaining_volume, remaining_credits):
    from prunpy.models.material import Material
    if not isinstance(material, prun.Material):
        material = prun.loader.get_material(material)
    
    if material.volume == 0:
        max_by_volume = float('inf')
    else:
        max_by_volume = int(remaining_volume / material.volume)

    if material.weight == 0:
        max_by_weight = float('inf')
    else:
        max_by_weight = int(remaining_weight / material.weight)

    max_by_cost   = int(remaining_credits / trade['buy']['count'])
    max_units = min(max_by_volume, max_by_weight, max_by_cost)
    return max_units


def get_fuel_cost(jumps):
    return base_cost + cost_per_jump * jumps


def main():
    #origin = sys.argv[1] if len(sys.argv) > 1 else "NC1"
    
    exchanges = prun.loader.get_all_exchanges()
    for code, exchange in exchanges.items():
        find_trades(code)

if __name__ == "__main__":
    main()
