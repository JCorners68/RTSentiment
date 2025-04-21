import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from prometheus_client import make_asgi_app

try:
    # When running in the Docker container
    from routes import auth, sentiment, subscriptions
    from db.database import init_db
except ImportError:
    # When running directly or with relative imports
    from api.routes import auth, sentiment, subscriptions
    from api.db.database import init_db

app = FastAPI(
    title="Trading Sentiment Analysis API",
    description="API for real-time trading sentiment analysis",
    version="1.0.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["Sentiment"])
app.include_router(
    subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"]
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Database initialized")

@app.get("/")
async def root():
    return {"message": "Trading Sentiment Analysis API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)