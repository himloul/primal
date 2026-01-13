"""
MaltaVRP Backend API
Exposes the CVRPTW solver via FastAPI and serves the Web UI.
"""

import os
import uvicorn
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import optimization logic
try:
    from .optimization import create_data_model, solve_vrp, extract_solution, get_engine
except ImportError:
    from optimization import create_data_model, solve_vrp, extract_solution, get_engine

app = FastAPI(title="MaltaVRP Solver API", version="1.0")

# --- DATA MODELS ---

class Vehicle(BaseModel):
    id: str
    capacity: int

class Depot(BaseModel):
    location: Tuple[float, float] # [Lon, Lat]

class Fleet(BaseModel):
    depot: Depot
    taxis: List[Vehicle]

class UserRequest(BaseModel):
    id: str
    p_lon: float
    p_lat: float
    d_lon: float
    d_lat: float
    passengers: int
    service_time: int = 120
    ready_time: int = 0
    due_time: int = 86400

class SolveRequest(BaseModel):
    fleet: Fleet
    users: List[UserRequest]

# --- API ENDPOINTS ---

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MaltaVRP Solver"}

@app.post("/solve")
def solve_cvrptw(request: SolveRequest):
    """
    Solves the Vehicle Routing Problem with Time Windows.
    Input: JSON Fleet and User Requests.
    Output: Optimized Routes and Schedules.
    """
    try:
        fleet_dict = request.fleet.dict()
        users_dict = [u.dict() for u in request.users]
        
        mapped_users = []
        for u in users_dict:
            mapped_users.append({
                "id": u['id'],
                "longitude_p": u['p_lon'],
                "latitude_p": u['p_lat'],
                "longitude_d": u['d_lon'],
                "latitude_d": u['d_lat'],
                "number_people": u['passengers'],
                "service_time": u['service_time'],
                "ready_time": u['ready_time'],
                "due_time": u['due_time']
            })

        engine = get_engine()
        data, locations = create_data_model(fleet_dict, mapped_users, engine)
        solution, routing, manager = solve_vrp(data)
        
        if not solution:
            raise HTTPException(status_code=422, detail="No solution found.")
            
        result = extract_solution(solution, routing, manager, locations, mapped_users)
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- STATIC FILES & UI ---

# Serve the static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    """Serves the main UI page."""
    return FileResponse('static/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)