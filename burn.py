import pyperclip
import json
import re
import sys
import prunpy as prun
from prunpy import loader

def main():

    if len(sys.argv) < 2:
        print("Usage: python burn.py <planet identifier> <target days>")

    # Planet is arg1, an error will be thrown if invalid planet
    planet_identifier = sys.argv[1]
    planet = loader.get_planet(planet_identifier)
	
    username = loader.get_username()
    base = prun.RealBase(planet.natural_id, username)
    burn_rate = base.get_daily_burn()
    inventory = base.storage
    # target_days is arg2
	
    target_days = float(sys.argv[2]) if len(sys.argv) > 2 else 7.0
    needed = burn_rate.invert() * target_days
    needed -= inventory
    needed = needed.prune_negatives().ceil()

    exchange = prun.loader.get_exchange('NC1')
    total_cost = 0
    for ticker, amount in needed.resources.items():
        good = exchange.get_good(ticker)
        total_cost += good.buy_price_for_amount(amount)

    print(f"Supplies needed: {needed}")
    print(f"Cost: {total_cost:.0f}")
    print(f"Weight: {needed.get_total_weight():.2f}")
    print(f"Volume: {needed.get_total_volume():.2f}")

if __name__ == "__main__":
    main()