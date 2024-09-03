#!/usr/bin/env python3

import json
import sys
from termcolor import colored

import prunpy as prun
color = prun.terminal_color_scale

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
    filtered_planets = {}
    for name, planet in planets.items():
        match = True
        for f in filters:
            if f.lower() == 'fertile':
                if planet.rawdata['Fertility'] == -1:
                    match = False
                    break
            elif f.lower() == 'infertile':
                if planet.rawdata['Fertility'] != -1:
                    match = False
                    break
            elif f.lower() == 'colonized':
                if planet.get_population_count().pioneers < 1000:
                    match = False
                    break
            elif f.lower() == 'uncolonized':
                if planet.get_population_count().pioneers > 100:
                    match = False
                    break
        if match:
            filtered_planets[name] = planet
    return filtered_planets

def print_planet_info(planet):
    planet_name_string = ""
    if planet.name != planet.natural_id:
        planet_name_string = f"({planet.name})"
    exchange, distance = planet.get_nearest_exchange()

    colonized_status = colored("Colonized", "green") if planet.rawdata["HasAdministrationCenter"] else colored("Uncolonized", "red")
    
    population = planet.get_population_count()
    pioneers = population.pioneers

    print(f"{planet.natural_id} {planet_name_string}")
    print(f"Population: {planet.get_population_string()}")
    print(f"{color(distance,0,10,'.0f',inverse=True)} jumps from {exchange}")

    # Resources
    print(colored("Resources:", "white"))
    for ticker, resource in planet.resources.items():
        print(f"- {ticker}: {color(resource["factor"],0,1,'.2%')}")

    # Fertility
    fertility = planet.rawdata["Fertility"]
    fertility_status = ""
    if fertility == -1:
        fertility_status = colored("Infertile", "red")
    else:
        fertility_status = colored(f"Fertile ({fertility+1:.2%})", "green")
        water = any(ticker == "H2O" for ticker in planet.resources.keys())
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

        planets = prun.importer.get_all_planets()


        for name, planet in planets.copy().items():
            for ticker in required_resources:
                if ticker not in planet.resources.keys():
                    if name in planets.keys():
                        del planets[name]


        # matching_planets = find_planets_with_resources(planets, required_resources)

        # all_planet_data = load_json_data(all_planets_file)
        # updated_planets = []
        # for planet in matching_planets:
        #     planet_info = next((p for p in all_planet_data if p["PlanetName"] == planet["name"] or p["PlanetNaturalId"] == planet["name"]), None)
        #     if planet_info:
        #         updated_planets.append({
        #             "name": planet["name"],
        #             "info": planet_info,
        #             "resources": planet["resources"]
        #         })

        if filters:
            planets = filter_planets(planets, filters)

        if len(planets.keys()):
            print("Planets with all specified resources and their details:")
            for name, planet in planets.items():
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
