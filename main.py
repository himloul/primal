import gmplot
import webbrowser
from User import user
from Taxi import taxi
from Mapper import get_shortest, get_duration, get_possible


# key of API
key = 'AIzaSyA2KJIwDsDNnjBOzQUdqn_6TVyE2DHbscM'


gmap = gmplot.GoogleMapPlotter(35.911079, 14.405030, 11, apikey=key)

# region Define malta area for display purposes
malta_region = zip(*[
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
])
gmap.polygon(*malta_region, face_color='white', edge_color='red', edge_width=4)
# endregion

# region Create a dictionary for each person waiting, containing start and finish point for each
user1 = user('Malta international airport', 'St. Peters Pool, malta', 2, 'user1', key)
user2 = user('St Pauls Battery, malta', 'Mamo Tower, malta', 3, 'user2', key)
user3 = user('Mnajdra, malta', 'Gudja Parish Church, malta', 1, 'user3', key)
user4 = user('Knisja Parrokkjali San Gwann, malta', "Torri ta' San Ġiljan, malta", 3, 'user4', key)

user_dict = [user1, user2, user3, user4]

taxi1 = taxi('Kappella Ta Bir Miftuħ, malta', key, 0, 4)
taxi2 = taxi("St. Anthony's Chapel, malta", key, 0, 4)

taxi_dict = [taxi1, taxi2]
# endregion

# region Display user routes
for user in user_dict:
    start_location = user.start_geo()
    end_location = user.end_geo()

    gmap.text(start_location[0], start_location[1], 'Start', color='green')
    gmap.text(end_location[0], end_location[1], 'End', color='red')
# endregion

# region Calculate shortest route from any taxi to start of a route
shortest_start = ['','',10000000]
loop_num = 0
for taxi in taxi_dict:
    for user in user_dict:
        start = taxi.get_location()
        end = user.get_start()

        duration = get_duration(start, end, key)

        if duration < shortest_start[2]:
            shortest_start = [taxi, user, duration]

current_taxi = shortest_start[0]
first_user = shortest_start[1]

start_location = current_taxi.geo()
end_location = first_user.start_geo()

# endregion

current_taxi.update_location(first_user.get_start())
current_taxi.add_people(first_user)

next = True

waypoints = []
waypoints.append(end_location)
while len(user_dict) != 0:
    currents = current_taxi.get_users()

    if next == True:
        if len(currents) != 0:
            dests = get_possible(currents, user_dict)
        else:
            dests = [x.get_start() for x in user_dict]

    else:
        dests.remove(next)

    going = get_shortest(current_taxi.get_location(), dests, key)

    for passengers in user_dict:
        if passengers.get_end() == going:
            print(passengers.get_identity(), ' Trip: ', current_taxi.get_location(), ' -> ', going, ' end')
            current_taxi.remove_people(passengers)
            user_dict.remove(passengers)
            next = True
            current_taxi.update_location(going)
            waypoints.append(current_taxi.geo())

        elif passengers.get_start() == going:
            if current_taxi.add_people(passengers):
                print(passengers.get_identity(), ' Trip: ', current_taxi.get_location(), ' -> ', going, ' start')
                next = True
                current_taxi.update_location(going)
                waypoints.append(current_taxi.geo())

            else:
                next = passengers.get_start()

gmap.directions(start_location, waypoints[-1], waypoints=waypoints[:-1])

gmap.draw('map.html')

webbrowser.open_new_tab('map.html')
