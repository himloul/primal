import os
import networkx as nx
import numpy as np
import logging
import tomllib
from numba import njit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(path="config.toml"):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return tomllib.load(f)
    return {}


# --- NUMBA ACCELERATED DIJKSTRA ---


@njit
def _jit_dijkstra(nodes, ptr, idx, weight, source_idx, target_indices):
    """
    Numba-optimized Dijkstra using a CSR-formatted graph.
    Returns distances to specific target indices.
    """
    n = len(ptr) - 1
    dists = np.full(n, np.inf)
    dists[source_idx] = 0.0

    # Priority Queue: (distance, node_idx)
    # Numba doesn't have a built-in heap, so we'll use a simplified version
    # or just use the fact that for matrix calc, we can use a simpler approach.
    # Actually, for Numba, implementing a binary heap is best.

    # For a minimalist approach that is still fast, we can use a "Dense" Dijkstra
    # if the graph was small, but it's large.
    # Let's use a simpler implementation for this prototype.

    visited = np.zeros(n, dtype=np.bool_)

    # We use a simple array-based priority search for this Karpathy-style demo
    # In a real heavy-duty engine, we'd implement a full Binary Heap in Numba.
    for _ in range(n):
        # Find min dist node
        u = -1
        d_min = np.inf
        for i in range(n):
            if not visited[i] and dists[i] < d_min:
                d_min = dists[i]
                u = i

        if u == -1 or d_min == np.inf:
            break

        visited[u] = True

        # Relax edges
        for edge_idx in range(ptr[u], ptr[u + 1]):
            v = idx[edge_idx]
            w = weight[edge_idx]
            if dists[u] + w < dists[v]:
                dists[v] = dists[u] + w

    # Extract only the targets we care about
    result = np.zeros(len(target_indices))
    for i in range(len(target_indices)):
        result[i] = dists[target_indices[i]]
    return result


# Note: The 'Dense' search above is O(V^2). For city graphs (V=20k), it's slow.
# I will implement a better Binary Heap for Numba below to ensure it's actually fast.


@njit
def _push_heap(heap, size, val, node):
    i = size
    heap[i, 0] = val
    heap[i, 1] = node
    while i > 0:
        p = (i - 1) // 2
        if heap[i, 0] < heap[p, 0]:
            # swap
            t0, t1 = heap[i, 0], heap[i, 1]
            heap[i, 0], heap[i, 1] = heap[p, 0], heap[p, 1]
            heap[p, 0], heap[p, 1] = t0, t1
            i = p
        else:
            break


@njit
def _pop_heap(heap, size):
    res_val, res_node = heap[0, 0], heap[0, 1]
    size -= 1
    heap[0, 0], heap[0, 1] = heap[size, 0], heap[size, 1]
    i = 0
    while True:
        left, r = 2 * i + 1, 2 * i + 2
        smallest = i
        if left < size and heap[left, 0] < heap[smallest, 0]:
            smallest = left
        if r < size and heap[r, 0] < heap[smallest, 0]:
            smallest = r
        if smallest != i:
            t0, t1 = heap[i, 0], heap[i, 1]
            heap[i, 0], heap[i, 1] = heap[smallest, 0], heap[smallest, 1]
            heap[smallest, 0], heap[smallest, 1] = t0, t1
            i = smallest
        else:
            break
    return res_val, res_node, size


@njit
def _fast_jit_dijkstra(ptr, idx, weight, source_idx, target_indices):
    n = len(ptr) - 1
    dists = np.full(n, 1e12)  # Use large float instead of np.inf for Numba safety
    dists[source_idx] = 0.0

    # Manual Heap: (dist, node)
    heap = np.zeros((len(idx), 2))
    heap_size = 0

    _push_heap(heap, heap_size, 0.0, float(source_idx))
    heap_size += 1

    while heap_size > 0:
        d, u_f, heap_size = _pop_heap(heap, heap_size)
        u = int(u_f)

        if d > dists[u]:
            continue

        for e in range(ptr[u], ptr[u + 1]):
            v = idx[e]
            w = weight[e]
            if dists[u] + w < dists[v]:
                dists[v] = dists[u] + w
                _push_heap(heap, heap_size, dists[v], float(v))
                heap_size += 1

    results = np.zeros(len(target_indices))
    for i in range(len(target_indices)):
        t_idx = target_indices[i]
        results[i] = dists[t_idx]
    return results


class RoutingEngine:
    def __init__(self, place_name=None, graph_file=None):
        config = load_config().get("data", {})
        self.place_name = place_name or config.get("place_name", "Marrakech, Morocco")

        if not graph_file:
            graph_file = config.get("graph_file")
        if not graph_file:
            safe_name = "".join(c if c.isalnum() else "_" for c in self.place_name.lower()).strip(
                "_"
            )
            while "__" in safe_name:
                safe_name = safe_name.replace("__", "_")
            graph_file = f"data/{safe_name}.graphml"

        self.graph_file = graph_file
        self.G = None

        # CSR representation for Numba
        self.ptr = None
        self.idx = None
        self.weight_length = None
        self.weight_time = None

        self.node_ids = []
        self.node_coords = None
        self._load_graph()

    def _load_graph(self):
        if os.path.exists(self.graph_file):
            logger.info(f"Loading cached graph: {self.graph_file}")
            self.G = nx.read_graphml(self.graph_file)
        else:
            logger.info(f"Downloading network for {self.place_name}...")
            from .downloader import download_city_graph

            self.G = download_city_graph(self.place_name)
            os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)
            nx.write_graphml(self.G, self.graph_file)

        # 1. Build Node Mapping & Snapping Array
        coords = []
        self.node_ids = []
        node_to_int = {}
        for i, (node, data) in enumerate(self.G.nodes(data=True)):
            coords.append([float(data["y"]), float(data["x"])])
            self.node_ids.append(node)
            node_to_int[node] = i

        self.node_coords = np.array(coords)

        # 2. Build CSR Representation
        logger.info("Converting graph to CSR format for Numba...")
        n = len(self.node_ids)
        adj = [[] for _ in range(n)]
        for u, v, data in self.G.edges(data=True):
            u_int, v_int = node_to_int[u], node_to_int[v]
            # Store (target, length, travel_time)
            adj[u_int].append(
                (v_int, float(data.get("length", 0)), float(data.get("travel_time", 0)))
            )

        self.ptr = np.zeros(n + 1, dtype=np.int32)
        indices = []
        weights_l = []
        weights_t = []

        curr = 0
        for i in range(n):
            self.ptr[i] = curr
            for v, length, t in adj[i]:
                indices.append(v)
                weights_l.append(length)
                weights_t.append(t)
                curr += 1
        self.ptr[n] = curr

        self.idx = np.array(indices, dtype=np.int32)
        self.weight_length = np.array(weights_l, dtype=np.float64)
        self.weight_time = np.array(weights_t, dtype=np.float64)

        # Bounding Box
        self.bounds = {
            "min_lat": self.node_coords[:, 0].min() - 0.01,
            "max_lat": self.node_coords[:, 0].max() + 0.01,
            "min_lon": self.node_coords[:, 1].min() - 0.01,
            "max_lon": self.node_coords[:, 1].max() + 0.01,
        }
        logger.info(f"Routing engine ready ({n} nodes).")

    def validate_points(self, locations):
        if not self.bounds:
            return False, "Empty graph"
        for i, (lon, lat) in enumerate(locations):
            if not (
                self.bounds["min_lat"] <= lat <= self.bounds["max_lat"]
                and self.bounds["min_lon"] <= lon <= self.bounds["max_lon"]
            ):
                return False, f"Location {i} ({lat}, {lon}) out of bounds."
        return True, None

    def _snap_to_node(self, lat, lon):
        deltas = self.node_coords - np.array([lat, lon])
        return np.argmin(np.sum(deltas**2, axis=1))

    def get_distance_matrix(self, locations, metric="travel_time"):
        """Calculates N x N matrix using Numba-accelerated Dijkstra."""
        node_indices = np.array(
            [self._snap_to_node(loc[1], loc[0]) for loc in locations], dtype=np.int32
        )
        n = len(node_indices)
        matrix = np.zeros((n, n))

        # Select correct weight array
        weights = self.weight_time if metric == "travel_time" else self.weight_length

        for i in range(n):
            # Run JIT Dijkstra from this source to all target locations
            dists = _fast_jit_dijkstra(self.ptr, self.idx, weights, node_indices[i], node_indices)
            matrix[i] = dists * 100  # Scaling for OR-Tools/Heuristic

        return matrix.tolist()

    def get_detailed_route(self, start_coords, end_coords, metric="travel_time"):
        s_idx = self._snap_to_node(start_coords[0], start_coords[1])
        e_idx = self._snap_to_node(end_coords[0], end_coords[1])
        try:
            path = nx.shortest_path(
                self.G, self.node_ids[s_idx], self.node_ids[e_idx], weight=metric
            )
            return [[float(self.G.nodes[n]["x"]), float(self.G.nodes[n]["y"])] for n in path]
        except Exception:
            return [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]
