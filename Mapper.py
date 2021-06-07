import requests

def get_duration(start_str, end_str, key):
    start_location_joined = start_str.replace(' ', '+')
    end_location_joined = end_str.replace(' ', '+')

    direction_json = requests.get('https://maps.googleapis.com/maps/api/directions/json?origin=' +
                                  start_location_joined
                                  + '&destination=' +
                                  end_location_joined
                                  + '&key=' + key)

    duration = direction_json.json()['routes'][0]['legs'][0]['duration']['text']

    return int(duration.replace(' mins', ''))

def get_shortest(start_str, end_list, key):
    durat = 10000000000
    for end_str in end_list:
        start_location_joined = start_str.replace(' ', '+')
        end_location_joined = end_str.replace(' ', '+')

        direction_json = requests.get('https://maps.googleapis.com/maps/api/directions/json?origin=' +
                                      start_location_joined
                                      + '&destination=' +
                                      end_location_joined
                                      + '&key=' + key)

        duration = direction_json.json()['routes'][0]['legs'][0]['duration']['text']
        try:
            duration = int(duration.replace(' mins', ''))
        except ValueError:
            duration = int(duration.replace(' min', ''))

        if duration < durat:
            durat = duration
            st = end_str

    return st

def get_possible(current_user_list, all_users):
    dest_list = []

    for auser in all_users:
        for buser in current_user_list:
            if auser == buser:
                dest_list.append(auser.get_end())

            else:
                dest_list.append(auser.get_start())

    return dest_list