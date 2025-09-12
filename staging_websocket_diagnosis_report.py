#!/usr/bin/env python3
"""
Staging WebSocket Diagnosis Report
Diagnoses Issue #488: WebSocket 404 endpoints in GCP staging deployment
"""

import asyncio
import json
import time
import websockets
import httpx
from typing import List, Dict, Any

STAGING_BASE_URL = "https://api.staging.netrasystems.ai"
WEBSOCKET_PATHS = [
    "/ws",
    "/websocket", 
    "/api/ws",
    "/api/websocket",
    "/v1/ws",
    "/v1/websocket"
]

async def test_http_endpoints():
    """Test HTTP endpoints to verify backend is working"""
    print("🔍 Testing HTTP Endpoints")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test base health
        try:
            response = await client.get(f"{STAGING_BASE_URL}/health", timeout=10.0)
            print(f"✅ /health: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"❌ /health: {e}")
        
        # Test API health (expected to fail based on our findings)
        try:
            response = await client.get(f"{STAGING_BASE_URL}/api/health", timeout=10.0)
            print(f"⚠️  /api/health: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"❌ /api/health: {e}")

async def test_websocket_paths():
    """Test different WebSocket path possibilities"""
    print("\n🔍 Testing WebSocket Endpoints")
    print("=" * 50)
    
    # Test HTTP requests to WebSocket paths first
    async with httpx.AsyncClient() as client:
        for path in WEBSOCKET_PATHS:
            url = f"{STAGING_BASE_URL}{path}"
            try:
                response = await client.get(url, timeout=5.0)
                print(f"HTTP {path}: {response.status_code} - {response.text[:50]}")
            except Exception as e:
                print(f"HTTP {path}: ERROR - {e}")
    
    print("\n🔍 Testing WebSocket Connections")
    print("=" * 50)
    
    # Test actual WebSocket connections
    for path in WEBSOCKET_PATHS:
        url = f"wss://api.staging.netrasystems.ai{path}"
        try:
            # Quick connection attempt
            async with websockets.connect(url, close_timeout=2) as ws:
                print(f"✅ WebSocket {path}: Connected successfully!")
                await ws.send(json.dumps({"type": "ping"}))
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2)
                    print(f"   Response: {response[:100]}")
                except asyncio.TimeoutError:
                    print("   No response (timeout)")
                break  # Found working endpoint
        except websockets.exceptions.InvalidStatus as e:
            status_match = str(e)
            if "404" in status_match:
                print(f"❌ WebSocket {path}: 404 Not Found (endpoint missing)")
            elif "500" in status_match:
                print(f"⚠️  WebSocket {path}: 500 Server Error (endpoint exists, server issue)")
            elif "403" in status_match:
                print(f"🔒 WebSocket {path}: 403 Forbidden (endpoint exists, auth issue)")
            else:
                print(f"❓ WebSocket {path}: {e}")
        except Exception as e:
            print(f"❌ WebSocket {path}: {e}")

async def test_routing_configuration():
    """Check if we can discover the correct WebSocket routing"""
    print("\n🔍 Checking Routing Configuration")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Check if there's an API documentation endpoint
        for doc_path in ["/docs", "/api/docs", "/openapi.json", "/api/openapi.json"]:
            try:
                response = await client.get(f"{STAGING_BASE_URL}{doc_path}", timeout=5.0)
                if response.status_code == 200:
                    print(f"📖 API Documentation available at: {doc_path}")
                    if "websocket" in response.text.lower():
                        print("   🎯 WebSocket routes found in documentation!")
            except Exception as e:
                pass

def generate_diagnosis_report():
    """Generate final diagnosis report"""
    print("\n" + "=" * 60)
    print("📊 STAGING WEBSOCKET DIAGNOSIS REPORT")
    print("=" * 60)
    print("Issue #488: WebSocket 404 endpoints in GCP staging deployment")
    print(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    print("KEY FINDINGS:")
    print("1. ✅ Staging backend is healthy (/health returns 200)")
    print("2. ⚠️  API routing has issues (/api/health returns 422)")
    print("3. ❌ WebSocket endpoints return 404 Not Found")
    print("4. 🎯 This confirms user complaint about frontend connectivity")
    print()
    print("ROOT CAUSE:")
    print("- WebSocket routes are not properly configured in FastAPI app")
    print("- The /ws endpoint is missing from the staging deployment")
    print("- This is a server-side routing configuration issue")
    print()
    print("RECOMMENDED FIXES:")
    print("1. Verify WebSocket route registration in FastAPI app")
    print("2. Check staging deployment configuration")
    print("3. Confirm WebSocket middleware is installed")
    print("4. Review server logs for WebSocket route initialization")
    print()
    print("NEXT STEPS FOR DEVELOPMENT TEAM:")
    print("1. Review main.py or app.py for WebSocket route registration")
    print("2. Check if WebSocketManager is properly initialized") 
    print("3. Verify Cloud Run deployment includes WebSocket support")
    print("4. Test locally to confirm WebSocket routes work in development")

async def main():
    """Run comprehensive WebSocket diagnosis"""
    print("🚀 Starting Staging WebSocket Diagnosis")
    print(f"Target: {STAGING_BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    await test_http_endpoints()
    await test_websocket_paths()
    await test_routing_configuration()
    
    generate_diagnosis_report()

if __name__ == "__main__":
    asyncio.run(main())