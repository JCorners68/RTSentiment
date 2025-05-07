"""
UAT Environment verification tests.

These tests verify that the UAT environment is set up correctly and all services are running.
"""
import pytest
import requests
import time

# URL constants - in a real implementation these would be specified in a config file
DATA_ACQUISITION_URL = "https://data-acquisition.uat.example.com"

def test_data_acquisition_service_health():
    """Test that the data acquisition service is running and healthy."""
    # Give the service a moment to start
    time.sleep(2)
    
    # Send a request to the health check endpoint
    try:
        response = requests.get(f"{DATA_ACQUISITION_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-acquisition"
        assert data["environment"] == "uat"
    except requests.exceptions.ConnectionError:
        pytest.fail("Could not connect to the data acquisition service. Is it running?")

def test_data_acquisition_service_functionality():
    """Test basic functionality of the data acquisition service."""
    # Create a data source
    source = {
        "id": "uat-test-source",
        "name": "UAT Test Source",
        "type": "twitter",
        "status": "active"
    }
    
    try:
        response = requests.post(f"{DATA_ACQUISITION_URL}/sources", json=source)
        assert response.status_code == 200
        
        # Get the data source
        response = requests.get(f"{DATA_ACQUISITION_URL}/sources/uat-test-source")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "uat-test-source"
        
        # Ingest some data
        payload = {
            "source_id": "uat-test-source",
            "text": "This is a test message from the UAT environment verification test."
        }
        response = requests.post(f"{DATA_ACQUISITION_URL}/data", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    except requests.exceptions.ConnectionError:
        pytest.fail("Could not connect to the data acquisition service API endpoints.")