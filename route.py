#!/usr/bin/env python3

import json
import math
from fio_api import fio

""" rawsystem example:
  {
    "Connections": [
      {
        "SystemConnectionId": "01bfaf846e85228ea194e31272c83cf8-f7bf1dac70fc79c9b365accf54b6ef68",
        "ConnectingId": "f7bf1dac70fc79c9b365accf54b6ef68"
      },
      {
        "SystemConnectionId": "01bfaf846e85228ea194e31272c83cf8-3e3dcecc4b0a9a0f03df1d95587e1096",
        "ConnectingId": "3e3dcecc4b0a9a0f03df1d95587e1096"
      }
    ],
    "SystemId": "01bfaf846e85228ea194e31272c83cf8",
    "Name": "CH-771",
    "NaturalId": "CH-771",
    "Type": "K",
    "PositionX": 527.2559814453125,
    "PositionY": 631.3751220703125,
    "PositionZ": 98.09454345703125,
    "SectorId": "sector-31",
    "SubSectorId": "subsector-31-1",
    "UserNameSubmitted": "SAGANAKI",
    "Timestamp": "2024-08-13T16:42:19.074265"
  },
"""


class System:
    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.name = rawdata.get('Name')
        self.id = rawdata.get('NaturalId')
        self.hash = rawdata.get('SystemId')
        self.pos = {
            'x': rawdata.get('PositionX'),
            'y': rawdata.get('PositionY'),
            'z': rawdata.get('PositionZ'),
        }
        
        #self.connections = []
        #for connection in rawdata.get('Connections', []):

    def init_connections(self):
        pass

    def __repr__(self):
        return json.dumps({
            "name": self.name,
            "id": self.id,
            "hash": self.hash,
            "pos": self.pos,
            "connections": getattr(self, 'connections', [])
        }, indent=2)


def distance(pos1, pos2):
    return math.sqrt((pos1['x'] - pos2['x'])**2 + (pos1['y'] - pos2['y'])**2 + (pos1['z'] - pos2['z'])**2)

def main():
    rawsystems = fio.request("GET", f"/systemstars", cache=-1)

    id_lookup = {system["SystemId"]: system["NaturalId"] for system in rawsystems}

    systems = {}
    for rawsystem in rawsystems:
        for connection in rawsystem["Connections"]:
            connection["NaturalId"] = id_lookup[connection["ConnectingId"]]
        systems[rawsystem["NaturalId"]] = System(rawsystem)


    for natural_id in systems:
        system = systems[natural_id]
        for connection in system.rawdata["Connections"]:
            new_connections = []
            new_connection = {
                "system": connection["NaturalId"],
                "distance": distance(system.pos, systems[connection["NaturalId"]].pos)
            }
            new_connections.append(new_connection)
        system.connections = new_connections
        del system.rawdata

    print(systems)



if __name__ == "__main__":
    main()
