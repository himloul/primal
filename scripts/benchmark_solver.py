import time
import tracemalloc
import random
import logging
from src.routing import RoutingEngine
from src.optimization import solve_cpdptw

# Disable logging to keep output clean
logging.getLogger().setLevel(logging.WARNING)


def generate_random_problem(n_users=20):
    # Marrakech approx bounds
    min_lat, max_lat = 31.60, 31.66
    min_lon, max_lon = -8.03, -7.98

    fleet = {
        "depot": {"location": [-8.000, 31.630]},
        "taxis": [{"id": f"TX{i}", "capacity": 3} for i in range(10)],
    }

    users = []
    for i in range(n_users):
        users.append(
            {
                "id": f"U{i}",
                "p_lon": random.uniform(min_lon, max_lon),
                "p_lat": random.uniform(min_lat, max_lat),
                "d_lon": random.uniform(min_lon, max_lon),
                "d_lat": random.uniform(min_lat, max_lat),
                "passengers": 3,
                "service_time": 60,
                "ready_time": 0,
                "due_time": 7200,
            }
        )
    return fleet, users


def benchmark_engine(engine_name, fleet, users, routing_engine, config):
    print(f"Testing Engine: {engine_name}...")

    # Start tracing memory
    tracemalloc.start()
    start_time = time.perf_counter()

    # Run Solver
    result = solve_cpdptw(fleet, users, routing_engine, solver_config=config)

    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latency = end_time - start_time
    peak_mb = peak / 10**6

    # Extract cost
    cost = result.get("total_cost") if result.get("status") == "success" else "FAILED"
    vehicles = result.get("metrics", {}).get("vehicle_count", 0)
    routes = result.get("routes", []) if result.get("status") == "success" else []

    return {
        "engine": engine_name,
        "latency": latency,
        "memory": peak_mb,
        "cost": cost,
        "vehicles": vehicles,
        "routes": routes,
    }


def print_routes(engine_name, routes):
    print(f"\n--- {engine_name} Sequences ---")
    if not routes:
        print("No routes found.")
        return

    for r in routes:
        # Create a simple breadcrumb string: Depot -> U1 -> U2 -> Depot
        # Using 'id' from step, or falling back to node index if id not present
        path = " -> ".join([str(step.get("id", "node")) for step in r.get("steps", [])])
        print(f"Vehicle {r.get('vehicle_id', 0)}: {path}")


def run_comparison():
    print("Initializing Routing Engine...")
    engine = RoutingEngine()

    # Using 50 users for a competitive stress test
    fleet, users = generate_random_problem(50)

    print("\n--- Solver Tournament (50 Users) ---")

    # 1. Benchmark OR-Tools
    res_ortools = benchmark_engine(
        "OR-Tools", fleet, users, engine, {"use_heuristic_solver": False, "time_limit_seconds": 10}
    )

    # 2. Benchmark Heuristic
    res_heuristic = benchmark_engine(
        "Custom Heuristic", fleet, users, engine, {"use_heuristic_solver": True}
    )

    print("\n" + "=" * 60)
    print(f"{'Metric':<20} | {'OR-Tools':<15} | {'Custom (Numba)':<15}")
    print("-" * 60)

    # Format Cost
    cost_o = (
        f"{res_ortools['cost']:.2f}"
        if isinstance(res_ortools["cost"], (int, float))
        else str(res_ortools["cost"])
    )
    cost_h = (
        f"{res_heuristic['cost']:.2f}"
        if isinstance(res_heuristic["cost"], (int, float))
        else str(res_heuristic["cost"])
    )

    print(
        f"{'Latency (s)':<20} | {res_ortools['latency']:>14.2f} | {res_heuristic['latency']:>14.2f}"
    )
    print(
        f"{'Memory (MB)':<20} | {res_ortools['memory']:>14.2f} | {res_heuristic['memory']:>14.2f}"
    )
    print(f"{'Total Cost':<20} | {cost_o:>14} | {cost_h:>14}")
    print(
        f"{'Vehicle Count':<20} | {res_ortools['vehicles']:>14} | {res_heuristic['vehicles']:>14}"
    )
    print("=" * 60)

    # Print Sequences
    print_routes("OR-Tools", res_ortools["routes"])
    print_routes("Custom Heuristic", res_heuristic["routes"])


if __name__ == "__main__":
    run_comparison()
