import json
import re
import sys
import argparse
import prunpy as prun
from prunpy import loader

def main():
    parser = argparse.ArgumentParser(description='Calculate resource burn requirements for a planet')
    parser.add_argument('planet', help='Planet identifier')
    parser.add_argument('--days', type=float, default=7.0, help='Target number of days (default: 7)')
    parser.add_argument('--weight', type=float, help='Target weight to expand to')
    parser.add_argument('--volume', type=float, help='Target volume to expand to')
    args = parser.parse_args()

    # Planet is arg1, an error will be thrown if invalid planet
    planet = loader.get_planet(args.planet)
    
    username = loader.get_username()
    base = prun.RealBase(planet.natural_id, username)
    burn_rate = base.get_daily_burn()
    pop_consumption = base.get_daily_population_maintenance()
    burn_rate -= pop_consumption
    inventory = base.storage

    # Calculate needed resources based on expansion method
    if args.weight is not None or args.volume is not None:
        # Use weight/volume expansion to get total needed
        burn_rate = burn_rate.invert()
        needed = burn_rate.expand(weight=args.weight, volume=args.volume)
        needed = needed.prune_negatives().floor()
    else:
        # Use days expansion (default behavior)
        needed = burn_rate.invert() * args.days
        needed -= inventory  # Only subtract inventory for days-based calculation
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