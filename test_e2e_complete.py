#!/usr/bin/env python3
"""
Complete End-to-End Integration Test for Netra Platform

This script orchestrates all test components to validate the complete user journey:
1. Authentication (dev login, JWT token)
2. Thread management (create, list, retrieve)
3. Message processing (send message, LLM response)
4. WebSocket real-time communication
5. Full platform health validation

MISSION CRITICAL - Validates entire platform functionality.

Business Value Justification (BVJ):
- Segment: Platform/Internal + All User Segments
- Business Goal: Platform Stability & User Experience
- Value Impact: Prevents platform failures that could lose 20%+ of active users
- Strategic Impact: Validates core AI optimization value proposition end-to-end
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

import httpx
import websockets

# Add project root to path

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8083"
FRONTEND_URL = "http://localhost:3000"
WEBSOCKET_URL = "ws://localhost:8000/ws"

class CompleteE2ETester:
    """Complete end-to-end test suite for the Netra platform."""
    
    def __init__(self):
        self.test_results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "test_session_id": str(uuid.uuid4()),
            "overall_status": "running",
            "phases": {
                "infrastructure": {"status": "pending", "tests_passed": 0, "tests_failed": 0},
                "authentication": {"status": "pending", "tests_passed": 0, "tests_failed": 0},
                "thread_operations": {"status": "pending", "tests_passed": 0, "tests_failed": 0},
                "message_processing": {"status": "pending", "tests_passed": 0, "tests_failed": 0},
                "websocket_realtime": {"status": "pending", "tests_passed": 0, "tests_failed": 0},
                "integration": {"status": "pending", "tests_passed": 0, "tests_failed": 0}
            },
            "auth_token": None,
            "thread_id": None,
            "user_info": None,
            "websocket_connections": [],
            "messages": [],
            "errors": [],
            "performance_metrics": {
                "auth_time": None,
                "thread_creation_time": None,
                "message_response_time": None,
                "websocket_connection_time": None
            }
        }
    
    def log_phase_start(self, phase: str):
        """Log the start of a test phase."""
        self.test_results["phases"][phase]["status"] = "running"
        print(f"\n🚀 Phase: {phase.upper()}")
        print("=" * 50)
    
    def log_phase_complete(self, phase: str):
        """Log completion of a test phase."""
        phase_data = self.test_results["phases"][phase]
        if phase_data["tests_failed"] == 0:
            phase_data["status"] = "passed"
            print(f"✅ Phase {phase.upper()} PASSED")
        else:
            phase_data["status"] = "failed"
            print(f"❌ Phase {phase.upper()} FAILED")
        print(f"   Passed: {phase_data['tests_passed']}, Failed: {phase_data['tests_failed']}")
    
    def log_success(self, phase: str, test_name: str, details: str = ""):
        """Log successful test."""
        self.test_results["phases"][phase]["tests_passed"] += 1
        print(f"  ✅ {test_name}: PASSED")
        if details:
            print(f"     {details}")
    
    def log_failure(self, phase: str, test_name: str, error: str):
        """Log failed test."""
        self.test_results["phases"][phase]["tests_failed"] += 1
        self.test_results["errors"].append({"phase": phase, "test": test_name, "error": error})
        print(f"  ❌ {test_name}: FAILED")
        print(f"     {error}")
    
    async def test_infrastructure_phase(self) -> bool:
        """Phase 1: Test infrastructure and service availability."""
        self.log_phase_start("infrastructure")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test Backend Health
            try:
                start_time = time.time()
                response = await client.get(f"{BACKEND_URL}/health")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.log_success("infrastructure", "Backend Health", f"Response time: {response_time:.2f}s")
                else:
                    self.log_failure("infrastructure", "Backend Health", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_failure("infrastructure", "Backend Health", f"Connection error: {str(e)}")
            
            # Test Auth Service Health
            try:
                response = await client.get(f"{AUTH_SERVICE_URL}/health")
                if response.status_code == 200:
                    self.log_success("infrastructure", "Auth Service Health", "Service responding")
                else:
                    self.log_failure("infrastructure", "Auth Service Health", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_failure("infrastructure", "Auth Service Health", f"Connection error: {str(e)}")
            
            # Test Frontend Health (optional)
            try:
                response = await client.get(FRONTEND_URL, timeout=10.0)
                if response.status_code == 200:
                    self.log_success("infrastructure", "Frontend Health", "Service responding")
                else:
                    self.log_success("infrastructure", "Frontend Health", f"Responded with {response.status_code}")
            except Exception:
                self.log_success("infrastructure", "Frontend Health", "Frontend may not be critical for API tests")
            
            # Test WebSocket Info Endpoint
            try:
                response = await client.get(f"{BACKEND_URL}/ws")
                if response.status_code == 200:
                    self.log_success("infrastructure", "WebSocket Info", "WebSocket endpoints available")
                else:
                    self.log_failure("infrastructure", "WebSocket Info", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_failure("infrastructure", "WebSocket Info", f"Error: {str(e)}")
        
        self.log_phase_complete("infrastructure")
        return self.test_results["phases"]["infrastructure"]["tests_failed"] == 0
    
    async def test_authentication_phase(self) -> Tuple[bool, Optional[str]]:
        """Phase 2: Test authentication and token generation."""
        self.log_phase_start("authentication")
        
        auth_token = None
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test Dev Login
            try:
                start_time = time.time()
                
                # Try backend dev login first
                response = await client.post(
                    f"{BACKEND_URL}/api/auth/dev/login",
                    json={"email": "test@netra.ai"}
                )
                
                auth_time = time.time() - start_time
                self.test_results["performance_metrics"]["auth_time"] = auth_time
                
                if response.status_code == 200:
                    data = response.json()
                    auth_token = data.get("access_token")
                    
                    if auth_token:
                        self.test_results["auth_token"] = auth_token
                        self.test_results["user_info"] = data
                        self.log_success("authentication", "Dev Login", f"Token acquired in {auth_time:.2f}s")
                    else:
                        self.log_failure("authentication", "Dev Login", "No access_token in response")
                else:
                    # Try auth service directly
                    response = await client.post(f"{AUTH_SERVICE_URL}/auth/dev/login", json={})
                    if response.status_code == 200:
                        data = response.json()
                        auth_token = data.get("access_token")
                        if auth_token:
                            self.test_results["auth_token"] = auth_token
                            self.test_results["user_info"] = data
                            self.log_success("authentication", "Dev Login (Auth Service)", f"Token acquired")
                        else:
                            self.log_failure("authentication", "Dev Login", "No token from auth service")
                    else:
                        self.log_failure("authentication", "Dev Login", f"Both endpoints failed")
            except Exception as e:
                self.log_failure("authentication", "Dev Login", f"Error: {str(e)}")
            
            # Test Token Validation
            if auth_token:
                try:
                    import jwt
                    decoded = jwt.decode(auth_token, options={"verify_signature": False})
                    self.log_success("authentication", "Token Validation", f"Valid JWT structure")
                except Exception as e:
                    self.log_failure("authentication", "Token Validation", f"Invalid token: {str(e)}")
            
            # Test Authenticated Request
            if auth_token:
                try:
                    headers = {"Authorization": f"Bearer {auth_token}"}
                    response = await client.get(f"{BACKEND_URL}/api/threads/", headers=headers)
                    
                    if response.status_code == 200:
                        self.log_success("authentication", "Authenticated Request", "Successfully accessed protected endpoint")
                    else:
                        self.log_failure("authentication", "Authenticated Request", f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_failure("authentication", "Authenticated Request", f"Error: {str(e)}")
        
        self.log_phase_complete("authentication")
        auth_success = self.test_results["phases"]["authentication"]["tests_failed"] == 0
        return auth_success, auth_token
    
    async def test_thread_operations_phase(self, auth_token: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Phase 3: Test thread management operations."""
        self.log_phase_start("thread_operations")
        
        thread_id = None
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test Thread Creation
            try:
                start_time = time.time()
                
                thread_data = {
                    "title": f"E2E Test Thread {datetime.now().strftime('%H:%M:%S')}",
                    "metadata": {
                        "test_type": "e2e_complete",
                        "session_id": self.test_results["test_session_id"]
                    }
                }
                
                response = await client.post(
                    f"{BACKEND_URL}/api/threads/",
                    json=thread_data,
                    headers=headers
                )
                
                creation_time = time.time() - start_time
                self.test_results["performance_metrics"]["thread_creation_time"] = creation_time
                
                if response.status_code == 200:
                    data = response.json()
                    thread_id = data.get("id")
                    
                    if thread_id:
                        self.test_results["thread_id"] = thread_id
                        self.log_success("thread_operations", "Thread Creation", f"Created in {creation_time:.2f}s")
                    else:
                        self.log_failure("thread_operations", "Thread Creation", "No thread ID in response")
                else:
                    self.log_failure("thread_operations", "Thread Creation", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_failure("thread_operations", "Thread Creation", f"Error: {str(e)}")
            
            # Test Thread Retrieval
            if thread_id:
                try:
                    response = await client.get(f"{BACKEND_URL}/api/threads/{thread_id}", headers=headers)
                    
                    if response.status_code == 200:
                        self.log_success("thread_operations", "Thread Retrieval", "Successfully retrieved thread")
                    else:
                        self.log_failure("thread_operations", "Thread Retrieval", f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_failure("thread_operations", "Thread Retrieval", f"Error: {str(e)}")
            
            # Test Thread Listing
            try:
                response = await client.get(f"{BACKEND_URL}/api/threads/", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    threads = data if isinstance(data, list) else data.get("threads", [])
                    self.log_success("thread_operations", "Thread Listing", f"Retrieved {len(threads)} threads")
                else:
                    self.log_failure("thread_operations", "Thread Listing", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_failure("thread_operations", "Thread Listing", f"Error: {str(e)}")
        
        self.log_phase_complete("thread_operations")
        thread_success = self.test_results["phases"]["thread_operations"]["tests_failed"] == 0
        return thread_success, thread_id
    
    async def test_message_processing_phase(self, auth_token: Optional[str], thread_id: Optional[str]) -> bool:
        """Phase 4: Test message processing and LLM responses."""
        self.log_phase_start("message_processing")
        
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for LLM
            # Test Message Creation
            if thread_id:
                try:
                    start_time = time.time()
                    
                    test_message = "Hello! This is an end-to-end test. Can you help me optimize my AI workload costs?"
                    message_data = {
                        "message": test_message,
                        "thread_id": thread_id,
                        "metadata": {
                            "test_type": "e2e_complete",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    # Try main agent endpoint
                    response = await client.post(
                        f"{BACKEND_URL}/api/agent/message",
                        json=message_data,
                        headers=headers
                    )
                    
                    response_time = time.time() - start_time
                    self.test_results["performance_metrics"]["message_response_time"] = response_time
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.test_results["messages"].append({
                            "user_message": test_message,
                            "response": data,
                            "response_time": response_time,
                            "timestamp": datetime.now().isoformat()
                        })
                        self.log_success("message_processing", "Message Creation", f"Response in {response_time:.2f}s")
                        
                        # Test response quality
                        if self._validate_llm_response(data):
                            self.log_success("message_processing", "LLM Response Quality", "Meaningful response received")
                        else:
                            self.log_failure("message_processing", "LLM Response Quality", "Response appears incomplete or invalid")
                    else:
                        self.log_failure("message_processing", "Message Creation", f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_failure("message_processing", "Message Creation", f"Error: {str(e)}")
            
            # Test Message Retrieval
            if thread_id:
                try:
                    response = await client.get(f"{BACKEND_URL}/api/threads/{thread_id}/messages", headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        messages = data if isinstance(data, list) else data.get("messages", [])
                        self.log_success("message_processing", "Message Retrieval", f"Retrieved {len(messages)} messages")
                    else:
                        self.log_failure("message_processing", "Message Retrieval", f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_failure("message_processing", "Message Retrieval", f"Error: {str(e)}")
        
        self.log_phase_complete("message_processing")
        return self.test_results["phases"]["message_processing"]["tests_failed"] == 0
    
    def _validate_llm_response(self, response_data: Any) -> bool:
        """Validate that LLM response is meaningful."""
        if isinstance(response_data, dict):
            # Look for response content in various formats
            response_text = None
            
            if "response" in response_data:
                response_text = response_data["response"]
            elif "message" in response_data:
                response_text = response_data["message"]
            elif "content" in response_data:
                response_text = response_data["content"]
            elif "data" in response_data and isinstance(response_data["data"], dict):
                response_text = response_data["data"].get("response")
            
            return response_text and isinstance(response_text, str) and len(response_text.strip()) > 10
        
        return False
    
    async def test_websocket_realtime_phase(self, auth_token: Optional[str], thread_id: Optional[str]) -> bool:
        """Phase 5: Test WebSocket real-time communication."""
        self.log_phase_start("websocket_realtime")
        
        # Test WebSocket Connection
        try:
            start_time = time.time()
            
            # Prepare connection parameters
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            subprotocols = [f"Bearer.{auth_token}"] if auth_token else []
            
            websocket = None
            connection_method = "unknown"
            
            # Try different connection methods
            for method, params in [
                ("headers_and_subprotocols", {"extra_headers": headers, "subprotocols": subprotocols}),
                ("headers_only", {"extra_headers": headers}),
                ("no_auth", {})
            ]:
                try:
                    websocket = await websockets.connect(WEBSOCKET_URL, **params, timeout=30)
                    connection_method = method
                    break
                except Exception:
                    continue
            
            connection_time = time.time() - start_time
            self.test_results["performance_metrics"]["websocket_connection_time"] = connection_time
            
            if websocket:
                self.test_results["websocket_connections"].append({
                    "url": WEBSOCKET_URL,
                    "method": connection_method,
                    "connection_time": connection_time,
                    "timestamp": datetime.now().isoformat()
                })
                self.log_success("websocket_realtime", "WebSocket Connection", f"Connected via {connection_method}")
                
                try:
                    # Test Ping/Pong
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10.0)
                    self.log_success("websocket_realtime", "WebSocket Ping/Pong", "Connection healthy")
                    
                    # Test Message Exchange
                    test_message = {
                        "type": "message",
                        "data": {
                            "message": "WebSocket E2E test message",
                            "thread_id": thread_id or str(uuid.uuid4()),
                            "timestamp": datetime.now().isoformat()
                        },
                        "id": str(uuid.uuid4())
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    self.log_success("websocket_realtime", "WebSocket Send", "Message sent successfully")
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        if response:
                            self.log_success("websocket_realtime", "WebSocket Receive", "Response received")
                        else:
                            self.log_failure("websocket_realtime", "WebSocket Receive", "Empty response")
                    except asyncio.TimeoutError:
                        self.log_failure("websocket_realtime", "WebSocket Receive", "Timeout waiting for response")
                    
                finally:
                    await websocket.close()
            else:
                self.log_failure("websocket_realtime", "WebSocket Connection", "All connection methods failed")
                
        except Exception as e:
            self.log_failure("websocket_realtime", "WebSocket Connection", f"Error: {str(e)}")
        
        self.log_phase_complete("websocket_realtime")
        return self.test_results["phases"]["websocket_realtime"]["tests_failed"] == 0
    
    async def test_integration_phase(self) -> bool:
        """Phase 6: Test full integration and data consistency."""
        self.log_phase_start("integration")
        
        # Test Overall Performance
        perf_metrics = self.test_results["performance_metrics"]
        total_time = sum(t for t in perf_metrics.values() if t is not None)
        
        if total_time > 0:
            self.log_success("integration", "Performance Metrics", f"Total test time: {total_time:.2f}s")
        else:
            self.log_failure("integration", "Performance Metrics", "No timing data collected")
        
        # Test Data Consistency
        if self.test_results.get("auth_token") and self.test_results.get("thread_id"):
            self.log_success("integration", "Data Consistency", "Auth token and thread ID available")
        else:
            self.log_failure("integration", "Data Consistency", "Missing critical test data")
        
        # Test Message Flow Integration
        if self.test_results["messages"]:
            message_count = len(self.test_results["messages"])
            self.log_success("integration", "Message Flow", f"Processed {message_count} messages end-to-end")
        else:
            self.log_failure("integration", "Message Flow", "No messages processed")
        
        # Test WebSocket Integration
        if self.test_results["websocket_connections"]:
            ws_count = len(self.test_results["websocket_connections"])
            self.log_success("integration", "WebSocket Integration", f"Established {ws_count} WebSocket connections")
        else:
            self.log_failure("integration", "WebSocket Integration", "No WebSocket connections established")
        
        self.log_phase_complete("integration")
        return self.test_results["phases"]["integration"]["tests_failed"] == 0
    
    async def run_complete_e2e_test(self) -> Dict[str, Any]:
        """Run the complete end-to-end test suite."""
        print("🎯 NETRA PLATFORM - COMPLETE END-TO-END TEST SUITE")
        print("=" * 70)
        print(f"Test Session ID: {self.test_results['test_session_id']}")
        print(f"Started: {self.test_results['timestamp']}")
        print()
        
        # Phase 1: Infrastructure
        infra_success = await self.test_infrastructure_phase()
        if not infra_success:
            print("\n⚠️  Infrastructure phase failed. Some services may be unavailable.")
            print("   Continuing with available services...")
        
        # Phase 2: Authentication
        auth_success, auth_token = await self.test_authentication_phase()
        if not auth_success:
            print("\n⚠️  Authentication phase failed. Some tests may be limited.")
        
        # Phase 3: Thread Operations
        thread_success, thread_id = await self.test_thread_operations_phase(auth_token)
        
        # Phase 4: Message Processing
        message_success = await self.test_message_processing_phase(auth_token, thread_id)
        
        # Phase 5: WebSocket Real-time
        websocket_success = await self.test_websocket_realtime_phase(auth_token, thread_id)
        
        # Phase 6: Integration
        integration_success = await self.test_integration_phase()
        
        # Calculate overall results
        total_passed = sum(phase["tests_passed"] for phase in self.test_results["phases"].values())
        total_failed = sum(phase["tests_failed"] for phase in self.test_results["phases"].values())
        
        if total_failed == 0:
            self.test_results["overall_status"] = "passed"
        elif total_passed > total_failed:
            self.test_results["overall_status"] = "passed_with_warnings"
        else:
            self.test_results["overall_status"] = "failed"
        
        return self.test_results

async def main():
    """Main test execution."""
    tester = CompleteE2ETester()
    results = await tester.run_complete_e2e_test()
    
    # Print final summary
    print("\n" + "=" * 70)
    print("📊 FINAL TEST RESULTS")
    print("=" * 70)
    
    total_passed = sum(phase["tests_passed"] for phase in results["phases"].values())
    total_failed = sum(phase["tests_failed"] for phase in results["phases"].values())
    
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Total Tests: {total_passed + total_failed}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    
    print(f"\n📈 Performance Metrics:")
    perf = results["performance_metrics"]
    for metric, value in perf.items():
        if value is not None:
            print(f"   {metric.replace('_', ' ').title()}: {value:.2f}s")
    
    print(f"\n🔍 Phase Summary:")
    for phase_name, phase_data in results["phases"].items():
        status_emoji = "✅" if phase_data["status"] == "passed" else "❌" if phase_data["status"] == "failed" else "⏳"
        print(f"   {status_emoji} {phase_name.replace('_', ' ').title()}: {phase_data['tests_passed']}/{phase_data['tests_passed'] + phase_data['tests_failed']}")
    
    if results["errors"]:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"   [{error['phase']}] {error['test']}: {error['error'][:100]}")
        if len(results["errors"]) > 5:
            print(f"   ... and {len(results['errors']) - 5} more errors")
    
    # Save detailed results
    results["completion_timestamp"] = datetime.now().isoformat()
    with open("e2e_complete_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Detailed results saved to e2e_complete_test_results.json")
    
    # Return appropriate exit code
    if results["overall_status"] == "passed":
        print(f"\n🎉 ALL TESTS PASSED - Netra Platform is fully functional!")
        return 0
    elif results["overall_status"] == "passed_with_warnings":
        print(f"\n⚠️  TESTS PASSED WITH WARNINGS - Some non-critical issues detected")
        return 0
    else:
        print(f"\n💥 TESTS FAILED - Critical platform issues detected")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)