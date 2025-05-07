"""
Unit tests for the data acquisition service main module.
"""
import sys
import os
from fastapi.testclient import TestClient

# Add the src directory to the path so we can import the main module
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from main import app, DataSource

client = TestClient(app)

def test_read_root():
    """Test the health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "data-acquisition"

def test_create_source():
    """Test creating a data source."""
    source = {
        "id": "test-source",
        "name": "Test Source",
        "type": "twitter",
        "status": "active",
        "config": {"api_key": "dummy-key"}
    }
    response = client.post("/sources", json=source)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-source"
    assert data["name"] == "Test Source"

def test_get_sources():
    """Test retrieving all data sources."""
    # First create a source
    source = {
        "id": "another-source",
        "name": "Another Test Source",
        "type": "rss",
        "status": "active"
    }
    client.post("/sources", json=source)
    
    # Now get all sources
    response = client.get("/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check if our source is in the list
    source_ids = [s["id"] for s in data]
    assert "another-source" in source_ids

def test_ingest_data():
    """Test ingesting data from a source."""
    # First create a source
    source = {
        "id": "data-source",
        "name": "Data Test Source",
        "type": "custom",
        "status": "active"
    }
    client.post("/sources", json=source)
    
    # Now ingest data
    payload = {
        "source_id": "data-source",
        "text": "This is a test message that will be analyzed for sentiment.",
        "metadata": {"author": "test-user", "timestamp": "2023-01-01T00:00:00Z"}
    }
    response = client.post("/data", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify data was stored
    response = client.get("/data")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check if our data is in the list
    matching_data = [d for d in data if d["text"] == payload["text"]]
    assert len(matching_data) >= 1