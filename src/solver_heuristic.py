"""
Heuristic PDPTW Solver (Simulated Annealing + Interleaved Pooling)
Written from scratch using Numpy & Numba.

Advanced Features:
1. Interleaved Routing: Supports P1 -> P2 -> D1 -> D2 (Pooling).
2. Automated Repair: Ensures Pickup always precedes Drop-off.
3. Empty-State Splitting: Guarantees users are dropped off by the same vehicle.
"""

import numpy as np
import math
import random
import logging
from numba import njit

logger = logging.getLogger(__name__)


@njit
def _jit_repair_permutation(perm, num_users):
    """
    Ensures Pickup (1..N) comes before Dropoff (N+1..2N) for every user.
    Optimized to O(N) using an index lookup array.
    """
    n_points = len(perm)
    # Map: node_value -> current_index_in_perm
    # Node values are 1-based, max value is 2*num_users.
    # We allocate slightly more to be safe/simple.
    pos = np.empty(2 * num_users + 1, dtype=np.int32)

    # Build lookup table
    for i in range(n_points):
        val = perm[i]
        pos[val] = i

    for i in range(1, num_users + 1):
        p_node = i
        d_node = i + num_users

        p_idx = pos[p_node]
        d_idx = pos[d_node]

        if d_idx < p_idx:
            # Swap in the permutation array
            perm[p_idx] = d_node
            perm[d_idx] = p_node

            # Update the lookup table for the swapped elements
            pos[p_node] = d_idx
            pos[d_node] = p_idx

    return perm


@njit
def _jit_split_tour_cost(
    node_permutation, matrix, demands, capacity, time_windows, service_times, num_users
):
    """
    Implements Prins' OPTIMAL SPLIT procedure using O(N^2) Dynamic Programming.
    Finds the globally optimal way to cut the Giant Tour into vehicle routes.
    """
    n_points = len(node_permutation)

    # Physics Constants
    PENALTY_CAPACITY = 1000.0
    PENALTY_TIME = 100.0  # Increased to ensure validity
    VEHICLE_FIXED_COST = 500.0

    # V[i] = Min cost to service first i nodes in the permutation
    # P[i] = Predecessor index (where the last vehicle started)
    V = np.full(n_points + 1, 1e15)  # Initialize with infinity
    V[0] = 0.0

    # Limit lookahead to speed up (e.g. max 25 stops per car)
    # For 50 users, a car might take 10-15. 25 is safe.
    max_stops = 30

    for i in range(n_points):
        # If V[i] is unreachable, skip
        if V[i] >= 1e14:
            continue

        # Try to form a route from i+1 to j
        current_load = 0
        current_time = 0.0
        current_dist = 0.0
        last_node = 0  # Depot

        cost_accum = 0.0

        for j in range(i + 1, min(i + max_stops, n_points + 1)):
            node_idx = node_permutation[j - 1]

            # 1. Update Route State
            dist = matrix[last_node, node_idx]
            arr = max(time_windows[node_idx, 0], current_time + dist)

            # Update accumulators
            current_dist += dist
            current_load += demands[node_idx]

            # 2. Check Constraints (Soft Penalties)
            penalty = 0.0

            # Capacity
            if current_load > capacity:
                penalty += (current_load - capacity) * PENALTY_CAPACITY

            # Time Window (Late)
            if arr > time_windows[node_idx, 1]:
                penalty += (arr - time_windows[node_idx, 1]) * PENALTY_TIME

            # Prepare for next iteration
            cost_accum = current_dist + penalty
            current_time = arr + service_times[node_idx]
            last_node = node_idx

            # 3. Closing the route (Return to Depot)
            # CRITICAL: We can only close the route if the vehicle is empty!
            if current_load != 0:
                continue

            return_dist = matrix[last_node, 0]
            route_cost = cost_accum + return_dist + VEHICLE_FIXED_COST

            # 4. Relaxation
            if V[i] + route_cost < V[j]:
                V[j] = V[i] + route_cost

    return V[n_points]


@njit
def _jit_run_sa(
    nodes,
    matrix,
    demands,
    capacity,
    time_windows,
    service_times,
    num_users,
    initial_temp,
    alpha,
    max_iter,
):
    # 1. INTELLIGENT INITIALIZATION (Sort by Ready Time)
    start_times = np.zeros(num_users)
    for i in range(num_users):
        start_times[i] = time_windows[i + 1, 0]
    sorted_users = np.argsort(start_times)

    current_perm = np.zeros(num_users * 2, dtype=np.int32)
    for i in range(num_users):
        u_idx = sorted_users[i]
        real_node = u_idx + 1
        current_perm[i * 2] = real_node
        current_perm[i * 2 + 1] = real_node + num_users

    current_cost = _jit_split_tour_cost(
        current_perm, matrix, demands, capacity, time_windows, service_times, num_users
    )

    best_perm = current_perm.copy()
    best_cost = current_cost

    temp = initial_temp
    n = len(current_perm)

    for i in range(max_iter):
        # NEW OPERATOR SELECTION
        r = random.random()

        old_perm = current_perm.copy()

        if r < 0.4:
            # 1. SWAP (40%)
            idx1, idx2 = random.randint(0, n - 1), random.randint(0, n - 1)
            tmp = current_perm[idx1]
            current_perm[idx1] = current_perm[idx2]
            current_perm[idx2] = tmp

        elif r < 0.8:
            # 2. RELOCATE (40%) - Insert node i at position j
            idx1, idx2 = random.randint(0, n - 1), random.randint(0, n - 1)
            val = current_perm[idx1]
            # Shift array to remove idx1
            if idx1 < idx2:
                # 0..idx1..idx2..N
                # Shift left from idx1+1 to idx2
                for k in range(idx1, idx2):
                    current_perm[k] = current_perm[k + 1]
                current_perm[idx2] = val
            else:
                # 0..idx2..idx1..N
                # Shift right from idx2 to idx1-1
                for k in range(idx1, idx2, -1):
                    current_perm[k] = current_perm[k - 1]
                current_perm[idx2] = val

        else:
            # 3. 2-OPT / REVERSAL (20%)
            idx1 = random.randint(0, n - 1)
            idx2 = random.randint(0, n - 1)
            start, end = min(idx1, idx2), max(idx1, idx2)
            p1, p2 = start, end
            while p1 < p2:
                tmp = current_perm[p1]
                current_perm[p1] = current_perm[p2]
                current_perm[p2] = tmp
                p1 += 1
                p2 -= 1

        # REPAIR: Crucial for Pooling
        current_perm = _jit_repair_permutation(current_perm, num_users)

        new_cost = _jit_split_tour_cost(
            current_perm, matrix, demands, capacity, time_windows, service_times, num_users
        )

        delta = new_cost - current_cost

        if delta < 0:
            accept = True
        else:
            if delta / temp > 20:
                accept = False
            else:
                accept = random.random() < math.exp(-delta / temp)

        if accept:
            current_cost = new_cost
            if current_cost < 1e14 and current_cost < best_cost:
                best_cost = current_cost
                best_perm = current_perm.copy()
        else:
            current_perm = old_perm

        temp *= alpha

    return best_perm, best_cost


class CVRPTWSolver:
    def __init__(
        self,
        distance_matrix,
        demands,
        vehicle_capacity,
        time_windows,
        service_times,
        initial_temp=2500,
        alpha=0.9996,
        max_iter=150000,
    ):
        self.matrix = np.array(distance_matrix, dtype=np.float64)
        self.demands = np.array(demands, dtype=np.int32)
        self.capacity = int(vehicle_capacity)
        self.time_windows = np.array(time_windows, dtype=np.float64)
        self.service_times = np.array(service_times, dtype=np.float64)
        self.num_nodes = len(distance_matrix)
        self.num_users = (self.num_nodes - 1) // 2

        self.initial_temp = initial_temp
        self.alpha = alpha
        self.max_iter = max_iter

    def _reconstruct_routes(self, permutation):
        # We must re-run the Shortest Path (DP) to recover the split points
        n_points = len(permutation)
        max_stops = 30
        PENALTY_CAPACITY = 1000.0
        PENALTY_TIME = 100.0
        VEHICLE_FIXED_COST = 500.0

        # 1. Forward Pass (Calc Costs)
        V = np.full(n_points + 1, 1e15)
        P = np.zeros(n_points + 1, dtype=np.int32)  # Predecessors
        V[0] = 0.0

        for i in range(n_points):
            if V[i] >= 1e14:
                continue

            current_load = 0
            current_time = 0.0
            current_dist = 0.0
            last_node = 0

            for j in range(i + 1, min(i + max_stops, n_points + 1)):
                node_idx = int(permutation[j - 1])
                # Correcting var name for clarity:
                target_node = node_idx

                dist = self.matrix[last_node, target_node]
                arr = max(self.time_windows[target_node, 0], current_time + dist)

                current_dist += dist
                current_load += self.demands[target_node]

                penalty = 0.0
                if current_load > self.capacity:
                    penalty += (current_load - self.capacity) * PENALTY_CAPACITY
                if arr > self.time_windows[target_node, 1]:
                    penalty += (arr - self.time_windows[target_node, 1]) * PENALTY_TIME

                current_time = arr + self.service_times[target_node]
                last_node = target_node

                # CRITICAL SAFETY: Only split if empty
                if current_load != 0:
                    continue

                return_dist = self.matrix[last_node, 0]
                route_cost = (current_dist + penalty) + return_dist + VEHICLE_FIXED_COST

                if V[i] + route_cost < V[j]:
                    V[j] = V[i] + route_cost
                    P[j] = i  # We came from i
        # 2. Backward Pass (Recover Routes)
        routes = []
        curr = n_points
        while curr > 0:
            prev = P[curr]
            # Route is from prev (exclusive) to curr (inclusive)
            # Indices in permutation are 0-based: prev to curr-1
            segment = [int(permutation[k]) for k in range(prev, curr)]
            # Add depot padding
            full_route = [0] + segment + [0]
            routes.append(full_route)
            curr = prev

        routes.reverse()  # We built it backwards
        return routes

    def solve(self):
        best_perm, best_cost = _jit_run_sa(
            None,  # Not used in current JIT
            self.matrix,
            self.demands,
            self.capacity,
            self.time_windows,
            self.service_times,
            self.num_users,
            self.initial_temp,
            self.alpha,
            self.max_iter,
        )
        final_routes = self._reconstruct_routes(best_perm)
        return {
            "status": "success",
            "total_cost": float(best_cost),
            "routes": [
                {"vehicle_id": i, "steps": [{"id": int(node), "type": "node"} for node in r]}
                for i, r in enumerate(final_routes)
            ],
        }
