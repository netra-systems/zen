#!/usr/bin/env python3
"""
Investigation script to discover available endpoints on staging services
"""

import asyncio
import httpx
import json

AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"
BACKEND_URL = "https://api.staging.netrasystems.ai"

async def investigate_endpoints():
    """Investigate available endpoints on both staging services"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 80)
        print("STAGING SERVICES ENDPOINT INVESTIGATION")
        print("=" * 80)
        
        # Test Auth Service
        print(f"\n[AUTH SERVICE]: {AUTH_SERVICE_URL}")
        print("-" * 50)
        
        auth_endpoints = [
            "/",
            "/health",
            "/docs",
            "/auth",
            "/auth/register", 
            "/auth/login",
            "/auth/me",
            "/auth/logout",
            "/api/auth/register",
            "/api/auth/login",
        ]
        
        for endpoint in auth_endpoints:
            try:
                response = await client.get(f"{AUTH_SERVICE_URL}{endpoint}")
                print(f"GET  {endpoint:20} -> {response.status_code}")
                if response.status_code == 200:
                    try:
                        content = response.json()
                        if len(str(content)) < 200:
                            print(f"     Response: {content}")
                    except:
                        pass
            except Exception as e:
                print(f"GET  {endpoint:20} -> ERROR: {e}")
        
        # Test Backend Service
        print(f"\n[BACKEND SERVICE]: {BACKEND_URL}")
        print("-" * 50)
        
        backend_endpoints = [
            "/",
            "/health",
            "/docs", 
            "/auth",
            "/auth/me",
            "/api/auth/me",
            "/api/demo",
            "/api/demo/",
            "/api/health",
            "/status",
        ]
        
        for endpoint in backend_endpoints:
            try:
                response = await client.get(f"{BACKEND_URL}{endpoint}")
                print(f"GET  {endpoint:20} -> {response.status_code}")
                if response.status_code == 200:
                    try:
                        content = response.json()
                        if len(str(content)) < 200:
                            print(f"     Response: {content}")
                    except:
                        pass
            except Exception as e:
                print(f"GET  {endpoint:20} -> ERROR: {e}")
        
        # Check if auth service has a different path structure
        print(f"\n[AUTH SERVICE - ROOT STRUCTURE CHECK]")
        print("-" * 50)
        
        try:
            root_response = await client.get(AUTH_SERVICE_URL)
            print(f"Root response: {root_response.status_code}")
            if root_response.status_code == 404:
                print("Root returns 404 - checking if service exists at all...")
                
                # Try common GCP service patterns
                gcp_patterns = [
                    f"{AUTH_SERVICE_URL}/",
                    f"{AUTH_SERVICE_URL}/api",
                    f"{AUTH_SERVICE_URL}/api/v1",
                    f"{AUTH_SERVICE_URL}/v1",
                ]
                
                for pattern in gcp_patterns:
                    try:
                        response = await client.get(pattern)
                        print(f"Pattern {pattern}: {response.status_code}")
                    except Exception as e:
                        print(f"Pattern {pattern}: ERROR {e}")
                        
        except Exception as e:
            print(f"Root check error: {e}")
        
        print(f"\n[DETAILED BACKEND ANALYSIS]")
        print("-" * 50)
        
        # Get backend openapi docs if available
        try:
            docs_response = await client.get(f"{BACKEND_URL}/docs")
            print(f"Backend /docs: {docs_response.status_code}")
            
            openapi_response = await client.get(f"{BACKEND_URL}/openapi.json")
            print(f"Backend OpenAPI: {openapi_response.status_code}")
            
            if openapi_response.status_code == 200:
                openapi_data = openapi_response.json()
                paths = list(openapi_data.get("paths", {}).keys())
                print(f"Available paths from OpenAPI: {len(paths)} endpoints")
                
                # Show auth-related endpoints
                auth_paths = [path for path in paths if "auth" in path.lower()]
                if auth_paths:
                    print(f"Auth-related endpoints: {auth_paths}")
                
        except Exception as e:
            print(f"Backend docs error: {e}")

if __name__ == "__main__":
    asyncio.run(investigate_endpoints())