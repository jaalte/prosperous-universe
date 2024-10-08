#!/usr/bin/env python3

import prunpy as prun
import json
import time
import sys

def check_orders():
    own_company = prun.Company('fishnet fabrication')
    _ = prun.loader.rawexchangedata

    own_buy_orders = []
    own_sell_orders = []

    for code, exchange in prun.loader.exchanges.items():
        goods = exchange.goods
        
        for ticker, good in goods.items():
            for buy_order in good.buy_orders:
                if buy_order['company_name'] == own_company.name:
                    print(json.dumps(buy_order, indent=2))
                    buy_order = buy_order.copy()
                    buy_order['ticker'] = ticker
                    buy_order['exchange'] = exchange.code
                    own_buy_orders.append(buy_order)

            for sell_order in good.sell_orders:
                name = sell_order['company_name']
                own_name = own_company.name
                if own_name in name:
                    sell_order = sell_order.copy()
                    sell_order['ticker'] = ticker
                    sell_order['exchange'] = exchange.code
                    own_sell_orders.append(sell_order)

    overcutting_buy_orders = []
    for my_order in own_buy_orders:
        ticker = my_order['ticker']
        all_orders = prun.loader.exchanges[my_order['exchange']].goods[ticker].buy_orders

        for order in all_orders:
            if order['cost'] > my_order['cost']:
                order['mine'] = my_order
                overcutting_buy_orders.append(order)
    
    undercutting_sell_orders = []
    for my_order in own_sell_orders:
        ticker = my_order['ticker']
        all_orders = prun.loader.exchanges[my_order['exchange']].goods[ticker].sell_orders

        for order in all_orders:
            if order['cost'] < my_order['cost']:
                order['mine'] = my_order
                undercutting_sell_orders.append(order)

    if len(overcutting_buy_orders):
        for order in overcutting_buy_orders:
            print(f"{order['company_name']} is overcutting your {order['mine']['ticker']} buy order by {order['mine']['cost'] - order['cost']}! ({order['cost']} vs {order['mine']['cost']})")
    else:
        pass

    if len(undercutting_sell_orders):
        for order in undercutting_sell_orders:
            print(f"{order['company_name']} is undercutting your {order['mine']['ticker']} sell order by {order['mine']['cost'] - order['cost']}! ({order['cost']} vs {order['mine']['cost']})")
    else:
        print("No undercutting sell orders")

def main():
    if any("listen" in arg.lower() for arg in sys.argv):
        while True:
            check_orders()
            time.sleep(15*60+10)  # Sleep for 15 minutes (900 seconds)
    else:
        check_orders()

if __name__ == "__main__":
    main()
