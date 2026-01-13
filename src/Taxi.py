from geopy.geocoders import Nominatim
import logging

# Set up geocoder
geolocator = Nominatim(user_agent="maltavrp")

class taxi:
    def __init__(self, location, key=None, number_people=0, capacity=4):
        self.location = location
        self.number = number_people
        self.capacity = capacity
        self.users = []
        self.key = key

    def update_location(self, location):
        self.location = location

    def get_location(self):
        return self.location

    def geo(self):
        """Helper to geocode using OpenStreetMap."""
        try:
            location = geolocator.geocode(self.location)
            if location:
                return (location.latitude, location.longitude)
            return None
        except Exception as e:
            logging.error(f"Geocoding error: {e}")
            return None

    def add_people(self, user):
        if self.number+user.get_number() > self.capacity:
            return False
        else:
            self.number = self.number+user.get_number()
            if user in self.users:
                self.users.remove(user)
            self.users.append(user)
            return True

    def is_finish(self, user):
        if self.location == user.get_end():
            return True
        else:
            return False

    def is_start(self, user):
        if self.location == user.get_start():
            return True
        else:
            return False

    def get_people(self):
        return self.number

    def get_capacity(self):
        return self.capacity

    def remove_people(self, user):
        self.number = self.number-user.get_number()
        self.users.remove(user)

    def get_users(self):
        return self.users