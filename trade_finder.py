#!/usr/bin/env python3

import json
import math
from fio_api import fio
import fio_utils as utils

origin = "NC1"
travel_cost = 5000

ship_specs = {
    "weight": 500,
    "volume": 500,
}

""" Example good dict:
{
  "MaterialTicker": "AMM",
  "ExchangeCode": "NC1",
  "MMBuy": 61.0,
  "MMSell": null,
  "PriceAverage": 221.66,
  "AskCount": 6576,
  "Ask": 222.0,
  "Supply": 11518,
  "BidCount": 470,
  "Bid": 200.0,
  "Demand": 39642
}
"""

def main():
    exchanges = utils.get_all_exchanges()

    allmaterials = fio.request("GET", "/material/allmaterials", cache=60*60*24)
    material_lookup = {material['Ticker']: material for material in allmaterials}

    #for code, exchange in exchanges.items():
        #print(f"{code}: {exchange.name}")


    # First pass: filter to only profitable routes
    profitable_routes = []
    # Iterate through other exchanges
    for dest_code, exchange in exchanges.items():
        if dest_code == origin: continue
        oex = exchanges[origin]
        dex = exchanges[dest_code]

        # Check all materials
        for material_ticker in exchanges[origin].goods:
            og = exchanges[origin].goods[material_ticker]
            dg = exchanges[dest_code].goods[material_ticker]
            
            if og['Ask'] is None or og['Ask'] == 0: continue
            if dg['Bid'] is None or dg['Bid'] == 0: continue

            route = {
                "origin": oex,
                "destination": dex,
                "material": material_ticker,
                "profit_per_unit": dg['Bid'] - og['Ask'],
                "origin_good": og,
                "destination_good": dg,
            }

            if route['profit_per_unit'] > 0:
                profitable_routes.append(route)
    

    #for route in profitable_routes:

    

    print(f"{route['origin'].ticker} -> {route['destination'].ticker}: {route['material']}:")
    print(f"    {route['profit_per_unit']:.2f}: {route['origin_good']['Ask']} -> {route['destination_good']['Bid']}")

    # Optional: Check actual trades available to accurately tally bid/ask costs
     # Good to do now since far fewer viable routes

    # Sort in order of profit and group by destination

    # For each destination

if __name__ == "__main__":
    main()
