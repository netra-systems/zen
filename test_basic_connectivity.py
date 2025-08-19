#!/usr/bin/env python3
"""
Basic connectivity test to verify services are accessible
"""
import asyncio
import httpx

async def test_connectivity():
    """Test basic connectivity to services."""
    print("Testing service connectivity...")
    
    # Test backend service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            print(f"Backend (8000): {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Backend (8000): ERROR - {e}")
    
    # Test auth service  
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/auth/health", timeout=5.0)
            print(f"Auth (8001): {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Auth (8001): ERROR - {e}")

if __name__ == "__main__":
    asyncio.run(test_connectivity())