"""
Load Test Validation - Quick connectivity test before full load test.
"""

import asyncio
import aiohttp

async def test_basic_connectivity():
    """Test basic HTTP connectivity to the system."""
    base_url = "http://localhost:54421"
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # Test health endpoint
            async with session.get(f"{base_url}/health") as response:
                print(f"Health endpoint: {response.status}")
                if response.status == 200:
                    data = await response.text()
                    print(f"Health response: {data[:100]}...")
                
            # Test API root
            async with session.get(f"{base_url}/") as response:
                print(f"Root endpoint: {response.status}")
                
            # Test demo endpoint
            async with session.get(f"{base_url}/demo") as response:
                print(f"Demo endpoint: {response.status}")
                
    except Exception as e:
        print(f"Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_basic_connectivity())
    if result:
        print("[PASS] Basic connectivity test passed")
    else:
        print("[FAIL] Basic connectivity test failed")