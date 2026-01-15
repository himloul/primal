"""
Integration tests for the FastAPI endpoints.
Tests the request/response lifecycle and async polling.
"""

import time
import pytest
from fastapi.testclient import TestClient
from src.api import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    """Verify the API is up."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_solve_async_flow(client):
    """Tests the full Async flow: Submit -> Get Task ID -> Poll Result."""

    payload = {
        "fleet": {
            "depot": {"location": [-8.0194, 31.6300]},
            "taxis": [{"id": "TX1", "capacity": 4}],
        },
        "users": [
            {
                "id": "U1",
                "p_lon": -7.9891,
                "p_lat": 31.6258,
                "d_lon": -8.0120,
                "d_lat": 31.6450,
                "passengers": 1,
                "service_time": 120,
                "ready_time": 0,
                "due_time": 3600,
            }
        ],
    }

    # 1. Submit Solve Task
    response = client.post("/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]

    # 2. Poll for Completion (with timeout)
    completed = False
    for _ in range(60):  # Max 60 seconds
        status_resp = client.get(f"/tasks/{task_id}")
        task = status_resp.json()

        if task["status"] == "completed":
            completed = True
            assert "routes" in task["result"]
            break
        elif task["status"] == "failed":
            pytest.fail(f"Solver failed unexpectedly: {task.get('error')}")
        elif task["status"] == "error":
            pytest.fail(f"Solver crashed: {task.get('error')}")

        time.sleep(1)

    assert completed is True
