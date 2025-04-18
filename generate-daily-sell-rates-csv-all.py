#!/usr/bin/env python3

import prunpy as prun
import csv
import time


def main():
    exchanges = ["NC1", "AI1", "CI1", "IC1", "NC2", "CI2"]
    sell_rates = {}

    # Initialize sell_rates with tickers as keys and empty lists as values
    for ticker in prun.loader.material_ticker_list:
        sell_rates[ticker] = []

    # Collect sell rates for all exchanges
    for exchange in exchanges:
        print(f"Processing exchange: {exchange}")
        for ticker in prun.loader.material_ticker_list:
            history = prun.PriceHistory(ticker, exchange)
            avg_traded_daily = round(history.average_traded_daily, 2)
            print(f"{ticker} ({exchange}): {avg_traded_daily} per day")
            sell_rates[ticker].append(avg_traded_daily)

    # Get current date in ISO format
    current_date = time.strftime("%Y-%m-%d")

    # Save sell_rates to CSV file
    filename = f"sell_rates_{current_date}.csv"
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(["ticker"] + exchanges)
        # Write sell rates
        for ticker, rates in sell_rates.items():
            writer.writerow([ticker] + rates)

    print(f"File saved: {filename}")


if __name__ == '__main__':
    main()
