import prunpy as prun

def find_largest_pop():
    max_pop = {dem: 0 for dem in prun.constants.DEMOGRAPHICS}
    planets = prun.importer.get_all_planets()

    print("Start:")
    for name, planet in planets.items():
        population = planet.get_population_count().population
        for dem, count in population.items():
            if max_pop[dem] < count:
                max_pop[dem] = count
                print(f"New best {dem} on {planet.name}")

    print(max_pop)



def main():
    #find_largest_pop()

    buildings = prun.importer.get_all_buildings()

    for ticker, building in buildings.items():
        print(f"{ticker}: {building.planet.name}: {building.get_daily_maintenance()}")














if __name__ == "__main__":
    main()