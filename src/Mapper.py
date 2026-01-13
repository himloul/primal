from geopy.geocoders import Nominatim
from routing import RoutingEngine
import logging

# Set up geocoder
geolocator = Nominatim(user_agent="maltavrp")
# Initialize Routing Engine for Malta
engine = RoutingEngine()

def _geocode(address):
    """Helper to geocode using OpenStreetMap."""
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        logging.error(f"Geocoding error: {e}")
        return None

def get_duration(start_str, end_str, key=None):
    """Calculates duration in minutes using OSMnx."""
    start_coords = _geocode(start_str)
    end_coords = _geocode(end_str)
    
    if not start_coords or not end_coords:
        return 1000000
        
    # Get travel time in seconds and convert to minutes
    seconds = engine.get_route_info(start_coords, end_coords, metric='travel_time')
    return int(seconds / 60)

# Shortest direction form start to end
def get_shortest(start_str, end_list, key=None):
    """Finds the destination address with the shortest distance."""
    start_coords = _geocode(start_str)
    if not start_coords:
        return end_list[0] if end_list else None
        
    shortest_dist = 10000000000
    best_end = end_list[0] if end_list else None
    
    for end_str in end_list:
        end_coords = _geocode(end_str)
        if not end_coords:
            continue
            
        dist = engine.get_route_info(start_coords, end_coords, metric='length')
        
        if dist < shortest_dist:
            shortest_dist = dist
            best_end = end_str

    return best_end

def get_possible(current_user_list, all_users):
    dest_list = []

    for auser in all_users:
        for buser in current_user_list:
            if auser == buser:
                dest_list.append(auser.get_end())

            else:
                dest_list.append(auser.get_start())

    return dest_list
