#!/usr/bin/env python3

import csv
import heapq

def read_system_links(filename):
    graph = {}
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        for row in reader:
            left, right = row
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
    graph = read_system_links('systemlinks.csv')
    path = a_star_search(graph, origin, destination)
    return number_of_jumps(path)

if __name__ == "__main__":
    origin = 'OT-580'
    destination = 'DW-161'
    jumps = jump_distance(origin, destination)
    print(f"Number of jumps from {origin} to {destination}: {jumps}")
