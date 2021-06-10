import pandas as pd
import gmplot
import ortools
import geopandas
import osrm

# Import Taxis
taxis = pd.read_csv('taxis.csv', sep = ";")
taxis

# Import Users
users = pd.read_csv('users.csv', sep = ";")
users

src = taxis[['latitude', 'longitude']].values.tolist()
dst = users[['latitude_p', 'longitude_p']].values.tolist()

osrm.RequestConfig # this shows the current default url
osrm.RequestConfig.host = "http://router.project-osrm.org" # this sets the new url
osrm.RequestConfig # this shows the current url (changed)

time_matrix = osrm.table(coords_src=src,coords_dest=dst, output='dataframe')[0]

pd.melt(pd.DataFrame(time_matrix))
