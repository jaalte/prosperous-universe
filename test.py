import prunpy as prun

def find_largest_pop():
    max_pop = {dem: 0 for dem in prun.constants.DEMOGRAPHICS}
    planets = prun.loader.get_all_planets()

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

    buildings = prun.loader.get_all_buildings()

    # for ticker, building in buildings.items():
    #     print(f"{ticker}: {building.planet.name}: {building.get_daily_maintenance()}")

    from prunpy.models.recipe_tree import RecipeTreeNode

    recipe = prun.loader.get_best_recipe('WCB')

    root_node = RecipeTreeNode(
        recipe=recipe,
        priority_mode='profit_ratio',
        include_worker_upkeep=True
    )

    print(root_node)

    # materials = prun.ResourceList("8 COF, 7 CU, 17 FE, 46 GC, 114 H2O, 2 KOM, 13 LST, 7 MG, 8 NL, 3 PWO, 79 RAT, 7 S, 55 SIO")
    # materials += prun.ResourceList("5 COF, 34 DW, 5 OVE, 2 PWO, 34 RAT")
    # print(materials)

    planets = prun.loader.get_all_planets()
    minable_resources = set()
    for name, planet in planets.items():
        for ticker, resource in planet.resources.items():
            minable_resources.add(ticker)
    
    print(minable_resources)

    for resource in minable_resources:
        







if __name__ == "__main__":
    main()