# Primal VRP

A minimalist, high-performance toolkit for solving the **Capacitated Pickup and Delivery Problem with Time Windows (CPDPTW)**. 

Everything is kept small, simple, and hopefully easy to read. Instead of heavy GIS libraries or complex service layers, we use flat NumPy arrays, manual bit-shaking, and Numba JIT kernels to solve NP-hard routing problems at C speeds.

Essentially, we have a fleet of taxis and a stream of people who need to go from A to B within specific time constraints. The math here is NP-hard, but we can get very high-quality solutions by combining Google's OR-Tools with actual road network topology from OpenStreetMap.

## Technical Architecture

The system is split into three main parts:

1. [Unified CLI](main.py): One entry point to rule them all. No separate scripts. It downloads maps, runs solvers, or starts the server.
2. [CSR Routing](src/routing.py): We convert the OpenStreetMap network into a **Compressed Sparse Row (CSR)** format. We then run a manual **Binary Heap Dijkstra** compiled with Numba.
3. Dual Engine Solver:
   - [Custom Heuristic](./src/solver_heuristic.py): Using **Simulated Annealing** coupled with **Prins' Optimal Split (2004)**. It uses Dynamic Programming ($O(N^2)$) to find the mathematically optimal way to cut a "Giant Tour" into vehicle routes. On 50-user benchmarks, it is **~2.5x faster** and **~10%+ higher quality** than OR-Tools.
   - OR-tools (Optional for benchmark): A robust Constraint Programming solver using Guided Local Search. Requires `benchmark` extra.
4. [Async API](src/api.py): A lean FastAPI wrapper that offloads heavy math to a ProcessPoolExecutor.
   
## Running it

You'll need [uv](https://github.com/astral-sh/uv).

```bash
# Setup (Core)
uv sync

# 1. Download a city (e.g. Marrakech)
uv run python main.py download --city "Marrakech, Morocco"

# 2. Solve a problem via CLI
uv run python main.py solve --input data/users.csv --heuristic

# 3. Run the "Tournament" Benchmark (Requires OR-Tools)
uv sync --extra benchmark
uv run python -m scripts.benchmark_solver

# 4. Launch the Dashboard UI
uv run python main.py server
# > Zero-dependency Leaflet.js visualizer (no build step).
```

## The Physics

- **Soft Penalties:** We use Lagrangian-style soft penalties for capacity and time window violations. This smooths the energy landscape, allowing the SA solver to "tunnel" through invalid states to find global optima.
- **Scaling:** Solvers like integers. We scale all travel times by 100 to keep sub-second precision without using floats in the hot loop.
- **In-place Mutation:** Zero memory allocation during the search loop.
- **Optimal Splitting:** Every mutation step triggers a DP pass to re-optimize fleet partitioning.

## Trade-offs

To achieve C-level performance in pure Python, we specialized the solver for a specific problem class. This is not a general-purpose CSP engine; it is a specialized optimization tool.

1.  **Homogeneous Fleet:** The CSR data structure is optimized for a uniform vehicle profile (identical speed & capacity). Mixed fleets (e.g., combining vans and trucks) require the slower OR-Tools path.
2.  **Elastic Fleet Sizing:** The Prins' Split algorithm solves for the *optimal* number of vehicles to minimize global cost. It prioritizes efficiency over strict resource constraints (e.g., it may use 4 vehicles instead of a fixed limit of 3 if it results in a better solution).
3.  **Deterministic Routing:** Edge weights are pre-compiled for speed. Integrating dynamic factors (like real-time traffic) requires re-generating the graph weights, which is a batch operation.

## License
MIT.
