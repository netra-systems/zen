"""
Standalone Auth Service - No External Dependencies
Minimal authentication service for Netra
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, UTC

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
ph = PasswordHasher()

# Security
security = HTTPBearer()

# Unified Health System (simplified for standalone service)
class SimpleHealthInterface:
    """Simplified health interface for standalone auth service."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.start_time = datetime.now(UTC)
    
    def get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status."""
        return {
            "status": "healthy",
            "service": self.service_name,
            "version": self.version,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": self._get_uptime_seconds()
        }
    
    def _get_uptime_seconds(self) -> float:
        """Calculate service uptime in seconds."""
        return (datetime.now(UTC) - self.start_time).total_seconds()

# Initialize health interface
health_interface = SimpleHealthInterface("auth-service", "1.0.0")

# Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int

class DevLoginRequest(BaseModel):
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: str
    uptime_seconds: Optional[float] = None

# Temporary in-memory user store (replace with database in production)
USERS_DB = {
    "admin@netra.ai": {
        "id": "user_001",
        "email": "admin@netra.ai",
        "hashed_password": ph.hash("admin123"),
        "role": "admin"
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Standalone Auth Service...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Port: {os.getenv('PORT', '8080')}")
    
    yield
    
    logger.info("Shutting down Auth Service...")

# Create FastAPI app
app = FastAPI(
    title="Netra Auth Service",
    description="Standalone Authentication Service",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

if not cors_origins:
    cors_origins = ["*"]  # Allow all in development

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Security middleware for production
if os.getenv("ENVIRONMENT") in ["staging", "production"]:
    allowed_hosts = [
        "*.netrasystems.ai",
        "*.run.app",
        "localhost"
    ]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False

def create_access_token(data: dict) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Verify and decode a JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        user_id: str = payload.get("user_id")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(email=email, user_id=user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "auth-service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "login": "/auth/login",
            "verify": "/auth/verify",
            "logout": "/auth/logout",
            "dev_login": "/auth/dev_login"
        }
    }

@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint with unified health system"""
    return health_interface.get_basic_health()

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login endpoint"""
    # Check if user exists
    user = USERS_DB.get(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"email": user["email"], "user_id": user["id"]}
    )
    
    return LoginResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.get("/auth/verify")
async def verify(token_data: TokenData = Depends(verify_token)):
    """Verify token endpoint"""
    return {
        "valid": True,
        "email": token_data.email,
        "user_id": token_data.user_id
    }

@app.post("/auth/logout")
async def logout(token_data: TokenData = Depends(verify_token)):
    """Logout endpoint (client should discard token)"""
    return {"message": "Logged out successfully"}

@app.post("/auth/dev_login", response_model=LoginResponse)
async def dev_login(request: DevLoginRequest):
    """Development login endpoint - mocks JWT OAuth for testing"""
    # Only allow in development environment
    if os.getenv("ENVIRONMENT", "development") not in ["development", "testing"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is not available in this environment"
        )
    
    # Create or use a dev user
    dev_user = {
        "id": f"dev_user_{request.email.replace('@', '_').replace('.', '_')}",
        "email": request.email,
        "role": "dev_user"
    }
    
    # Create access token with dev user data
    access_token = create_access_token(
        data={"email": dev_user["email"], "user_id": dev_user["id"]}
    )
    
    logger.info(f"Dev login successful for user: {request.email}")
    
    return LoginResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)