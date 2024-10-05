#!/usr/bin/env python3

import re
import sys
import json
import prunpy as prun

# Global variables to hold data
resources = {}
MARKET = "NC1"  # Declare the market variable

# Load resources from API data and refactor into a dictionary
def load_resources():
    global resources

    # Fetch materials data
    materials = prun.fio.request("GET", "/material/allmaterials", cache=60*60*24)

    # Initialize resources with materials data
    for material in materials:
        ticker = material['Ticker']
        resources[ticker] = {
            'name': material['Name'],
            'category': material['CategoryName'],
            'weight': float(material['Weight']),
            'volume': float(material['Volume']),
            'prices': {
                'MMBuy': None,
                'MMSell': None,
                'average': None,
                'askAmt': None,
                'askPrice': None,
                'askAvail': None,
                'bidAmt': None,
                'bidPrice': None,
                'bidAvail': None,
                'manufactured': None
            },
            'bestRecipe': None,
            'craftTime': None  # Initialize craftTime to None
        }

    # Fetch prices data
    prices = prun.fio.request("GET", "/csv/prices", response_format="csv", cache=900)

    # Update resources with prices data
    for price in prices:
        ticker = price['Ticker']
        if ticker in resources:
            market_tag = f"{MARKET}-"
            if any(market_tag in key for key in price.keys()):
                resources[ticker]['prices'].update({
                    'MMBuy': float(price['MMBuy']) if price['MMBuy'] else None,
                    'MMSell': float(price['MMSell']) if price['MMSell'] else None,
                    'average': float(price[f'{MARKET}-Average']) if price[f'{MARKET}-Average'] else None,
                    'askAmt': float(price[f'{MARKET}-AskAmt']) if price[f'{MARKET}-AskAmt'] else None,
                    'askPrice': float(price[f'{MARKET}-AskPrice']) if price[f'{MARKET}-AskPrice'] else None,
                    'askAvail': float(price[f'{MARKET}-AskAvail']) if price[f'{MARKET}-AskAvail'] else None,
                    'bidAmt': float(price[f'{MARKET}-BidAmt']) if price[f'{MARKET}-BidAmt'] else None,
                    'bidPrice': float(price[f'{MARKET}-BidPrice']) if price[f'{MARKET}-BidPrice'] else None,
                    'bidAvail': float(price[f'{MARKET}-BidAvail']) if price[f'{MARKET}-BidAvail'] else None,
                })

# Helper function to format numbers
def fm(num):
    return ('{:.2f}'.format(num)).rstrip('0').rstrip('.') if isinstance(num, float) else str(num)

# Function to parse input string into a list of (quantity, ticker) pairs
def parse_input(input_string):
    # Sort tickers by length in descending order to prioritize longer tickers
    sorted_tickers = sorted(resources.keys(), key=len, reverse=True)

    # Create a regex pattern that matches any of the tickers
    pattern = r'\b(\d+)\s*x?\s*({})\b'.format('|'.join(re.escape(ticker) for ticker in sorted_tickers))

    # Find all matches of the pattern
    matches = re.findall(pattern, input_string)

    recognized_tickers = {ticker for _, ticker in matches}

    # Check for unrecognized tickers
    unrecognized = re.findall(r'(\d+\s*x?\s*[A-Z0-9]+)', input_string)
    for item in unrecognized:
        quantity, ticker = re.findall(r'(\d+)\s*x?\s*([A-Z0-9]+)', item)[0]
        if ticker not in recognized_tickers:
            print(f"Unrecognized material ticker: {ticker}")

    return [(int(quantity), ticker) for quantity, ticker in matches]
# Function to calculate and print the table
def estimate_costs_volumes(input_string):
    items = parse_input(input_string)

    total_mass = 0
    total_volume = 0
    total_cost = 0

    print(f"{'Resource':<10} {'Count':<6} {'MPU':<6} {'VPU':<6} {'CPU':<8} {'TM':<8} {'TV':<8} {'TC':<10}")
    print("="*68)

    for count, ticker in items:
        if ticker in resources:
            mpu = resources[ticker]['weight']
            vpu = resources[ticker]['volume']
            cpu = resources[ticker]['prices']['askPrice'] if resources[ticker]['prices']['askPrice'] else 0

            tm = mpu * count
            tv = vpu * count
            tc = cpu * count

            total_mass += tm
            total_volume += tv
            total_cost += tc

            print(f"{ticker:<10} {count:<6} {fm(mpu):<6} {fm(vpu):<6} {fm(cpu):<8} {fm(tm):<8} {fm(tv):<8} {fm(tc):<10}")

    print("="*68)
    print(f"{'Total':<40} {fm(total_mass):<8} {fm(total_volume):<8} {fm(total_cost):<10}")

# Main script
if __name__ == "__main__":
    # Load the data once
    load_resources()

    # Concatenate all script arguments into one input string
    input_string = " ".join(sys.argv[1:])

    # Estimate costs and volumes
    estimate_costs_volumes(input_string)
