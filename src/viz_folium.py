import folium
import webbrowser
import os

class FoliumMap:
    """
    A FOSS alternative to Google Maps visualization using Folium (Leaflet.js).
    """

    def __init__(self, center_lat=35.854938, center_lon=14.486100, zoom_start=11):
        self.m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles='OpenStreetMap')
        
        # Color mapping from gmplot style to folium/bootstrap style
        self.color_map = {
            'gold': 'orange',
            'coral': 'red',
            'dodgerblue': 'blue',
            'mediumpurple': 'purple',
            'palegreen': 'green',
            'white': 'lightgray'
        }

    def _get_color(self, color_name):
        return self.color_map.get(color_name, 'blue')

    def add_geofence(self):
        """Adds the predefined Malta region polygon."""
        malta_region = [
            (35.803328, 14.554822),
            (35.800475, 14.496695),
            (35.825082, 14.398712),
            (35.868734, 14.326598),
            (35.973936, 14.290459),
            (36.004854, 14.266097),
            (36.030803, 14.177367),
            (36.087915, 14.176825),
            (36.096223, 14.259044),
            (36.054412, 14.353785),
            (35.882201, 14.593547),
            (35.828978, 14.586117)
        ]
        
        folium.Polygon(
            locations=malta_region,
            color='royalblue',
            weight=4,
            fill=True,
            fill_color='skyblue',
            fill_opacity=0.4,
            popup='Malta Region'
        ).add_to(self.m)

    def add_marker(self, lat, lon, label=None, color='blue', popup_text=None, icon_type='info-sign'):
        """Adds a custom circular marker with a number inside."""
        f_color = self._get_color(color)
        
        # HTML for a circular marker with white border and number
        html = f"""
            <div style="
                background-color: {f_color};
                border: 2px solid white;
                color: white;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                text-align: center;
                line-height: 30px;
                font-weight: bold;
                font-family: sans-serif;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
            ">
                {label}
            </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=popup_text if popup_text else str(label),
            icon=folium.DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15), # Center the icon
                html=html
            )
        ).add_to(self.m)

    def add_circle_marker(self, lat, lon, radius=600, color='blue'):
        """Adds a circle (e.g., for the depot)."""
        f_color = self._get_color(color)
        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color='white',
            weight=1,
            fill=True,
            fill_color=f_color,
            fill_opacity=0.6
        ).add_to(self.m)

    def draw_route(self, coordinates, color='blue'):
        """
        Draws a polyline route.
        coordinates: List of (lat, lon) tuples.
        """
        f_color = self._get_color(color)
        folium.PolyLine(
            locations=coordinates,
            color=f_color,
            weight=5,
            opacity=0.8
        ).add_to(self.m)

    def save(self, filename='map.html'):
        """Saves the map to an HTML file and attempts to open it."""
        self.m.save(filename)
        # webbrowser.open_new_tab(filename)
        print(f"Map saved to {filename}")

