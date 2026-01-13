import os
import osmnx as ox
import networkx as nx
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RoutingEngine:
    """
    A lightweight, pure-Python routing engine using OpenStreetMap data via OSMnx.
    Replaces OSRM for calculating distance matrices.
    """

    def __init__(self, place_name="Marrakech, Morocco", graph_file="data/marrakech_graph.graphml"):
        self.place_name = place_name
        self.graph_file = graph_file
        self.G = None
        self._load_graph()

    def _load_graph(self):
        """Loads the graph from a file or downloads it from OSM."""
        if os.path.exists(self.graph_file):
            logger.info(f"Loading cached graph from {self.graph_file}...")
            self.G = ox.load_graphml(self.graph_file)
        else:
            logger.info(f"Downloading driving network for {self.place_name}...")
            # Download the drive network
            self.G = ox.graph_from_place(self.place_name, network_type="drive")

            # Add edge speeds (using default fallback) and travel times
            self.G = ox.add_edge_speeds(self.G)
            self.G = ox.add_edge_travel_times(self.G)

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)
            logger.info(f"Saving graph to {self.graph_file}...")
            ox.save_graphml(self.G, self.graph_file)

        logger.info("Graph loaded successfully.")

    def get_distance_matrix(self, locations, metric="length"):
        """
        Calculates an N x N distance matrix between a list of (lon, lat) tuples.
        
        Args:
            locations: List of (lon, lat) tuples.
            metric: 'length' (meters) or 'travel_time' (seconds).
            
        Returns:
            A list of lists representing the cost to travel between every point.
        """
        # Unzip coordinates.
        lons, lats = zip(*locations)

        # Snap the input coordinates to the nearest valid graph nodes.
        # This prevents 'No Path' errors if a coordinate is inside a building or park.
        nodes = ox.distance.nearest_nodes(self.G, lons, lats)

        n = len(nodes)
        matrix = np.zeros((n, n))

        logger.info(f"Calculating {n}x{n} distance matrix using NetworkX...")

        # Optimization: We use Single-Source Dijkstra.
        # Running Dijkstra once for each starting node allows us to find the 
        # shortest path to ALL other nodes in one pass, rather than N*N separate calls.
        for i in range(n):
            source_node = nodes[i]
            # nx.single_source_dijkstra_path_length returns a dictionary: {target_node: distance}
            lengths = nx.single_source_dijkstra_path_length(
                self.G, source_node, weight=metric
            )

            for j in range(n):
                target_node = nodes[j]
                if i == j:
                    matrix[i][j] = 0
                else:
                    # Default to a high cost (1000 units) if unreachable
                    # We multiply by 100 to provide integer precision for the OR-Tools solver.
                    matrix[i][j] = lengths.get(target_node, 1000.0) * 100

        return matrix.tolist()

    def get_route_info(self, start_coords, end_coords, metric='length'):
        """
        Calculates simple point-to-point cost. Useful for heuristic scripts.
        Input: (lat, lon) tuples.
        """
        start_node = ox.distance.nearest_nodes(self.G, start_coords[1], start_coords[0])
        end_node = ox.distance.nearest_nodes(self.G, end_coords[1], end_coords[0])
        
        try:
            return nx.shortest_path_length(self.G, start_node, end_node, weight=metric)
        except nx.NetworkXNoPath:
            return 100000.0

    def get_detailed_route(self, start_coords, end_coords, metric='travel_time'):
        """
        Retrieves the exact geometry (list of nodes) along the shortest path.
        This is used to draw routes that follow actual streets on the map.
        """
        start_node = ox.distance.nearest_nodes(self.G, start_coords[1], start_coords[0])
        end_node = ox.distance.nearest_nodes(self.G, end_coords[1], end_coords[0])

        try:
            # Get the list of node IDs forming the shortest path
            path = nx.shortest_path(self.G, start_node, end_node, weight=metric)
            
            # Convert node IDs back to [lon, lat] coordinates
            route_coords = []
            for node in path:
                node_data = self.G.nodes[node]
                route_coords.append([node_data['x'], node_data['y']])
            
            return route_coords
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Fallback to straight line if the graph is disconnected
            return [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]
