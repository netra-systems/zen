#!/usr/bin/env python
"""Quick staging environment test"""

import asyncio
import aiohttp
import json
import sys
from shared.isolated_environment import IsolatedEnvironment

STAGING_BACKEND_URL = "https://api.staging.netrasystems.ai"
STAGING_AUTH_URL = "https://auth-service-staging-pnovr5vsba-uc.a.run.app"

async def test_backend_health():
    """Test backend health endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{STAGING_BACKEND_URL}/health") as response:
                data = await response.json()
                print(f"[OK] Backend Health: {response.status} - {data.get('status', 'unknown')}")
                return response.status == 200
        except Exception as e:
            print(f"[FAIL] Backend Health Failed: {e}")
            return False

async def test_backend_api():
    """Test backend API endpoints"""
    async with aiohttp.ClientSession() as session:
        # Test system info
        try:
            async with session.get(f"{STAGING_BACKEND_URL}/system/info") as response:
                data = await response.json()
                print(f"[OK] System Info: {response.status} - Version {data.get('version', 'unknown')}")
        except Exception as e:
            print(f"[FAIL] System Info Failed: {e}")

async def test_websocket_connection():
    """Test WebSocket connectivity"""
    ws_url = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws"
    
    try:
        async with aiohttp.ClientSession() as session:
            # This just tests if the endpoint exists
            async with session.ws_connect(
                ws_url,
                timeout=aiohttp.ClientTimeout(total=5),
                headers={"Authorization": "Bearer test"}
            ) as ws:
                print(f"[OK] WebSocket endpoint reachable")
                await ws.close()
    except aiohttp.ClientError as e:
        if "401" in str(e) or "403" in str(e):
            print(f"[OK] WebSocket endpoint exists (auth required)")
        else:
            print(f"[FAIL] WebSocket Connection Failed: {e}")
    except Exception as e:
        print(f"[U+2717] WebSocket Connection Failed: {e}")

async def main():
    """Run all staging tests"""
    print("=" * 60)
    print("STAGING ENVIRONMENT TESTS")
    print("=" * 60)
    
    # Run tests
    await test_backend_health()
    await test_backend_api()
    await test_websocket_connection()
    
    print("=" * 60)
    print("Tests completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
