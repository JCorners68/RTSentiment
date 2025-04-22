from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/login")
async def login():
    """Simplified login endpoint"""
    return {"access_token": "demo_token", "token_type": "bearer"}

@router.get("/me")
async def read_users_me():
    """Get current user info"""
    return {"username": "demo_user", "email": "demo@example.com"}