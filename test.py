import prunpy as prun

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