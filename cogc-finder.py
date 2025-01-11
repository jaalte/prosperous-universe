import prunpy as prun
import sys
from prunpy.utils.terminal_formatting import terminal_color_scale as color_scale


def find_nearby_with_cogc(cogc, exchange_code):
    planets = prun.loader.get_all_planets()
    filtered_planets = {}
    for name, planet in planets.items():
        if planet.get_nearest_exchange()[0] == exchange_code and planet.cogc == cogc:
            filtered_planets[name] = planet
    planets = filtered_planets
    
    if len(planets) > 0:
        print(f"\n    {cogc} planets near {exchange_code}:")
        for name, planet in planets.items():
            name_string = f"{planet.natural_id}"
            shortened_name = ''
            if planet.natural_id != planet.name:
                MAX_NAME_LENGTH = 9
                if len(planet.name) > MAX_NAME_LENGTH:
                    shortened_name = (planet.name+" "*MAX_NAME_LENGTH)[:MAX_NAME_LENGTH].strip()+'…'
                else:
                    shortened_name = planet.name

            if shortened_name:
                name_string = f"{name_string} ({shortened_name+')':<10}"

            message = (
                f"      {name_string:<21} "
                f"{color_scale(planet.exchange_distance,0,15, ">2", inverse=True)} jumps from "
                f"{planet.get_nearest_exchange()[0]}    "
                f"Population {planet.population}    "
                f"Modifiers: [{planet.get_environment_string()}] "
                f"(~{color_scale(planet.get_building_cost_factor(),1,15,">4.1f",inverse=True)}x cost)    "
                f"Resources: {planet.get_resource_string(separator=', '):<30}    "
            )
            print(message)
        print('\n')


def main():
    if len(sys.argv) > 1:
        exchange_code = sys.argv[1]
    else:
        exchange_code = 'NC1'

    # Pre-load data
    _ = prun.loader.get_exchange_goods()

    for cogc in prun.constants.COGCS:
        find_nearby_with_cogc(cogc, exchange_code)

if __name__ == "__main__":
    main()