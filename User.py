import gmplot

class user:
    def __init__(self, start, end, number_of_people, identity, key):
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

    def start_geo(self):
        return gmplot.GoogleMapPlotter.geocode(self.start, apikey=self.key)

    def end_geo(self):
        return gmplot.GoogleMapPlotter.geocode(self.end, apikey=self.key)

    def get_end(self):
        return self.end

    def get_number(self):
        return self.number

    def get_identity(self):
        return self.identity
