# MarrakechVRP

A minimalist, high-performance engine for solving the **Capacitated Pickup and Delivery Problem with Time Windows (CPDPTW)**. While currently localized to Marrakech, The implementation is city-agnostic and generalizes to any road network via OpenStreetMap.

Essentially, we have a fleet of taxis and a stream of people who need to go from A to B within specific time constraints. The math here is NP-hard, but we can get very high-quality solutions by combining Google's OR-Tools with actual road network topology from OpenStreetMap.

## Technical Architecture

The system is split into three main parts:

1. [Optimization](src/optimization.py): We use OR-Tools' Constraint Programming solver. The problem is modeled as a Pickup & Delivery problem where every request is a pair of nodes $(i, j)$ that must be served by the same vehicle, with $i$ visited before $j$. We enforce capacity constraints and hard time windows using a cumulative Time dimension.
1. [Routing Engine](src/routing.py): Instead of using straight-line "as-the-crow-flies" distances, we download the Marrakech road graph via `osmnx`. We calculate the $N \times N$ cost matrix by running Single-Source Dijkstra $N$ times. For visualization, we trace the actual path through the graph nodes to get the real road geometry.
2. **Interface:** A lightweight FastAPI backend that exposes a `/solve` endpoint and serves a minimalist, shadcn-inspired dashboard. No React/Next.js bloat—just vanilla JS and Leaflet.js.

## The Gory Details

- **Scaling:** OR-Tools is an integer solver. Since travel times are floats, we scale everything by 100 (mapping 1.55 seconds to 155). This preserves precision while keeping the solver efficient.
- **Graph Snapping:** GPS coordinates rarely land exactly on a road. We use a k-d tree to snap every input point to the nearest graph node before computing paths.
- **Time Windows:** The solver includes 'Slack' variables, allowing vehicles to arrive early and wait until a user's `ready_time` is reached.

## Running this thing

You'll need a standard Python 3.12+ install.

```bash
# Setup
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt

# Run
.\env\Scripts\uvicorn src.api:app --reload
```

Navigate to `localhost:8000`. Edit your fleet size, add some requests, and hit Optimize. It’ll trace the paths through Marrakech and show you the schedule.

## Current Limitations

This is a research-grade prototype. It currently uses static OpenStreetMap speed limits (ignoring rush-hour traffic) and assumes a central depot start for all vehicles. See `TODO.md` for the roadmap.

## License
MIT.
