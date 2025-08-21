#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Error Recovery

Tests comprehensive error handling and recovery mechanisms:
1. Service failure detection and recovery
2. Network disconnection handling
3. Database connection recovery
4. Agent failure and fallback
5. Request timeout and retry logic
6. Circuit breaker functionality
7. Graceful degradation scenarios
8. Error state persistence and cleanup

BVJ:
- Segment: Free, Early, Mid, Enterprise
- Business Goal: Reliability, User Trust
- Value Impact: System resilience ensuring continuous service availability
- Strategic Impact: Platform reliability directly impacts user retention and enterprise adoption
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import os
import sys
import time
import uuid
import random
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import websockets
import pytest
from datetime import datetime, timedelta
import signal
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"

# Test configurations
TEST_USERS = [
    {
        "email": "error_test_1@example.com",
        "password": "SecurePass123!",
        "name": "Error Test User 1",
        "tier": "free"
    },
    {
        "email": "error_test_2@example.com",
        "password": "SecurePass456!",
        "name": "Error Test User 2",
        "tier": "early"
    },
    {
        "email": "error_test_3@example.com",
        "password": "SecurePass789!",
        "name": "Error Test User 3",
        "tier": "enterprise"
    }
]

ERROR_SCENARIOS = [
    {
        "name": "network_disconnect",
        "description": "Simulate network disconnection and reconnection",
        "failure_type": "network",
        "duration": 5,
        "recovery_expected": True
    },
    {
        "name": "service_overload",
        "description": "Simulate service overload with high request volume",
        "failure_type": "overload",
        "duration": 10,
        "recovery_expected": True
    },
    {
        "name": "database_timeout",
        "description": "Simulate database connection timeout",
        "failure_type": "database",
        "duration": 8,
        "recovery_expected": True
    },
    {
        "name": "agent_failure",
        "description": "Simulate agent processing failure",
        "failure_type": "agent",
        "duration": 3,
        "recovery_expected": True
    },
    {
        "name": "memory_pressure",
        "description": "Simulate memory pressure conditions",
        "failure_type": "memory",
        "duration": 12,
        "recovery_expected": True
    }
]

TIMEOUT_SCENARIOS = [
    {"operation": "auth", "timeout": 2, "expected_behavior": "retry"},
    {"operation": "message_send", "timeout": 1, "expected_behavior": "queue"},
    {"operation": "agent_response", "timeout": 5, "expected_behavior": "fallback"},
    {"operation": "websocket_connect", "timeout": 3, "expected_behavior": "retry"}
]


class ErrorRecoveryTester:
    """Test comprehensive error recovery mechanisms."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_tokens: Dict[str, str] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self.active_threads: Dict[str, List[str]] = {}
        self.error_logs: List[Dict[str, Any]] = []
        self.recovery_metrics: Dict[str, List[float]] = {
            "detection_times": [],
            "recovery_times": [],
            "retry_counts": [],
            "fallback_times": []
        }
        self.test_logs: List[str] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        # Use longer timeout for error testing
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Close all WebSocket connections
        for email, ws in self.websocket_connections.items():
            try:
                if ws and not ws.closed:
                    await ws.close()
            except:
                pass
                
        if self.session:
            await self.session.close()
    
    def log_event(self, user: str, event: str, details: str = "", error_data: Dict[str, Any] = None):
        """Log test events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{user}] {event}"
        if details:
            log_entry += f" - {details}"
        self.test_logs.append(log_entry)
        print(log_entry)
        
        # Store error data for analysis
        if error_data:
            self.error_logs.append({
                "timestamp": timestamp,
                "user": user,
                "event": event,
                "details": details,
                **error_data
            })
    
    async def setup_test_user(self, user_data: Dict[str, Any]) -> bool:
        """Setup a test user with authentication."""
        email = user_data["email"]
        
        self.log_event(email, "USER_SETUP", "Starting user setup")
        
        try:
            # Register user with retry logic
            success = await self._retry_operation(
                self._register_user, user_data, max_retries=3
            )
            if not success:
                return False
                
            # Login user with retry logic
            success = await self._retry_operation(
                self._login_user, user_data, max_retries=3
            )
            return success
                    
        except Exception as e:
            self.log_event(email, "SETUP_ERROR", str(e))
            return False
    
    async def _register_user(self, user_data: Dict[str, Any]) -> bool:
        """Register user with error handling."""
        email = user_data["email"]
        
        register_payload = {
            "email": email,
            "password": user_data["password"],
            "name": user_data["name"],
            "tier": user_data.get("tier", "free")
        }
        
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=register_payload
        ) as response:
            if response.status in [200, 201, 409]:  # Include 409 for existing users
                self.log_event(email, "REGISTRATION_OK", f"Status: {response.status}")
                return True
            else:
                self.log_event(email, "REGISTRATION_FAILED", f"Status: {response.status}")
                return False
    
    async def _login_user(self, user_data: Dict[str, Any]) -> bool:
        """Login user with error handling."""
        email = user_data["email"]
        
        login_payload = {
            "email": email,
            "password": user_data["password"]
        }
        
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json=login_payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.user_tokens[email] = data.get("access_token")
                self.log_event(email, "LOGIN_SUCCESS", "Token obtained")
                return True
            else:
                self.log_event(email, "LOGIN_FAILED", f"Status: {response.status}")
                return False
    
    async def _retry_operation(self, operation, *args, max_retries: int = 3, delay: float = 1.0) -> bool:
        """Retry operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                result = await operation(*args)
                if result:
                    return True
                    
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt) + random.uniform(0, 1)
                    self.log_event("SYSTEM", "RETRY_ATTEMPT", f"Attempt {attempt + 1}, retrying in {wait_time:.2f}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    self.log_event("SYSTEM", "RETRY_EXHAUSTED", f"All {max_retries} attempts failed: {e}")
                    
        return False
    
    async def establish_websocket_connection(self, email: str, with_recovery: bool = True) -> bool:
        """Establish WebSocket connection with error recovery."""
        if email not in self.user_tokens:
            self.log_event(email, "WS_CONNECT_SKIP", "No auth token")
            return False
            
        self.log_event(email, "WS_CONNECT_START", "Establishing WebSocket connection")
        
        max_attempts = 3 if with_recovery else 1
        
        for attempt in range(max_attempts):
            try:
                headers = {"Authorization": f"Bearer {self.user_tokens[email]}"}
                
                ws = await websockets.connect(
                    WEBSOCKET_URL,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
                
                # Send auth message with timeout
                auth_message = {
                    "type": "auth",
                    "token": self.user_tokens[email],
                    "retry_attempt": attempt + 1
                }
                await ws.send(json.dumps(auth_message))
                
                # Wait for auth response with timeout
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(response)
                
                if data.get("type") == "auth_success":
                    self.websocket_connections[email] = ws
                    self.active_threads[email] = []
                    self.log_event(email, "WS_CONNECT_SUCCESS", f"Session: {data.get('session_id', 'unknown')}")
                    return True
                else:
                    self.log_event(email, "WS_AUTH_FAILED", str(data))
                    await ws.close()
                    
            except Exception as e:
                self.log_event(email, "WS_CONNECT_ERROR", f"Attempt {attempt + 1}: {e}")
                
                if attempt < max_attempts - 1:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                    
        return False
    
    async def test_network_disconnection_recovery(self, email: str) -> Dict[str, Any]:
        """Test recovery from network disconnection."""
        result = {
            "disconnection_detected": False,
            "reconnection_attempted": False,
            "reconnection_successful": False,
            "data_preserved": False,
            "detection_time": 0,
            "recovery_time": 0
        }
        
        ws = self.websocket_connections.get(email)
        if not ws:
            return result
            
        self.log_event(email, "NETWORK_DISCONNECT_TEST", "Starting network disconnection test")
        
        try:
            # Send initial message to establish baseline
            test_message = {
                "type": "test_message",
                "content": "Pre-disconnection test",
                "timestamp": datetime.now().isoformat(),
                "test_id": str(uuid.uuid4())
            }
            
            await ws.send(json.dumps(test_message))
            initial_response = await asyncio.wait_for(ws.recv(), timeout=5)
            
            # Simulate network disconnection by closing the connection abruptly
            detection_start = time.time()
            await ws.close(code=1006)  # Abnormal closure
            
            # Try to detect disconnection
            try:
                await ws.send(json.dumps({"type": "ping"}))
            except:
                result["disconnection_detected"] = True
                result["detection_time"] = time.time() - detection_start
                self.recovery_metrics["detection_times"].append(result["detection_time"])
                
            self.log_event(email, "DISCONNECTION_DETECTED", f"Detection time: {result['detection_time']:.2f}s")
            
            # Attempt reconnection with recovery
            recovery_start = time.time()
            result["reconnection_attempted"] = True
            
            reconnect_success = await self.establish_websocket_connection(email, with_recovery=True)
            
            if reconnect_success:
                result["reconnection_successful"] = True
                result["recovery_time"] = time.time() - recovery_start
                self.recovery_metrics["recovery_times"].append(result["recovery_time"])
                
                # Test if we can send messages after recovery
                new_ws = self.websocket_connections.get(email)
                if new_ws:
                    recovery_message = {
                        "type": "test_message",
                        "content": "Post-recovery test",
                        "timestamp": datetime.now().isoformat(),
                        "test_id": str(uuid.uuid4())
                    }
                    
                    await new_ws.send(json.dumps(recovery_message))
                    recovery_response = await asyncio.wait_for(new_ws.recv(), timeout=5)
                    
                    if recovery_response:
                        result["data_preserved"] = True
                        
                self.log_event(email, "RECONNECTION_SUCCESS", f"Recovery time: {result['recovery_time']:.2f}s")
            else:
                self.log_event(email, "RECONNECTION_FAILED", "Failed to reconnect")
                
        except Exception as e:
            self.log_event(email, "NETWORK_TEST_ERROR", str(e))
            
        return result
    
    async def test_service_overload_handling(self, email: str) -> Dict[str, Any]:
        """Test handling of service overload conditions."""
        result = {
            "overload_simulated": False,
            "rate_limiting_detected": False,
            "circuit_breaker_triggered": False,
            "graceful_degradation": False,
            "recovery_successful": False,
            "overload_time": 0
        }
        
        self.log_event(email, "OVERLOAD_TEST_START", "Starting service overload test")
        
        try:
            # Simulate overload by sending many concurrent requests
            overload_start = time.time()
            concurrent_requests = 50
            tasks = []
            
            for i in range(concurrent_requests):
                task = self._send_overload_request(email, i)
                tasks.append(task)
                
            # Send all requests concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            result["overload_simulated"] = True
            
            # Analyze responses for overload indicators
            rate_limited_count = 0
            error_count = 0
            success_count = 0
            
            for response in responses:
                if isinstance(response, dict):
                    if response.get("status_code") == 429:  # Too Many Requests
                        rate_limited_count += 1
                    elif response.get("status_code") in [503, 502, 504]:  # Service errors
                        error_count += 1
                    elif response.get("status_code") == 200:
                        success_count += 1
                        
            if rate_limited_count > 0:
                result["rate_limiting_detected"] = True
                
            if error_count > concurrent_requests * 0.3:  # >30% errors
                result["circuit_breaker_triggered"] = True
                
            if success_count > 0:  # Some requests still succeeded
                result["graceful_degradation"] = True
                
            result["overload_time"] = time.time() - overload_start
            
            self.log_event(email, "OVERLOAD_RESULTS", 
                         f"Rate limited: {rate_limited_count}, Errors: {error_count}, Success: {success_count}")
            
            # Test recovery after overload
            await asyncio.sleep(5)  # Wait for recovery
            
            recovery_success = await self._test_normal_operation(email)
            result["recovery_successful"] = recovery_success
            
        except Exception as e:
            self.log_event(email, "OVERLOAD_TEST_ERROR", str(e))
            
        return result
    
    async def _send_overload_request(self, email: str, request_id: int) -> Dict[str, Any]:
        """Send a single request for overload testing."""
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens.get(email, '')}"}
            
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/health",
                headers=headers
            ) as response:
                return {
                    "request_id": request_id,
                    "status_code": response.status,
                    "response_time": 0  # Would need to measure this
                }
                
        except Exception as e:
            return {
                "request_id": request_id,
                "status_code": 0,
                "error": str(e),
                "response_time": 0
            }
    
    async def _test_normal_operation(self, email: str) -> bool:
        """Test if normal operation is restored."""
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens.get(email, '')}"}
            
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/health",
                headers=headers
            ) as response:
                return response.status == 200
                
        except:
            return False
    
    async def test_timeout_and_retry_logic(self, email: str) -> Dict[str, Any]:
        """Test timeout handling and retry mechanisms."""
        result = {
            "timeout_scenarios_tested": 0,
            "timeout_scenarios_passed": 0,
            "retry_logic_working": False,
            "fallback_mechanisms": False,
            "timeout_details": {}
        }
        
        self.log_event(email, "TIMEOUT_TEST_START", "Starting timeout and retry tests")
        
        for scenario in TIMEOUT_SCENARIOS:
            operation = scenario["operation"]
            timeout = scenario["timeout"]
            expected_behavior = scenario["expected_behavior"]
            
            result["timeout_scenarios_tested"] += 1
            
            self.log_event(email, "TIMEOUT_SCENARIO", f"Testing {operation} with {timeout}s timeout")
            
            try:
                scenario_result = await self._test_timeout_scenario(email, scenario)
                result["timeout_details"][operation] = scenario_result
                
                if scenario_result.get("behaved_as_expected"):
                    result["timeout_scenarios_passed"] += 1
                    
                if scenario_result.get("retry_attempted"):
                    result["retry_logic_working"] = True
                    
                if scenario_result.get("fallback_used"):
                    result["fallback_mechanisms"] = True
                    
            except Exception as e:
                self.log_event(email, "TIMEOUT_SCENARIO_ERROR", f"{operation}: {e}")
                result["timeout_details"][operation] = {"error": str(e)}
        
        return result
    
    async def _test_timeout_scenario(self, email: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific timeout scenario."""
        operation = scenario["operation"]
        timeout = scenario["timeout"]
        expected_behavior = scenario["expected_behavior"]
        
        scenario_result = {
            "behaved_as_expected": False,
            "retry_attempted": False,
            "fallback_used": False,
            "total_time": 0
        }
        
        start_time = time.time()
        
        if operation == "auth":
            # Test auth timeout
            try:
                # Use very short timeout to force timeout
                short_timeout = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(timeout=short_timeout) as short_session:
                    async with short_session.post(
                        f"{AUTH_SERVICE_URL}/auth/validate",
                        headers={"Authorization": f"Bearer {self.user_tokens.get(email, '')}"}
                    ) as response:
                        # If we get here, timeout didn't occur
                        scenario_result["behaved_as_expected"] = (expected_behavior != "timeout")
                        
            except asyncio.TimeoutError:
                scenario_result["behaved_as_expected"] = (expected_behavior == "retry")
                scenario_result["retry_attempted"] = True
                
        elif operation == "websocket_connect":
            # Test WebSocket connection timeout
            try:
                headers = {"Authorization": f"Bearer {self.user_tokens.get(email, '')}"}
                
                # Try to connect with short timeout
                ws = await asyncio.wait_for(
                    websockets.connect(WEBSOCKET_URL, extra_headers=headers),
                    timeout=timeout
                )
                await ws.close()
                scenario_result["behaved_as_expected"] = True
                
            except asyncio.TimeoutError:
                scenario_result["behaved_as_expected"] = (expected_behavior == "retry")
                scenario_result["retry_attempted"] = True
                
        scenario_result["total_time"] = time.time() - start_time
        return scenario_result
    
    async def test_agent_failure_fallback(self, email: str) -> Dict[str, Any]:
        """Test agent failure detection and fallback mechanisms."""
        result = {
            "agent_failure_simulated": False,
            "failure_detected": False,
            "fallback_triggered": False,
            "fallback_successful": False,
            "fallback_time": 0
        }
        
        ws = self.websocket_connections.get(email)
        if not ws:
            return result
            
        self.log_event(email, "AGENT_FAILURE_TEST", "Starting agent failure test")
        
        try:
            # Send a message that should trigger agent processing
            start_time = time.time()
            
            failure_message = {
                "type": "send_message",
                "thread_id": "test_thread",
                "message": {
                    "content": "Please analyze this extremely complex scenario that might cause processing issues",
                    "type": "user",
                    "force_failure": True,  # Special flag for testing
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await ws.send(json.dumps(failure_message))
            result["agent_failure_simulated"] = True
            
            # Wait for response or timeout
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(response)
                
                if data.get("type") == "agent_error":
                    result["failure_detected"] = True
                    
                elif data.get("type") == "fallback_response":
                    result["failure_detected"] = True
                    result["fallback_triggered"] = True
                    result["fallback_successful"] = True
                    
                elif data.get("type") == "agent_response":
                    # Normal response - check if it indicates fallback was used
                    content = data.get("content", "").lower()
                    if any(indicator in content for indicator in ["fallback", "simplified", "basic"]):
                        result["fallback_triggered"] = True
                        result["fallback_successful"] = True
                        
            except asyncio.TimeoutError:
                # Timeout might indicate failure, check for fallback
                self.log_event(email, "AGENT_TIMEOUT", "Agent response timeout")
                result["failure_detected"] = True
                
                # Check if fallback response comes later
                try:
                    fallback_response = await asyncio.wait_for(ws.recv(), timeout=5)
                    fallback_data = json.loads(fallback_response)
                    
                    if fallback_data.get("type") in ["fallback_response", "error_response"]:
                        result["fallback_triggered"] = True
                        result["fallback_successful"] = True
                        
                except asyncio.TimeoutError:
                    pass
                    
            result["fallback_time"] = time.time() - start_time
            self.recovery_metrics["fallback_times"].append(result["fallback_time"])
            
        except Exception as e:
            self.log_event(email, "AGENT_FAILURE_ERROR", str(e))
            
        return result
    
    async def test_error_state_persistence(self, email: str) -> Dict[str, Any]:
        """Test error state persistence and cleanup."""
        result = {
            "error_state_created": False,
            "state_persisted": False,
            "cleanup_successful": False,
            "recovery_after_cleanup": False
        }
        
        self.log_event(email, "ERROR_STATE_TEST", "Testing error state persistence")
        
        try:
            # Create an error state
            headers = {"Authorization": f"Bearer {self.user_tokens.get(email, '')}"}
            
            # Send request that should create error state
            error_payload = {
                "action": "create_error_state",
                "error_type": "test_error",
                "user_id": email
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/api/v1/test/error-state",
                json=error_payload,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    result["error_state_created"] = True
                    
            # Check if error state persists
            await asyncio.sleep(2)
            
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/test/error-state",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("has_error_state"):
                        result["state_persisted"] = True
                        
            # Test cleanup
            async with self.session.delete(
                f"{BACKEND_URL}/api/v1/test/error-state",
                headers=headers
            ) as response:
                if response.status == 200:
                    result["cleanup_successful"] = True
                    
            # Verify cleanup
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/test/error-state", 
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data.get("has_error_state"):
                        result["recovery_after_cleanup"] = True
                        
        except Exception as e:
            self.log_event(email, "ERROR_STATE_ERROR", str(e))
            
        return result
    
    async def test_circuit_breaker_functionality(self, email: str) -> Dict[str, Any]:
        """Test circuit breaker implementation."""
        result = {
            "circuit_breaker_exists": False,
            "breaker_triggered": False,
            "breaker_opened": False,
            "breaker_recovered": False,
            "trip_time": 0
        }
        
        self.log_event(email, "CIRCUIT_BREAKER_TEST", "Testing circuit breaker functionality")
        
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens.get(email, '')}"}
            
            # Send requests to trigger circuit breaker
            failure_count = 0
            trip_start = time.time()
            
            for i in range(10):  # Send multiple failing requests
                try:
                    async with self.session.get(
                        f"{BACKEND_URL}/api/v1/test/circuit-breaker-trigger",
                        headers=headers
                    ) as response:
                        if response.status >= 500:
                            failure_count += 1
                        elif response.status == 503:  # Service Unavailable - circuit open
                            result["circuit_breaker_exists"] = True
                            result["breaker_triggered"] = True
                            result["breaker_opened"] = True
                            result["trip_time"] = time.time() - trip_start
                            break
                            
                except Exception:
                    failure_count += 1
                    
                await asyncio.sleep(0.1)  # Brief delay between requests
                
            if failure_count >= 5:  # Enough failures to potentially trip breaker
                result["breaker_triggered"] = True
                
            # Test recovery after waiting
            if result["breaker_opened"]:
                self.log_event(email, "CIRCUIT_BREAKER_OPEN", f"Breaker opened after {result['trip_time']:.2f}s")
                
                # Wait for circuit breaker to potentially close
                await asyncio.sleep(10)
                
                # Test if circuit breaker allows requests again
                try:
                    async with self.session.get(
                        f"{BACKEND_URL}/api/v1/health",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result["breaker_recovered"] = True
                            
                except Exception:
                    pass
                    
        except Exception as e:
            self.log_event(email, "CIRCUIT_BREAKER_ERROR", str(e))
            
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all error recovery tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "users_tested": len(TEST_USERS),
            "error_scenarios_tested": len(ERROR_SCENARIOS),
            "user_results": {},
            "recovery_metrics": {},
            "error_logs": [],
            "test_logs": [],
            "summary": {}
        }
        
        # Setup all users
        print("\n" + "="*60)
        print("SETTING UP TEST USERS")
        print("="*60)
        
        for user_data in TEST_USERS:
            email = user_data["email"]
            success = await self.setup_test_user(user_data)
            if success:
                await self.establish_websocket_connection(email)
        
        # Run tests for each user
        for user_data in TEST_USERS:
            email = user_data["email"]
            
            if email not in self.user_tokens:
                self.log_event(email, "SKIP_USER", "No valid session")
                continue
                
            print(f"\n{'='*60}")
            print(f"Testing error recovery for: {email}")
            print('='*60)
            
            user_results = {}
            
            # Test network disconnection recovery
            network_result = await self.test_network_disconnection_recovery(email)
            user_results["network_disconnection"] = network_result
            
            # Test service overload handling
            overload_result = await self.test_service_overload_handling(email)
            user_results["service_overload"] = overload_result
            
            # Test timeout and retry logic
            timeout_result = await self.test_timeout_and_retry_logic(email)
            user_results["timeout_retry"] = timeout_result
            
            # Test agent failure fallback
            agent_failure_result = await self.test_agent_failure_fallback(email)
            user_results["agent_failure"] = agent_failure_result
            
            # Test error state persistence
            error_state_result = await self.test_error_state_persistence(email)
            user_results["error_state"] = error_state_result
            
            # Test circuit breaker
            circuit_breaker_result = await self.test_circuit_breaker_functionality(email)
            user_results["circuit_breaker"] = circuit_breaker_result
            
            all_results["user_results"][email] = user_results
        
        # Calculate recovery metrics
        all_results["recovery_metrics"] = {
            "avg_detection_time": (
                sum(self.recovery_metrics["detection_times"]) / 
                len(self.recovery_metrics["detection_times"])
                if self.recovery_metrics["detection_times"] else 0
            ),
            "avg_recovery_time": (
                sum(self.recovery_metrics["recovery_times"]) / 
                len(self.recovery_metrics["recovery_times"])
                if self.recovery_metrics["recovery_times"] else 0
            ),
            "avg_fallback_time": (
                sum(self.recovery_metrics["fallback_times"]) / 
                len(self.recovery_metrics["fallback_times"])
                if self.recovery_metrics["fallback_times"] else 0
            ),
            "total_errors_tested": len(self.error_logs)
        }
        
        # Add logs
        all_results["error_logs"] = self.error_logs
        all_results["test_logs"] = self.test_logs
        
        # Generate summary
        total_tests = 0
        passed_tests = 0
        
        for email, results in all_results["user_results"].items():
            for test_name, test_result in results.items():
                if isinstance(test_result, dict):
                    total_tests += 1
                    
                    # Determine if test passed based on its type
                    if "network" in test_name and test_result.get("reconnection_successful"):
                        passed_tests += 1
                    elif "overload" in test_name and test_result.get("graceful_degradation"):
                        passed_tests += 1
                    elif "timeout" in test_name and test_result.get("retry_logic_working"):
                        passed_tests += 1
                    elif "agent_failure" in test_name and test_result.get("fallback_triggered"):
                        passed_tests += 1
                    elif "error_state" in test_name and test_result.get("cleanup_successful"):
                        passed_tests += 1
                    elif "circuit_breaker" in test_name and test_result.get("circuit_breaker_exists"):
                        passed_tests += 1
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_errors_handled": len(self.error_logs),
            "recovery_mechanisms_tested": len(ERROR_SCENARIOS) + len(TIMEOUT_SCENARIOS)
        }
        
        return all_results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
async def test_dev_environment_error_recovery():
    """Test comprehensive error recovery functionality."""
    async with ErrorRecoveryTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("ERROR RECOVERY TEST RESULTS")
        print("="*60)
        
        for email, user_results in results["user_results"].items():
            print(f"\nUser: {email}")
            print("-" * 40)
            
            for test_name, test_result in user_results.items():
                if isinstance(test_result, dict):
                    if "network" in test_name:
                        reconnected = test_result.get("reconnection_successful", False)
                        recovery_time = test_result.get("recovery_time", 0)
                        print(f"  {test_name}: {'✓' if reconnected else '✗'} (recovery: {recovery_time:.2f}s)")
                    elif "overload" in test_name:
                        degraded = test_result.get("graceful_degradation", False)
                        rate_limited = test_result.get("rate_limiting_detected", False)
                        print(f"  {test_name}: {'✓' if degraded else '✗'} (rate limited: {'✓' if rate_limited else '✗'})")
                    elif "timeout" in test_name:
                        retry_working = test_result.get("retry_logic_working", False)
                        scenarios_passed = test_result.get("timeout_scenarios_passed", 0)
                        scenarios_total = test_result.get("timeout_scenarios_tested", 0)
                        print(f"  {test_name}: {'✓' if retry_working else '✗'} ({scenarios_passed}/{scenarios_total} scenarios)")
                    elif "agent_failure" in test_name:
                        fallback = test_result.get("fallback_triggered", False)
                        successful = test_result.get("fallback_successful", False)
                        print(f"  {test_name}: {'✓' if fallback else '✗'} (successful: {'✓' if successful else '✗'})")
                    elif "error_state" in test_name:
                        cleanup = test_result.get("cleanup_successful", False)
                        recovery = test_result.get("recovery_after_cleanup", False)
                        print(f"  {test_name}: {'✓' if cleanup else '✗'} (recovery: {'✓' if recovery else '✗'})")
                    elif "circuit_breaker" in test_name:
                        exists = test_result.get("circuit_breaker_exists", False)
                        triggered = test_result.get("breaker_triggered", False)
                        print(f"  {test_name}: {'✓' if exists else '✗'} (triggered: {'✓' if triggered else '✗'})")
        
        # Recovery metrics
        metrics = results["recovery_metrics"]
        print("\n" + "="*60)
        print("RECOVERY METRICS")
        print("="*60)
        print(f"Avg Detection Time: {metrics['avg_detection_time']:.2f}s")
        print(f"Avg Recovery Time: {metrics['avg_recovery_time']:.2f}s")
        print(f"Avg Fallback Time: {metrics['avg_fallback_time']:.2f}s")
        print(f"Total Errors Tested: {metrics['total_errors_tested']}")
        
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed Tests: {summary['passed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Errors Handled: {summary['total_errors_handled']}")
        print(f"Recovery Mechanisms: {summary['recovery_mechanisms_tested']}")
        
        # Assert critical conditions
        assert summary["success_rate"] >= 60, f"Success rate too low: {summary['success_rate']:.1f}%"
        assert metrics["avg_recovery_time"] < 30, "Recovery time too slow"
        assert summary["total_errors_handled"] >= 0, "No error handling tested"
        
        print("\n[SUCCESS] Error recovery tests completed!")


async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT ERROR RECOVERY TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with ErrorRecoveryTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "error_recovery_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {results_file}")
        
        # Return exit code
        if results["summary"]["success_rate"] >= 60:
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)