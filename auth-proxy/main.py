"""
Simple OAuth proxy for staging environment.
Handles OAuth redirects with proper CORS headers.
"""
import os
from datetime import UTC, datetime
from typing import Any, Dict

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Import unified CORS configuration
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.cors_config import get_fastapi_cors_config

app = FastAPI()

# Use unified CORS configuration from shared module
cors_config = get_fastapi_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)

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
            f"{BACKEND_URL}/auth/{provider}/login",
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
            f"{BACKEND_URL}/auth/{provider}/callback",
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