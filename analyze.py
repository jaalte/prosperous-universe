#!/usr/bin/env python3

import json
from fio_api import fio

# Global variables
USERNAME = "fishmodem"

class Planet:
    def __init__(self, planet_id):
        self.rawdata = fio.request("GET", f"/planet/{planet_id}")
        self.name = self.rawdata.get('PlanetName')
        self.id = self.rawdata.get('PlanetId')
        self.identifier = self.rawdata.get('PlanetIdentifier')

        # Init resources
        allmaterials = fio.request("GET", f"/material/allmaterials")
        self.resources = {}
        for resource in self.rawdata.get('Resources', []):
        

class Base:
    def __init__(self, rawdata):
        # Store the raw JSON data
        self.rawdata = rawdata

        # Create a Planet object
        self.planet = Planet(planet_id=self.rawdata.get('PlanetId'))

        # Extract and count buildings by their ticker
        self.buildings = {}
        for building in rawdata.get('Buildings', []):
            ticker = building.get('BuildingTicker')
            if ticker:
                if ticker in self.buildings:
                    self.buildings[ticker] += 1
                else:
                    self.buildings[ticker] = 1

    def __repr__(self):
        return f"Base(Planet: {self.planet.name}, Buildings: {self.buildings})"


def main():
    sites = fio.request("GET", f"/sites/{USERNAME}")

    # Create Base objects
    bases = []
    for site_data in sites:
        base = Base(site_data)
        bases.append(base)

    # For debugging: Print a summary of each base
    for base in bases:
        print(base)
        print(json.dumps(base.planet.rawdata, indent=2))

if __name__ == "__main__":
    main()
