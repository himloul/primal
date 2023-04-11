# MaltaVRP 🚖
Capacited Vehicles Routing Problem (CVRP) on Taxis service.  
Malta as a case study.

## Quick start

Create a virtual environment

```bash
# Create the env
python -m venv env

# Activate
source env/Scripts/activate

pip3 install -U pip

# Install your modules
pip3 install osrm

# Create the requirements.txt file
pip freeze > requirements.txt

# After finishing the work, deactivate
deactivate
```
NOTE
> if it shows an error related to GDAL.  
Download the wheel from http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal  
then install it 

```bash
pip install "c:\Users\hamza\Downloads\GDAL-3.3.3-cp39-cp39-win_amd64.whl"
pip install osrm
pip install --force-reinstall -v "polyline==1.3"
```

## Drafts

```
Objective: 516991
Route for vehicle 0:
 0 ->  4 ->  8 ->  14 ->  18 ->  3 ->  13 -> 0
Distance of the route: 5026m

Route for vehicle 1:
 0 ->  9 ->  19 ->  1 ->  6 ->  16 ->  5 ->  11 ->  15 -> 0
Distance of the route: 4978m

Route for vehicle 2:
 0 ->  7 ->  17 ->  2 ->  12 ->  10 ->  20 -> 0
Distance of the route: 4387m

Total Distance of all routes: 14391m
([[0, 4, 8, 14, 18, 3, 13, 0], 5026], [[0, 9, 19, 1, 6, 16, 5, 11, 15, 0], 4978], [[0, 7, 17, 2, 12, 10, 20, 0], 4387])
```