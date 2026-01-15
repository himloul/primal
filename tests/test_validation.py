def test_out_of_bounds_validation(sample_fleet, sample_users, mock_engine):
    """Ensures the solver rejects coordinates far outside the graph."""
    # We must mock the bounds in the engine since our MockEngine is simple
    mock_engine.bounds = {"min_lat": 31.0, "max_lat": 32.0, "min_lon": -8.5, "max_lon": -7.5}

    # Add validate_points method to mock
    def validate(locs):
        for i, (lon, lat) in enumerate(locs):
            if not (31.0 <= lat <= 32.0 and -8.5 <= lon <= -7.5):
                return False, "Out of bounds"
        return True, None

    mock_engine.validate_points = validate

    # Create a user in Paris (Way outside Marrakech)
    sample_users[0]["latitude_p"] = 48.8566
    sample_users[0]["longitude_p"] = 2.3522

    from src.optimization import solve_cpdptw

    result = solve_cpdptw(sample_fleet, sample_users, mock_engine)

    assert result["status"] == "failed"
    assert "Invalid Coordinates" in result["error"]
