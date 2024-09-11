import prunpy as prun

USERNAME = 'fishmodem'
PLANET = 'Montem'

def main():
    planet = prun.loader.get_planet(PLANET)
    base = prun.RealBase(planet.natural_id, USERNAME)

    hb2_mats = prun.Building('HB2', planet).construction_materials
    clf_mats = prun.Building('CLF', planet).construction_materials

    print(f"HB2: {hb2_mats}")
    print(f"2xCLF: {clf_mats*2}")

    daily_burn = prun.ResourceList({
        'GC': 14.41,
        'NL': 2.4,
    })

    days = 4
    print(f"{days} days of new burn: {daily_burn*days}")
    #print(f"...of existing burn: {daily_burn}")

    total = hb2_mats + clf_mats*2 + daily_burn*days

    print(f"\nTotal: {total}")
    print(f"Cost: {total.get_total_value('NC1', 'buy')}")

if __name__ == '__main__':
    main()