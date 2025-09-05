#!/usr/bin/env python
"""Discover what endpoints are actually available on staging"""

import aiohttp
import asyncio
import json
import ssl
from shared.isolated_environment import IsolatedEnvironment

STAGING_BASE = "https://api.staging.netrasystems.ai"

async def discover_endpoints():
    """Try various endpoints to see what's available"""
    
    # Common API patterns to try
    endpoints = [
        "/",
        "/health",
        "/api/health",
        "/api/v1/health",
        "/status",
        "/api/status",
        "/swagger",
        "/docs",
        "/api/docs",
        "/api-docs",
        "/openapi.json",
        "/api/openapi.json",
        
        # Auth endpoints
        "/auth/login",
        "/api/auth/login",
        "/api/v1/auth/login",
        "/login",
        "/api/login",
        
        # Agent endpoints
        "/agents",
        "/api/agents",
        "/api/v1/agents",
        "/agent",
        "/api/agent",
        
        # Chat/Message endpoints
        "/chat",
        "/api/chat",
        "/api/v1/chat",
        "/message",
        "/api/message",
        "/api/v1/message",
        "/messages",
        "/api/messages",
        "/api/v1/messages",
        
        # WebSocket info
        "/ws",
        "/websocket",
        "/api/websocket",
        
        # User endpoints
        "/user",
        "/api/user",
        "/api/v1/user",
        "/users",
        "/api/users",
        
        # Version info
        "/version",
        "/api/version",
        "/info",
        "/api/info"
    ]
    
    timeout = aiohttp.ClientTimeout(total=5)
    
    print("Discovering available endpoints on staging...")
    print("="*60)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        available = []
        
        for endpoint in endpoints:
            url = f"{STAGING_BASE}{endpoint}"
            try:
                async with session.get(url) as resp:
                    if resp.status in [200, 201, 204]:
                        content_type = resp.headers.get('content-type', '')
                        if 'json' in content_type:
                            try:
                                data = await resp.json()
                                print(f"[OK] GET {endpoint} - {resp.status} - JSON response")
                                if isinstance(data, dict) and len(str(data)) < 200:
                                    print(f"  Response: {data}")
                            except:
                                print(f"[OK] GET {endpoint} - {resp.status}")
                        else:
                            print(f"[OK] GET {endpoint} - {resp.status} - {content_type}")
                        available.append(endpoint)
                    elif resp.status == 401:
                        print(f"[AUTH] GET {endpoint} - 401 Unauthorized (needs auth)")
                        available.append(f"{endpoint} (auth required)")
                    elif resp.status == 405:
                        print(f"[WARN] GET {endpoint} - 405 Method Not Allowed (try POST)")
                    elif resp.status == 404:
                        pass  # Skip 404s to reduce noise
                    else:
                        print(f"[?] GET {endpoint} - {resp.status}")
            except asyncio.TimeoutError:
                print(f"[TIMEOUT] GET {endpoint} - Timeout")
            except Exception as e:
                if "Cannot connect" not in str(e):
                    print(f"[ERROR] GET {endpoint} - Error: {e}")
        
        print("\n" + "="*60)
        print("TRYING POST ENDPOINTS")
        print("="*60)
        
        # Try POST for certain endpoints
        post_endpoints = [
            "/auth/login",
            "/api/auth/login",
            "/login",
            "/api/login",
            "/chat",
            "/api/chat",
            "/message",
            "/api/message",
            "/api/v1/message",
            "/agent/message",
            "/api/agent/message"
        ]
        
        for endpoint in post_endpoints:
            url = f"{STAGING_BASE}{endpoint}"
            try:
                test_data = {"test": True, "message": "test"}
                async with session.post(url, json=test_data) as resp:
                    if resp.status in [200, 201, 202]:
                        print(f"[OK] POST {endpoint} - {resp.status}")
                        available.append(f"POST {endpoint}")
                    elif resp.status == 400:
                        print(f"[WARN] POST {endpoint} - 400 Bad Request (needs proper payload)")
                        available.append(f"POST {endpoint} (needs payload)")
                    elif resp.status == 401:
                        print(f"[AUTH] POST {endpoint} - 401 Unauthorized")
                        available.append(f"POST {endpoint} (auth required)")
                    elif resp.status == 422:
                        print(f"[WARN] POST {endpoint} - 422 Unprocessable Entity (wrong payload format)")
                        available.append(f"POST {endpoint} (wrong format)")
            except Exception as e:
                if "404" not in str(e):
                    pass
        
        print("\n" + "="*60)
        print("SUMMARY OF AVAILABLE ENDPOINTS")
        print("="*60)
        for ep in available:
            print(f"  * {ep}")
        
        return available

if __name__ == "__main__":
    asyncio.run(discover_endpoints())