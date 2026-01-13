""" 
Capacitated Pickup Delivery Problem (CPDP) 
Headless Solver optimized for Travel Time using OR-Tools and OSMnx.
"""

import os
import json
import csv
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# Robust import handling for both script execution and package/API execution
try:
    from .routing import RoutingEngine
except ImportError:
    from routing import RoutingEngine

# Global engine instance for reuse (Singleton Pattern)
_ENGINE = None

def get_engine():
    global _ENGINE
    if _ENGINE is None:
        # Defaults to Marrakech, Morocco driving network
        _ENGINE = RoutingEngine()
    return _ENGINE

# --- CONFIGURATION & DATA LOADING ---

def load_fleet(path='data/fleet.json'):
    """Loads taxi fleet configuration from JSON."""
    with open(path, 'r') as f:
        return json.load(f)

def load_users(path='data/users.csv'):
    """Loads passenger requests from CSV and parses data types."""
    users = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f) 
        for row in reader:
            row['latitude_p'] = float(row['p_lat'])
            row['longitude_p'] = float(row['p_lon'])
            row['latitude_d'] = float(row['d_lat'])
            row['longitude_d'] = float(row['d_lon'])
            row['number_people'] = int(row['passengers'])
            row['service_time'] = int(row['service_time'])
            row['ready_time'] = int(row['ready_time'])
            row['due_time'] = int(row['due_time'])
            users.append(row)
    return users

# --- OPTIMIZATION CORE ---

def create_data_model(fleet_data, users_data, engine):
    """Stores the data for the problem and generates the cost matrix."""
    data = {}
    
    # Extract depot location (supports both API JSON and local JSON formats)
    if isinstance(fleet_data.get('depot'), list):
         depot_loc = fleet_data['depot']
    else:
         depot_loc = fleet_data['depot']['location']

    # 1. Build Coordinate List for Distance Matrix
    # The matrix must include all relevant locations: Depot (Index 0), then all Pickups, then all Dropoffs.
    locations = [depot_loc] 
    
    for u in users_data:
        locations.append([u['longitude_p'], u['latitude_p']]) # Indices 1 to N
    for u in users_data:
        locations.append([u['longitude_d'], u['latitude_d']]) # Indices N+1 to 2N
    
    print(f"Calculating travel time matrix for {len(locations)} points...")
    raw_matrix = engine.get_distance_matrix(locations, metric='travel_time')
    
    # OR-Tools requires Integer costs. 
    # We scale seconds by 100 to preserve precision (e.g. 1.55s becomes 155)
    data['time_matrix'] = [[int(round(val)) for val in row] for row in raw_matrix]
    
    # Service time represents boarding/unboarding time at each stop.
    service_times = [0] 
    service_times.extend([u['service_time'] * 100 for u in users_data]) # Pickups
    service_times.extend([u['service_time'] * 100 for u in users_data]) # Dropoffs
    data['service_times'] = service_times
    
    # Time Windows: Defines when a stop is 'open' for service.
    time_windows = [[0, 24 * 3600 * 100]] # Depot open 24h
    for u in users_data:
        time_windows.append([u['ready_time'] * 100, u['due_time'] * 100]) # Pickup windows
    for u in users_data:
        time_windows.append([0, 24 * 3600 * 100]) # Dropoffs usually open-ended
        
    data['time_windows'] = time_windows
    data['num_vehicles'] = len(fleet_data['taxis'])
    data['vehicle_capacities'] = [t['capacity'] for t in fleet_data['taxis']]
    data['depot'] = 0
    
    # Demands: Positive for pickups (consume capacity), Negative for deliveries (free capacity)
    pickups_count = len(users_data)
    demands = [0]
    demands.extend([u['number_people'] for u in users_data])
    demands.extend([-u['number_people'] for u in users_data])
    data['demands'] = demands
    
    # Pickup/Delivery Pairs: Connects index i to index i + N
    data['pickups_deliveries'] = []
    for i in range(1, pickups_count + 1):
        data['pickups_deliveries'].append([i, i + pickups_count])
        
    return data, locations

def solve_vrp(data):
    """Configures the OR-Tools model and executes the solver."""
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    # Transition Callback: Total time = Driving time + Service time at the departure node
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node] + data['service_times'][from_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Capacity Constraint
    def demand_callback(from_index):
        return data['demands'][manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    # Time Dimension with 'Slack' (Allows vehicles to wait if they arrive before ready_time)
    dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index,
        3600 * 100, # Allow up to 1 hour of waiting time at any node
        24 * 3600 * 100, # Max total time per vehicle (24 hours)
        False, 
        dimension_name)
    time_dimension = routing.GetDimensionOrDie(dimension_name)
    
    # Apply Time Window constraints
    for location_idx, time_window in enumerate(data['time_windows']):
        index = manager.NodeToIndex(location_idx)
        try:
            time_dimension.CumulVar(index).SetRange(int(time_window[0]), int(time_window[1]))
        except OverflowError:
            raise

    # Objective: Minimize the start/end times of each route
    for i in range(data['num_vehicles']):
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

    # Pickup and Delivery Logic: Ensuring same vehicle and P-before-D order
    for request in data['pickups_deliveries']:
        p_idx = manager.NodeToIndex(request[0])
        d_idx = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(p_idx, d_idx)
        routing.solver().Add(routing.VehicleVar(p_idx) == routing.VehicleVar(d_idx))
        routing.solver().Add(time_dimension.CumulVar(p_idx) <= time_dimension.CumulVar(d_idx))

    # Solver Strategy
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION

    solution = routing.SolveWithParameters(search_params)
    return solution, routing, manager

# --- OUTPUT GENERATORS ---

def extract_solution(solution, routing, manager, locations, users_data):
    """Transforms the OR-Tools solution into a human-readable and JSON-ready dictionary."""
    if not solution:
        return None

    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    routes = []
    engine = get_engine()
    
    def get_node_info(idx):
        if idx == 0: return {"type": "depot", "id": "depot"}
        n_users = len(users_data)
        if 1 <= idx <= n_users:
            u = users_data[idx - 1]
            return {"type": "pickup", "id": u.get('id', f"u{idx}"), "user_index": idx-1}
        elif n_users + 1 <= idx <= 2 * n_users:
            u = users_data[idx - 1 - n_users]
            return {"type": "dropoff", "id": u.get('id', f"u{idx}"), "user_index": idx-1-n_users}
        return {"type": "unknown", "id": "unknown"}

    for vehicle_id in range(routing.vehicles()):
        index = routing.Start(vehicle_id)
        route_steps = []
        full_geometry = [] # High-resolution road path
        route_cost = 0
        
        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            coords = locations[node_idx]
            time_var = time_dimension.CumulVar(index)
            arrival_sec = solution.Min(time_var) / 100
            node_info = get_node_info(node_idx)
            
            route_steps.append({
                "stop_sequence": len(route_steps),
                "type": node_info['type'],
                "id": node_info['id'],
                "location": [coords[0], coords[1]],
                "arrival_time_sec": arrival_sec,
                "arrival_time_formatted": f"{int(arrival_sec // 3600):02d}:{int((arrival_sec % 3600) // 60):02d}"
            })
            
            # Trace geometry between current node and the next node in the solution
            prev_idx = index
            index = solution.Value(routing.NextVar(index))
            next_node_idx = manager.IndexToNode(index)
            
            leg_geo = engine.get_detailed_route(
                [coords[1], coords[0]], # Lat, Lon
                [locations[next_node_idx][1], locations[next_node_idx][0]] # Lat, Lon
            )
            full_geometry.extend(leg_geo)
            
            route_cost += routing.GetArcCostForVehicle(prev_idx, index, vehicle_id)
            
        # Add the final return to Depot
        node_idx = manager.IndexToNode(index)
        coords = locations[node_idx]
        time_var = time_dimension.CumulVar(index)
        arrival_sec = solution.Min(time_var) / 100
        
        route_steps.append({
            "stop_sequence": len(route_steps),
            "type": "depot",
            "id": "depot_end",
            "location": [coords[0], coords[1]],
            "arrival_time_sec": arrival_sec,
            "arrival_time_formatted": f"{int(arrival_sec // 3600):02d}:{int((arrival_sec % 3600) // 60):02d}"
        })
        
        if len(route_steps) > 2: 
            routes.append({
                "vehicle_id": vehicle_id, 
                "cost_time": route_cost, 
                "steps": route_steps,
                "geometry": full_geometry
            })
            total_time += route_cost

    return {"status": "success", "total_cost": solution.ObjectiveValue(), "total_time_cost": total_time, "routes": routes}

def main():
    """Main CLI entry point for testing local data."""
    engine = get_engine()
    fleet = load_fleet()
    users = load_users()
    data, locations = create_data_model(fleet, users, engine)
    solution, routing, manager = solve_vrp(data)
    result = extract_solution(solution, routing, manager, locations, users)
    
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("No solution found.")

if __name__ == '__main__':
    main()
