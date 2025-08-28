#!/usr/bin/env python3
"""Test CORS issue with 127.0.0.1 vs localhost."""

import httpx
import asyncio

async def test_cors():
    """Test CORS with different origins."""
    
    # Test with 127.0.0.1 origin (the problematic one)
    print("Testing with 127.0.0.1:3000 origin...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8000/api/threads?limit=20&offset=0",
                headers={
                    "Origin": "http://127.0.0.1:3000",
                    "Referer": "http://127.0.0.1:3000/",
                }
            )
            print(f"Status: {response.status_code}")
            print(f"CORS Headers:")
            for header in response.headers:
                if "access-control" in header.lower() or header.lower() == "vary":
                    print(f"  {header}: {response.headers[header]}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test with localhost origin (should work)
    print("Testing with localhost:3000 origin...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8000/api/threads?limit=20&offset=0",
                headers={
                    "Origin": "http://localhost:3000",
                    "Referer": "http://localhost:3000/",
                }
            )
            print(f"Status: {response.status_code}")
            print(f"CORS Headers:")
            for header in response.headers:
                if "access-control" in header.lower() or header.lower() == "vary":
                    print(f"  {header}: {response.headers[header]}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test OPTIONS preflight request
    print("Testing OPTIONS preflight with 127.0.0.1:3000...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.options(
                "http://localhost:8000/api/threads",
                headers={
                    "Origin": "http://127.0.0.1:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization,content-type",
                }
            )
            print(f"Status: {response.status_code}")
            print(f"CORS Headers:")
            for header in response.headers:
                if "access-control" in header.lower() or header.lower() == "vary":
                    print(f"  {header}: {response.headers[header]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("Starting CORS test...\n")
    asyncio.run(test_cors())