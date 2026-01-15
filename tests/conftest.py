"""
Shared test fixtures for CVRP tests.
"""

import pytest


class MockEngine:
    def get_distance_matrix(self, locations, metric="travel_time"):
        n = len(locations)
        return [[10 if i != j else 0 for j in range(n)] for i in range(n)]

    def get_detailed_route(self, start, end):
        # Returns simple path from start to end (Lon, Lat)
        return [[start[1], start[0]], [end[1], end[0]]]

    def validate_points(self, locations):
        return True, None


@pytest.fixture
def mock_engine():
    return MockEngine()


@pytest.fixture
def sample_fleet():
    return {"depot": {"location": [0.0, 0.0]}, "taxis": [{"id": "T1", "capacity": 4}]}


@pytest.fixture
def sample_users():
    return [
        {
            "id": "U1",
            "longitude_p": 0.1,
            "latitude_p": 0.1,
            "longitude_d": 0.2,
            "latitude_d": 0.2,
            "number_people": 2,
            "service_time": 0,
            "ready_time": 0,
            "due_time": 1000,
        }
    ]
