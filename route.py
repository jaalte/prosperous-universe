#!/usr/bin/env python3

import json
import math
import pandas as pd
import numpy as np
from fio_api import fio
import fio_utils as utils

import csv
from sklearn.linear_model import LinearRegression


def main():
    systems = utils.get_all_systems()

    # load jump_data.csv using pandas
    df = pd.read_csv("jump-data.csv")
    jump_data = df.to_dict(orient="records")

    reactor_data = {}

    for row in jump_data:
        origin = row["origin"]
        destination = row["destination"]
        hours = row["hours"]
        fuel = row["fuel"]
        reactor = row["reactor"]

        if origin in systems and destination in systems[origin].connections:
            distance = systems[origin].connections[destination]["distance"]
            fuel_ratio = fuel / distance  # Fuel per parsec
            hours_ratio = distance / hours  # Parsecs per hour

            print(f"{origin} -> {destination}: {distance:.1f} parsecs ({fuel_ratio:.2f} fuel/parsec) in {hours} hours ({hours_ratio:.2f} parsecs/hour) at {reactor*100:.0f}% reactor")

            # Accumulate data for averages
            if reactor not in reactor_data:
                reactor_data[reactor] = {
                    "total_fuel": 0,
                    "total_parsecs": 0,
                    "total_hours": 0,
                    "count": 0
                }
            reactor_data[reactor]["total_fuel"] += fuel
            reactor_data[reactor]["total_parsecs"] += distance
            reactor_data[reactor]["total_hours"] += hours
            reactor_data[reactor]["count"] += 1

        else:
            print(f"Connection not found for {origin} -> {destination}")

    # Calculate and print averages
    reactor_levels = []
    avg_fuel_per_parsec_values = []
    avg_parsecs_per_hour_values = []

    for reactor, data in reactor_data.items():
        avg_fuel_per_parsec = data["total_fuel"] / data["total_parsecs"]
        avg_parsecs_per_hour = data["total_parsecs"] / data["total_hours"]

        reactor_levels.append(reactor * 100)
        avg_fuel_per_parsec_values.append(avg_fuel_per_parsec)
        avg_parsecs_per_hour_values.append(avg_parsecs_per_hour)

        print(f"\nReactor {reactor*100:.0f}%:")
        print(f"  Average: {avg_fuel_per_parsec:.2f} fuel per parsec")
        print(f"  Average: {avg_parsecs_per_hour:.2f} parsecs per hour")

    # Perform linear regression for fuel per parsec
    reactor_levels_np = np.array(reactor_levels).reshape(-1, 1)
    fuel_model = LinearRegression().fit(reactor_levels_np, avg_fuel_per_parsec_values)
    fuel_slope = fuel_model.coef_[0]
    fuel_intercept = fuel_model.intercept_

    # Perform linear regression for parsecs per hour
    speed_model = LinearRegression().fit(reactor_levels_np, avg_parsecs_per_hour_values)
    speed_slope = speed_model.coef_[0]
    speed_intercept = speed_model.intercept_

    print("\nApproximate equations:")
    print(f"Fuel per parsec = {fuel_slope:.4f} * Reactor Level + {fuel_intercept:.4f}")
    print(f"Parsecs per hour = {speed_slope:.4f} * Reactor Level + {speed_intercept:.4f}")


if __name__ == "__main__":
    main()
