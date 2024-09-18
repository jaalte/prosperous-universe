from prunpy.constants import DISTANCE_PER_PARSEC

class System:
    def __init__(self, hashid):
        rawdata = loader.systemstars_lookup[hashid]

        self.name = rawdata.get('Name')
        self.natural_id = rawdata.get('NaturalId')
        self.id = rawdata.get('NaturalId')
        self.hash = rawdata.get('SystemId')
        self.pos = {
            'x': rawdata.get('PositionX'),
            'y': rawdata.get('PositionY'),
            'z': rawdata.get('PositionZ'),
        }
        self.sectorid = rawdata.get('SectorId')
        self.subsectorid = rawdata.get('SubSectorId')

        self.connections = {}
        for connection in rawdata.get('Connections', []):
            system_hash = connection["ConnectingId"]
            other_system = loader.systemstars_lookup[system_hash]
            connection_name = other_system.get('Name')
            connection_pos = {
                'x': other_system.get('PositionX'),
                'y': other_system.get('PositionY'),
                'z': other_system.get('PositionZ')
            }
            self.connections[connection_name] = {
                'system': connection_name,
                'distance': distance(self.pos, connection_pos)/DISTANCE_PER_PARSEC,
            }

        self.planets = loader.system_planet_lookup.get(hashid, [])

    def get_route_to(self, system_natural_id):

        # mockup, not init
        route = {
            'systems': [],
            'total_parsecs': 0,
            'total_jumps': 0,
        }

        distance = 0 # in parsecs


        return route


    def __str__(self):
        return f"[System {self.name} ({self.natural_id}), {len(self.connections)} connections, {len(self.planets)} planets]"
