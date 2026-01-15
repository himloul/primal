"""
Primal VRP: A high-performance toolkit for CVRP optimization.
Unified CLI Entry Point.
"""

import argparse
import json
import os
import sys
import csv
import uvicorn
from src.routing import RoutingEngine
from src.optimization import solve_cpdptw


def cmd_download(args):
    print(f"Downloading graph for: {args.city}...")
    engine = RoutingEngine(place_name=args.city)
    print(f"Success! Graph saved to: {engine.graph_file}")


def cmd_solve(args):
    print(f"Loading engine for: {args.city or 'Default (Marrakech)'}...")
    engine = RoutingEngine(place_name=args.city)

    fleet = None
    users = []

    # 1. Handle Input Data
    if args.input.endswith(".csv"):
        print(f"Parsing users from CSV: {args.input}")
        with open(args.input, "r") as f:
            reader = csv.DictReader(f)
            users = [row for row in reader]

        # Load fleet from separate file or default
        fleet_file = args.fleet or "data/fleet.json"
        if os.path.exists(fleet_file):
            print(f"Loading fleet from: {fleet_file}")
            with open(fleet_file, "r") as f:
                fleet = json.load(f)
        else:
            print("No fleet file found. Using default fleet (4 vehicles, capacity 4).")
            fleet = {
                "depot": {"location": [-8.0194, 31.6300]},
                "taxis": [{"id": f"TX-{i + 1}", "capacity": 4} for i in range(4)],
            }
    else:
        # Assume JSON with {'fleet': ..., 'users': ...}
        print(f"Parsing combined data from JSON: {args.input}")
        with open(args.input, "r") as f:
            data = json.load(f)
            fleet = data.get("fleet")
            users = data.get("users")

    if not fleet or not users:
        print("Error: Could not find fleet or user data in input.")
        sys.exit(1)

    # 2. Construct override config from CLI args
    solver_config = {}
    if args.heuristic:
        solver_config["use_heuristic_solver"] = True
    if args.time_limit:
        solver_config["time_limit_seconds"] = args.time_limit

    print(
        f"Optimizing (Engine: {'Heuristic' if solver_config.get('use_heuristic_solver') else 'OR-Tools'})..."
    )
    result = solve_cpdptw(fleet, users, engine, solver_config=solver_config)

    if result.get("status") == "success":
        print("\n" + "=" * 40)
        print(f"SOLVE SUCCESSFUL ({result['metrics']['engine']})")
        print(f"Total Cost: {result['total_cost']:.2f}")
        print("=" * 40)

        for route in result["routes"]:
            # Create a simple breadcrumb string: Depot -> U1 -> U2 -> Depot
            path = " -> ".join([step["id"] for step in route["steps"]])
            print(f"Vehicle {route['vehicle_id']}: {path}")
        print("=" * 40)
    else:
        print(f"Solve Failed: {result.get('error')}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull detailed JSON saved to: {args.output}")


def cmd_server(args):
    print(f"Starting API Server on {args.host}:{args.port}...")
    uvicorn.run("src.api:app", host=args.host, port=args.port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(description="Primal VRP Toolkit")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Download Command
    dl_parser = subparsers.add_parser("download", help="Download a city graph")
    dl_parser.add_argument("--city", default="Marrakech, Morocco", help="City name")

    # Solve Command
    solve_parser = subparsers.add_parser("solve", help="Solve a VRP problem from a file")
    solve_parser.add_argument("--input", required=True, help="Path to input file (JSON or CSV)")
    solve_parser.add_argument("--fleet", help="Path to fleet JSON (required if input is CSV)")
    solve_parser.add_argument("--city", help="City name override")
    solve_parser.add_argument(
        "--heuristic", action="store_true", help="Force use of custom heuristic solver"
    )
    solve_parser.add_argument("--time-limit", type=int, help="Solver time limit in seconds")
    solve_parser.add_argument("--output", help="Path to save results")

    # Server Command
    server_parser = subparsers.add_parser("server", help="Launch the FastAPI server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host address")
    server_parser.add_argument("--port", type=int, default=8000, help="Port")
    server_parser.add_argument("--reload", action="store_true", help="Enable hot-reload")

    args = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "solve":
        cmd_solve(args)
    elif args.command == "server":
        cmd_server(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
