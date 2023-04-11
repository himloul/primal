'''
To solve the Vehicle Routing Problem (VRP) using `OSRM` in Python, 
you can use the osrm package, which provides a wrapper around the OSRM routing engine. 
Here's an example of how to use osrm to solve VRP: 

In this example, we first use the `osrm` package to compute the distance matrix between all pairs of locations. 
We then use the `ortools` package to solve the VRP with time windows using the Clarke-Wright algorithm. 
Finally, we print the solution, which consists of a list of routes for each vehicle.

Resources:
Clark-Wright Savings Algorithm | Single-Depot VRP | MIT - https://web.mit.edu/urban_or_book/www/book/chapter6/6.4.12.html

To install osrm

```bash
pip install osrm
```

if it shows an error related to GDAL
Download the wheel from http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
then install it 

```
pip install "c:\Users\hamza\Downloads\GDAL-3.3.3-cp39-cp39-win_amd64.whl"
pip install osrm
pip install --force-reinstall -v "polyline==1.3"
```

'''

import osrm

# Define problem data
num_vehicles = 3
vehicle_capacities = [50, 50, 50]
depot_location = (37.7749295,-122.4194155)
customer_locations = [(37.773012,-122.441313), (37.762991,-122.405455), (37.781650,-122.404827)]
demands = [20, 30, 10]

# Create OSRM client
client = osrm.Client()

# Compute distance matrix
locations = [depot_location] + customer_locations
distances = []
for loc1 in locations:
    row = []
    for loc2 in locations:
        route = osrm.simple_route(
            coordinates=[loc1, loc2],
            overview=osrm.overview.full,
            geometries=osrm.geometries.geojson
        )
        distance = route['routes'][0]['distance']
        row.append(distance)
    distances.append(row)

# Solve the problem using the VRP with time windows algorithm
# Here we use the VRP-TW algorithm provided by the OR-Tools package
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# Create routing model
routing = pywrapcp.RoutingModel(num_vehicles, 1, [0])
for i in range(num_vehicles):
    routing.AddDimension(
        evaluator_index=0,
        slack_max=0,
        capacity=vehicle_capacities[i],
        fix_start_cumul_to_zero=True,
        name='Capacity'
    )

# Define cost function
def cost_function(from_index, to_index):
    return distances[from_index][to_index]
routing.SetArcCostEvaluatorOfAllVehicles(cost_function)

# Define time windows
time_windows = [(0, 480), (240, 720), (360, 600)]
for i, (start_time, end_time) in enumerate(time_windows):
    routing.AddDimension(
        evaluator_index=0,
        slack_max=end_time - start_time,
        capacity=1,
        fix_start_cumul_to_zero=False,
        name='TimeWindow_{}'.format(i)
    )
    time_evaluator_index = routing.GetDimensionOrDie(i + 1)
    for j in range(num_vehicles):
        index = routing.End(j)
        time_windows_var = routing.GetMutableDimension(time_evaluator_index)
        time_windows_var.CumulVar(index).SetRange(start_time, end_time)

# Solve the problem
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
solution = routing.SolveWithParameters(search_parameters)

# Print the solution
if solution:
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route = []
        while not routing.IsEnd(index):
            route.append(index)
            index = solution.Value(routing.NextVar(index))
        route.append(routing.End(vehicle_id))
        print(route)
