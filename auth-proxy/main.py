"""
Simple OAuth proxy for staging environment.
Handles OAuth redirects with proper CORS headers.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os
import httpx

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

BACKEND_URL = os.getenv("BACKEND_URL", "https://backend.staging.netrasystems.ai")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://app.staging.netrasystems.ai")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "auth-proxy"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

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