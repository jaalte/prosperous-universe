#!/usr/bin/env python3

import requests
import csv
import io

# URL to fetch the CSV data
url = "https://rest.fnar.net/csv/prices"

# Headers for the request
headers = {
    "accept": "application/csv"
}

# Constant to determine which market columns to keep
market = "NC1"

# Make the GET request
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Read the CSV data
    data = response.content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(data))

    # Define the columns to keep and their new names based on the market
    columns_to_keep = {
        "Ticker": "Ticker",
        "MMBuy": "MMBuy",
        "MMSell": "MMSell",
        f"{market}-Average": "Average",
        f"{market}-AskAmt": "AskAmt",
        f"{market}-AskPrice": "AskPrice",
        f"{market}-AskAvail": "AskAvail",
        f"{market}-BidAmt": "BidAmt",
        f"{market}-BidPrice": "BidPrice",
        f"{market}-BidAvail": "BidAvail"
    }

    # Filter and rename the columns
    cleaned_data = []
    for row in csv_reader:
        cleaned_row = {new_name: row[old_name] for old_name, new_name in columns_to_keep.items() if old_name in row}
        cleaned_data.append(cleaned_row)

    # Write the cleaned data to prices.csv
    with open("prices.csv", "w", newline='') as file:
        csv_writer = csv.DictWriter(file, fieldnames=columns_to_keep.values())
        csv_writer.writeheader()
        csv_writer.writerows(cleaned_data)

    print("Data successfully written to prices.csv")
else:
    print(f"Failed to retrieve data. Status code: {response.status_code}")
