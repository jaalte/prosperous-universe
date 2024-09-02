import pyperclip
import json
import re
import sys
import fio_utils as utils

def parse_clipboard_data():
    # Get the clipboard data
    clipboard_data = pyperclip.paste()
    
    # Split the data into lines
    lines = clipboard_data.splitlines()
    
    # Initialize an empty dictionary to store parsed data
    data_dict = {}

    # Variables to track the current state
    current_ticker = None

    # Iterate through the lines and parse the data
    for line in lines:
        # Match the ticker line (e.g., "RAT", "COF", "S", "H2O")
        ticker_match = re.match(r'^[A-Z0-9]{1,3}$', line.strip())
        if ticker_match:
            current_ticker = ticker_match.group()
            continue

        # Match the line with details
        detail_match = re.match(r'^(.*)\s+(-?\d+\.?\d*)\s+\/\s+Day\s+(\d+)\s+(-?\d+)\s+(\d+)\s+Days$', line.strip())
        if detail_match and current_ticker:
            name = detail_match.group(1).strip()
            production = float(detail_match.group(2))
            inventory = int(detail_match.group(3))
            needed = int(detail_match.group(4))
            days_left = int(detail_match.group(5))

            # Store the parsed data in the dictionary
            data_dict[current_ticker] = {
                "ticker": current_ticker,
                "name": name,
                "production": production,
                "inventory": inventory,
                "needed": needed,
                "days_left": days_left
            }

    # Return the dictionary
    return data_dict

def main():
    parsed_data = parse_clipboard_data()

    # Corrected iteration over the values in the parsed_data dictionary
    burn_rate = utils.ResourceList({rate['ticker']: rate['production'] for rate in parsed_data.values()})
    #needed = utils.ResourceList({rate['ticker']: rate['needed'] for rate in parsed_data.values()})
    inv = utils.ResourceList({rate['ticker']: rate['inventory'] for rate in parsed_data.values()})

    # target_days is arg1
    target_days = int(sys.argv[1]) or 7

    needed = burn_rate.invert() * target_days
    needed -= inv
    needed = needed.prune_negatives().ceil()

    print(f"Supplies needed: {needed}")
    print(f"Cost: {needed.get_total_value('NC1', 'buy'):.0f}")
    print(f"Weight: {needed.get_total_weight():.2f}")
    print(f"Volume: {needed.get_total_volume():.2f}")


if __name__ == "__main__":
    main()