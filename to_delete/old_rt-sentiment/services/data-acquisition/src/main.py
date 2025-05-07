"""
Data Acquisition Service - Main Module

This module provides the main FastAPI application for the data acquisition service.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Data Acquisition Service",
    description="Service for gathering data from various sources for sentiment analysis",
    version="0.1.0",
)

# Data models
class DataSource(BaseModel):
    """Model representing a data source."""
    id: str
    name: str
    type: str
    status: str = "active"
    config: Dict = {}

class DataPayload(BaseModel):
    """Model representing data from a source."""
    source_id: str
    text: str
    metadata: Optional[Dict] = None

# In-memory storage for demo purposes
data_sources: Dict[str, DataSource] = {}
collected_data: List[DataPayload] = []

@app.get("/")
def read_root():
    """Health check endpoint."""
    environment = os.environ.get("ENVIRONMENT", "development")
    return {
        "status": "healthy", 
        "service": "data-acquisition",
        "environment": environment
    }

@app.get("/sources", response_model=List[DataSource])
def get_sources():
    """Get all registered data sources."""
    return list(data_sources.values())

@app.post("/sources", response_model=DataSource)
def create_source(source: DataSource):
    """Register a new data source."""
    if source.id in data_sources:
        raise HTTPException(status_code=400, detail="Source already exists")
    
    data_sources[source.id] = source
    logger.info(f"Created new data source: {source.id}")
    return source

@app.get("/sources/{source_id}", response_model=DataSource)
def get_source(source_id: str):
    """Get a specific data source by ID."""
    if source_id not in data_sources:
        raise HTTPException(status_code=404, detail="Source not found")
    return data_sources[source_id]

@app.post("/data", response_model=Dict)
def ingest_data(payload: DataPayload):
    """Ingest data from a source."""
    if payload.source_id not in data_sources:
        raise HTTPException(status_code=404, detail="Source not found")
    
    collected_data.append(payload)
    logger.info(f"Ingested data from source: {payload.source_id}")
    
    # In a real implementation, this would forward data to the sentiment analysis service
    return {"status": "success", "message": "Data ingested successfully"}

@app.get("/data", response_model=List[DataPayload])
def get_data():
    """Get all collected data (for demo purposes)."""
    return collected_data

if __name__ == "__main__":
    # Run the application with uvicorn when executed directly
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)