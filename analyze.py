#!/usr/bin/env python3

import json
from fio_api import fio
import fio_utils as utils

# Editable global variables
username = "fishmodem"

def main():
    sites = fio.request("GET", f"/sites/{username}")

    # Create Base objects
    bases = []
    for site_data in sites:
        base = utils.Base(site_data)
        bases.append(base)

    # For debugging: Print a summary of each base
    for base in bases:
        print(f"\n{base}\n")
        #print(json.dumps(base.planet.resources, indent=2))

if __name__ == "__main__":
    main()
