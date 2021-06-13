# ----------------------------------------------------

"""Capacited Vehicles Routing Problem (CVRP)."""
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
from Mapper import get_shortest, get_duration, get_possible

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
matrix = osrm.table(dst, output='np')[0].tolist()


# Configure OSRM server
osrm.RequestConfig.host = "http://router.project-osrm.org" # this sets the new url

# DATA MODEL ------------------

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    data['distance_matrix'] = matrix
    data['demands'] = demands
    data['vehicle_capacities'] = [4, 4, 4]
    data['num_vehicles'] = 3
    data['depot'] = 0
    return data


def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    total_distance = 0
    total_load = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        route_load = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += data['demands'][node_index]
            plan_output += ' {0} Load({1}) -> '.format(node_index, route_load)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        plan_output += ' {0} Load({1})\n'.format(manager.IndexToNode(index),
                                                 route_load)
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        plan_output += 'Load of the route: {}\n'.format(route_load)
        print(plan_output)
        total_distance += route_distance
        total_load += route_load
    print('Total distance of all routes: {}m'.format(total_distance))
    print('Total load of all routes: {}'.format(total_load))

#### Save routes to a list or array ####

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
    """Solve the CVRP problem."""
    # Instantiate the data problem.
    data = create_data_model()

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)


    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(1)

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
    
list_coord = [tuple(l) for l in [t[::-1] for t in dst]] # list of tuples of coordinates (lat, lon) in a list

path = 1 # access first route
solut = []
solut[:] = sol[path][0]
solut = [list_coord[i] for i in solut]
  

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

users
gmap.polygon(*malta_region, face_color='skyblue', edge_color='royalblue', edge_width=4)
for j in range(1,len(solut)-1):
  gmap.text(solut[j][0]+0.003, solut[j][1], '(' + str(j) + ')' + str(demands[j]), color='navy')
gmap.directions(solut[0],solut[len(solut)-1], waypoints = solut[1:(len(solut)-2)])

gmap.draw('map2.html')
webbrowser.open_new_tab('map2.html')
