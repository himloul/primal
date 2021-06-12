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

# Data preparation
taxis = pd.read_csv('taxis.csv', sep = ";")
users = pd.read_csv('users_cal.csv', sep = ";")
depot = [[-9.575533, 30.416634]]

# list of pickups and deliveries coordinates
src = taxis[['longitude', 'latitude']].values.tolist()
dst = depot + users[['longitude_p', 'latitude_p']].values.tolist() + users[['longitude_p', 'latitude_p']].values.tolist()

# list of pickup - delivery
pd_list = []
for i in range(1,len(users['key'])+1,1):
  pd_list.append([i,i+len(users['key'])])

# Configure OSRM server
osrm.RequestConfig.host = "http://router.project-osrm.org" # this sets the new url

#### Data ####

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    # data['distance_matrix'] = osrm.table(coords_src=src,coords_dest=dst, output='np')[0].tolist()
    data['distance_matrix'] = osrm.table(dst, output='np')[0].tolist()
    data['num_vehicles'] = 2 #len(taxis.index)
    data['pickups_deliveries'] = pd_list
    data['depot'] = 0
    return data

#### Model ####

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
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        print(plan_output)
        total_distance += route_distance
    print('Total Distance of all routes: {}m'.format(total_distance))

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
    while not routing.IsEnd(index):
      previous_index = index
      index = solution.Value(routing.NextVar(index))
      route.append(manager.IndexToNode(index))
      route_distance += routing.GetArcCostForVehicle(previous_index, index, route_nbr)
    routes.append([route, route_distance])
    # ([[routing_0], distance_0], [[routing_1], distance_1], [[routing_2], distance_2])
    
    
  return routes


def main():
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model()

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])

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
        3000,  # vehicle maximum travel distance
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
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)

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

# List of routing to dataframe
dst_df = pd.DataFrame({'loc': depot+dst})
dst_df["id"] = dst_df.index

def dfroute(i):
  """From list to dataframe"""
  # TODO: write code...
  df = pd.DataFrame({'id': sol[i][0]})
  df['tx'] = i
  df["step"] = df.index+1
  routing_df = pd.merge(df,dst_df,on='id',how='left')
  routing_df[['lon','lat']] = pd.DataFrame(routing_df['loc'].tolist(), index= routing_df.index)
  return(routing_df)

dfroute(1)

# merge dataframes into one.
appended_data = []
for i in range(0,len(sol)):
  appended_data.append(dfroute(i))

appended_data = pd.concat(appended_data)

#### Plot ####
# ----------------------------------------------------
# key of API
key = 'AIzaSyA2KJIwDsDNnjBOzQUdqn_6TVyE2DHbscM'
gmaps.configure(api_key=key)

gmap = gmplot.GoogleMapPlotter(35.911079, 14.405030, 11, apikey=key)

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
gmap.polygon(*malta_region, face_color='skyblue', edge_color='royalblue', edge_width=4)

# Draw map
gmap.draw( "map.html" ) 
# Open map in a browser
webbrowser.open_new_tab("map.html")


list_coord = [tuple(l) for l in [t[::-1] for t in depot+dst]] # list of tuples of coordinates (lat, lon) in a list
fig = gmaps.figure()
markers = gmaps.marker_layer(list_coord)
fig.add_layer(markers)
fig
from ipywidgets.embed import embed_minimal_html
embed_minimal_html('export.html', views=[fig])
