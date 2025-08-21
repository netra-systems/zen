"""
Simple OAuth proxy for staging environment.
Handles OAuth redirects with proper CORS headers.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os
import httpx
from typing import Dict, Any
from datetime import datetime, UTC

app = FastAPI()

# CORS configuration with regex support for wildcard subdomains
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class WildcardCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)
        
        # Check if origin matches allowed patterns
        if origin:
            # Allow any subdomain of staging.netrasystems.ai
            if re.match(r'^https://[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$', origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
            # Also allow localhost for development
            elif origin in ["http://localhost:3000", "http://localhost:3001"]:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response

app.add_middleware(WildcardCORSMiddleware)

BACKEND_URL = os.getenv("BACKEND_URL", "https://api.staging.netrasystems.ai")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://app.staging.netrasystems.ai")

# Simplified Health Interface for Auth Proxy
class ProxyHealthInterface:
    """Simple health interface for auth proxy service."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.start_time = datetime.now(UTC)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status with proxy-specific information."""
        return {
            "status": "healthy",
            "service": self.service_name,
            "version": self.version,
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": self._get_uptime_seconds(),
            "backend_url": BACKEND_URL,
            "frontend_url": FRONTEND_URL
        }
    
    def _get_uptime_seconds(self) -> float:
        """Calculate service uptime in seconds."""
        return (datetime.now(UTC) - self.start_time).total_seconds()

# Initialize health interface
health_interface = ProxyHealthInterface("auth-proxy", "1.0.0")

@app.get("/")
async def root() -> Dict[str, Any]:
    """Health check endpoint with service information."""
    return health_interface.get_health_status()

@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint with unified health system."""
    return health_interface.get_health_status()

@app.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Proxy OAuth login requests to backend."""
    params = dict(request.query_params)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_URL}/api/auth/{provider}/login",
            params=params,
            follow_redirects=False
        )
        if response.status_code == 302:
            return RedirectResponse(
                url=response.headers.get("Location"),
                status_code=302
            )
    return response.json()

@app.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request):
    """Handle OAuth callbacks."""
    params = dict(request.query_params)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_URL}/api/auth/{provider}/callback",
            params=params,
            follow_redirects=False
        )
        if response.status_code == 302:
            # Redirect to frontend after successful auth
            redirect_url = response.headers.get("Location", FRONTEND_URL)
            return RedirectResponse(
                url=redirect_url,
                status_code=302
            )
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)