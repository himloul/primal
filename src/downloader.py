"""
Minimalist OpenStreetMap Downloader
Fetches road networks via the Overpass API using Geocoding.
"""

import requests
import networkx as nx
import logging
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def download_city_graph(city_name="Marrakech"):
    logging.info(f"Geocoding {city_name} to find bounding box...")

    geo_url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json"
    headers = {"User-Agent": "PrimalVRP/1.0"}
    geo_resp = requests.get(geo_url, headers=headers)

    if not geo_resp.json():
        raise Exception(f"Could not geocode city: {city_name}")

    bounds = geo_resp.json()[0]["boundingbox"]
    bbox = f"{bounds[0]},{bounds[2]},{bounds[1]},{bounds[3]}"

    logging.info(f"Fetching road network within bbox: {bbox}")

    query = f"""
    [out:json][timeout:180];
    (
      way["highway"~"primary|secondary|tertiary|residential|unclassified"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]

    response = None
    for url in endpoints:
        try:
            logging.info(f"Trying Overpass endpoint: {url}")
            response = requests.get(url, params={"data": query}, timeout=180)
            if response.status_code == 200:
                break
        except Exception as e:
            logging.warning(f"Endpoint {url} failed: {e}")
            continue

    if not response or response.status_code != 200:
        status_code = response.status_code if response else "None"
        raise Exception(f"Overpass API request failed. Status: {status_code}")

    data = response.json()
    elements = data.get("elements", [])

    G = nx.MultiDiGraph()
    nodes = {e["id"]: e for e in elements if e["type"] == "node"}
    ways = [e for e in elements if e["type"] == "way"]

    logging.info(f"Parsing {len(ways)} roads and {len(nodes)} intersections...")

    if not ways:
        raise Exception("No road data found in this area.")

    for way in ways:
        nodes_in_way = way.get("nodes", [])
        tags = way.get("tags", {})

        highway_type = tags.get("highway", "residential")
        speeds = {
            "primary": 60,
            "secondary": 50,
            "tertiary": 40,
            "residential": 30,
            "unclassified": 30,
        }
        speed = float(tags.get("maxspeed", speeds.get(highway_type, 30)))

        for i in range(len(nodes_in_way) - 1):
            u, v = nodes_in_way[i], nodes_in_way[i + 1]
            if u in nodes and v in nodes:
                G.add_node(u, x=nodes[u]["lon"], y=nodes[u]["lat"])
                G.add_node(v, x=nodes[v]["lon"], y=nodes[v]["lat"])

                lat1, lon1 = nodes[u]["lat"], nodes[u]["lon"]
                lat2, lon2 = nodes[v]["lat"], nodes[v]["lon"]
                dist = haversine_distance(lat1, lon1, lat2, lon2)

                G.add_edge(u, v, length=dist, travel_time=dist / (speed / 3.6))

                if tags.get("oneway") != "yes":
                    G.add_edge(v, u, length=dist, travel_time=dist / (speed / 3.6))

    # Ensure the graph is strongly connected
    logging.info("Cleaning graph: Selecting Largest Strongly Connected Component...")
    # Get the set of nodes in the largest strongly connected component
    nodes_in_gcc = max(nx.strongly_connected_components(G), key=len)
    # Create a new graph with only these nodes
    G = G.subgraph(nodes_in_gcc).copy()
    logging.info(f"Final clean graph: {len(G.nodes)} nodes.")

    return G
