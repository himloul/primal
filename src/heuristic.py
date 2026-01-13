from user import user
from taxi import taxi
from mapper import get_shortest, get_duration, get_possible
from viz_folium import FoliumMap
import os

# Initialize Folium Map centered on Malta
m = FoliumMap(center_lat=35.911079, center_lon=14.405030, zoom_start=11)
m.add_geofence()

# region Create a dictionary for each person waiting, containing start and finish point for each
# Note: key=None as we no longer use Google Maps
user1 = user('Malta international airport', 'St. Peters Pool, malta', 2, 'user1')
user2 = user('St Pauls Battery, malta', 'Mamo Tower, malta', 3, 'user2')
user3 = user('Mnajdra, malta', 'Gudja Parish Church, malta', 1, 'user3')
user4 = user('Knisja Parrokkjali San Gwann, malta', "Torri ta' San Ġiljan, malta", 3, 'user4')

user_dict = [user1, user2, user3, user4]

taxi1 = taxi('Kappella Ta Bir Miftuħ, malta', number_people=0, capacity=4)
taxi2 = taxi("St. Anthony's Chapel, malta", number_people=0, capacity=4)

taxi_dict = [taxi1, taxi2]
# endregion

# region Display user routes on Folium Map
for u in user_dict:
    start_location = u.start_geo()
    end_location = u.end_geo()

    if start_location:
        m.add_marker(start_location[0], start_location[1], label='Start', color='palegreen', popup_text=f"{u.get_identity()} Start")
    if end_location:
        m.add_marker(end_location[0], end_location[1], label='End', color='coral', popup_text=f"{u.get_identity()} End")
# endregion

# region Calculate shortest route from any taxi to start of a route
shortest_start = ['', '', 10000000]
for t in taxi_dict:
    for u in user_dict:
        start = t.get_location()
        end = u.get_start()

        duration = get_duration(start, end)

        if duration < shortest_start[2]:
            shortest_start = [t, u, duration]

current_taxi = shortest_start[0]
first_user = shortest_start[1]

# Get coordinates for the taxi's path
start_location = current_taxi.geo()
# endregion

current_taxi.update_location(first_user.get_start())
current_taxi.add_people(first_user)

next_step = True

waypoints = []
if start_location:
    waypoints.append(start_location)

while len(user_dict) != 0:
    currents = current_taxi.get_users()

    if next_step == True:
        if len(currents) != 0:
            dests = get_possible(currents, user_dict)
        else:
            dests = [x.get_start() for x in user_dict]
    else:
        dests.remove(next_step)

    going = get_shortest(current_taxi.get_location(), dests)

    found = False
    for passengers in user_dict:
        if passengers.get_end() == going:
            print(passengers.get_identity(), ' Trip: ', current_taxi.get_location(), ' -> ', going, ' end')
            current_taxi.remove_people(passengers)
            user_dict.remove(passengers)
            next_step = True
            current_taxi.update_location(going)
            waypoints.append(current_taxi.geo())
            found = True
            break

        elif passengers.get_start() == going:
            if current_taxi.add_people(passengers):
                print(passengers.get_identity(), ' Trip: ', current_taxi.get_location(), ' -> ', going, ' start')
                next_step = True
                current_taxi.update_location(going)
                waypoints.append(current_taxi.geo())
                found = True
                break
            else:
                next_step = passengers.get_start()
                found = True
                break
    
    if not found:
        # Fallback to prevent infinite loop if destination not in user_dict
        break

# Draw the final route on the map
m.draw_route(waypoints, color='dodgerblue')
m.save('export/map_heuristic.html')
print("Heuristic map saved to export/map_heuristic.html")