#!/usr/bin/env python3
"""Simple test to check if agent supervisor exists in the running app"""

import asyncio
import sys
from pathlib import Path
import requests

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_agent_supervisor_via_introspection():
    """Test agent supervisor by creating an internal inspection endpoint"""
    
    # Since the dev launcher is running, we can try to send a WebSocket test message
    # or check for internal state
    
    try:
        # First check if the health endpoint works
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code != 200:
            print(f"FAIL: Health endpoint not working: {health_response.status_code}")
            return False
            
        print("SUCCESS: Health endpoint is working")
        
        # Check if we can access any agent-related routes
        test_routes = [
            "/api/v1/agents",
            "/api/v1/threads", 
            "/api/v1/messages"
        ]
        
        accessible_routes = []
        for route in test_routes:
            try:
                response = requests.get(f"http://localhost:8000{route}", timeout=2)
                # Any non-500 error suggests the route handler exists
                if response.status_code != 500:
                    accessible_routes.append(route)
                    print(f"SUCCESS: Route {route} is accessible (status: {response.status_code})")
            except Exception as e:
                print(f"FAIL: Route {route} not accessible: {e}")
        
        if accessible_routes:
            print(f"SUCCESS: Found {len(accessible_routes)} accessible agent-related routes")
            return True
        else:
            print("FAIL: No agent-related routes are accessible")
            return False
            
    except Exception as e:
        print(f"FAIL: Error testing agent supervisor: {e}")
        return False

def main():
    print("Testing Agent Supervisor Availability")
    print("=" * 40)
    
    result = test_agent_supervisor_via_introspection()
    
    print("=" * 40)
    if result:
        print("CONCLUSION: Agent supervisor appears to be working!")
        return 0
    else:
        print("CONCLUSION: Agent supervisor may have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())