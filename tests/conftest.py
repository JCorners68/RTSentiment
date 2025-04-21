import pytest
import os
import sys

# Add the parent directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Fixture for test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    # Set environment variables for testing
    os.environ["TESTING"] = "1"
    os.environ["FINBERT_USE_ONNX"] = "false"
    os.environ["FINBERT_USE_GPU"] = "false"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
    
    yield
    
    # Clean up after tests
    os.environ.pop("TESTING", None)