#!/usr/bin/env python3
"""
Thread and Message Test Script for Netra Platform

This script tests thread creation, message sending, and LLM agent responses.
MISSION CRITICAL - Part of comprehensive E2E test suite.

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Core Platform Functionality
- Value Impact: Tests the primary user interaction flow (chat)
- Strategic Impact: Validates AI optimization engine works end-to-end
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

import httpx

# Add project root to path

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"

class ThreadMessageTester:
    """Test thread and message operations for the Netra platform."""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.session: Optional[httpx.AsyncClient] = None
        self.auth_token = auth_token
        self.test_results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "thread_id": None,
            "messages": [],
            "errors": []
        }
    
    async def __aenter__(self):
        """Setup test environment."""
        self.session = httpx.AsyncClient(timeout=60.0)  # Longer timeout for LLM responses
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    def log_success(self, test_name: str, details: str = ""):
        """Log successful test."""
        self.test_results["tests_passed"] += 1
        print(f"✅ {test_name}: PASSED")
        if details:
            print(f"   Details: {details}")
    
    def log_failure(self, test_name: str, error: str):
        """Log failed test."""
        self.test_results["tests_failed"] += 1
        self.test_results["errors"].append({"test": test_name, "error": error})
        print(f"❌ {test_name}: FAILED")
        print(f"   Error: {error}")
    
    async def test_thread_creation(self) -> Optional[str]:
        """Test creating a new thread."""
        try:
            thread_data = {
                "title": "E2E Test Thread",
                "metadata": {
                    "test_type": "e2e",
                    "created_by": "test_script",
                    "test_id": str(uuid.uuid4())
                }
            }
            
            response = await self.session.post(
                f"{BACKEND_URL}/api/threads/",
                json=thread_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                thread_id = data.get("id")
                
                if thread_id:
                    self.test_results["thread_id"] = thread_id
                    self.log_success("Thread Creation", f"Created thread: {thread_id}")
                    return thread_id
                else:
                    self.log_failure("Thread Creation", "No thread ID in response")
                    return None
            else:
                self.log_failure("Thread Creation", f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_failure("Thread Creation", f"Request error: {str(e)}")
            return None
    
    async def test_thread_retrieval(self, thread_id: str) -> bool:
        """Test retrieving the created thread."""
        try:
            response = await self.session.get(
                f"{BACKEND_URL}/api/threads/{thread_id}",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == thread_id:
                    self.log_success("Thread Retrieval", f"Retrieved thread: {thread_id}")
                    return True
                else:
                    self.log_failure("Thread Retrieval", "Thread ID mismatch")
                    return False
            else:
                self.log_failure("Thread Retrieval", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_failure("Thread Retrieval", f"Request error: {str(e)}")
            return False
    
    async def test_message_creation(self, thread_id: str, message: str) -> Optional[Dict]:
        """Test sending a message to the thread."""
        try:
            # First, try the agent route (main message endpoint)
            message_data = {
                "message": message,
                "thread_id": thread_id,
                "metadata": {
                    "test_message": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            response = await self.session.post(
                f"{BACKEND_URL}/api/agent/message",
                json=message_data,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_results["messages"].append({
                    "user_message": message,
                    "response": data,
                    "timestamp": datetime.now().isoformat()
                })
                self.log_success("Message Creation", f"Sent message to thread {thread_id}")
                return data
            else:
                # Try alternative endpoint pattern
                response = await self.session.post(
                    f"{BACKEND_URL}/api/threads/{thread_id}/messages",
                    json={"content": message, "role": "user"},
                    headers=self.get_auth_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.test_results["messages"].append({
                        "user_message": message,
                        "response": data,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.log_success("Message Creation (Alt Endpoint)", f"Sent message to thread {thread_id}")
                    return data
                else:
                    self.log_failure("Message Creation", f"Both endpoints failed. Last: HTTP {response.status_code}: {response.text}")
                    return None
                
        except Exception as e:
            self.log_failure("Message Creation", f"Request error: {str(e)}")
            return None
    
    async def test_message_retrieval(self, thread_id: str) -> List[Dict]:
        """Test retrieving messages from the thread."""
        try:
            response = await self.session.get(
                f"{BACKEND_URL}/api/threads/{thread_id}/messages",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data if isinstance(data, list) else data.get("messages", [])
                self.log_success("Message Retrieval", f"Retrieved {len(messages)} messages")
                return messages
            else:
                self.log_failure("Message Retrieval", f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_failure("Message Retrieval", f"Request error: {str(e)}")
            return []
    
    async def test_llm_response_quality(self, response_data: Dict) -> bool:
        """Test that LLM response is meaningful and properly formatted."""
        try:
            # Check for common response patterns
            if isinstance(response_data, dict):
                # Look for response content in various possible formats
                response_text = None
                
                # Check common response patterns
                if "response" in response_data:
                    response_text = response_data["response"]
                elif "message" in response_data:
                    response_text = response_data["message"]
                elif "content" in response_data:
                    response_text = response_data["content"]
                elif "data" in response_data and isinstance(response_data["data"], dict):
                    response_text = response_data["data"].get("response")
                
                if response_text and isinstance(response_text, str) and len(response_text.strip()) > 10:
                    self.log_success("LLM Response Quality", f"Response length: {len(response_text)} chars")
                    return True
                else:
                    self.log_failure("LLM Response Quality", f"No meaningful response text found. Data: {str(response_data)[:200]}")
                    return False
            else:
                self.log_failure("LLM Response Quality", "Response is not a dictionary")
                return False
                
        except Exception as e:
            self.log_failure("LLM Response Quality", f"Validation error: {str(e)}")
            return False
    
    async def test_thread_list(self) -> bool:
        """Test listing user's threads."""
        try:
            response = await self.session.get(
                f"{BACKEND_URL}/api/threads/",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                threads = data if isinstance(data, list) else data.get("threads", [])
                self.log_success("Thread List", f"Retrieved {len(threads)} threads")
                return True
            else:
                self.log_failure("Thread List", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_failure("Thread List", f"Request error: {str(e)}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all thread and message tests."""
        print("🧵 Starting Thread & Message Tests for Netra Platform\n")
        
        # Test thread operations
        thread_id = await self.test_thread_creation()
        if thread_id:
            await self.test_thread_retrieval(thread_id)
            
            # Test message operations
            test_message = "Hello! This is a test message from the E2E test suite. Can you help me optimize my AI workload?"
            response_data = await self.test_message_creation(thread_id, test_message)
            
            if response_data:
                await self.test_llm_response_quality(response_data)
            
            # Wait a moment for message processing
            await asyncio.sleep(2)
            
            # Retrieve messages to verify they were saved
            messages = await self.test_message_retrieval(thread_id)
            
            # Test thread listing
            await self.test_thread_list()
        
        return self.test_results

async def get_auth_token() -> Optional[str]:
    """Get authentication token using the auth test script logic."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try backend dev login first
            response = await client.post(
                f"{BACKEND_URL}/api/auth/dev/login",
                json={"email": "test@netra.ai"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            
            # If that fails, try auth service directly
            response = await client.post(
                "http://localhost:8083/auth/dev/login",
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            
            return None
    except:
        return None

async def main():
    """Main test execution."""
    print("🔑 Getting authentication token...")
    auth_token = await get_auth_token()
    
    if not auth_token:
        print("❌ Failed to get authentication token. Running tests without auth...")
        print("   This may cause authentication-related failures.")
    else:
        print(f"✅ Got authentication token: {auth_token[:20]}...")
    
    async with ThreadMessageTester(auth_token) as tester:
        results = await tester.run_all_tests()
        
        print(f"\n📊 Thread & Message Test Results:")
        print(f"   ✅ Tests Passed: {results['tests_passed']}")
        print(f"   ❌ Tests Failed: {results['tests_failed']}")
        
        if results.get("thread_id"):
            print(f"   🧵 Thread ID: {results['thread_id']}")
        
        if results["messages"]:
            print(f"   💬 Messages Processed: {len(results['messages'])}")
        
        if results["errors"]:
            print(f"\n❌ Errors:")
            for error in results["errors"]:
                print(f"   - {error['test']}: {error['error']}")
        
        # Save results to file
        with open("thread_message_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📝 Results saved to thread_message_test_results.json")
        
        # Return success if all tests passed
        success = results["tests_failed"] == 0 and results["tests_passed"] > 0
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)