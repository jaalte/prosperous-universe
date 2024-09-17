from prunpy.data_loader import loader

class Container:
    def __init__(self, mass_capacity, volume_capacity):
        self.mass_capacity = mass_capacity
        self.volume_capacity = volume_capacity

    def get_max_capacity_for(self, resource_ticker):
        from prunpy.models.material import Material
        material = loader.get_material(resource_ticker)
        #print(json.dumps(material, indent=4))
        max_by_volume = int(self.volume_capacity / material.volume)
        max_by_mass = int(self.mass_capacity / material.weight)

        return min(max_by_volume, max_by_mass)

# Won't work until API is better reintegrated with username support
class Ship:
    def __init__(self, id):
        ships = fio.request("GET", f"/ship/ships/{USERNAME}", cache=60*60*24)
        #print(json.dumps(ships, indent=4))

        self.rawdata = next((ship for ship in ships if ship.get('Registration') == id), None)

    def get_time_to(self, system_natural_id, reactor):
        distance = self.get_parsecs_to(system_natural_id)
        hours = 0.0318*reactor+0.7763

    def get_fuel_to(self, system_natural_id, reactor):
        distance = self.get_parsecs_to(system_natural_id)
        fuel = 0.0721*reactor-0.0730
