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

import csv

# Hardcoded CSV data
data = """
origin,destination,time (decimal hours),parsecs
Moria,Gundabad,2.633,6
Gundabad,LB-428,3.067,7
LB-428,LB-599,3.85,9
LB-599,OZ-189,2.95,7
OZ-189,VH-778,4.867,12
VH-778,Hortus,3.5,8
Moria,Gundabad,2.3833333333333333,6
Gundabad,LB-506,2.3166666666666664,6
LB-506,QQ-082,4.15,11
QQ-082,QQ-786,4.766666666666667,13
QQ-786,OP-964,1.8333333333333335,5
OP-964,OP-533,0.9,2
OP-533,XD-436,2.35,6
Moria,TO-392,4.0,8
TO-392,Midway,5.316666666666666,11
Midway,YI-059,3.85,8
YI-059,YI-280,5.4,11
YI-280,YI-715,1.9333333333333333,4
YI-715,YI-683,2.6666666666666665,6
YI-683,YI-705,3.466666666666667,7
YI-705,YI-209,1.7833333333333332,4
YI-209,YI-265,1.8333333333333335,4
YI-265,OY-799,5.516666666666667,12
OY-799,UP-170,3.6666666666666665,8
UP-170,UP-305,1.5666666666666667,3
UP-305,UP-102,4.783333333333333,10
"""

def main():
    systems = utils.get_all_systems()

    reader = csv.DictReader(data.strip().splitlines())

    total_distance = 0
    total_parsecs = 0
    count = 0

    for row in reader:
        origin = row['origin']
        destination = row['destination']
        time = float(row['time (decimal hours)'])
        parsecs = int(row['parsecs'])

        if origin in systems and destination in systems[origin].connections:
            distance = systems[origin].connections[destination]['distance']
            ratio_time_distance = time / distance
            ratio_distance_parsecs = distance / parsecs

            total_distance += distance
            total_parsecs += parsecs
            count += 1

            print(f"{origin}, {destination}, {time}, {distance}, {parsecs}, {ratio_time_distance:.2f}, {ratio_distance_parsecs:.2f}")
        else:
            print(f"Connection not found for {origin} -> {destination}")

    if count > 0:
        average_distance_parsecs = total_distance / total_parsecs
        print(f"\nAverage distance per parsec: {average_distance_parsecs:.2f}")
    else:
        print("\nNo valid connections found.")

if __name__ == "__main__":
    main()

    



if __name__ == "__main__":
    main()
