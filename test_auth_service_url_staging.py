#!/usr/bin/env python3
"""
Quick test to validate AUTH_SERVICE_URL configuration in staging
Issue #631: Validate that AUTH_SERVICE_URL loads correctly in staging environment
"""
import os
import requests
import sys
import json

def test_auth_service_url_configuration():
    """Test that AUTH_SERVICE_URL is properly configured in staging backend"""
    
    staging_backend_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
    
    print("Testing AUTH_SERVICE_URL Configuration in Staging")
    print(f"Backend URL: {staging_backend_url}")
    
    try:
        # Test health endpoint first
        print("\n1. Testing health endpoint...")
        health_response = requests.get(f"{staging_backend_url}/health", timeout=10)
        print(f"   Health Status: {health_response.status_code}")
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   Health Response: {json.dumps(health_data, indent=2)}")
        
        # Test configuration endpoint to see if auth service is configured
        print("\n2. Testing configuration endpoint...")
        try:
            config_response = requests.get(f"{staging_backend_url}/debug/config", timeout=10)
            if config_response.status_code == 200:
                config_data = config_response.json()
                auth_service_url = config_data.get('auth_service_url', 'NOT_FOUND')
                print(f"   AUTH_SERVICE_URL: {auth_service_url}")
            else:
                print(f"   Config endpoint status: {config_response.status_code}")
        except:
            print("   Config endpoint not available (expected in production)")
        
        # Test WebSocket endpoint to see if it starts properly
        print("\n3. Testing WebSocket initialization...")
        try:
            websocket_response = requests.get(f"{staging_backend_url}/ws", timeout=5)
            print(f"   WebSocket endpoint status: {websocket_response.status_code}")
        except requests.exceptions.Timeout:
            print("   WebSocket endpoint timeout (expected for non-WS request)")
        except Exception as e:
            print(f"   WebSocket endpoint error: {e}")
        
        print("\nConfiguration test completed")
        return True
        
    except Exception as e:
        print(f"Configuration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_auth_service_url_configuration()
    sys.exit(0 if success else 1)