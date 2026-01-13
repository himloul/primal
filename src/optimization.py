""" Capacitated Pickup Delivery Problem """

import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
from routing import RoutingEngine
from viz_folium import FoliumMap

# DATA PREPARATION ------------------

# Users
users = pd.read_csv('data/users.csv', sep=";")
users = users.round({'longitude_p': 6, 'latitude_p': 6, 'longitude_d': 6, 'latitude_d': 6})

# Depot location (Lon, Lat)
depot = [[14.486100, 35.854938]]

# Taxis
taxis = [[14.469428, 35.885589], [14.45726, 35.902826], [14.424397, 35.89612], [14.354686, 35.952366], [14.476262, 35.839197]]
nv = 4  # Number of vehicles

# List of pickups and deliveries coordinates (Lon, Lat)
# dst is used for routing calculation, so it stays [Lon, Lat]
dst = [[14.4861, 35.854938], [14.401655, 35.846377], [14.497267, 35.887131], [14.433823, 35.929024],
       [14.527481, 35.845083], [14.469545, 35.890592], [14.387005, 35.885561], [14.47568, 35.837131],
       [14.465858, 35.932434], [14.523563, 35.814807], [14.376637, 35.923736], [14.508826, 35.863944],
       [14.420673, 35.900094], [14.434887, 35.887856], [14.36185, 35.958519], [14.527125, 35.854735],
       [14.419283, 35.946309], [14.537346, 35.877379], [14.330287, 35.986799], [14.442159, 35.854071],
       [14.488344, 35.916907]]

# Initialize Routing Engine (Replaces OSRM)
# This will download/cache the Malta OSM graph on first run.
engine = RoutingEngine()

# DATA MODEL ------------------

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    
    # Calculate Time Matrix (Seconds * 100) using OSMnx
    print("Calculating travel time matrix via RoutingEngine...")
    # 'travel_time' uses speed limits to calculate seconds
    raw_matrix = engine.get_distance_matrix(dst, metric='travel_time')
    
    # OR-Tools requires integers.
    # The matrix is already scaled by 100 in routing.py, so we just round to int.
    data['time_matrix'] = [[int(round(val)) for val in row] for row in raw_matrix]
    
    data['num_vehicles'] = nv
    data['vehicle_capacities'] = [4, 4, 4, 4]
    data['demands'] = [0, 1, 2, 3, 2, 2, 2, 4, 2, 1, 3, -1, -2, -3, -2, -2, -2, -4, -2, -1, -3]
    data['pickups_deliveries'] = [[1, 11], [2, 12], [3, 13], [4, 14], [5, 15], [6, 16], [7, 17], [8, 18], [9, 19],
                                  [10, 20]]
    data['depot'] = 0
    return data

def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    total_time = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_time = 0
        while not routing.IsEnd(index):
            plan_output += ' {} -> '.format(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_time += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        
        # Convert back from scaled integer (seconds * 100) to minutes
        time_min = (route_time / 100) / 60
        plan_output += 'Time of the route: {:.2f} min\n'.format(time_min)
        print(plan_output)
        total_time += route_time
    
    total_time_min = (total_time / 100) / 60
    print('Total Time of all routes: {:.2f} min'.format(total_time_min))

def get_routes(solution, routing, manager):
    """Get vehicle routes from a solution and store them in an array."""
    routes = []
    for route_nbr in range(routing.vehicles()):
        index = routing.Start(route_nbr)
        route = [manager.IndexToNode(index)]
        route_distance = 0 # Keeps name generic, but now represents cost (time)

        while not routing.IsEnd(index):
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, route_nbr)
        routes.append([route, route_distance])

    return routes

def main():
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model()

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']), data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Define cost of each arc.
    def time_callback(from_index, to_index):
        """Returns the travel time between the two nodes."""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    # Add Time constraint.
    dimension_name = 'Time'
    # Max time per vehicle: 10 hours = 36000 seconds. 
    # Scaled by 100 => 3,600,000
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack (wait time at nodes) - set to >0 to allow waiting
        3600000,  # vehicle maximum travel time
        True,  # start cumul to zero
        dimension_name)
    time_dimension = routing.GetDimensionOrDie(dimension_name)
    time_dimension.SetGlobalSpanCostCoefficient(100)

    # Define Transportation Requests.
    for request in data['pickups_deliveries']:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(
                delivery_index))
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index) <=
            time_dimension.CumulVar(delivery_index))

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Get the routes
    if solution:
        print_solution(data, manager, routing, solution)
        routes = get_routes(solution, routing, manager)
        return routes
    return ()

if __name__ == '__main__':
    sol = main()
    
    if not sol:
        print("No solution found.")
        exit()

    # ------------ VISUALIZATION (FOSS / Folium) ---------------
    
    # 1. Prepare Coordinates
    # list_coord stores (Lat, Lon) for visualization, converting from original dst which is [Lon, Lat]
    list_coord = [(t[1], t[0]) for t in dst] 
    list_nodes = ["depot"] + users["key"].values.tolist() + users["key"].values.tolist()
    
    # Extract coordinates and node names for each route from the solution indices
    solution_coord = [[list_coord[i] for i in route_data[0]] for route_data in sol]
    solution_nodes = [[list_nodes[i] for i in route_data[0]] for route_data in sol]
    
    colors = ['gold', 'coral', 'dodgerblue', 'mediumpurple', 'palegreen']

    # 2. Initialize Map (Centered on Depot)
    depot_lat, depot_lon = 35.854938, 14.486100
    m = FoliumMap(center_lat=depot_lat, center_lon=depot_lon, zoom_start=11)
    
    # 3. Add Geofence
    m.add_geofence()
    
    # 4. Add Depot
    m.add_circle_marker(depot_lat, depot_lon, radius=600, color='blue')
    
    # 5. Plot Routes and Markers
    for k in range(len(solution_coord)):
        route_coords = solution_coord[k]
        route_nodes = solution_nodes[k]
        route_color = colors[k % len(colors)]
        
        # Draw the path
        m.draw_route(route_coords, color=route_color)
        
        # Add Markers (excluding last point if it's the depot to avoid clutter, or maybe include it)
        # Note: solution_coord[k] includes start and end (depot)
        for j in range(len(route_coords)):
             # Skip the final return to depot for marker plotting if desired, 
             # but keeping it is fine.
             
             # Info window logic from original: "Destination: {next_stop}"
             # We try to replicate looking ahead
             next_dest = "End of Route"
             if j < len(route_nodes) - 1:
                 next_dest = route_nodes[j+1]
             elif j == len(route_nodes) - 1:
                 next_dest = "Depot"
                 
             popup_html = f"<b>Stop:</b> {j}<br><b>Current:</b> {route_nodes[j]}<br><b>Next:</b> {next_dest}"
             
             m.add_marker(
                 lat=route_coords[j][0],
                 lon=route_coords[j][1],
                 label=str(j),
                 color=route_color,
                 popup_text=popup_html
             )

    # 6. Save Map
    m.save('export/map.html')