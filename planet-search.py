#!/usr/bin/env python3

import json
import sys
from termcolor import colored

import prunpy as prun
color = prun.terminal_color_scale

COLONIZED_POPULATION_THRESHOLD = 1000

def parse_arguments():
    # if len(sys.argv) < 2:
    #     print("Usage: python planet-finder.py <planet_name> or python planet-finder.py search <RESOURCE1> <RESOURCE2> ... [Fertile|Infertile|Colonized|Uncolonized]")
    #     sys.exit(1)

    args = list(sys.argv[1:])
    terms = {}

    # Identify tickers
    tickers = prun.loader.material_ticker_list
    terms['resources'] = []
    for arg in args.copy():
        if arg.upper() in tickers:
            terms['resources'].append(arg)
            args.remove(arg)

    # Identify fertility filter, case insensitive
    terms['fertility'] = None
    for arg in args.copy():
        if arg.lower() in ['fertile', 'infertile']:
            if arg == 'fertile':
                terms['fertility'] = True
            else:
                terms['fertility'] = False
            args.remove(arg)


    # Identify colonized filter, case insensitive
    terms['colonized'] = None
    for arg in args.copy():
        if arg.lower() in ['colonized', 'uncolonized']:
            if arg == 'colonized':
                terms['colonized'] = True
            else:
                terms['colonized'] = False
            args.remove(arg)

    terms['planet_whitelist'] = []
    for arg in args.copy():
        planet = None
        try:
            planet = prun.loader.get_planet(arg)
        except:
            pass
        
        if planet is not None:
            terms['planet_whitelist'].append(planet.natural_id)
            args.remove(arg)

    if len(args) > 0:
        print(f"Unrecognized arguments: {args}")
        sys.exit(1)

    return terms

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

def print_terms(terms):
    header_string = "Searching for planets..."

    resources_string = ""
    if len(terms['resources']) > 0:
        resources_string = "\n  Resources: " + ", ".join(terms['resources'])

    # "Ability to grow plants" or "No fertility" based on value
    fertility_string = ""
    if terms['fertility'] is not None:
        fertility_string = "\n  Ability to grow plants" if terms['fertility'] else "\n  No fertility"

    colonized_string = ""
    if terms['colonized'] is not None:
        colonized_string = "\n  Colonized" if terms['colonized'] else "\n  Uncolonized"

    # "Within all planets" or "Within these planets" if whitelist is not empty
    planet_string = "\n  Within all planets"
    if len(terms['planet_whitelist']) > 0:
        planet_string = f"\n  Within these planets: {', '.join(terms['planet_whitelist'])}"


    print(
        f"{header_string}"
        f"{resources_string}"
        f"{fertility_string}"
        f"{colonized_string}"
        f"{planet_string}"
    )

def apply_filters(planets, terms):

    if len(terms['planet_whitelist']) > 0:
        planets = filter_planets(planets, lambda p: p.natural_id in terms['planet_whitelist'], "that aren't in the whitelist")

    if len(terms['resources']) > 0:
        def resource_condition(planet):
            planet_resources = [ticker for ticker in planet.resources.keys()]
            return all(resource in planet_resources for resource in terms['resources'])
        planets = filter_planets(planets, resource_condition, "that don't have required resources")

    if terms['fertility'] is not None:
        def fertity_condition(planet):
            if terms['fertility'] is None: return True
            if planet.environment['fertility'] == -1:
                fertile = False
            else:
                fertile = True
            return fertile == terms['fertility']
        planets = filter_planets(planets, fertity_condition, "that aren't fertile")

    if terms['colonized'] is not None:
        def colonized_condition(planet):
            if terms['colonized'] is None: return True
            if planet.population.total < COLONIZED_POPULATION_THRESHOLD:
                colonized = False
            else:
                colonized = True
            return colonized == terms['colonized']
        planets = filter_planets(planets, colonized_condition, f"that have less than {COLONIZED_POPULATION_THRESHOLD} population")

    return planets

def filter_planets(planets, condition, message):
    """
    Filters the planets list based on a given condition and prints a summary message.

    Parameters:
    planets (list): The list of planets to be filtered.
    condition (function): A function that returns True for elements to keep.
    message (str): The message describing the filter being applied.

    Returns:
    list: The filtered list of planets.
    """
    prior_count = len(planets)
    planets = [planet for planet in planets if condition(planet)]
    diff = prior_count - len(planets)
    pct = diff / prior_count * 100
    print(f"Removed {diff} ({pct:>.0f}%) planets {message}")
    return planets

def main():

    # Terms worth adding:
    #  Blacklists
    #  COGC
    #  Nearest exchanges
    #  Exchange distance
    terms = parse_arguments()
    #print_terms(terms)

    print(json.dumps(terms, indent=4))

    planets = prun.loader.get_all_planets()
    planets = list(planets.values())
    #if len(terms['planet_whitelist']) > 0:
        

    planets = apply_filters(planets, terms)

    for planet in planets:
        print_planet_info(planet)
    


    return

if __name__ == "__main__":
    main()
