#!/usr/bin/env python3

import re
import csv
import sys
import os
import time
import subprocess

# Global variables to hold data
resources = {}
MARKET = "NC1"  # Declare the market variable

# Function to fetch new prices data if the file is missing or older than 15 minutes
def check_and_fetch_prices(prices_filename='all-prices.csv'):
    if not os.path.exists(prices_filename) or (time.time() - os.path.getmtime(prices_filename)) > 900:
        print("Fetching new prices data from the API...")
        with open(prices_filename, 'wb') as file:
            response = subprocess.run(
                ["curl", "-X", "GET", "https://rest.fnar.net/csv/prices", "-H", "accept: application/csv"],
                stdout=file
            )
            if response.returncode != 0:
                print("Error fetching data from the API")
                sys.exit(1)
    else:
        print("Using cached prices data")

# Load resources from prices.csv and materials.csv and refactor into a dictionary
def loadResources(prices_filename='all-prices.csv', materials_filename='materials.csv'):
    global resources

    # Load materials data
    with open(materials_filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            ticker = row['Ticker']
            resources[ticker] = {
                'name': row['Name'],
                'category': row['Category'],
                'weight': float(row['Weight']),
                'volume': float(row['Volume']),
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

    # Load prices data
    with open(prices_filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            ticker = row['Ticker']
            if ticker in resources:
                market_tag = f"{MARKET}-"
                if any(market_tag in key for key in row.keys()):
                    resources[ticker]['prices'].update({
                        'MMBuy': float(row['MMBuy']) if row['MMBuy'] else None,
                        'MMSell': float(row['MMSell']) if row['MMSell'] else None,
                        'average': float(row[f'{MARKET}-Average']) if row[f'{MARKET}-Average'] else None,
                        'askAmt': float(row[f'{MARKET}-AskAmt']) if row[f'{MARKET}-AskAmt'] else None,
                        'askPrice': float(row[f'{MARKET}-AskPrice']) if row[f'{MARKET}-AskPrice'] else None,
                        'askAvail': float(row[f'{MARKET}-AskAvail']) if row[f'{MARKET}-AskAvail'] else None,
                        'bidAmt': float(row[f'{MARKET}-BidAmt']) if row[f'{MARKET}-BidAmt'] else None,
                        'bidPrice': float(row[f'{MARKET}-BidPrice']) if row[f'{MARKET}-BidPrice'] else None,
                        'bidAvail': float(row[f'{MARKET}-BidAvail']) if row[f'{MARKET}-BidAvail'] else None,
                    })

# Helper function to format numbers
def fm(num):
    return ('{:.2f}'.format(num)).rstrip('0').rstrip('.') if isinstance(num, float) else str(num)

# Function to parse input string into a list of (quantity, ticker) pairs
def parse_input(input_string):
    # Find all matches of the pattern: number followed by a ticker
    matches = re.findall(r'(\d+)\s*x?\s*([A-Z]+)', input_string)
    return [(int(quantity), ticker) for quantity, ticker in matches]

# Function to calculate and print the table
def estimate_costs_volumes(input_string):
    items = parse_input(input_string)

    total_mass = 0
    total_volume = 0
    total_cost = 0

    line_length = 64

    print(f"{'Ticker':<7} {'Count':<6} {'MPU':<6} {'VPU':<6} {'CPU':<8} {'TM':<8} {'TV':<8} {'TC':<10}")
    print("="*line_length)

    for count, ticker in items:
        if ticker in resources:
            mpu = resources[ticker]['weight']
            vpu = resources[ticker]['volume']
            cpu = resources[ticker]['prices']['average'] if resources[ticker]['prices']['average'] else 0

            tm = mpu * count
            tv = vpu * count
            tc = cpu * count

            total_mass += tm
            total_volume += tv
            total_cost += tc

            print(f"{ticker:<7} {count:<6} {fm(mpu):<6} {fm(vpu):<6} {fm(cpu):<8} {fm(tm):<8} {fm(tv):<8} {fm(tc):<10}")

    print("="*line_length)
    print(f"{'Total':<37} {fm(total_mass):<8} {fm(total_volume):<8} {fm(total_cost):<10}")

# Main script
if __name__ == "__main__":
    # Check and fetch the latest prices data if necessary
    check_and_fetch_prices()

    # Load the data once
    loadResources()

    # Concatenate all script arguments into one input string
    input_string = " ".join(sys.argv[1:])

    # Estimate costs and volumes
    estimate_costs_volumes(input_string)
