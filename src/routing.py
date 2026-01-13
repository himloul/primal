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

    def __init__(self, place_name="Malta", graph_file="data/malta_graph.graphml"):
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
            self.G = ox.graph_from_place(self.place_name, network_type='drive')
            
            # Add edge speeds (using default fallback) and travel times
            self.G = ox.add_edge_speeds(self.G)
            self.G = ox.add_edge_travel_times(self.G)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)
            logger.info(f"Saving graph to {self.graph_file}...")
            ox.save_graphml(self.G, self.graph_file)
        
        logger.info("Graph loaded successfully.")

    def get_distance_matrix(self, locations, metric='length'):
        """
        Calculates the distance matrix between a list of (lon, lat) tuples.
        
        Args:
            locations: List of (lon, lat) tuples.
            metric: 'length' (meters) or 'travel_time' (seconds).
            
        Returns:
            A list of lists representing the N x N distance matrix.
        """
        # Unzip coordinates. Input is (Lon, Lat) based on optimization.py
        lons, lats = zip(*locations)
        
        # Find nearest graph nodes for all locations (OSMnx expects X=Lon, Y=Lat)
        nodes = ox.distance.nearest_nodes(self.G, lons, lats)
        
        n = len(nodes)
        matrix = np.zeros((n, n))

        logger.info(f"Calculating {n}x{n} distance matrix using NetworkX...")
        
        # Note: Dijkstra is fast enough for Malta (~50 points). 
        # For larger datasets, we would use igraph or pandana.
        for i in range(n):
            source_node = nodes[i]
            # Compute shortest paths from source to ALL other nodes in the graph
            # This returns a dictionary {target_node: distance}
            lengths = nx.single_source_dijkstra_path_length(self.G, source_node, weight=metric)
            
            for j in range(n):
                target_node = nodes[j]
                if i == j:
                    matrix[i][j] = 0
                else:
                    # Default to a high cost if unreachable
                    # Multiply by 100 to preserve precision as integers for OR-Tools
                    matrix[i][j] = lengths.get(target_node, 1000.0) * 100

        return matrix.tolist()

    def get_route_info(self, start_coords, end_coords, metric='length'):
        """
        Calculates distance or time between two (lat, lon) points.
        Input is (lat, lon) to match user/taxi geo methods.
        """
        start_node = ox.distance.nearest_nodes(self.G, start_coords[1], start_coords[0])
        end_node = ox.distance.nearest_nodes(self.G, end_coords[1], end_coords[0])
        
        try:
            return nx.shortest_path_length(self.G, start_node, end_node, weight=metric)
        except nx.NetworkXNoPath:
            return 100000.0
