#!/usr/bin/env python3
"""
Simple Thread and Message Test Script for Netra Platform
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Any

import httpx

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8083"

async def get_auth_token():
    """Get authentication token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Try auth service directly since it worked
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/dev/login",
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
        except Exception:
            pass
        return None

async def test_threads_and_messages():
    """Test thread and message functionality."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests_passed": 0,
        "tests_failed": 0,
        "thread_id": None,
        "messages": [],
        "errors": []
    }
    
    print("Starting Thread and Message Tests")
    
    # Get authentication token
    auth_token = await get_auth_token()
    if not auth_token:
        print("FAIL: Could not get authentication token")
        results["tests_failed"] += 1
        return results
    
    print(f"PASS: Got auth token: {auth_token[:20]}...")
    results["tests_passed"] += 1
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test Thread Creation
        try:
            thread_data = {
                "title": "E2E Test Thread",
                "metadata": {
                    "test_type": "e2e",
                    "created_by": "test_script"
                }
            }
            
            response = await client.post(
                f"{BACKEND_URL}/api/threads/",
                json=thread_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                thread_id = data.get("id")
                
                if thread_id:
                    results["thread_id"] = thread_id
                    print(f"PASS: Thread Creation - Created thread: {thread_id}")
                    results["tests_passed"] += 1
                else:
                    print("FAIL: Thread Creation - No thread ID in response")
                    results["tests_failed"] += 1
            else:
                print(f"FAIL: Thread Creation - Status {response.status_code}: {response.text}")
                results["tests_failed"] += 1
                
        except Exception as e:
            print(f"FAIL: Thread Creation - {str(e)}")
            results["tests_failed"] += 1
        
        # Test Thread Retrieval
        if results.get("thread_id"):
            try:
                response = await client.get(
                    f"{BACKEND_URL}/api/threads/{results['thread_id']}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print("PASS: Thread Retrieval")
                    results["tests_passed"] += 1
                else:
                    print(f"FAIL: Thread Retrieval - Status {response.status_code}")
                    results["tests_failed"] += 1
                    
            except Exception as e:
                print(f"FAIL: Thread Retrieval - {str(e)}")
                results["tests_failed"] += 1
        
        # Test Message Creation (try agent endpoint)
        if results.get("thread_id"):
            try:
                message = "Hello! This is a test message. Can you help me optimize my AI workloads?"
                message_data = {
                    "message": message,
                    "thread_id": results["thread_id"]
                }
                
                response = await client.post(
                    f"{BACKEND_URL}/api/agent/message",
                    json=message_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results["messages"].append({
                        "user_message": message,
                        "response": data,
                        "timestamp": datetime.now().isoformat()
                    })
                    print("PASS: Message Creation")
                    results["tests_passed"] += 1
                else:
                    print(f"FAIL: Message Creation - Status {response.status_code}: {response.text}")
                    results["tests_failed"] += 1
                    
            except Exception as e:
                print(f"FAIL: Message Creation - {str(e)}")
                results["tests_failed"] += 1
        
        # Test Message Retrieval
        if results.get("thread_id"):
            try:
                response = await client.get(
                    f"{BACKEND_URL}/api/threads/{results['thread_id']}/messages",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    messages = data if isinstance(data, list) else data.get("messages", [])
                    print(f"PASS: Message Retrieval - Found {len(messages)} messages")
                    results["tests_passed"] += 1
                else:
                    print(f"FAIL: Message Retrieval - Status {response.status_code}")
                    results["tests_failed"] += 1
                    
            except Exception as e:
                print(f"FAIL: Message Retrieval - {str(e)}")
                results["tests_failed"] += 1
        
        # Test Thread List
        try:
            response = await client.get(
                f"{BACKEND_URL}/api/threads/",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                threads = data if isinstance(data, list) else data.get("threads", [])
                print(f"PASS: Thread List - Found {len(threads)} threads")
                results["tests_passed"] += 1
            else:
                print(f"FAIL: Thread List - Status {response.status_code}")
                results["tests_failed"] += 1
                
        except Exception as e:
            print(f"FAIL: Thread List - {str(e)}")
            results["tests_failed"] += 1
    
    return results

async def main():
    """Main test execution."""
    results = await test_threads_and_messages()
    
    print(f"\nThread and Message Test Results:")
    print(f"   Passed: {results['tests_passed']}")
    print(f"   Failed: {results['tests_failed']}")
    
    if results.get("thread_id"):
        print(f"   Thread ID: {results['thread_id']}")
    
    if results["messages"]:
        print(f"   Messages Processed: {len(results['messages'])}")
    
    # Save results to file
    with open("thread_message_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to thread_message_test_results.json")
    
    # Return success if all tests passed
    success = results["tests_failed"] == 0 and results["tests_passed"] > 0
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)