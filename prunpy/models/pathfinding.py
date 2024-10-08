#!/usr/bin/env python3

import csv
import heapq
import os
from prunpy.api import fio
import json

CACHE_FILE = './cache/jump_distance.csv'

# Load the cache when the script is run or imported
def load_cache():
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header
            for row in reader:
                origin, destination, distance = row
                cache[(origin, destination)] = int(distance)
    return cache

cache = load_cache()

def save_to_cache(origin, destination, distance):
    with open(CACHE_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([origin, destination, distance])
    cache[(origin, destination)] = distance

def read_system_links(filename):
    graph = {}
    links = fio.request('GET', '/csv/systemlinks', response_format='csv', cache=True)
    for pair in links:
        left = pair['Left']
        right = pair['Right']
        if left not in graph:
            graph[left] = []
        if right not in graph:
            graph[right] = []
        graph[left].append(right)
        graph[right].append(left)
    return graph

def heuristic(node, goal):
    return 0

def a_star_search(graph, start, goal):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {node: float('inf') for node in graph}
    g_score[start] = 0

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in graph[current]:
            tentative_g_score = g_score[current] + 1
            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                heapq.heappush(open_set, (tentative_g_score, neighbor))

    return None

def reconstruct_path(came_from, current):
    total_path = [current]
    while current in came_from:
        current = came_from[current]
        total_path.append(current)
    total_path.reverse()
    return total_path

def number_of_jumps(path):
    return len(path) - 1 if path else float('inf')

def jump_distance(origin, destination):
    if (origin, destination) in cache:
        return cache[(origin, destination)]
    
    graph = read_system_links('systemlinks.csv')
    path = a_star_search(graph, origin, destination)
    distance = number_of_jumps(path)
    
    save_to_cache(origin, destination, distance)
    
    return distance

def appx_travel_time(jumps):
    return jumps*3+6+4

if __name__ == "__main__":
    origin = 'OT-580'
    destination = 'DW-161'
    jumps = jump_distance(origin, destination)
    print(f"Number of jumps from {origin} to {destination}: {jumps}")
