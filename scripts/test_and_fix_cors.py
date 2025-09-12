"""
Test and fix CORS configuration for localhost vs 127.0.0.1 mismatch.
"""

import asyncio
import httpx
import json
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment


async def test_cors_preflight(
    frontend_origin: str,
    backend_url: str
) -> Dict[str, Any]:
    """Test CORS preflight request."""
    async with httpx.AsyncClient() as client:
        try:
            # Send OPTIONS request (preflight)
            response = await client.options(
                backend_url,
                headers={
                    "Origin": frontend_origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type, Authorization"
                }
            )
            
            result = {
                "origin": frontend_origin,
                "backend_url": backend_url,
                "status_code": response.status_code,
                "cors_headers": {
                    "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin", "NOT SET"),
                    "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods", "NOT SET"),
                    "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers", "NOT SET"),
                    "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials", "NOT SET"),
                },
                "success": response.status_code == 200
            }
            
            if response.status_code != 200:
                result["error"] = response.text
                
            return result
            
        except Exception as e:
            return {
                "origin": frontend_origin,
                "backend_url": backend_url,
                "error": str(e),
                "success": False
            }


async def test_actual_request(
    frontend_origin: str,
    backend_url: str
) -> Dict[str, Any]:
    """Test actual GET request with CORS."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                backend_url,
                headers={
                    "Origin": frontend_origin,
                    "Accept": "application/json"
                }
            )
            
            result = {
                "origin": frontend_origin,
                "backend_url": backend_url,
                "status_code": response.status_code,
                "cors_headers": {
                    "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin", "NOT SET"),
                },
                "success": response.status_code in [200, 201]
            }
            
            return result
            
        except Exception as e:
            return {
                "origin": frontend_origin,
                "backend_url": backend_url,
                "error": str(e),
                "success": False
            }


async def main():
    """Test CORS configuration."""
    print("=" * 60)
    print("CORS Configuration Test")
    print("=" * 60)
    
    # Test scenarios
    test_cases = [
        # Your exact scenario
        ("http://127.0.0.1:3000", "http://localhost:8000/api/threads"),
        
        # Reverse scenario
        ("http://localhost:3000", "http://127.0.0.1:8000/api/threads"),
        
        # Same host scenarios (should always work)
        ("http://localhost:3000", "http://localhost:8000/api/threads"),
        ("http://127.0.0.1:3000", "http://127.0.0.1:8000/api/threads"),
    ]
    
    print("\n1. Testing CORS Preflight Requests (OPTIONS)")
    print("-" * 40)
    
    for frontend_origin, backend_url in test_cases:
        result = await test_cors_preflight(frontend_origin, backend_url)
        
        status = " PASS:  PASS" if result["success"] else " FAIL:  FAIL"
        print(f"\n{status} Frontend: {frontend_origin}")
        print(f"     Backend:  {backend_url}")
        
        if not result["success"]:
            print(f"     Status:   {result.get('status_code', 'N/A')}")
            if "error" in result:
                print(f"     Error:    {result['error']}")
            print(f"     CORS Origin Header: {result.get('cors_headers', {}).get('Access-Control-Allow-Origin', 'NOT SET')}")
    
    print("\n\n2. Testing Actual GET Requests")
    print("-" * 40)
    
    for frontend_origin, backend_url in test_cases:
        result = await test_actual_request(frontend_origin, backend_url)
        
        status = " PASS:  PASS" if result["success"] else " FAIL:  FAIL"
        print(f"\n{status} Frontend: {frontend_origin}")
        print(f"     Backend:  {backend_url}")
        
        if not result["success"]:
            if "error" in result:
                print(f"     Error:    {result['error']}")
            else:
                print(f"     Status:   {result.get('status_code', 'N/A')}")
                print(f"     CORS Origin Header: {result.get('cors_headers', {}).get('Access-Control-Allow-Origin', 'NOT SET')}")
    
    print("\n\n3. SOLUTION")
    print("-" * 40)
    print("""
The issue is that browsers treat 'localhost' and '127.0.0.1' as different origins,
even though they resolve to the same address.

IMMEDIATE FIX (Choose one):
1. Use consistent hostnames - access both frontend and backend via either:
   - http://localhost:3000  ->  http://localhost:8000
   - http://127.0.0.1:3000  ->  http://127.0.0.1:8000

2. Set environment variable to allow all local origins:
   export CORS_ORIGINS="*"  (for development only)

3. The backend CORS configuration should already handle this, but if not,
   ensure the backend is running with proper environment detection.

DEBUGGING:
- Check that your backend is detecting 'development' environment
- Verify CORS middleware is properly initialized
- Check backend logs for CORS-related messages
""")


if __name__ == "__main__":
    print("Testing CORS configuration...")
    print("Make sure your backend is running on port 8000")
    asyncio.run(main())