import os
import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Authentication Service",
    description="Authentication service for real-time sentiment analysis",
    version="1.0.0",
)

@app.get("/")
async def root():
    return {"message": "Auth Service API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)