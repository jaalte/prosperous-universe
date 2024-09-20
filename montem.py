import prunpy as prun

USERNAME = 'fishmodem'
PLANET = 'Montem'

def main():
    planet = prun.loader.get_planet(PLANET)
    base = prun.RealBase(planet.natural_id, USERNAME)


    hb2 = prun.Building('HB2', planet)
    chp = prun.Building('CHP', planet)
    clf = prun.Building('CLF', planet)

    hb2_mats = prun.Building('HB2', planet).construction_materials
    chp_mats = prun.Building('CHP', planet).construction_materials
    clf_mats = prun.Building('CLF', planet).construction_materials
    total_mats = hb2_mats + chp_mats + clf_mats*2
    print(f"Total construction materials: {total_mats}")

    chp_recipe = chp.filter_recipes('IND')[0] \
                    .apply_multiplier(1.4707)
    clf_recipe = clf.filter_recipes('HMS')[0] \
                    .apply_multiplier(1.2373)

    #chp_burn = chp_recipe.daily_burn
    #clf_burn = clf_recipe.daily_burn.remove('IND', quiet=True)

    delta = chp_recipe.daily.delta + clf_recipe.daily.delta*2

    daily_burn = delta.invert().prune_negatives()

    print(f"Daily burn: {daily_burn}")

    days = 4
    total_burn = (daily_burn*days).ceil()
    print(f"{days} days of new burn: {total_burn}")
    #print(f"...of existing burn: {daily_burn}")

    total = total_mats + total_burn

    print(f"\nTotal: {total}")
    print(f"Cost: {total.get_total_value('NC1', 'buy')}")

if __name__ == '__main__':
    main()