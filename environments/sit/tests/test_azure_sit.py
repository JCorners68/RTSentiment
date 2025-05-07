"""
Azure SIT Environment verification tests.

These tests verify that the SIT environment is deployed correctly in Azure
and all services are running.
"""
import os
import pytest
import requests
import time
import json

def get_service_endpoint():
    """Get the service endpoint from the service_endpoints.txt file."""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    endpoint_file = os.path.join(script_dir, "config", "service_endpoints.txt")
    
    if not os.path.exists(endpoint_file):
        pytest.skip(f"Service endpoints file not found: {endpoint_file}")
        
    with open(endpoint_file, "r") as f:
        lines = f.readlines()
        
    # Parse the endpoint from the file
    for line in lines:
        if line.startswith("Data Acquisition Service:"):
            return line.split(":", 1)[1].strip()
            
    pytest.skip("Data Acquisition Service endpoint not found in endpoints file")
    return None

def test_data_acquisition_service_health():
    """Test that the data acquisition service is running and healthy in Azure."""
    endpoint = get_service_endpoint()
    
    # Give the service a moment to start
    time.sleep(2)
    
    # Send a request to the health check endpoint
    try:
        response = requests.get(f"{endpoint}/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-acquisition"
        assert data["environment"] == "sit"
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Could not connect to the data acquisition service at {endpoint}. Is it running?")

def test_data_acquisition_service_functionality():
    """Test basic functionality of the data acquisition service in Azure."""
    endpoint = get_service_endpoint()
    
    # Create a data source
    source = {
        "id": "test-source-azure",
        "name": "Test Source Azure",
        "type": "twitter",
        "status": "active"
    }
    
    try:
        response = requests.post(f"{endpoint}/sources", json=source)
        assert response.status_code == 200
        
        # Get the data source
        response = requests.get(f"{endpoint}/sources/test-source-azure")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-source-azure"
        
        # Ingest some data
        payload = {
            "source_id": "test-source-azure",
            "text": "This is a test message from the Azure SIT environment verification test."
        }
        response = requests.post(f"{endpoint}/data", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Could not connect to the data acquisition service API endpoints at {endpoint}.")

def test_kubernetes_connectivity():
    """Test that we can connect to the Kubernetes cluster."""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kubeconfig = os.path.join(script_dir, "config", "kubeconfig")
    
    if not os.path.exists(kubeconfig):
        pytest.skip(f"Kubeconfig file not found: {kubeconfig}")
    
    # Use kubectl to get the cluster info
    result = os.system(f"KUBECONFIG={kubeconfig} kubectl cluster-info")
    assert result == 0, "Failed to connect to the Kubernetes cluster"
    
    # Check that the sit namespace exists
    result = os.system(f"KUBECONFIG={kubeconfig} kubectl get namespace sit")
    assert result == 0, "SIT namespace not found in the Kubernetes cluster"
    
    # Check that the data-acquisition deployment exists
    result = os.system(f"KUBECONFIG={kubeconfig} kubectl get deployment -n sit data-acquisition")
    assert result == 0, "Data acquisition deployment not found in the SIT namespace"