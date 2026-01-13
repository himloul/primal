""" 
Capacitated Pickup Delivery Problem (CPDP) 
Optimized for Travel Time using OR-Tools and OSMnx.
"""

import os
import json
import csv
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from routing import RoutingEngine
from viz_folium import FoliumMap

# --- CONFIGURATION & DATA LOADING ---

def load_fleet(path='data/fleet.json'):
    with open(path, 'r') as f:
        return json.load(f)

def load_users(path='data/users.csv'):
    users = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            # Convert numeric strings to appropriate types
            row['latitude_p'] = float(row['latitude_p'])
            row['longitude_p'] = float(row['longitude_p'])
            row['latitude_d'] = float(row['latitude_d'])
            row['longitude_d'] = float(row['longitude_d'])
            row['number_people'] = int(row['number_people'])
            users.append(row)
    return users

# --- OPTIMIZATION CORE ---

def create_data_model(fleet_data, users_data, engine):
    """Stores the data for the problem."""
    data = {}
    
    depot_loc = fleet_data['depot']['location']
    
    # 1. Build Coordinate List for Distance Matrix
    # Format: [Depot] + [Pickups] + [Deliveries]
    locations = [depot_loc] # Index 0
    
    # Add Pickups
    for u in users_data:
        locations.append([u['longitude_p'], u['latitude_p']])
    
    # Add Deliveries
    for u in users_data:
        locations.append([u['longitude_d'], u['latitude_d']])
    
    # 2. Calculate Travel Time Matrix (Seconds * 100)
    print(f"Calculating travel time matrix for {len(locations)} points...")
    raw_matrix = engine.get_distance_matrix(locations, metric='travel_time')
    data['time_matrix'] = [[int(round(val)) for val in row] for row in raw_matrix]
    
    # 3. Vehicle Data
    data['num_vehicles'] = len(fleet_data['taxis'])
    data['vehicle_capacities'] = [t['capacity'] for t in fleet_data['taxis']]
    data['depot'] = 0
    
    # 4. Demands (0 for depot, +N for pickups, -N for deliveries)
    pickups_count = len(users_data)
    demands = [0] # Depot
    demands.extend([u['number_people'] for u in users_data]) # Pickups
    demands.extend([-u['number_people'] for u in users_data]) # Deliveries
    data['demands'] = demands
    
    # 5. Pickup/Delivery Pairs
    # Pickup index i (1 to N) matches Delivery index i + N
    data['pickups_deliveries'] = []
    for i in range(1, pickups_count + 1):
        data['pickups_deliveries'].append([i, i + pickups_count])
        
    return data, locations

def solve_vrp(data):
    """Entry point for the OR-Tools solver."""
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    # Cost Evaluator (Time)
    def time_callback(from_index, to_index):
        return data['time_matrix'][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Capacity Constraint
    def demand_callback(from_index):
        return data['demands'][manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    # Time Dimension (Maximum Shift Length)
    routing.AddDimension(transit_callback_index, 0, 3600000, True, 'Time')
    time_dimension = routing.GetDimensionOrDie('Time')
    time_dimension.SetGlobalSpanCostCoefficient(100)

    # Pickup and Delivery constraints
    for request in data['pickups_deliveries']:
        p_idx = manager.NodeToIndex(request[0])
        d_idx = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(p_idx, d_idx)
        routing.solver().Add(routing.VehicleVar(p_idx) == routing.VehicleVar(d_idx))
        routing.solver().Add(time_dimension.CumulVar(p_idx) <= time_dimension.CumulVar(d_idx))

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION

    solution = routing.SolveWithParameters(search_params)
    return solution, routing, manager

# --- OUTPUT & VISUALIZATION ---

def process_results(solution, routing, manager, locations, users_data):
    if not solution:
        print("No solution found!")
        return

    print(f"Objective (Total Cost): {solution.ObjectiveValue()}")
    
    # Prepare Map
    depot_lat, depot_lon = locations[0][1], locations[0][0]
    m = FoliumMap(center_lat=depot_lat, center_lon=depot_lon)
    m.add_geofence()
    m.add_circle_marker(depot_lat, depot_lon, color='white')

    colors = ['gold', 'coral', 'dodgerblue', 'mediumpurple', 'palegreen']
    
    # Node names for popups
    node_names = ["Depot"] + [f"Pickup {u['key']}" for u in users_data] + [f"Dropoff {u['key']}" for u in users_data]

    for vehicle_id in range(routing.vehicles()):
        index = routing.Start(vehicle_id)
        route_coords = []
        route_nodes = []
        
        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            coords = locations[node_idx]
            route_coords.append((coords[1], coords[0])) # Convert to Lat, Lon
            route_nodes.append(node_names[node_idx])
            index = solution.Value(routing.NextVar(index))
            
        # Add the final return to depot
        node_idx = manager.IndexToNode(index)
        coords = locations[node_idx]
        route_coords.append((coords[1], coords[0]))
        route_nodes.append(node_names[node_idx])

        if len(route_coords) > 2: # Only plot active vehicles
            color = colors[vehicle_id % len(colors)]
            m.draw_route(route_coords, color=color)
            for j, (lat, lon) in enumerate(route_coords):
                m.add_marker(lat, lon, label=str(j), color=color, popup_text=f"Stop {j}: {route_nodes[j]}")

    m.save('export/map.html')
    print("Map updated: export/map.html")

def main():
    # 1. Setup Environment
    os.makedirs('export', exist_ok=True)
    engine = RoutingEngine()
    
    # 2. Load Data
    fleet = load_fleet()
    users = load_users()
    
    # 3. Model & Solve
    data, locations = create_data_model(fleet, users, engine)
    solution, routing, manager = solve_vrp(data)
    
    # 4. Results
    process_results(solution, routing, manager, locations, users)

if __name__ == '__main__':
    main()
