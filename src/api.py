"""
CVRP Backend API
A thin wrapper around the Solver Service.
"""

import uuid
import time
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .optimization import solve_cpdptw
from .routing import RoutingEngine

# In-memory store for background tasks
tasks_db: Dict[str, Dict[str, Any]] = {}
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the Routing Engine once on startup
    print("Initializing Routing Engine...")
    app_state["engine"] = RoutingEngine()

    # Initialize Process Pool for CPU-bound tasks
    # limit workers to prevent memory exhaustion
    app_state["executor"] = ProcessPoolExecutor(max_workers=2)

    yield

    print("Shutting down...")
    app_state["executor"].shutdown()


app = FastAPI(title="CVRP API", version="1.2", lifespan=lifespan)


# --- SCHEMAS ---


class Vehicle(BaseModel):
    id: str
    capacity: int


class Depot(BaseModel):
    location: Tuple[float, float]


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
    use_heuristic: bool = False


# --- BACKGROUND TASK ---


async def solve_background_task(
    task_id: str,
    fleet: dict,
    users: list,
    engine: RoutingEngine,
    executor: ProcessPoolExecutor,
    use_heuristic: bool,
):
    try:
        tasks_db[task_id]["status"] = "processing"

        # Construct config override
        solver_config = {"use_heuristic_solver": use_heuristic}

        # Offload the heavy CPU blocking function to a separate process
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            executor, solve_cpdptw, fleet, users, engine, solver_config
        )

        if result.get("status") == "failed":
            tasks_db[task_id]["status"] = "failed"
            tasks_db[task_id]["error"] = result.get("error")
        else:
            tasks_db[task_id]["result"] = result
            tasks_db[task_id]["status"] = "completed"
            tasks_db[task_id]["completed_at"] = time.time()
    except Exception as e:
        tasks_db[task_id]["status"] = "error"
        tasks_db[task_id]["error"] = str(e)


# --- ENDPOINTS ---


@app.post("/solve")
async def solve(request: SolveRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {"status": "queued", "created_at": time.time(), "result": None}

    # Pass the shared engine and executor to the background task
    background_tasks.add_task(
        solve_background_task,
        task_id,
        request.fleet.model_dump(),
        [u.model_dump() for u in request.users],
        app_state["engine"],
        app_state["executor"],
        request.use_heuristic,
    )
    return {"task_id": task_id}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404)
    return task


@app.get("/health")
def health():
    return {"status": "ok"}


# --- UI ---
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
