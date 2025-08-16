"""Simple test for factory status endpoint without git operations."""

import requests
import json
from datetime import datetime

def test_factory_status():
    """Test the factory status endpoint."""
    print(f"\n{'='*60}")
    print("Testing Factory Status Endpoint")
    print(f"{'='*60}\n")
    
    # Test without auth first
    url = "http://localhost:55015/api/factory-status/test"
    print(f"Testing: GET {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Data:")
            print(json.dumps(data, indent=2))
            print("\n✅ Factory Status test endpoint is working!")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 5 seconds")
        print("The endpoint might be blocked by git operations")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    test_factory_status()
