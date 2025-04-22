from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

@router.get("/")
async def get_subscriptions():
    """Get all subscriptions"""
    return [
        {"id": 1, "name": "Bloomberg", "status": "active"},
        {"id": 2, "name": "Reuters", "status": "active"},
        {"id": 3, "name": "Twitter", "status": "inactive"},
    ]

@router.post("/")
async def create_subscription():
    """Create a new subscription (simplified)"""
    return {"id": 4, "name": "New Subscription", "status": "pending"}