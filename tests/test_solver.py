"""
Integration tests for the Solver Logic using the main entry point.
"""

from src.optimization import solve_cpdptw


def test_solver_feasibility(sample_fleet, sample_users, mock_engine):
    """Ensures the solver can find a simple path for 1 user."""
    result = solve_cpdptw(sample_fleet, sample_users, mock_engine)
    assert result["status"] == "success"
    assert len(result["routes"]) >= 1


def test_capacity_constraint_ortools(sample_users, mock_engine):
    """Ensures OR-Tools fails if passengers exceed taxi capacity (Hard Constraint)."""
    fleet = {
        "depot": {"location": [0.0, 0.0]},
        "taxis": [{"id": "T1", "capacity": 1}],  # Capacity 1 vs 2 People
    }
    result = solve_cpdptw(fleet, sample_users, mock_engine)
    # OR-Tools returns failed status when no solution is found
    assert result["status"] == "failed"


def test_pickup_delivery_sequence(sample_fleet, sample_users, mock_engine):
    """Verifies that Pickup always happens before Delivery."""
    result = solve_cpdptw(sample_fleet, sample_users, mock_engine)
    assert result["status"] == "success"

    # Check the first route
    route = result["routes"][0]["steps"]
    # Find indices
    pickup_idx = -1
    dropoff_idx = -1
    for i, step in enumerate(route):
        if step["type"] == "pickup":
            pickup_idx = i
        elif step["type"] == "dropoff":
            dropoff_idx = i

    assert pickup_idx != -1
    assert dropoff_idx != -1
    assert pickup_idx < dropoff_idx
