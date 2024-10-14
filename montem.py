import prunpy as prun
from prunpy.data_loader import loader
from prunpy.utils.resource_list import ResourceList

USERNAME = 'fishmodem'
PLANET = 'Montem'
MAX_PRODUCTION_RATIO = 0.25

def hms_production_crunch():
    planet = prun.loader.get_planet(PLANET)
    #base = prun.RealBase(planet.natural_id, USERNAME)

    hb2 = prun.Building('HB2', planet)
    chp = prun.Building('CHP', planet)
    clf = prun.Building('CLF', planet)

    hb2_mats = prun.Building('HB2', planet).construction_materials
    chp_mats = prun.Building('CHP', planet).construction_materials
    clf_mats = prun.Building('CLF', planet).construction_materials
    total_mats = hb2_mats + chp_mats + clf_mats*2
    print(f"Total construction materials: {total_mats}")

    chp_recipe = chp.filter_recipes('IND')[0] # \
                    #.apply_multiplier(1.4707)
    clf_recipe = clf.filter_recipes('HMS')[0] # \
                    #.apply_multiplier(1.2373)

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

def calc_material(ticker):
    planet = prun.loader.get_planet(PLANET)
    #base = prun.RealBase(planet.natural_id, USERNAME)
    exchange = loader.exchanges[planet.get_nearest_exchange()[0]]

    recipe = loader.get_material_recipes(ticker)[0]

    print(recipe)
    cost = recipe.inputs.get_total_value('NC1', 'buy')
    revenue = recipe.outputs.get_total_value('NC1', 'sell')
    profit = revenue - cost

    daily_sold = exchange.get_price_history(ticker).average_traded_daily

    print(f"{ticker}: {profit:.0f} ({revenue:.0f} - {cost:.0f}), max {daily_sold*MAX_PRODUCTION_RATIO:.2f}")


def main():
    #hms_production_crunch()
    for ticker in ['HMS', 'HSS', 'LC']:
        calc_material(ticker)

if __name__ == '__main__':
    main()