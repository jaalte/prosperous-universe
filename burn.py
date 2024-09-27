import pyperclip
import json
import re
import sys
import prunpy as prun

INVALID_CLIPBOARD_ERROR = """
    No valid burn data found in clipboard.
    You need to copy the text from XIT BURN_PlanetName,
    from the "Needs" header to the last "Days" entry.
"""

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

    if len(data_dict) == 0:
        print(INVALID_CLIPBOARD_ERROR)
        sys.exit(1)

    # Return the dictionary
    return data_dict

def main():
    parsed_data = parse_clipboard_data()

    # Corrected iteration over the values in the parsed_data dictionary
    burn_rate = prun.ResourceList({rate['ticker']: rate['production'] for rate in parsed_data.values()})
    #needed = prun.ResourceList({rate['ticker']: rate['needed'] for rate in parsed_data.values()})
    inv = prun.ResourceList({rate['ticker']: rate['inventory'] for rate in parsed_data.values()})

    # Subtract 1 from each resource since estimate doesn't account for time until consumption
    # Also helps lessen impact of travel times
    inv -= prun.ResourceList({rate['ticker']: 1 for rate in parsed_data.values()})
    inv = inv.prune_negatives()

    # target_days is arg1
    target_days = float(sys.argv[1]) if len(sys.argv) > 1 else 7.0

    needed = burn_rate.invert() * target_days
    needed -= inv
    needed = needed.prune_negatives().ceil()

    print(f"Supplies needed: {needed}")
    print(f"Cost: {needed.get_total_value('NC1', 'buy'):.0f}")
    print(f"Weight: {needed.get_total_weight():.2f}")
    print(f"Volume: {needed.get_total_volume():.2f}")


if __name__ == "__main__":
    main()
