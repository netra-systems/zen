#!/usr/bin/env python3
"""
Direct API Test for Agent Orchestration Recovery
Tests the actual backend agent endpoints that the Cypress test is trying to verify.
"""

import requests
import time
import json
import sys
from shared.isolated_environment import IsolatedEnvironment

def test_backend_health():
    """Test backend service health"""
    print("Testing backend health...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        print(f"Backend status: {response.status_code}")
        if response.status_code == 200:
            print(f"Backend response: {response.json()}")
            return True
        return False
    except Exception as e:
        print(f"Backend connection failed: {e}")
        return False

def test_auth_health():
    """Test auth service health"""
    print("Testing auth service health...")
    try:
        response = requests.get("http://localhost:8081/health", timeout=10)
        print(f"Auth status: {response.status_code}")
        if response.status_code == 200:
            print(f"Auth response: {response.json()}")
            return True
        return False
    except Exception as e:
        print(f"Auth connection failed: {e}")
        return False

def test_agent_endpoints():
    """Test agent endpoints that the Cypress test expects"""
    print("\nTesting agent endpoints...")
    
    base_url = "http://localhost:8001"
    agent_types = ["triage", "data", "optimization", "reporting", "analysis"]
    
    results = {}
    for agent in agent_types:
        print(f"Testing {agent} agent...")
        
        # Try different endpoint patterns
        endpoints = [
            f"{base_url}/api/agents/{agent}",
            f"{base_url}/api/v1/agents/{agent}",
            f"{base_url}/agents/{agent}"
        ]
        
        agent_results = []
        for endpoint in endpoints:
            try:
                # Test GET request
                response = requests.get(endpoint, timeout=5)
                agent_results.append({
                    "endpoint": endpoint,
                    "method": "GET", 
                    "status": response.status_code,
                    "success": response.status_code < 500
                })
                print(f"  GET {endpoint}: {response.status_code}")
                
                # Test POST request (what the frontend would actually do)
                post_data = {
                    "message": f"Test {agent} request",
                    "user_id": "test-user"
                }
                response = requests.post(endpoint, json=post_data, timeout=5)
                agent_results.append({
                    "endpoint": endpoint,
                    "method": "POST",
                    "status": response.status_code,
                    "success": response.status_code < 500
                })
                print(f"  POST {endpoint}: {response.status_code}")
                
            except requests.exceptions.Timeout:
                agent_results.append({
                    "endpoint": endpoint,
                    "method": "GET/POST",
                    "status": "TIMEOUT",
                    "success": False
                })
                print(f"  {endpoint}: TIMEOUT")
            except requests.exceptions.ConnectionError:
                agent_results.append({
                    "endpoint": endpoint,
                    "method": "GET/POST", 
                    "status": "CONNECTION_ERROR",
                    "success": False
                })
                print(f"  {endpoint}: CONNECTION_ERROR")
            except Exception as e:
                agent_results.append({
                    "endpoint": endpoint,
                    "method": "GET/POST",
                    "status": f"ERROR: {e}",
                    "success": False
                })
                print(f"  {endpoint}: ERROR - {e}")
        
        results[agent] = agent_results
    
    return results

def test_websocket_endpoints():
    """Test WebSocket endpoints for real-time agent communication"""
    print("\nTesting WebSocket endpoints...")
    
    # Test if WebSocket endpoints are available 
    ws_endpoints = [
        "http://localhost:8001/ws",
        "http://localhost:8001/api/ws",
        "http://localhost:8000/ws"  # Check if main backend also has WS
    ]
    
    for endpoint in ws_endpoints:
        try:
            # Test if endpoint exists by making HTTP request (will get upgrade error but proves endpoint exists)
            response = requests.get(endpoint, timeout=3)
            print(f"WebSocket endpoint {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"WebSocket endpoint {endpoint}: ERROR - {e}")

def main():
    """Main test execution"""
    print("Agent Orchestration Recovery Test")
    print("=" * 50)
    
    # Test service health
    backend_ok = test_backend_health()
    auth_ok = test_auth_health()
    
    if not backend_ok:
        print("Backend service not available - cannot test agent orchestration")
        return 1
        
    if not auth_ok:
        print("Auth service not available - authentication may fail")
    
    # Test agent endpoints
    agent_results = test_agent_endpoints()
    
    # Test WebSocket endpoints
    test_websocket_endpoints()
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    total_tests = 0
    successful_tests = 0
    
    for agent, results in agent_results.items():
        print(f"\n{agent.upper()} AGENT:")
        for result in results:
            total_tests += 1
            status = "PASS" if result["success"] else "FAIL"
            if result["success"]:
                successful_tests += 1
            print(f"  {result['method']} {result['endpoint']}: {status} ({result['status']})")
    
    print(f"\nTOTAL: {successful_tests}/{total_tests} tests passed")
    
    if successful_tests == 0:
        print("No agent endpoints are working - this indicates a fundamental issue")
        return 1
    elif successful_tests < total_tests // 2:
        print("Many agent endpoints failing - partial functionality")
        return 1
    else:
        print("Agent endpoints are mostly functional")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)