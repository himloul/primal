import pandas as pd
import gmplot
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import geopandas
import osrm
import numpy as np

# Data preparation
taxis = pd.read_csv('taxis.csv', sep = ";")
users = pd.read_csv('users.csv', sep = ";")

src = taxis[['latitude', 'longitude']].values.tolist()
dst = users[['latitude_p', 'longitude_p']].values.tolist() + users[['latitude_d', 'longitude_d']].values.tolist()

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    data['distance_matrix'] =   [[0.0,25.7,69.8,169.7,126.8],
                                [26.1,0.0,88.1,149.4004,106.3],
                                [70.2,80.6,0.0,100.0,65.256],
                                [158.4,137.6,99.8,0.0,49.4],
                                [115.4,94.6,65.6,48.8,0.0]] # osrm.table(dst, output='np',annotations='distance')[0].tolist()
    
    data['num_vehicles'] = 2  #len(taxis.index)
    data['depot'] = 0
    return data  

def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    max_route_distance = 0
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
        max_route_distance = max(route_distance, max_route_distance)
    print('Maximum of the route distances: {}m'.format(max_route_distance))



def main():
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model()

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])

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

    # Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        30000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print('No solution found !')


if __name__ == '__main__':
    main()
    
    
    
    # [
    #     [0, 6, 9, 8, 7, 3, 6, 2, 3, 2, 6, 6, 4, 4, 5, 9, 7],
    #     [6, 0, 8, 3, 2, 6, 8, 4, 8, 8, 13, 7, 5, 8, 12, 10, 14],
    #     [9, 8, 0, 11, 10, 6, 3, 9, 5, 8, 4, 15, 14, 13, 9, 18, 9],
    #     [8, 3, 11, 0, 1, 7, 10, 6, 10, 10, 14, 6, 7, 9, 14, 6, 16],
    #     [7, 2, 10, 1, 0, 6, 9, 4, 8, 9, 13, 4, 6, 8, 12, 8, 14],
    #     [3, 6, 6, 7, 6, 0, 2, 3, 2, 2, 7, 9, 7, 7, 6, 12, 8],
    #     [6, 8, 3, 10, 9, 2, 0, 6, 2, 5, 4, 12, 10, 10, 6, 15, 5],
    #     [2, 4, 9, 6, 4, 3, 6, 0, 4, 4, 8, 5, 4, 3, 7, 8, 10],
    #     [3, 8, 5, 10, 8, 2, 2, 4, 0, 33, 4, 9, 8, 7, 3, 13, 6],
    #     [2, 8, 8, 10, 9, 2, 5, 4, 3, 0, 4, 6, 5, 4, 3, 9, 5],
    #     [6, 13, 4, 14, 13, 7, 4, 8, 4, 4, 0, 10, 9, 8, 4, 13, 4],
    #     [6, 7, 15, 6, 4, 9, 12, 5, 9, 6, 10, 0, 1, 3, 7, 3, 10],
    #     [4, 5, 14, 7, 6, 7, 10, 4, 8, 5, 9, 1, 0, 2, 6, 4, 8],
    #     [4, 8, 13, 9, 8, 7, 10, 3, 7, 4, 8, 3, 2, 0, 4, 5, 6],
    #     [5, 12, 9, 14, 12, 6, 6, 7, 3, 3, 4, 7, 6, 4, 0, 9, 2],
    #     [9, 10, 18, 6, 8, 12, 15, 8, 13, 9, 13, 3, 4, 5, 9, 0, 9],
    #     [7, 14, 9, 16, 14, 8, 5, 10, 6, 5, 4, 10, 8, 6, 2, 9, 0]
    # ]
    
    # [
    #     [0, 2451, 713, 1018, 1631, 1374, 2408, 213, 2571, 875, 1420, 2145, 1972],
    #     [2451, 0, 1745, 1524, 831, 1240, 959, 2596, 403, 1589, 1374, 357, 579],
    #     [713, 1745, 0, 355, 920, 803, 1737, 851, 1858, 262, 940, 1453, 1260],
    #     [1018, 1524, 355, 0, 700, 862, 1395, 1123, 1584, 466, 1056, 1280, 987],
    #     [1631, 831, 920, 700, 0, 663, 1021, 1769, 949, 796, 879, 586, 371],
    #     [1374, 1240, 803, 862, 663, 0, 1681, 1551, 1765, 547, 225, 887, 999],
    #     [2408, 959, 1737, 1395, 1021, 1681, 0, 2493, 678, 1724, 1891, 1114, 701],
    #     [213, 2596, 851, 1123, 1769, 1551, 2493, 0, 2699, 1038, 1605, 2300, 2099],
    #     [2571, 403, 1858, 1584, 949, 1765, 678, 2699, 0, 1744, 1645, 653, 600],
    #     [875, 1589, 262, 466, 796, 547, 1724, 1038, 1744, 0, 679, 1272, 1162],
    #     [1420, 1374, 940, 1056, 879, 225, 1891, 1605, 1645, 679, 0, 1017, 1200],
    #     [2145, 357, 1453, 1280, 586, 887, 1114, 2300, 653, 1272, 1017, 0, 504],
    #     [1972, 579, 1260, 987, 371, 999, 701, 2099, 600, 1162, 1200, 504, 0]
    # ]
    
    # [
    #     [0, 548, 776, 696, 582, 274, 502, 194, 308, 194, 536, 502, 388, 354, 468, 776, 662],
    #     [548, 0, 684, 308, 194, 502, 730, 354, 696, 742, 1084, 594, 480, 674, 1016, 868, 1210],
    #     [776, 684, 0, 992, 878, 502, 274, 810, 468, 742, 400, 1278, 1164,1130, 788, 1552, 754],
    #     [696, 308, 992, 0, 114, 650, 878, 502, 844, 890, 1232, 514, 628, 822, 1164, 560, 1358],
    #     [582, 194, 878, 114, 0, 536, 764, 388, 730, 776, 1118, 400, 50014, 708,1050, 674, 1244],
    #     [274, 502, 502, 650, 536, 0, 228, 308, 194, 240, 582, 776, 662, 628,514, 1050, 708],
    #     [502, 730, 274, 878, 764, 228, 0, 536, 194, 468, 354, 1004, 890, 856, 514, 1278, 480],
    #     [194, 354, 810, 502, 388, 308, 536, 0, 342, 388, 730, 468, 354, 320, 662, 742, 856],
    #     [308, 696, 468, 844, 730, 194, 194, 3042, 0, 274, 388, 810, 696, 662, 320, 1084, 514],
    #     [194, 742, 742, 890, 776, 240, 468, 388, 274, 0, 342, 536, 422, 388,274, 810, 468],
    #     [536, 1084, 400, 1232, 1118, 582, 354, 730, 388, 342, 0, 878, 764,730, 388, 1152, 354],
    #     [502, 594, 1278, 514, 400, 776, 1004, 4068, 810, 536, 878, 0, 114,308, 650, 274, 844],
    #     [388, 480, 1164, 628, 514, 662, 890, 354, 696, 422, 764, 114, 0, 194,536, 388, 730],
    #     [354, 674, 1130, 822, 708, 628, 856, 320, 662, 388, 730, 308, 194, 0,342, 422, 536],
    #     [468, 1016, 788, 1164, 1050, 514, 514, 662, 320, 274, 388, 650, 536,342, 0, 764, 194],
    #     [776, 868, 1552, 560, 674, 1050, 1278, 742, 1084, 810, 1152, 274, 388, 422, 764, 0, 798],
    #     [662, 1210, 754, 1358, 1244, 708, 480, 856, 514, 468, 354, 844, 730, 536, 194, 798, 0],
    # ]
    

    
    # [
    #   [0.,2.15959635,5.15603243,12.15003864,12.66090817,8.06760374,11.25481465,17.31108648,15.37358741,8.34541481],
    # [1.15959635,0.,4.52227294,11.19223786,11.50131214,7.32033758,11.72388583,18.35259685,16.41378987,9.29953014],
    # [5.15603243,4.52227294,0.,7.44480948,10.26177912,10.15688933,16.24592213,22.1101544,20.18967731,13.40020548],
    # [12.15003864,11.19223786,7.44480948,0.,7.01813758,13.28961044,22.25645098,29.42422794,27.49154954,20.48281039],
    # [12.66090817,11.50131214,10.26177912,7.01813758,0.,9.22215871,19.74293886,29.16680205,27.25540014,19.97465594],
    # [8.06760374,7.32033758,10.15688933,13.28961044,9.22215871,0.,10.66219491,21.06632671,19.24994647,12.24773666],
    # [11.25481465,11.72388583,16.24592213,22.25645098,19.74293886,10.66219491,0.,11.67502344,10.21846781,6.08016463],
    # [17.31108648,18.35259685,22.1101544,29.42422794,29.16680205,21.06632671,11.67502344,0.,1.93885474,9.20353461],
    # [15.37358741,16.41378987,20.18967731,27.49154954,27.25540014,19.24994647,10.21846781,1.93885474,0.,7.28280909],
    # [8.34541481,9.29953014,13.40020548,20.48281039,19.97465594,12.24773666,6.08016463,9.20353461,7.28280909,0.]
    # ]
