"""Test helper functions for missing imports"""
import hashlib
import jwt
from datetime import datetime, timedelta
import os

def hash_password(password: str) -> str:
    """Simple password hashing for tests"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT token for testing"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    
    secret_key = os.environ.get("JWT_SECRET_KEY", "test-secret")
    return jwt.encode(to_encode, secret_key, algorithm="HS256")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return hash_password(plain_password) == hashed_password

# Mock BaseAgent for tests
class BaseAgent:
    """Mock BaseAgent for testing"""
    def __init__(self, *args, **kwargs):
        pass
    
    async def process(self, *args, **kwargs):
        return {"result": "mocked"}