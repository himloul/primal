"""
MaltaVRP Backend API
Exposes the CVRPTW solver via FastAPI with Background Tasks.
"""

import os
import uvicorn
import uuid
import time
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import optimization logic
try:
    from .optimization import create_data_model, solve_vrp, extract_solution, get_engine
except ImportError:
    from optimization import create_data_model, solve_vrp, extract_solution, get_engine

app = FastAPI(title="MaltaVRP Solver API", version="1.1")

# --- IN-MEMORY TASK STORE ---
# In a production app, this would be Redis or a Database.
tasks_db: Dict[str, Dict[str, Any]] = {}

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

# --- BACKGROUND WORKER ---

def run_optimization_task(task_id: str, fleet_dict: dict, users_list: list):
    """
    The actual heavy lifting. Runs in a background thread.
    """
    try:
        tasks_db[task_id]["status"] = "processing"
        
        # 1. Map users
        mapped_users = []
        for u in users_list:
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

        # 2. Get Engine (loads graph if first time)
        engine = get_engine()
        
        # 3. Solve
        data, locations = create_data_model(fleet_dict, mapped_users, engine)
        solution, routing, manager = solve_vrp(data)
        
        if not solution:
            tasks_db[task_id]["status"] = "failed"
            tasks_db[task_id]["error"] = "No feasible solution found."
            return

        # 4. Extract and Save
        result = extract_solution(solution, routing, manager, locations, mapped_users)
        tasks_db[task_id]["result"] = result
        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["completed_at"] = time.time()

    except Exception as e:
        import traceback
        tasks_db[task_id]["status"] = "error"
        tasks_db[task_id]["error"] = str(e)
        print(f"Task {task_id} failed:")
        traceback.print_exc()

# --- API ENDPOINTS ---

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MaltaVRP Solver"}

@app.post("/solve")
async def solve_cvrptw(request: SolveRequest, background_tasks: BackgroundTasks):
    """
    Starts an optimization task in the background.
    Returns a task_id for polling.
    """
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "status": "queued",
        "created_at": time.time(),
        "result": None
    }
    
    # Run the CPU-intensive task in the background
    background_tasks.add_task(
        run_optimization_task, 
        task_id, 
        request.fleet.dict(), 
        [u.dict() for u in request.users]
    )
    
    return {"task_id": task_id, "status": "queued"}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Poll this endpoint to check if the solver is finished.
    """
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

# --- STATIC FILES & UI ---

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
