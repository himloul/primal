""" Capacitated Pickup Delivery Problem"""

import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
import gmplot
import webbrowser

# DATA PREPARATION ------------------

#Users
users = pd.read_csv('users.csv', sep = ";")
users = users.round({'longitude_p': 6, 'latitude_p': 6, 'longitude_d': 6, 'latitude_d': 6})

#Depot location
depot = [[14.486100,35.854938]]
#Taxis
taxis = [[14.469428, 35.885589], [14.45726, 35.902826], [14.424397, 35.89612], [14.354686, 35.952366], [14.476262, 35.839197]]
nv = 4 # Number of vehicles

# list of pickups and deliveries coordinates
dst = [[14.4861, 35.854938], [14.401655, 35.846377], [14.497267, 35.887131], [14.433823, 35.929024], [14.527481, 35.845083], [14.469545, 35.890592], [14.387005, 35.885561], [14.47568, 35.837131], [14.465858, 35.932434], [14.523563, 35.814807], [14.376637, 35.923736], [14.508826, 35.863944], [14.420673, 35.900094], [14.434887, 35.887856], [14.36185, 35.958519], [14.527125, 35.854735], [14.419283, 35.946309], [14.537346, 35.877379], [14.330287, 35.986799], [14.442159, 35.854071], [14.488344, 35.916907]]
list_coord = [(35.854938, 14.4861), (35.846377, 14.401655), (35.887131, 14.497267), (35.929024, 14.433823), (35.845083, 14.527481), (35.890592, 14.469545), (35.885561, 14.387005), (35.837131, 14.47568), (35.932434, 14.465858), (35.814807, 14.523563), (35.923736, 14.376637), (35.863944, 14.508826), (35.900094, 14.420673), (35.887856, 14.434887), (35.958519, 14.36185), (35.854735, 14.527125), (35.946309, 14.419283), (35.877379, 14.537346), (35.986799, 14.330287), (35.854071, 14.442159), (35.916907, 14.488344)] 

# Configure OSRM server
osrm.RequestConfig.host = "http://router.project-osrm.org" # this sets the new url

# DATA MODEL ------------------

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    data['distance_matrix'] = [[0.0, 781.3, 358.7, 870.5, 455.6, 474.8, 740.9, 554.4, 785.7, 894.0, 1008.2, 238.5, 780.2, 577.3, 1561.6, 413.1, 1117.1, 502.4, 1975.7, 526.0, 640.5], [815.7, 0.0, 789.4, 922.3, 953.0, 735.9, 457.5, 634.3, 1216.4, 1113.6, 839.9, 970.8, 634.0, 547.6, 1393.3, 985.2, 970.4, 1173.5, 1807.4, 341.1, 1071.2], [479.4, 895.5, 0.0, 616.7, 700.5, 290.2, 757.0, 818.1, 531.9, 1138.9, 939.5, 483.4, 671.5, 507.8, 1307.9, 658.0, 863.3, 657.0, 1772.9, 615.8, 386.7], [893.0, 942.6, 613.7, 0.0, 1151.8, 543.9, 609.8, 1231.7, 567.1, 1590.2, 505.9, 934.7, 494.1, 534.5, 713.7, 1109.3, 282.8, 1108.3, 1178.7, 850.6, 453.4], [307.1, 954.8, 474.4, 1045.8, 0.0, 651.8, 980.5, 427.2, 961.0, 438.4, 1247.8, 277.5, 1005.4, 802.5, 1737.0, 104.9, 1292.4, 415.8, 2202.0, 699.5, 815.8], [439.9, 813.0, 205.1, 549.0, 698.7, 0.0, 553.5, 778.6, 603.8, 1137.1, 790.8, 481.6, 507.2, 304.3, 1240.2, 656.2, 795.6, 655.2, 1705.2, 542.0, 458.6], [765.0, 553.0, 687.1, 590.0, 1133.5, 482.0, 0.0, 869.4, 963.5, 1348.7, 475.0, 916.4, 301.7, 293.7, 952.7, 1091.0, 638.1, 1090.0, 1366.8, 566.8, 843.4], [314.0, 601.0, 579.0, 1117.0, 429.2, 721.3, 843.3, 0.0, 1032.2, 515.4, 1125.4, 447.0, 919.5, 765.0, 1678.8, 461.4, 1255.9, 710.9, 2092.9, 384.0, 887.0], [790.5, 1206.6, 511.2, 383.1, 1049.3, 602.4, 887.7, 1129.2, 0.0, 1487.7, 819.5, 832.2, 693.4, 732.2, 950.5, 1006.8, 505.9, 1005.8, 1415.5, 926.9, 253.8], [679.5, 1129.5, 870.9, 1442.3, 396.5, 1048.3, 1352.9, 584.1, 1357.5, 0.0, 1620.2, 674.0, 1392.2, 1189.3, 2133.5, 501.4, 1688.9, 812.3, 2587.7, 912.5, 1212.3], [1029.8, 845.5, 929.6, 474.4, 1398.3, 746.8, 471.9, 1161.9, 904.1, 1641.2, 0.0, 1181.2, 397.0, 558.5, 553.4, 1355.8, 434.6, 1354.8, 967.5, 831.6, 880.7], [298.7, 944.2, 331.2, 902.6, 217.1, 508.6, 871.3, 498.4, 817.8, 655.5, 1138.6, 0.0, 862.2, 659.3, 1593.8, 174.6, 1149.2, 263.9, 2058.8, 664.5, 672.6], [780.9, 639.8, 593.3, 488.5, 1039.7, 388.2, 307.0, 956.2, 783.2, 1435.5, 406.1, 822.6, 0.0, 262.6, 959.5, 997.2, 536.6, 996.2, 1373.6, 603.9, 663.1], [591.8, 552.4, 404.2, 562.9, 850.6, 199.1, 292.9, 816.8, 755.1, 1289.0, 560.2, 633.5, 246.2, 0.0, 1113.6, 808.1, 690.7, 807.1, 1527.7, 414.8, 609.9], [1550.5, 1375.1, 1271.2, 657.5, 1809.3, 1201.4, 974.1, 1691.5, 1008.1, 2170.8, 572.6, 1592.2, 926.6, 1088.1, 0.0, 1766.8, 538.6, 1765.8, 480.3, 1361.2, 1110.9], [339.7, 987.4, 431.9, 1003.3, 100.5, 609.3, 972.0, 459.8, 918.5, 538.9, 1239.3, 235.0, 962.9, 760.0, 1694.5, 0.0, 1249.9, 312.4, 2159.5, 732.1, 773.3], [1090.6, 976.3, 811.3, 258.7, 1349.4, 741.5, 643.5, 1292.7, 544.4, 1772.0, 446.3, 1132.3, 527.8, 689.3, 577.3, 1306.9, 0.0, 1305.9, 1042.3, 962.4, 651.0], [529.2, 1174.7, 561.7, 1133.1, 405.6, 739.1, 1101.8, 662.3, 1048.3, 844.0, 1369.1, 364.8, 1092.7, 889.8, 1824.3, 355.4, 1379.7, 0.0, 2289.3, 895.0, 903.1], [1937.1, 1752.8, 1668.8, 1055.1, 2206.9, 1599.0, 1308.8, 2069.2, 1405.7, 2548.5, 907.3, 1989.8, 1304.3, 1465.8, 449.5, 2164.4, 936.2, 2163.4, 0.0, 1738.9, 1508.5], [552.5, 342.5, 510.9, 905.2, 698.6, 547.7, 555.5, 412.8, 937.9, 892.1, 822.8, 708.5, 594.8, 391.9, 1376.2, 730.8, 953.3, 895.0, 1790.3, 0.0, 792.7], [605.5, 1021.6, 326.2, 433.0, 864.3, 417.4, 835.6, 944.2, 264.0, 1302.7, 869.9, 647.2, 601.9, 619.7, 1124.2, 821.8, 679.6, 820.8, 1589.2, 741.9, 0.0]]
    data['num_vehicles'] = nv
    data['vehicle_capacities'] = [4, 4, 4, 4]
    data['demands'] = [0, 1, 2, 3, 2, 2, 2, 4, 2, 1, 3, -1, -2, -3, -2, -2, -2, -4, -2, -1, -3]
    data['pickups_deliveries'] = [[1, 11], [2, 12], [3, 13], [4, 14], [5, 15], [6, 16], [7, 17], [8, 18], [9, 19], [10, 20]]
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

    # Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        50000,  # vehicle maximum travel distance
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

# list of the solution
sol

# ------------ EXTRACT THE RESULTS ---------------
# list of tuples of coordinates (lat, lon) in a list
# lists based on the solution
list_coord = [tuple(l) for l in [t[::-1] for t in dst]] # list of tuples of coordinates (lat, lon) in a list
list_nodes = ["depot"] + users["key"].values.tolist() + users["key"].values.tolist()
solution_coord = [[list_coord[i] for i in sol[j][0]] for j in range(len(sol))]
solution_nodes = [[list_nodes[i] for i in sol[j][0]] for j in range(len(sol))]
# Define colors
colors = {0: 'gold', 1: 'coral', 2: 'dodgerblue', 3: 'mediumpurple', 4: 'palegreen'}

#### Plot ####
# ----------------------------------------------------
# key of API
key = 'AIzaSyA2KJIwDsDNnjBOzQUdqn_6TVyE2DHbscM'
# ----------------------------

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

# Add markers
for k in range(len(solution_coord)):
    for j in range(len(solution_coord[k])-1):
        gmap.marker(solution_coord[k][j][0], solution_coord[k][j][1], 
        label = str(j), 
        title = str(j), color=colors[k], info_window = "<p><b>Destination:</b> "+str([i for i,val in enumerate(solution_nodes[k]) if val==solution_nodes[k][j]][1])+"</p>") # Next destination

# # Add circle
gmap.circle(depot[0][1], depot[0][0], 600, edge_color='#ffffff', fc='b')

# Directions
for k in range(len(solution_coord)):
    gmap.directions(solution_coord[k][0],solution_coord[k][len(solution_coord[k])-2], waypoints = solution_coord[k][1:(len(solution_coord[k])-2)])

gmap.draw('map.html')
webbrowser.open_new_tab('map.html')
