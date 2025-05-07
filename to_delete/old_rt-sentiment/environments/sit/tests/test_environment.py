"""
SIT Environment verification tests.

These tests verify that the SIT environment is set up correctly and all services are running.
"""
import pytest
import requests
import time

def test_data_acquisition_service_health():
    """Test that the data acquisition service is running and healthy."""
    # Give the service a moment to start
    time.sleep(2)
    
    # Send a request to the health check endpoint
    try:
        response = requests.get("http://localhost:8002/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-acquisition"
        assert data["environment"] == "sit"
    except requests.exceptions.ConnectionError:
        pytest.fail("Could not connect to the data acquisition service. Is it running?")

def test_data_acquisition_service_functionality():
    """Test basic functionality of the data acquisition service."""
    # Create a data source
    source = {
        "id": "test-source",
        "name": "Test Source",
        "type": "twitter",
        "status": "active"
    }
    
    try:
        response = requests.post("http://localhost:8002/sources", json=source)
        assert response.status_code == 200
        
        # Get the data source
        response = requests.get("http://localhost:8002/sources/test-source")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-source"
        
        # Ingest some data
        payload = {
            "source_id": "test-source",
            "text": "This is a test message from the SIT environment verification test."
        }
        response = requests.post("http://localhost:8002/data", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    except requests.exceptions.ConnectionError:
        pytest.fail("Could not connect to the data acquisition service API endpoints.")