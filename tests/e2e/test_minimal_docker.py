#!/usr/bin/env python
"""Minimal test to debug Docker crash issue"""

import requests
import time

def test_docker_health():
    """Test if Docker backend is accessible"""
    print("Testing Docker backend health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Backend status: {response.status_code}")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Failed to reach backend: {e}")
        return False

if __name__ == "__main__":
    # Simple test - no pytest, no async, no imports
    print("Starting minimal Docker test...")
    
    # Test 5 times with delays
    for i in range(5):
        print(f"\nAttempt {i+1}/5")
        if test_docker_health():
            print("SUCCESS - Backend is healthy")
        else:
            print("FAILED - Backend not reachable")
        
        if i < 4:
            print("Waiting 2 seconds...")
            time.sleep(2)
    
    print("\nTest complete - check if Docker is still running")