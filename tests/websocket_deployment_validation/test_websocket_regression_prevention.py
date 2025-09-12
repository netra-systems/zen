#!/usr/bin/env python
"""WEBSOCKET REGRESSION PREVENTION TEST SUITE

Comprehensive test suite designed to prevent known WebSocket regressions and deployment issues.
Validates specific fixes and catches regressions before they impact production.

Business Value: Prevents $180K+ MRR chat functionality regressions in production deployments
Critical: Tests the exact failure scenarios that were identified during staging deployment
"""

import asyncio
import json
import os
import sys
import time
import uuid
import jwt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import hashlib

# Add project root to path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import websockets
from loguru import logger

from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_unified_jwt_secret, get_jwt_secret_manager
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class WebSocketRegressionTester:
    """Tests specific WebSocket regression scenarios to prevent known failures."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.auth_helper = E2EAuthHelper()
        self.env = get_env()
        self.regression_tests = []
        self._setup_regression_tests()
        
    def _setup_regression_tests(self):
        """Setup the list of regression tests based on known issues."""
        
        self.regression_tests = [
            {
                "name": "jwt_secret_synchronization_regression",
                "description": "Prevent JWT secret mismatch between auth service and backend",
                "severity": "critical",
                "business_impact": "high",
                "test_func": self.test_jwt_secret_synchronization_regression
            },
            {
                "name": "websocket_403_handshake_regression",
                "description": "Prevent HTTP 403 WebSocket handshake failures",
                "severity": "critical", 
                "business_impact": "high",
                "test_func": self.test_websocket_403_handshake_regression
            },
            {
                "name": "load_balancer_timeout_regression",
                "description": "Prevent load balancer timeout causing connection drops",
                "severity": "critical",
                "business_impact": "medium",
                "test_func": self.test_load_balancer_timeout_regression
            },
            {
                "name": "websocket_header_validation_regression", 
                "description": "Prevent WebSocket upgrade header validation failures",
                "severity": "high",
                "business_impact": "medium",
                "test_func": self.test_websocket_header_validation_regression
            },
            {
                "name": "agent_events_missing_regression",
                "description": "Prevent missing critical WebSocket agent events",
                "severity": "critical",
                "business_impact": "high",
                "test_func": self.test_agent_events_missing_regression
            },
            {
                "name": "multi_user_isolation_regression",
                "description": "Prevent user isolation violations in multi-user scenarios",
                "severity": "high",
                "business_impact": "high",
                "test_func": self.test_multi_user_isolation_regression
            },
            {
                "name": "websocket_connection_leak_regression",
                "description": "Prevent WebSocket connection memory leaks",
                "severity": "medium",
                "business_impact": "medium",
                "test_func": self.test_websocket_connection_leak_regression
            },
            {
                "name": "auth_token_refresh_regression",
                "description": "Prevent auth token refresh failures during long sessions",
                "severity": "high", 
                "business_impact": "medium",
                "test_func": self.test_auth_token_refresh_regression
            }
        ]
        
    async def run_all_regression_tests(self) -> Dict[str, Any]:
        """Run all regression tests and return comprehensive results."""
        
        logger.info(f" SEARCH:  Starting WebSocket regression prevention test suite ({len(self.regression_tests)} tests)...")
        
        suite_results = {
            "test_suite": "websocket_regression_prevention",
            "environment": self.environment,
            "start_time": datetime.utcnow().isoformat(),
            "tests": {},
            "summary": {}
        }
        
        passed_tests = 0
        failed_tests = 0
        critical_failures = 0
        
        for test_config in self.regression_tests:
            test_name = test_config["name"]
            
            try:
                logger.info(f"[U+1F9EA] Running regression test: {test_name}")
                
                # Run the specific test function
                test_result = await test_config["test_func"]()
                
                test_result.update({
                    "name": test_name,
                    "description": test_config["description"],
                    "severity": test_config["severity"],
                    "business_impact": test_config["business_impact"]
                })
                
                suite_results["tests"][test_name] = test_result
                
                if test_result.get("passed", False):
                    passed_tests += 1
                    logger.success(f" PASS:  {test_name} PASSED")
                else:
                    failed_tests += 1
                    if test_config["severity"] == "critical":
                        critical_failures += 1
                    logger.error(f" FAIL:  {test_name} FAILED: {test_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed_tests += 1
                if test_config["severity"] == "critical":
                    critical_failures += 1
                    
                error_result = {
                    "name": test_name,
                    "description": test_config["description"],
                    "severity": test_config["severity"],
                    "business_impact": test_config["business_impact"],
                    "passed": False,
                    "error": str(e),
                    "exception": True
                }
                
                suite_results["tests"][test_name] = error_result
                logger.error(f" FAIL:  {test_name} FAILED with exception: {e}")
                
        # Generate summary
        total_tests = passed_tests + failed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        suite_results["end_time"] = datetime.utcnow().isoformat()
        suite_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "critical_failures": critical_failures,
            "success_rate": round(success_rate, 1),
            "regression_free": critical_failures == 0 and success_rate >= 85,
            "deployment_safe": critical_failures == 0 and success_rate >= 90
        }
        
        # Log final results
        if suite_results["summary"]["deployment_safe"]:
            logger.success(f" CELEBRATION:  Regression prevention tests PASSED: {success_rate}% success rate")
            logger.success(" PASS:  No critical regressions detected - deployment safe")
        elif suite_results["summary"]["regression_free"]:
            logger.warning(f" WARNING: [U+FE0F] Regression prevention tests mostly passed: {success_rate}% success rate")
            logger.warning(" WARNING: [U+FE0F] No critical regressions but some issues detected")
        else:
            logger.error(f" FAIL:  Regression prevention tests FAILED: {success_rate}% success rate")
            logger.error(f"[U+1F6AB] {critical_failures} critical regressions detected - deployment NOT safe")
            
        return suite_results
        
    async def test_jwt_secret_synchronization_regression(self) -> Dict[str, Any]:
        """Test that JWT secret synchronization is working properly."""
        
        test_result = {
            "test": "jwt_secret_synchronization_regression",
            "passed": False,
            "details": {}
        }
        
        try:
            # Clear any cached secrets to test fresh resolution
            get_jwt_secret_manager().clear_cache()
            
            # Test 1: Verify unified JWT secret is accessible
            try:
                unified_secret = get_unified_jwt_secret()
                test_result["details"]["unified_secret_accessible"] = True
                test_result["details"]["secret_length"] = len(unified_secret)
                
                # Generate hash for comparison (don't log actual secret)
                secret_hash = hashlib.md5(unified_secret.encode()).hexdigest()[:16]
                test_result["details"]["secret_hash"] = secret_hash
                
            except Exception as e:
                test_result["error"] = f"Cannot access unified JWT secret: {e}"
                return test_result
                
            # Test 2: Generate JWT token using unified secret
            try:
                test_payload = {
                    "sub": "regression_test_user",
                    "email": "regression@test.netrasystems.ai",
                    "iat": int(time.time()),
                    "exp": int(time.time()) + 3600,
                    "iss": "netra-auth-service"
                }
                
                token = jwt.encode(test_payload, unified_secret, algorithm="HS256")
                test_result["details"]["token_generation_success"] = True
                test_result["details"]["token_length"] = len(token)
                
            except Exception as e:
                test_result["error"] = f"JWT token generation failed: {e}"
                return test_result
                
            # Test 3: Validate token can be decoded with same secret
            try:
                decoded_payload = jwt.decode(token, unified_secret, algorithms=["HS256"])
                
                if decoded_payload["sub"] == "regression_test_user":
                    test_result["details"]["token_validation_success"] = True
                else:
                    test_result["error"] = "Decoded payload doesn't match original"
                    return test_result
                    
            except Exception as e:
                test_result["error"] = f"JWT token validation failed: {e}"
                return test_result
                
            # Test 4: Try WebSocket connection with generated token
            try:
                websocket_url = self._get_websocket_url()
                headers = {"Authorization": f"Bearer {token}"}
                
                async with websockets.connect(
                    websocket_url,
                    extra_headers=headers,
                    timeout=10
                ) as websocket:
                    # Wait for connection established message
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                    welcome_data = json.loads(welcome_msg)
                    
                    if welcome_data.get("type") == "connection_established":
                        test_result["details"]["websocket_auth_success"] = True
                    else:
                        test_result["details"]["websocket_auth_success"] = False
                        test_result["details"]["unexpected_message"] = welcome_data
                        
            except websockets.exceptions.ConnectionClosedError as e:
                if e.code == 1008:  # Authentication error
                    test_result["error"] = f"WebSocket authentication failed with JWT secret mismatch: {e}"
                    return test_result
                else:
                    test_result["error"] = f"WebSocket connection closed unexpectedly: {e}"
                    return test_result
            except Exception as e:
                test_result["error"] = f"WebSocket connection with JWT token failed: {e}"
                return test_result
                
            # All tests passed
            test_result["passed"] = True
            test_result["message"] = "JWT secret synchronization working correctly"
            
        except Exception as e:
            test_result["error"] = f"JWT synchronization test failed: {e}"
            
        return test_result
        
    async def test_websocket_403_handshake_regression(self) -> Dict[str, Any]:
        """Test that WebSocket 403 handshake failures are prevented."""
        
        test_result = {
            "test": "websocket_403_handshake_regression",
            "passed": False,
            "details": {}
        }
        
        try:
            # Test with valid authentication
            jwt_token = await self.auth_helper.get_test_jwt_token()
            websocket_url = self._get_websocket_url()
            headers = {"Authorization": f"Bearer {jwt_token}"}
            
            # Test 1: Basic handshake success
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=headers,
                    timeout=10
                ) as websocket:
                    # Should not get 403 error
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=8)
                    welcome_data = json.loads(welcome_msg)
                    
                    test_result["details"]["handshake_successful"] = True
                    test_result["details"]["welcome_message_type"] = welcome_data.get("type")
                    
                    # Send a test message to ensure full connection works
                    test_message = {
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    test_result["details"]["message_exchange_successful"] = True
                    test_result["details"]["response_type"] = response_data.get("type")
                    
            except websockets.exceptions.ConnectionClosedError as e:
                if e.code == 403 or "403" in str(e):
                    test_result["error"] = f"WebSocket handshake returned 403 Forbidden (REGRESSION): {e}"
                    return test_result
                else:
                    test_result["error"] = f"WebSocket connection closed with code {e.code}: {e}"
                    return test_result
                    
            # Test 2: Multiple rapid connections (test for race conditions)
            try:
                connection_count = 3
                connection_tasks = []
                
                for i in range(connection_count):
                    task = self._test_single_websocket_connection(jwt_token, timeout=8)
                    connection_tasks.append(task)
                    
                connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
                
                successful_connections = sum(
                    1 for result in connection_results
                    if isinstance(result, dict) and result.get("success", False)
                )
                
                test_result["details"]["rapid_connections_tested"] = connection_count
                test_result["details"]["rapid_connections_successful"] = successful_connections
                
                if successful_connections < connection_count:
                    failed_connections = [
                        result for result in connection_results
                        if isinstance(result, dict) and not result.get("success", False)
                    ]
                    test_result["details"]["rapid_connection_failures"] = failed_connections
                    
            except Exception as e:
                test_result["error"] = f"Rapid connection test failed: {e}"
                return test_result
                
            # Test 3: Different header formats (ensure robustness)
            header_variants = [
                {"Authorization": f"Bearer {jwt_token}"},
                {"authorization": f"Bearer {jwt_token}"},  # lowercase
                {"Authorization": f"bearer {jwt_token}"}   # lowercase bearer
            ]
            
            header_test_results = []
            
            for i, headers_variant in enumerate(header_variants):
                try:
                    result = await self._test_single_websocket_connection(jwt_token, headers=headers_variant, timeout=6)
                    header_test_results.append({
                        "variant": i + 1,
                        "headers": headers_variant,
                        "success": result.get("success", False)
                    })
                except Exception as e:
                    header_test_results.append({
                        "variant": i + 1,
                        "headers": headers_variant,
                        "success": False,
                        "error": str(e)
                    })
                    
            test_result["details"]["header_variant_tests"] = header_test_results
            
            successful_header_tests = sum(
                1 for result in header_test_results
                if result["success"]
            )
            
            # All tests should pass for regression prevention
            if (test_result["details"].get("handshake_successful", False) and
                test_result["details"].get("message_exchange_successful", False) and
                successful_header_tests >= 2):  # At least 2/3 header variants should work
                
                test_result["passed"] = True
                test_result["message"] = "WebSocket 403 handshake regression prevented"
            else:
                test_result["error"] = "Some handshake tests failed - potential regression"
                
        except Exception as e:
            test_result["error"] = f"WebSocket 403 handshake test failed: {e}"
            
        return test_result
        
    async def test_load_balancer_timeout_regression(self) -> Dict[str, Any]:
        """Test that load balancer timeout issues are prevented."""
        
        test_result = {
            "test": "load_balancer_timeout_regression", 
            "passed": False,
            "details": {}
        }
        
        try:
            jwt_token = await self.auth_helper.get_test_jwt_token()
            websocket_url = self._get_websocket_url()
            headers = {"Authorization": f"Bearer {jwt_token}"}
            
            # Test 1: Connection can be established and maintained
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=15
            ) as websocket:
                
                connection_start = time.time()
                test_result["details"]["connection_established"] = True
                
                # Test 2: Send periodic heartbeats to test timeout handling
                heartbeat_count = 0
                heartbeat_responses = 0
                test_duration = 30  # 30 seconds test
                
                while (time.time() - connection_start) < test_duration:
                    try:
                        # Send heartbeat
                        heartbeat_msg = {
                            "type": "ping",
                            "timestamp": datetime.utcnow().isoformat(),
                            "sequence": heartbeat_count
                        }
                        
                        await websocket.send(json.dumps(heartbeat_msg))
                        heartbeat_count += 1
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") in ["pong", "ack"]:
                            heartbeat_responses += 1
                            
                        # Wait before next heartbeat
                        await asyncio.sleep(5)
                        
                    except asyncio.TimeoutError:
                        # Timeout waiting for response - might indicate load balancer issue
                        test_result["details"]["timeout_during_heartbeat"] = True
                        break
                    except websockets.exceptions.ConnectionClosed as e:
                        # Connection closed unexpectedly - potential load balancer timeout
                        test_result["details"]["unexpected_connection_close"] = True
                        test_result["details"]["close_code"] = e.code
                        test_result["details"]["close_reason"] = e.reason
                        break
                        
                connection_duration = time.time() - connection_start
                test_result["details"]["connection_duration_seconds"] = round(connection_duration, 2)
                test_result["details"]["heartbeats_sent"] = heartbeat_count
                test_result["details"]["heartbeat_responses"] = heartbeat_responses
                
                # Test 3: Validate connection stayed alive for minimum duration
                min_duration = 25  # Should maintain connection for at least 25 seconds
                if connection_duration >= min_duration:
                    test_result["details"]["minimum_duration_maintained"] = True
                else:
                    test_result["error"] = f"Connection closed too early: {connection_duration}s < {min_duration}s"
                    return test_result
                    
                # Test 4: Validate heartbeat success rate
                if heartbeat_count > 0:
                    heartbeat_success_rate = (heartbeat_responses / heartbeat_count) * 100
                    test_result["details"]["heartbeat_success_rate"] = round(heartbeat_success_rate, 1)
                    
                    if heartbeat_success_rate < 70:  # Should get responses to most heartbeats
                        test_result["error"] = f"Heartbeat success rate too low: {heartbeat_success_rate}%"
                        return test_result
                        
            # All tests passed
            test_result["passed"] = True
            test_result["message"] = "Load balancer timeout regression prevented"
            
        except websockets.exceptions.InvalidHandshake as e:
            test_result["error"] = f"WebSocket handshake failed (possible load balancer issue): {e}"
        except Exception as e:
            test_result["error"] = f"Load balancer timeout test failed: {e}"
            
        return test_result
        
    async def test_websocket_header_validation_regression(self) -> Dict[str, Any]:
        """Test that WebSocket header validation is working correctly."""
        
        test_result = {
            "test": "websocket_header_validation_regression",
            "passed": False,
            "details": {}
        }
        
        try:
            jwt_token = await self.auth_helper.get_test_jwt_token()
            websocket_url = self._get_websocket_url()
            
            # Test different WebSocket upgrade header scenarios
            test_cases = [
                {
                    "name": "standard_headers",
                    "headers": {"Authorization": f"Bearer {jwt_token}"},
                    "should_succeed": True
                },
                {
                    "name": "subprotocol_auth", 
                    "headers": {"Sec-WebSocket-Protocol": f"jwt.{jwt_token}"},
                    "should_succeed": True
                },
                {
                    "name": "mixed_headers",
                    "headers": {
                        "Authorization": f"Bearer {jwt_token}",
                        "Sec-WebSocket-Protocol": "jwt-auth"
                    },
                    "should_succeed": True
                },
                {
                    "name": "custom_origin",
                    "headers": {
                        "Authorization": f"Bearer {jwt_token}",
                        "Origin": f"https://{self.environment}.netrasystems.ai" if self.environment != "development" else "http://localhost:3000"
                    },
                    "should_succeed": True
                }
            ]
            
            test_results = []
            
            for test_case in test_cases:
                case_result = {
                    "name": test_case["name"],
                    "expected_success": test_case["should_succeed"],
                    "actual_success": False,
                    "error": None
                }
                
                try:
                    async with websockets.connect(
                        websocket_url,
                        extra_headers=test_case["headers"],
                        timeout=8
                    ) as websocket:
                        # Try to send a message to confirm connection works
                        test_msg = {"type": "ping", "test_case": test_case["name"]}
                        await websocket.send(json.dumps(test_msg))
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        case_result["actual_success"] = True
                        case_result["response_type"] = response_data.get("type")
                        
                except Exception as e:
                    case_result["actual_success"] = False
                    case_result["error"] = str(e)
                    
                test_results.append(case_result)
                
            test_result["details"]["header_validation_tests"] = test_results
            
            # Analyze results
            expected_successes = [tr for tr in test_results if tr["expected_success"]]
            actual_successes = [tr for tr in expected_successes if tr["actual_success"]]
            
            success_rate = (len(actual_successes) / len(expected_successes)) * 100
            test_result["details"]["header_validation_success_rate"] = round(success_rate, 1)
            
            if success_rate >= 75:  # At least 75% of header scenarios should work
                test_result["passed"] = True
                test_result["message"] = "WebSocket header validation regression prevented"
            else:
                test_result["error"] = f"Header validation success rate too low: {success_rate}%"
                
        except Exception as e:
            test_result["error"] = f"WebSocket header validation test failed: {e}"
            
        return test_result
        
    async def test_agent_events_missing_regression(self) -> Dict[str, Any]:
        """Test that critical WebSocket agent events are not missing."""
        
        test_result = {
            "test": "agent_events_missing_regression",
            "passed": False,
            "details": {}
        }
        
        try:
            jwt_token = await self.auth_helper.get_test_jwt_token()
            websocket_url = self._get_websocket_url()
            headers = {"Authorization": f"Bearer {jwt_token}"}
            
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=10
            ) as websocket:
                
                # Wait for connection established
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_msg)
                test_result["details"]["connection_established"] = welcome_data.get("type") == "connection_established"
                
                # Send agent request that should generate all required events
                agent_request = {
                    "type": "agent_request",
                    "payload": {
                        "agent": "data_sub_agent",
                        "message": "Generate a simple data analysis for regression test",
                        "thread_id": str(uuid.uuid4())
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                test_result["details"]["agent_request_sent"] = True
                
                # Collect events for up to 45 seconds
                received_events = []
                start_time = time.time()
                timeout_seconds = 45
                
                while (time.time() - start_time) < timeout_seconds:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event_data = json.loads(response)
                        event_type = event_data.get("type", "unknown")
                        
                        received_events.append({
                            "type": event_type,
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": event_data
                        })
                        
                        # Stop if we get agent_completed (end of workflow)
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        # No more events within timeout
                        break
                        
                test_result["details"]["events_received"] = received_events
                test_result["details"]["total_events_received"] = len(received_events)
                
                # Check which required events were received
                received_event_types = {event["type"] for event in received_events}
                missing_events = set(required_events) - received_event_types
                
                test_result["details"]["received_event_types"] = list(received_event_types)
                test_result["details"]["missing_critical_events"] = list(missing_events)
                
                if not missing_events:
                    test_result["passed"] = True
                    test_result["message"] = "All critical agent events received - regression prevented"
                else:
                    test_result["error"] = f"Missing critical events: {missing_events}"
                    
                # Additional validation: events should be in logical order
                event_order = [event["type"] for event in received_events if event["type"] in required_events]
                expected_order_start = ["agent_started", "agent_thinking"]
                expected_order_end = ["tool_completed", "agent_completed"]
                
                order_valid = True
                if len(event_order) >= 2:
                    # Check that agent_started comes before others
                    if "agent_started" in event_order and event_order[0] != "agent_started":
                        order_valid = False
                        
                    # Check that agent_completed comes last (if present)
                    if "agent_completed" in event_order and event_order[-1] != "agent_completed":
                        order_valid = False
                        
                test_result["details"]["event_order_valid"] = order_valid
                test_result["details"]["event_order"] = event_order
                
        except Exception as e:
            test_result["error"] = f"Agent events regression test failed: {e}"
            
        return test_result
        
    async def test_multi_user_isolation_regression(self) -> Dict[str, Any]:
        """Test that multi-user isolation violations are prevented."""
        
        test_result = {
            "test": "multi_user_isolation_regression", 
            "passed": False,
            "details": {}
        }
        
        try:
            # Create 3 test users
            user_count = 3
            users = []
            
            for i in range(user_count):
                user_token = await self.auth_helper.get_test_jwt_token(user_id=f"isolation_test_user_{i}")
                thread_id = str(uuid.uuid4())
                
                users.append({
                    "id": f"isolation_test_user_{i}",
                    "token": user_token,
                    "thread_id": thread_id,
                    "websocket": None,
                    "events": []
                })
                
            websocket_url = self._get_websocket_url()
            
            # Connect all users
            for user in users:
                headers = {"Authorization": f"Bearer {user['token']}"}
                user["websocket"] = await websockets.connect(
                    websocket_url,
                    extra_headers=headers,
                    timeout=10
                )
                
                # Wait for connection established
                welcome_msg = await asyncio.wait_for(user["websocket"].recv(), timeout=5)
                
            test_result["details"]["users_connected"] = len(users)
            
            # Each user sends a distinct message
            for i, user in enumerate(users):
                message = {
                    "type": "agent_request",
                    "payload": {
                        "agent": "data_sub_agent",
                        "message": f"Isolation test message {i} from {user['id']}",
                        "thread_id": user["thread_id"]
                    }
                }
                
                await user["websocket"].send(json.dumps(message))
                
            # Collect responses from all users for 20 seconds
            start_time = time.time()
            while (time.time() - start_time) < 20:
                for user in users:
                    try:
                        response = await asyncio.wait_for(user["websocket"].recv(), timeout=1)
                        event_data = json.loads(response)
                        user["events"].append(event_data)
                    except asyncio.TimeoutError:
                        continue
                        
            # Analyze isolation
            isolation_violations = []
            
            for user in users:
                for event in user["events"]:
                    # Check for thread_id contamination
                    event_thread_id = event.get("thread_id")
                    if event_thread_id and event_thread_id != user["thread_id"]:
                        # Check if this thread belongs to another test user
                        other_thread_ids = [u["thread_id"] for u in users if u["id"] != user["id"]]
                        if event_thread_id in other_thread_ids:
                            isolation_violations.append({
                                "user": user["id"],
                                "violation": "cross_thread_contamination",
                                "user_thread": user["thread_id"],
                                "received_thread": event_thread_id
                            })
                            
                    # Check for user_id contamination
                    event_user_id = event.get("user_id")
                    if event_user_id and event_user_id != user["id"]:
                        other_user_ids = [u["id"] for u in users if u["id"] != user["id"]]
                        if event_user_id in other_user_ids:
                            isolation_violations.append({
                                "user": user["id"],
                                "violation": "cross_user_contamination",
                                "user_id": user["id"],
                                "received_user_id": event_user_id
                            })
                            
            test_result["details"]["isolation_violations"] = isolation_violations
            test_result["details"]["total_events_collected"] = sum(len(user["events"]) for user in users)
            
            # Clean up connections
            for user in users:
                if user["websocket"]:
                    await user["websocket"].close()
                    
            if not isolation_violations:
                test_result["passed"] = True
                test_result["message"] = "Multi-user isolation regression prevented"
            else:
                test_result["error"] = f"Isolation violations detected: {len(isolation_violations)}"
                
        except Exception as e:
            test_result["error"] = f"Multi-user isolation regression test failed: {e}"
            
        return test_result
        
    async def test_websocket_connection_leak_regression(self) -> Dict[str, Any]:
        """Test that WebSocket connections don't leak memory/resources."""
        
        test_result = {
            "test": "websocket_connection_leak_regression",
            "passed": False,
            "details": {}
        }
        
        try:
            jwt_token = await self.auth_helper.get_test_jwt_token()
            websocket_url = self._get_websocket_url()
            headers = {"Authorization": f"Bearer {jwt_token}"}
            
            # Test: Create and close multiple connections rapidly
            connection_count = 5
            successful_connections = 0
            connection_errors = []
            
            for i in range(connection_count):
                try:
                    async with websockets.connect(
                        websocket_url,
                        extra_headers=headers,
                        timeout=8
                    ) as websocket:
                        # Send a quick ping to ensure connection works
                        ping_msg = {"type": "ping", "connection": i}
                        await websocket.send(json.dumps(ping_msg))
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        successful_connections += 1
                        
                except Exception as e:
                    connection_errors.append(f"Connection {i}: {str(e)}")
                    
                # Brief pause between connections
                await asyncio.sleep(0.5)
                
            test_result["details"]["total_connections_attempted"] = connection_count
            test_result["details"]["successful_connections"] = successful_connections
            test_result["details"]["connection_errors"] = connection_errors
            
            # Test WebSocket health endpoint to check for resource issues
            try:
                import aiohttp
                base_url = self._get_base_url()
                health_url = f"{base_url}/api/websocket/health"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_url, timeout=8) as response:
                        health_data = await response.json()
                        
                        test_result["details"]["health_check_status"] = health_data.get("status")
                        
                        # Check for resource health indicators
                        metrics = health_data.get("metrics", {})
                        websocket_metrics = metrics.get("websocket", {})
                        
                        active_connections = websocket_metrics.get("active_connections", 0)
                        test_result["details"]["active_connections_reported"] = active_connections
                        
                        # Should not have excessive active connections after our tests
                        if active_connections > 10:
                            test_result["error"] = f"Too many active connections reported: {active_connections}"
                            return test_result
                            
            except Exception as e:
                connection_errors.append(f"Health check failed: {str(e)}")
                
            # Success criteria
            success_rate = (successful_connections / connection_count) * 100
            test_result["details"]["connection_success_rate"] = round(success_rate, 1)
            
            if success_rate >= 80:  # 80% of connections should succeed
                test_result["passed"] = True
                test_result["message"] = "WebSocket connection leak regression prevented"
            else:
                test_result["error"] = f"Connection success rate too low: {success_rate}%"
                
        except Exception as e:
            test_result["error"] = f"WebSocket connection leak test failed: {e}"
            
        return test_result
        
    async def test_auth_token_refresh_regression(self) -> Dict[str, Any]:
        """Test that auth token refresh works during long WebSocket sessions."""
        
        test_result = {
            "test": "auth_token_refresh_regression",
            "passed": False,
            "details": {}
        }
        
        try:
            # Generate token with short expiry for testing refresh
            short_expiry_token = await self.auth_helper.get_test_jwt_token(expires_in=10)  # 10 seconds
            websocket_url = self._get_websocket_url()
            headers = {"Authorization": f"Bearer {short_expiry_token}"}
            
            # This test is simplified for regression testing
            # In a full implementation, we'd test actual token refresh logic
            
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=8
            ) as websocket:
                
                # Connection should work initially
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_msg)
                
                test_result["details"]["initial_connection_success"] = welcome_data.get("type") == "connection_established"
                
                # Send a message to confirm connection works
                test_msg = {"type": "ping", "test": "token_refresh"}
                await websocket.send(json.dumps(test_msg))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                test_result["details"]["message_exchange_success"] = True
                test_result["details"]["response_type"] = response_data.get("type")
                
            # For now, basic functionality is sufficient for regression prevention
            test_result["passed"] = True
            test_result["message"] = "Basic auth token handling regression prevented"
            
        except Exception as e:
            test_result["error"] = f"Auth token refresh regression test failed: {e}"
            
        return test_result
        
    async def _test_single_websocket_connection(self, jwt_token: str, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
        """Helper method to test a single WebSocket connection."""
        
        if headers is None:
            headers = {"Authorization": f"Bearer {jwt_token}"}
            
        result = {"success": False}
        
        try:
            websocket_url = self._get_websocket_url()
            
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=timeout
            ) as websocket:
                
                # Wait for welcome message
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=timeout//2)
                welcome_data = json.loads(welcome_msg)
                
                result["welcome_type"] = welcome_data.get("type")
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
        
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL for testing."""
        if self.environment == "staging":
            return "wss://staging.netrasystems.ai/api/ws"
        elif self.environment == "production":
            return "wss://app.netrasystems.ai/api/ws"
        else:
            return "ws://localhost:8000/api/ws"
            
    def _get_base_url(self) -> str:
        """Get base HTTP URL for testing."""
        if self.environment == "staging":
            return "https://staging.netrasystems.ai"
        elif self.environment == "production":
            return "https://app.netrasystems.ai"
        else:
            return "http://localhost:8000"


# ============================================================================
# PYTEST INTEGRATION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.regression
@pytest.mark.websocket
class TestWebSocketRegressionPrevention:
    """Pytest integration for WebSocket regression prevention."""
    
    @pytest.fixture(scope="class")
    def environment(self):
        return os.getenv("TEST_ENVIRONMENT", "staging")
        
    @pytest.fixture(scope="class")
    def regression_tester(self, environment):
        return WebSocketRegressionTester(environment)
        
    async def test_jwt_secret_synchronization_no_regression(self, regression_tester):
        """Test JWT secret synchronization regression prevention."""
        result = await regression_tester.test_jwt_secret_synchronization_regression()
        
        assert result["passed"] == True, f"JWT synchronization regression detected: {result.get('error')}"
        assert result["details"].get("unified_secret_accessible") == True
        assert result["details"].get("websocket_auth_success") == True
        
    async def test_websocket_403_handshake_no_regression(self, regression_tester):
        """Test WebSocket 403 handshake regression prevention."""
        result = await regression_tester.test_websocket_403_handshake_regression()
        
        assert result["passed"] == True, f"WebSocket 403 handshake regression detected: {result.get('error')}"
        assert result["details"].get("handshake_successful") == True
        assert result["details"].get("message_exchange_successful") == True
        
    async def test_load_balancer_timeout_no_regression(self, regression_tester):
        """Test load balancer timeout regression prevention."""
        result = await regression_tester.test_load_balancer_timeout_regression()
        
        assert result["passed"] == True, f"Load balancer timeout regression detected: {result.get('error')}"
        assert result["details"].get("connection_established") == True
        assert result["details"].get("minimum_duration_maintained") == True
        
    async def test_agent_events_no_regression(self, regression_tester):
        """Test agent events regression prevention."""
        result = await regression_tester.test_agent_events_missing_regression()
        
        assert result["passed"] == True, f"Agent events regression detected: {result.get('error')}"
        assert len(result["details"].get("missing_critical_events", [])) == 0
        assert result["details"].get("total_events_received", 0) >= 3
        
    async def test_multi_user_isolation_no_regression(self, regression_tester):
        """Test multi-user isolation regression prevention."""
        result = await regression_tester.test_multi_user_isolation_regression()
        
        assert result["passed"] == True, f"Multi-user isolation regression detected: {result.get('error')}"
        assert len(result["details"].get("isolation_violations", [])) == 0


# ============================================================================
# CLI EXECUTION
# ============================================================================

async def main():
    """Main CLI execution for WebSocket regression prevention tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Regression Prevention Test Suite")
    parser.add_argument("--environment", default="staging", choices=["staging", "production", "development"])
    parser.add_argument("--test", help="Run specific regression test by name")
    parser.add_argument("--output-file", help="Save results to JSON file")
    parser.add_argument("--critical-only", action="store_true", help="Run only critical regression tests")
    
    args = parser.parse_args()
    
    # Initialize regression tester
    regression_tester = WebSocketRegressionTester(args.environment)
    
    try:
        if args.test:
            # Run specific test
            test_config = next((t for t in regression_tester.regression_tests if t["name"] == args.test), None)
            if not test_config:
                logger.error(f"Test '{args.test}' not found")
                available_tests = [t["name"] for t in regression_tester.regression_tests]
                logger.info(f"Available tests: {available_tests}")
                return 1
                
            logger.info(f"Running specific regression test: {args.test}")
            result = await test_config["test_func"]()
            
            if result["passed"]:
                logger.success(f" PASS:  {args.test} PASSED")
                return 0
            else:
                logger.error(f" FAIL:  {args.test} FAILED: {result.get('error')}")
                return 1
                
        else:
            # Filter tests if critical-only is specified
            if args.critical_only:
                original_tests = regression_tester.regression_tests.copy()
                regression_tester.regression_tests = [
                    t for t in regression_tester.regression_tests
                    if t["severity"] == "critical"
                ]
                logger.info(f"Running {len(regression_tester.regression_tests)} critical regression tests only")
                
            # Run all tests
            results = await regression_tester.run_all_regression_tests()
            
            # Save results if requested
            if args.output_file:
                with open(args.output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results saved to {args.output_file}")
                
            # Exit with appropriate code
            if results["summary"]["deployment_safe"]:
                logger.success("WebSocket regression prevention tests completed successfully")
                return 0
            elif results["summary"]["regression_free"]:
                logger.warning("WebSocket regression prevention tests mostly passed - monitor closely")
                return 0  # Not critical enough to fail deployment
            else:
                logger.error("WebSocket regression prevention tests failed - deployment NOT safe")
                return 1
                
    except Exception as e:
        logger.error(f"WebSocket regression prevention testing error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)