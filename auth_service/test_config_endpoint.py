#!/usr/bin/env python
"""
Test script to verify the /auth/config endpoint exists and works correctly
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

def test_config_endpoint():
    """Test that the /auth/config endpoint exists and returns expected structure"""
    client = TestClient(app)
    
    # Test the config endpoint
    response = client.get("/auth/config")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Verify response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    
    # Check required fields
    assert "google_client_id" in data, "Missing google_client_id"
    assert "endpoints" in data, "Missing endpoints"
    assert "development_mode" in data, "Missing development_mode"
    assert "authorized_javascript_origins" in data, "Missing authorized_javascript_origins"
    assert "authorized_redirect_uris" in data, "Missing authorized_redirect_uris"
    
    # Check endpoints structure
    endpoints = data["endpoints"]
    required_endpoints = ["login", "logout", "callback", "token", "user"]
    for endpoint in required_endpoints:
        assert endpoint in endpoints, f"Missing endpoint: {endpoint}"
    
    print("\n✅ All tests passed! The /auth/config endpoint is working correctly.")
    return True

if __name__ == "__main__":
    try:
        test_config_endpoint()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)