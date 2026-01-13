from geopy.geocoders import Nominatim
import logging

# Set up geocoder
geolocator = Nominatim(user_agent="maltavrp")

class user:
    def __init__(self, start, end, number_of_people, identity, key=None):
        self.start = start
        self.end = end
        self.number = number_of_people
        self.key = key
        self.identity = identity

    def change_start(self, new_loc):
        self.start = new_loc

    def change_end(self, new_loc):
        self.end = new_loc

    def get_start(self):
        return self.start

    def _geocode(self, address):
        """Helper to geocode using OpenStreetMap."""
        try:
            location = geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
            return None
        except Exception as e:
            logging.error(f"Geocoding error: {e}")
            return None

    def start_geo(self):
        return self._geocode(self.start)

    def end_geo(self):
        return self._geocode(self.end)

    def get_end(self):
        return self.end

    def get_number(self):
        return self.number

    def get_identity(self):
        return self.identity
