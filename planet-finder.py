#!/usr/bin/env python3

import json
import sys
from termcolor import colored

planet_resources_file = 'planet-resources.json'
all_planets_file = 'allplanets.json'
origin_planet_id = 'OT-889a'

def load_json_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def find_planets_with_resources(planets, required_resources):
    matching_planets = []
    for planet in planets:
        planet_resources = {resource['type'] for resource in planet['resources']}
        if all(resource in planet_resources for resource in required_resources):
            matching_planets.append(planet)
    return matching_planets

def filter_planets(planets, filters):
    filtered_planets = []
    for planet in planets:
        match = True
        for f in filters:
            if f.lower() == 'fertile':
                if planet['info']['Fertility'] == -1:
                    match = False
                    break
            elif f.lower() == 'infertile':
                if planet['info']['Fertility'] != -1:
                    match = False
                    break
            elif f.lower() == 'colonized':
                if not planet['info']['HasAdministrationCenter']:
                    match = False
                    break
            elif f.lower() == 'uncolonized':
                if planet['info']['HasAdministrationCenter']:
                    match = False
                    break
        if match:
            filtered_planets.append(planet)
    return filtered_planets

def print_planet_info(planet):
    info = planet["info"]
    resources = info["Resources"]
    planet_id = info["PlanetNaturalId"]
    planet_name = f" ({info['PlanetName']})" if info.get("PlanetName") and info.get("Namer") else ""
    faction_name = info.get("FactionName", "Unknown Faction")

    colonized_status = colored("Colonized", "green") if info["HasAdministrationCenter"] else colored("Uncolonized", "red")

    print(f"{planet_id}{planet_name}")
    print(f"{colonized_status} ({faction_name})")

    # Resources
    print(colored("Resources:", "white"))
    for resource in resources:
        resource_type = resource["Ticker"]
        factor = resource["Factor"] * 100
        if factor <= 33:
            color = "red"
        elif factor <= 66:
            color = "yellow"
        else:
            color = "green"
        resource_display = f"- {resource_type}: {factor:.2f}%"
        print(colored(resource_display, color))

    # Fertility
    fertility = info["Fertility"]
    fertility_status = ""
    if fertility == -1:
        fertility_status = colored("Infertile", "red")
    else:
        fertility_status = colored(f"Fertile ({fertility})", "green")
        water = any(res["Ticker"] == "H2O" for res in resources)
        if water:
            fertility_status += ", " + colored("has water", "green")
        else:
            fertility_status += ", " + colored("no water", "red")
    print(fertility_status)
    print("\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python planet-finder.py <planet_name> or python planet-finder.py search <RESOURCE1> <RESOURCE2> ... [Fertile|Infertile|Colonized|Uncolonized]")
        sys.exit(1)

    if sys.argv[1].lower() == "search":
        if len(sys.argv) < 3:
            print("Usage: python planet-finder.py search <RESOURCE1> <RESOURCE2> ... [Fertile|Infertile|Colonized|Uncolonized]")
            sys.exit(1)

        filters = [arg for arg in sys.argv[2:] if arg.lower() in ['fertile', 'infertile', 'colonized', 'uncolonized']]
        required_resources = set(arg for arg in sys.argv[2:] if arg.lower() not in ['fertile', 'infertile', 'colonized', 'uncolonized'])

        planets = load_json_data(planet_resources_file)
        matching_planets = find_planets_with_resources(planets, required_resources)

        all_planet_data = load_json_data(all_planets_file)
        updated_planets = []
        for planet in matching_planets:
            planet_info = next((p for p in all_planet_data if p["PlanetName"] == planet["name"] or p["PlanetNaturalId"] == planet["name"]), None)
            if planet_info:
                updated_planets.append({
                    "name": planet["name"],
                    "info": planet_info,
                    "resources": planet["resources"]
                })

        if filters:
            updated_planets = filter_planets(updated_planets, filters)

        if updated_planets:
            print("Planets with all specified resources and their details:")
            for planet in updated_planets:
                print_planet_info(planet)
        else:
            print("No planets found with all specified resources.")
    else:
        planet_name = sys.argv[1]
        planets = load_json_data(planet_resources_file)
        planet = next((p for p in planets if p["name"] == planet_name), None)

        if planet:
            all_planet_data = load_json_data(all_planets_file)
            planet_info = next((p for p in all_planet_data if p["PlanetName"] == planet_name or p["PlanetNaturalId"] == planet_name), None)
            if planet_info:
                planet_data = {
                    "name": planet_name,
                    "info": planet_info,
                    "resources": planet["resources"]
                }
                print_planet_info(planet_data)
            else:
                print(f"No information found for planet {planet_name}")
        else:
            all_planet_data = load_json_data(all_planets_file)
            planet_info = next((p for p in all_planet_data if p["PlanetName"] == planet_name or p["PlanetNaturalId"] == planet_name), None)
            if planet_info:
                planet_data = {
                    "name": planet_name,
                    "info": planet_info,
                    "resources": []  # No resource info available in planet-resources.json
                }
                print_planet_info(planet_data)
            else:
                print(f"No information found for planet {planet_name}")

if __name__ == "__main__":
    main()
