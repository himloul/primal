"""Simple Pickup Delivery Problem (PDP)."""

import pandas as pd
import gmplot
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import geopandas
import osrm
import numpy as np
import gmplot
import webbrowser
import gmaps
import googlemaps

# DATA PREPARATION ------------------

taxis = pd.read_csv('taxis.csv', sep = ";")
users = pd.read_csv('users.csv', sep = ";")
depot = [[14.486100,35.854938]]
users = users.round({'longitude_p': 6, 'latitude_p': 6, 'longitude_d': 6, 'latitude_d': 6})

# list of pickups and deliveries coordinates
src = taxis[['longitude', 'latitude']].values.tolist()
dst = depot + users[['longitude_p', 'latitude_p']].values.tolist() + users[['longitude_d', 'latitude_d']].values.tolist()

# list of pickup - delivery
pd_list = []
for i in range(1,len(users['key'])+1,1):
  pd_list.append([i,i+len(users['key'])])

# list of demands
d_list = users["number_people"].values.tolist()
demands = [0] + d_list + [i * -1 for i in d_list]
dmatrix = osrm.table(dst, output='np')[0].tolist()

# Configure OSRM server
osrm.RequestConfig.host = "http://router.project-osrm.org" # this sets the new url

# DATA MODEL ------------------

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    data['distance_matrix'] = dmatrix
    data['num_vehicles'] = 3
    data['pickups_deliveries'] = pd_list
    data['depot'] = 0
    return data


def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    total_distance = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            plan_output += ' {} -> '.format(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        print(plan_output)
        total_distance += route_distance
    print('Total Distance of all routes: {}m'.format(total_distance))

def get_routes(solution, routing, manager):
  """Get vehicle routes from a solution and store them in an array."""
  # Get vehicle routes and store them in a two dimensional array whose
  # i,j entry is the jth location visited by vehicle i along its route.
  routes = []
  for route_nbr in range(routing.vehicles()):
    index = routing.Start(route_nbr)
    route = [manager.IndexToNode(index)]
    route_distance = 0
    # route_load = 0
    
    while not routing.IsEnd(index):
      previous_index = index
      index = solution.Value(routing.NextVar(index))
      route.append(manager.IndexToNode(index))
      route_distance += routing.GetArcCostForVehicle(previous_index, index, route_nbr)
      # route_load += data['demands'][route_nbr]
    routes.append([route, route_distance]) # , route_load
    # ([[routing_0], distance_0], [[routing_1], distance_1], [[routing_2], distance_2])
    
  return routes

def main():
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model()

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)


    # Define cost of each arc.
    def distance_callback(from_index, to_index):
        """Returns the manhattan distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        9000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Define Transportation Requests.
    for request in data['pickups_deliveries']:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(
                delivery_index))
        routing.solver().Add(
            distance_dimension.CumulVar(pickup_index) <=
            distance_dimension.CumulVar(delivery_index))

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)
    
    # Get the routes
    routes = get_routes(solution, routing, manager)

    # Print solution on console.
    if solution:
        print_solution(data, manager, routing, solution)
    
    sol = ()
    # Display the routes.
    for i, route in enumerate(routes):
      sol += (route,)
      #print('Route', i, route)
    
    return(sol)

if __name__ == '__main__':
    sol = main()

sol

# ---------------------------
list_coord = [tuple(l) for l in [t[::-1] for t in dst]] # list of tuples of coordinates (lat, lon) in a list
list_nodes = ["depot"] + users["key"].values.tolist() + users["key"].values.tolist()
list_sign = ["*"]+ ["+" for i in range(0,len(users["key"].values))] + ["-" for i in range(0,len(users["key"].values))]
sols = [row[0] for row in sol]

# list of coordinates of the waypoints of routes
solution = [[list_coord[i] for i in sol[j][0]] for j in range(len(sol))]
solution_nodes = [[list_nodes[i] for i in sol[j][0]] for j in range(len(sol))]
sign_nodes = [[list_sign[i] for i in sol[j][0]] for j in range(len(sol))]


#### Plot ####
# ----------------------------------------------------
# key of API
key = 'AIzaSyA2KJIwDsDNnjBOzQUdqn_6TVyE2DHbscM'
gmaps.configure(api_key=key)
gmaps = googlemaps.Client(key=key)
# ----------------------------

import gmplot
import gmaps
gmap = gmplot.GoogleMapPlotter(35.854938,14.486100, 11, apikey=key)

# region Define malta area for display purposes
malta_region = zip(*[
    (35.803328, 14.554822),
    (35.800475, 14.496695),
    (35.825082, 14.398712),
    (35.868734, 14.326598),
    (35.973936, 14.290459),
    (36.004854, 14.266097),
    (36.030803, 14.177367),
    (36.087915, 14.176825),
    (36.096223, 14.259044),
    (36.054412, 14.353785),
    (35.882201, 14.593547),
    (35.828978, 14.586117)
])

# Add geofencing zone
gmap.polygon(*malta_region, face_color='skyblue', edge_color='royalblue', edge_width=4)

# Define colors
colors = {0: 'gold', 1: 'coral', 2: 'dodgerblue', 3: 'mediumpurple', 4: 'palegreen'}

# For legend
color_index = [(36.051892, 14.040469), (36.035764, 14.040421), (36.019764, 14.040421), (36.003764, 14.040421), (35.987764, 14.040421)]

for j in range(0,len(color_index)-1):
  gmap.marker(color_index[j][0], color_index[j][1], label = str(j), title = 'Route ' + str(j), color=colors[j])
  gmap.text(color_index[j][0], color_index[j][1]+0.01, 'Route ' + str(j))

# # Add markers

# Add markers
for k in range(len(solution)):
    for j in range(len(solution[k])-1):
        gmap.marker(solution[k][j][0], solution[k][j][1], 
        label = str(j), 
        title = str(demands[j]), 
        color=colors[k], 
        info_window = "<p><b>Request:</b> "+str(solution_nodes[k][j])+"<br><b>Number:</b> "+str(sign_nodes[k][j])+" "+str(abs(demands[j]))+"<br><b>Destination:</b> "
          +str([i for i,val in enumerate(solution_nodes[k]) if val==solution_nodes[k][j]][1])+"<br><b>Total:</b> </p>" # Next destination
          )


# Add text / users
for k in range(len(solution)):
    for j in range(len(solution[k])-1):
        gmap.text(solution[k][j][0], solution[k][j][1]+0.005, str(solution_nodes[k][j]), color='navy')
        
# Add text / sign
for k in range(len(solution)):
    for j in range(len(solution[k])-1):
        gmap.text(solution[k][j][0], solution[k][j][1]-0.005, str(sign_nodes[k][j]), color='navy')

# # Add circle
gmap.circle(depot[0][1], depot[0][0], 600, edge_color='#ffffff', fc='b')

for k in range(len(solution)):
    gmap.directions(solution[k][0],solution[k][len(solution[1])-2], waypoints = solution[k][1:(len(solution[k])-2)])

gmap.draw('maps.html')
webbrowser.open_new_tab('maps.html')


# def map_route(route_number, key):
#     """docstring for mapping"""
#     gmaps = googlemaps.Client(key=key)
#     k = route_number
#     # ----------------------------
#     
#     import gmplot
#     import gmaps
#     gmap = gmplot.GoogleMapPlotter(35.854938,14.486100, 11, apikey=key)
#     
#     # region Define malta area for display purposes
#     malta_region = zip(*[
#         (35.803328, 14.554822),
#         (35.800475, 14.496695),
#         (35.825082, 14.398712),
#         (35.868734, 14.326598),
#         (35.973936, 14.290459),
#         (36.004854, 14.266097),
#         (36.030803, 14.177367),
#         (36.087915, 14.176825),
#         (36.096223, 14.259044),
#         (36.054412, 14.353785),
#         (35.882201, 14.593547),
#         (35.828978, 14.586117)
#     ])
#     
#     # Add geofencing zone
#     gmap.polygon(*malta_region, face_color='skyblue', edge_color='royalblue', edge_width=4)
#     
#     # Define colors
#     colors = {0: 'orange', 1: 'yellowgreen', 2: 'dodgerblue', 3: 'peru', 4: 'palegreen'}
#     
#     # Add markers
#     for j in range(1,len(solution[1])-1):
#       gmap.marker(solution[k][j][0], solution[k][j][1], label = str(j), title = str(demands[j]), color=colors[k])
#     
#     # Add direction
#     gmap.directions(solution[k][0],solution[k][len(solution[1])-2], waypoints = solution[k][1:(len(solution[k])-2)])
#     
#     gmap.draw('map'+str(k)+'.html')
# map_route(3, key)
