#!/usr/bin/env python3

import requests
import time
import datetime
import subprocess
from threading import Timer

# Read API key from file
try:
    with open('./apikey.txt', 'r') as file:
        api_key = file.read().strip()
except Exception as e:
    print(f"Error reading API key: {e}")
    exit(1)

# Check if API key is read correctly
if not api_key:
    print("API key is empty or not read correctly.")
    exit(1)

# Your username
username = "fishmodem"
api_url = f"https://rest.fnar.net/production/{username}"
headers = {
    "accept": "application/json",
    "Authorization": api_key
}

# Dictionary to track scheduled notifications
scheduled_notifications = {}

def notify(message):
    # Trigger knotify
    subprocess.run(["knotify4", "--title", "Production Notification", "--text", message])

def schedule_notification(order_id, preemptive_message, system_message, completion_time):
    # Schedule a notification
    current_time = time.time()
    delay = completion_time - current_time
    if delay > 0:
        timer = Timer(delay, notify, [system_message])
        timer.start()
        scheduled_notifications[order_id] = timer
        print(preemptive_message)  # Print the preemptive notification

def clear_notifications():
    # Cancel all scheduled notifications
    for timer in scheduled_notifications.values():
        timer.cancel()
    scheduled_notifications.clear()

def format_eta(completion_time):
    current_time = time.time()
    delta = datetime.timedelta(seconds=(completion_time - current_time))
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"in {int(hours)}:{int(minutes):02d}"

def check_production():
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        production_lines = response.json()
        for line in production_lines:
            for order in line['Orders']:
                order_id = order['ProductionLineOrderId']
                completion_epoch_ms = order['CompletionEpochMs']
                if completion_epoch_ms is not None:
                    completion_time = completion_epoch_ms / 1000
                    planet_name = line['PlanetName']
                    standard_recipe = order['StandardRecipeName'].split(':')[0]
                    outputs = ', '.join(f"{output['MaterialAmount']} {output['MaterialTicker']}" for output in order['Outputs'])
                    completion_dt = datetime.datetime.fromtimestamp(completion_time)
                    eta = format_eta(completion_time)
                    preemptive_message = f"New notification queued: {completion_dt.strftime('%-m/%-d %H:%M:%S')} ({eta}) {planet_name}:{standard_recipe} will finish crafting {outputs}"
                    system_message = f"{planet_name}:{standard_recipe} finished crafting {outputs}"

                    if order_id not in scheduled_notifications:
                        schedule_notification(order_id, preemptive_message, system_message, completion_time)
    else:
        print("Failed to fetch production data:", response.status_code, response.text)

def main():
    while True:
        clear_notifications()
        check_production()
        time.sleep(60)

if __name__ == "__main__":
    main()
