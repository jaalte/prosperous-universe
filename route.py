#!/usr/bin/env python3

import json
import math
from fio_api import fio
import fio_utils as utils

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

def main():

    rawsystemstars = fio.request("GET", f"/systemstars", cache=-1)
    systemstars_lookup = {system["SystemId"]: system["NaturalId"] for system in rawsystemstars}

    

    systems = {}
    for rawsystem in rawsystemstars:
        for connection in rawsystem["Connections"]:
            connection["NaturalId"] = systemstars_lookup[connection["ConnectingId"]]
        systems[rawsystem["NaturalId"]] = System(rawsystem)


    for natural_id in systems:
        system = systems[natural_id]
        for connection in system.rawdata["Connections"]:
            new_connections = []
            new_connection = {
                "system": connection["NaturalId"],
                "distance": utils.distance(system.pos, systems[connection["NaturalId"]].pos)
            }
            new_connections.append(new_connection)
        system.connections = new_connections
        del system.rawdata

    print(systems)

    # Fetch from the actual allsystems endpoint (instead of systemstars) to get more info



if __name__ == "__main__":
    main()
