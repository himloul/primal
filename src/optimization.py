"""
Capacitated Pickup Delivery Problem (CPDP) Solver
A specialized mathematical model using Google OR-Tools and Custom Heuristics.
"""

import os
import tomllib
import logging
from .solver_heuristic import CVRPTWSolver

logger = logging.getLogger(__name__)

# --- DATA MODEL PREPARATION ---


def create_data_model(fleet_data, users_data, engine):
    """Prepares the time matrix, demands, and windows for OR-Tools/Heuristic."""
    data = {}
    depot_loc = fleet_data.get("depot", {}).get("location") or fleet_data.get("depot")
    locations = [depot_loc]
    for u in users_data:
        locations.append([u["longitude_p"], u["latitude_p"]])
    for u in users_data:
        locations.append([u["longitude_d"], u["latitude_d"]])

    logger.info(f"Calculating travel time matrix for {len(locations)} points...")
    raw_matrix = engine.get_distance_matrix(locations, metric="travel_time")
    data["time_matrix"] = [[int(round(val)) for val in row] for row in raw_matrix]

    service_times = [0]
    service_times.extend([u["service_time"] * 100 for u in users_data])  # Pickups
    service_times.extend([u["service_time"] * 100 for u in users_data])  # Dropoffs
    data["service_times"] = service_times

    time_windows = [[0, 24 * 3600 * 100]]  # Depot open 24h
    for u in users_data:
        time_windows.append([u["ready_time"] * 100, u["due_time"] * 100])
    for u in users_data:
        time_windows.append([0, 24 * 3600 * 100])

    data["time_windows"] = time_windows
    data["num_vehicles"] = len(fleet_data["taxis"])
    data["vehicle_capacities"] = [t["capacity"] for t in fleet_data["taxis"]]
    data["depot"] = 0

    pickups_count = len(users_data)
    demands = [0]
    demands.extend([u["number_people"] for u in users_data])
    demands.extend([-u["number_people"] for u in users_data])
    data["demands"] = demands
    data["pickups_deliveries"] = [[i, i + pickups_count] for i in range(1, pickups_count + 1)]

    return data, locations


# --- SHARED RESULT ENRICHMENT ---


def enrich_solution(routes_data, locations, users_data, engine, objective_value, engine_name):
    """Common logic to add geometry and formatted times to any solver output."""
    final_routes = []
    # total_time = 0

    for r in routes_data:
        steps = []
        for i, step_node in enumerate(r["route"]):
            node_idx = int(step_node)
            loc = locations[node_idx]

            # Map ID
            num_users = len(users_data)
            if node_idx == 0:
                step_id = "depot"
                step_type = "depot"
            elif 1 <= node_idx <= num_users:
                step_id = users_data[node_idx - 1]["id"]
                step_type = "pickup"
            else:
                step_id = users_data[node_idx - num_users - 1]["id"]
                step_type = "dropoff"

            steps.append(
                {
                    "stop_sequence": i,
                    "type": step_type,
                    "id": step_id,
                    "location": [loc[0], loc[1]],
                    "arrival_time_formatted": "00:00",  # Detailed timing requires a simulation pass
                }
            )

        # Inject road geometry
        geometry = []
        for i in range(len(steps) - 1):
            p1, p2 = steps[i]["location"], steps[i + 1]["location"]
            geometry.extend(engine.get_detailed_route([p1[1], p1[0]], [p2[1], p2[0]]))

        final_routes.append(
            {"vehicle_id": r.get("vehicle_id", 0), "steps": steps, "geometry": geometry}
        )

    return {
        "status": "success",
        "total_cost": float(objective_value),
        "metrics": {
            "total_nodes": len(locations),
            "vehicle_count": len(final_routes),
            "total_duration_sec": float(objective_value),
            "objective_value": float(objective_value),
            "engine": engine_name,
        },
        "routes": final_routes,
    }


# --- SOLVER LOGIC ---


def solve_vrp_ortools(data):
    """Configures the OR-Tools model and executes the solver."""
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
    except ImportError:
        logger.error("OR-Tools not found. Install with 'uv pip install primal-vrp[benchmark]'")
        return None

    manager = pywrapcp.RoutingIndexManager(
        len(data["time_matrix"]), data["num_vehicles"], data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        return (
            data["time_matrix"][from_node][manager.IndexToNode(to_index)]
            + data["service_times"][from_node]
        )

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return data["demands"][manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data["vehicle_capacities"], True, "Capacity"
    )

    routing.AddDimension(transit_callback_index, 3600 * 100, 24 * 3600 * 100, False, "Time")
    time_dimension = routing.GetDimensionOrDie("Time")
    for loc_idx, tw in enumerate(data["time_windows"]):
        time_dimension.CumulVar(manager.NodeToIndex(loc_idx)).SetRange(int(tw[0]), int(tw[1]))

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.seconds = 30
    search_params.log_search = False

    solution = routing.SolveWithParameters(search_params)
    if not solution:
        return None

    # Format for enrichment
    routes_data = []
    for vehicle_id in range(routing.vehicles()):
        index = routing.Start(vehicle_id)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        if len(route) > 2:
            routes_data.append({"vehicle_id": vehicle_id, "route": route})

    return routes_data, solution.ObjectiveValue() / 100


# --- ENTRY POINT ---


def solve_cpdptw(fleet_dict: dict, users_list: list, engine, solver_config=None):
    """Main entry point: Dispatches to OR-Tools or Heuristic engine."""
    mapped_users = []
    for u in users_list:
        mapped_users.append(
            {
                "id": str(u.get("id")),
                "longitude_p": float(u.get("p_lon") or u.get("longitude_p")),
                "latitude_p": float(u.get("p_lat") or u.get("latitude_p")),
                "longitude_d": float(u.get("d_lon") or u.get("longitude_d")),
                "latitude_d": float(u.get("d_lat") or u.get("latitude_d")),
                "number_people": int(u.get("passengers") or u.get("number_people")),
                "service_time": int(u.get("service_time", 120)),
                "ready_time": int(u.get("ready_time", 0)),
                "due_time": int(u.get("due_time", 86400)),
            }
        )

    depot_loc = fleet_dict.get("depot", {}).get("location") or fleet_dict.get("depot")
    valid_points = (
        [depot_loc]
        + [[u["longitude_p"], u["latitude_p"]] for u in mapped_users]
        + [[u["longitude_d"], u["latitude_d"]] for u in mapped_users]
    )

    is_valid, err = engine.validate_points(valid_points)
    if not is_valid:
        return {"status": "failed", "error": f"Invalid Coordinates: {err}"}

    data, locations = create_data_model(fleet_dict, mapped_users, engine)

    # Config
    config = {}
    if os.path.exists("config.toml"):
        with open("config.toml", "rb") as f:
            config = tomllib.load(f).get("solver", {})
    if solver_config:
        config.update(solver_config)

    if config.get("use_heuristic_solver"):
        logger.info("Solving with Custom Heuristic...")
        solver = CVRPTWSolver(
            data["time_matrix"],
            data["demands"],
            data["vehicle_capacities"][0],
            data["time_windows"],
            data["service_times"],
        )
        res = solver.solve()
        # Convert heuristic format to enrichment format
        routes_data = [
            {"vehicle_id": r["vehicle_id"], "route": [s["id"] for s in r["steps"]]}
            for r in res["routes"]
        ]
        return enrich_solution(
            routes_data,
            locations,
            mapped_users,
            engine,
            res["total_cost"] / 100,
            "Heuristic (SA/Numba)",
        )

    logger.info("Solving with OR-Tools...")
    res = solve_vrp_ortools(data)
    if not res:
        return {"status": "failed", "error": "No feasible solution found."}
    return enrich_solution(res[0], locations, mapped_users, engine, res[1], "OR-Tools (GLS)")
