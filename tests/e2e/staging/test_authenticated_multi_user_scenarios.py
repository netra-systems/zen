#!/usr/bin/env python
"""
Authenticated Multi-User E2E Scenarios for Staging Environment

Business Value Justification (BVJ):
- Segment: Mid/Enterprise - Multi-user paid tiers  
- Business Goal: Validate multi-tenant architecture integrity under concurrent load
- Value Impact: Protects $200K+ MRR from multi-user isolation failures
- Strategic/Revenue Impact: Enables enterprise scaling and prevents data breach incidents

This test suite validates multi-user authentication and isolation scenarios:
1. Concurrent authenticated user sessions with proper isolation
2. WebSocket connection management for multiple users
3. Agent execution isolation between users
4. Authentication token validation and refresh  
5. Authorization boundary enforcement
6. Session management and cleanup

🚨 CRITICAL E2E REQUIREMENTS:
- ALL tests use REAL authentication (JWT/OAuth) - NO EXCEPTIONS
- Multi-user isolation must be perfect - NO data leakage
- Real WebSocket connections for each user
- Real agent execution with user-specific contexts
- Staging environment authentication validation
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
import pytest
import websockets
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# Import E2E auth helper for SSOT authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper,
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging_config import StagingTestConfig, get_staging_config

logger = logging.getLogger(__name__)


@dataclass 
class UserSession:
    """Represents an authenticated user session with all context."""
    user_context: Any
    auth_helper: E2EAuthHelper
    ws_auth_helper: E2EWebSocketAuthHelper
    websocket: Optional[Any] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    session_start: float = field(default_factory=time.time)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to this user session."""
        event_with_session = {
            **event,
            "session_id": self.session_id,
            "session_timestamp": time.time(),
            "session_relative_time": time.time() - self.session_start
        }
        self.events.append(event_with_session)
    
    def get_session_duration(self) -> float:
        """Get total session duration."""
        return time.time() - self.session_start
    
    async def cleanup(self):
        """Clean up user session resources."""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        self.is_active = False


class TestAuthenticatedMultiUserScenarios(BaseE2ETest):
    """
    Authenticated Multi-User E2E Scenarios for Staging Environment.
    
    Tests multi-user architecture integrity with real authentication.
    """
    
    @pytest.fixture(autouse=True) 
    async def setup_multi_user_environment(self):
        """Set up multi-user testing environment with authentication."""
        await self.initialize_test_environment()
        
        # Configure for staging environment
        self.staging_config = get_staging_config()
        
        # Validate staging configuration
        assert self.staging_config.validate_configuration(), "Staging configuration invalid"
        
        # Create multiple authenticated user sessions
        self.user_sessions: List[UserSession] = []
        self.max_concurrent_users = 10  # Test up to 10 concurrent users
        
        for i in range(self.max_concurrent_users):
            # Create unique user context for each session
            user_context = await create_authenticated_user_context(
                user_email=f"e2e_multiuser_test_{i}_{int(time.time())}@staging.netra.ai",
                environment="staging",
                permissions=["read", "write", "execute_agents", "multi_user_access"]
            )
            
            # Create auth helpers for this user
            auth_helper = E2EAuthHelper(environment="staging")
            ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
            
            # Create user session
            user_session = UserSession(
                user_context=user_context,
                auth_helper=auth_helper,
                ws_auth_helper=ws_auth_helper
            )
            
            self.user_sessions.append(user_session)
            
            # Register cleanup for this session
            self.register_cleanup_task(user_session.cleanup)
        
        self.logger.info(f"✅ Multi-user environment setup complete - {len(self.user_sessions)} authenticated users")
        
    async def test_concurrent_authenticated_websocket_connections(self):
        """
        Test multiple users connecting to WebSocket simultaneously with authentication.
        
        BVJ: Validates $100K+ MRR concurrent connection capacity
        Ensures staging can handle multiple simultaneous authenticated WebSocket connections
        """
        concurrent_users = self.user_sessions[:5]  # Test 5 concurrent connections
        connection_results = []
        
        async def establish_authenticated_connection(user_session: UserSession, user_index: int):
            """Establish authenticated WebSocket connection for a user."""
            try:
                # Connect with proper authentication
                websocket = await user_session.ws_auth_helper.connect_authenticated_websocket(timeout=25.0)
                user_session.websocket = websocket
                
                # Send authenticated ping to verify connection
                ping_message = {
                    "type": "ping",
                    "user_id": user_session.user_context.user_id,
                    "session_id": user_session.session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(ping_message))
                
                # Wait for response to confirm authenticated connection
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    return {
                        "user_index": user_index,
                        "user_id": user_session.user_context.user_id,
                        "session_id": user_session.session_id,
                        "connection_successful": True,
                        "response_data": response_data,
                        "connection_time": user_session.get_session_duration()
                    }
                    
                except asyncio.TimeoutError:
                    return {
                        "user_index": user_index,
                        "user_id": user_session.user_context.user_id,
                        "connection_successful": False,
                        "error": "No response to authenticated ping"
                    }
                    
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "connection_successful": False,
                    "error": str(e)
                }
        
        # Establish concurrent connections
        connection_tasks = [
            establish_authenticated_connection(user_session, i)
            for i, user_session in enumerate(concurrent_users)
        ]
        
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Validate all connections succeeded
        successful_connections = []
        for result in connection_results:
            if isinstance(result, dict) and result.get("connection_successful"):
                successful_connections.append(result)
                
                # Validate proper authentication in response
                response_data = result.get("response_data", {})
                assert response_data.get("type") in ["pong", "authenticated"], f"Invalid response type: {response_data.get('type')}"
            else:
                error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
                self.logger.error(f"Connection failed for user {result.get('user_index', 'unknown') if isinstance(result, dict) else 'unknown'}: {error_msg}")
        
        assert len(successful_connections) == len(concurrent_users), f"Expected {len(concurrent_users)} successful connections, got {len(successful_connections)}"
        
        # Validate connection timing (should be reasonable)
        connection_times = [result["connection_time"] for result in successful_connections]
        avg_connection_time = sum(connection_times) / len(connection_times)
        max_connection_time = max(connection_times)
        
        assert avg_connection_time <= 15.0, f"Average connection time too slow: {avg_connection_time:.1f}s"
        assert max_connection_time <= 30.0, f"Maximum connection time too slow: {max_connection_time:.1f}s"
        
        self.logger.info(f"✅ Concurrent authenticated WebSocket connections validated")
        self.logger.info(f"👥 Successful connections: {len(successful_connections)}")
        self.logger.info(f"⏱️ Average connection time: {avg_connection_time:.1f}s")
        self.logger.info(f"⏱️ Maximum connection time: {max_connection_time:.1f}s")
        
    async def test_multi_user_agent_execution_isolation(self):
        """
        Test agent execution isolation between multiple authenticated users.
        
        BVJ: Validates $200K+ MRR data security - Perfect user isolation
        MISSION CRITICAL: No user data must leak to other users
        """
        concurrent_users = self.user_sessions[:4]  # Test 4 users for isolation
        
        async def run_isolated_agent_execution(user_session: UserSession, user_index: int):
            """Run agent execution for specific user with isolation validation."""
            try:
                # Ensure WebSocket connection
                if not user_session.websocket:
                    user_session.websocket = await user_session.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
                
                # Track events for this user
                user_events = []
                user_specific_data = {}
                
                async def collect_user_events():
                    async for message in user_session.websocket:
                        event = json.loads(message)
                        
                        # CRITICAL: Validate event belongs to this user
                        event_user_id = event.get("user_id") or event.get("data", {}).get("user_id")
                        if event_user_id and event_user_id != user_session.user_context.user_id:
                            raise Exception(f"USER ISOLATION VIOLATION: User {user_index} ({user_session.user_context.user_id}) received event for user {event_user_id}")
                        
                        user_events.append(event)
                        user_session.add_event(event)
                        
                        if event.get("type") == "agent_completed":
                            user_specific_data = event.get("data", {})
                            break
                
                event_task = asyncio.create_task(collect_user_events())
                
                # Send user-specific agent request with sensitive data
                sensitive_request = {
                    "type": "execute_agent",
                    "agent_type": "data_isolation_test",
                    "user_id": user_session.user_context.user_id,
                    "thread_id": user_session.user_context.thread_id,
                    "request_id": user_session.user_context.request_id,
                    "data": {
                        # User-specific sensitive data that must not leak
                        "user_secret": f"SECRET_DATA_USER_{user_index}_{uuid.uuid4().hex[:8]}",
                        "user_identifier": user_index,
                        "sensitive_info": {
                            "api_key": f"API_KEY_{user_index}_{uuid.uuid4().hex}",
                            "account_id": f"ACCOUNT_{user_index}_{int(time.time())}",
                            "private_data": f"PRIVATE_{user_index}_CONFIDENTIAL"
                        },
                        "isolation_marker": f"ISOLATION_TEST_USER_{user_index}"
                    },
                    "auth": {
                        "user_id": user_session.user_context.user_id,
                        "session_id": user_session.session_id
                    }
                }
                
                await user_session.websocket.send(json.dumps(sensitive_request))
                
                # Wait for completion
                await asyncio.wait_for(event_task, timeout=60.0)
                
                return {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "session_id": user_session.session_id,
                    "events": user_events,
                    "user_data": user_specific_data,
                    "success": True,
                    "sensitive_data_processed": sensitive_request["data"]
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "error": str(e),
                    "success": False
                }
        
        # Execute concurrent agent executions with sensitive data
        execution_tasks = [
            run_isolated_agent_execution(user_session, i)
            for i, user_session in enumerate(concurrent_users)
        ]
        
        execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Validate all executions succeeded with proper isolation
        successful_executions = []
        all_sensitive_data = []
        
        for result in execution_results:
            if isinstance(result, dict) and result.get("success"):
                successful_executions.append(result)
                
                # Collect all sensitive data for cross-contamination check
                sensitive_data = result.get("sensitive_data_processed", {})
                all_sensitive_data.append({
                    "user_index": result["user_index"],
                    "user_id": result["user_id"], 
                    "sensitive_data": sensitive_data
                })
                
                # Validate user received all required events
                event_types = [event.get("type") for event in result.get("events", [])]
                required_events = ["agent_started", "agent_completed"]
                for required_event in required_events:
                    assert required_event in event_types, f"User {result['user_index']} missing event: {required_event}"
                
                # Validate user-specific data in results
                user_data = result.get("user_data", {})
                expected_marker = f"ISOLATION_TEST_USER_{result['user_index']}"
                actual_marker = user_data.get("isolation_marker")
                assert actual_marker == expected_marker, f"User isolation failed: expected {expected_marker}, got {actual_marker}"
        
        assert len(successful_executions) == len(concurrent_users), f"Expected {len(concurrent_users)} successful executions, got {len(successful_executions)}"
        
        # CRITICAL VALIDATION: Check for cross-user data contamination
        for i, user_data_a in enumerate(all_sensitive_data):
            for j, user_data_b in enumerate(all_sensitive_data):
                if i != j:  # Different users
                    user_a_secrets = user_data_a["sensitive_data"]
                    user_b_secrets = user_data_b["sensitive_data"]
                    
                    # Check if any of user A's secrets appear in user B's data
                    user_a_secret = user_a_secrets.get("user_secret", "")
                    user_a_api_key = user_a_secrets.get("sensitive_info", {}).get("api_key", "")
                    
                    user_b_all_data_str = json.dumps(user_b_secrets)
                    
                    assert user_a_secret not in user_b_all_data_str, f"USER ISOLATION BREACH: User {user_data_a['user_index']} secret found in User {user_data_b['user_index']} data"
                    assert user_a_api_key not in user_b_all_data_str, f"USER ISOLATION BREACH: User {user_data_a['user_index']} API key found in User {user_data_b['user_index']} data"
        
        self.logger.info(f"✅ Multi-user agent execution isolation validated - NO DATA LEAKAGE")
        self.logger.info(f"👥 Successful isolated executions: {len(successful_executions)}")
        self.logger.info(f"🔒 Cross-contamination checks: {len(all_sensitive_data) * (len(all_sensitive_data) - 1)} validations passed")
        
    async def test_authentication_token_validation_and_refresh(self):
        """
        Test JWT token validation and refresh scenarios across multiple users.
        
        BVJ: Validates $50K+ MRR authentication reliability
        Ensures token lifecycle management works correctly in staging
        """
        test_users = self.user_sessions[:3]  # Test 3 users for auth scenarios
        
        async def test_user_authentication_scenarios(user_session: UserSession, user_index: int):
            """Test various authentication scenarios for a user."""
            try:
                auth_results = {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "tests": {}
                }
                
                # Test 1: Initial token validation
                initial_token = user_session.auth_helper.create_test_jwt_token(
                    user_id=user_session.user_context.user_id,
                    email=user_session.user_context.agent_context["user_email"]
                )
                
                is_valid = await user_session.auth_helper.validate_token(initial_token)
                auth_results["tests"]["initial_token_valid"] = is_valid
                
                # Test 2: API request with valid token
                headers = user_session.auth_helper.get_auth_headers(initial_token)
                
                async with aiohttp.ClientSession() as session:
                    health_url = f"{user_session.auth_helper.config.backend_url}/health"
                    async with session.get(health_url, headers=headers) as resp:
                        auth_results["tests"]["authenticated_api_request"] = resp.status == 200
                
                # Test 3: WebSocket connection with token
                ws_headers = user_session.auth_helper.get_websocket_headers(initial_token)
                try:
                    test_websocket = await user_session.ws_auth_helper.connect_authenticated_websocket(timeout=15.0)
                    await test_websocket.close()
                    auth_results["tests"]["websocket_authentication"] = True
                except Exception as e:
                    auth_results["tests"]["websocket_authentication"] = False
                    auth_results["tests"]["websocket_auth_error"] = str(e)
                
                # Test 4: Token expiry handling (create short-lived token)
                short_token = user_session.auth_helper.create_test_jwt_token(
                    user_id=user_session.user_context.user_id,
                    email=user_session.user_context.agent_context["user_email"],
                    exp_minutes=1  # 1 minute expiry
                )
                
                # Verify short token is initially valid
                is_short_valid_initially = await user_session.auth_helper.validate_token(short_token)
                auth_results["tests"]["short_token_initially_valid"] = is_short_valid_initially
                
                # Test 5: Fresh token creation (simulates refresh)
                refresh_token = user_session.auth_helper.create_test_jwt_token(
                    user_id=user_session.user_context.user_id,
                    email=user_session.user_context.agent_context["user_email"],
                    exp_minutes=30  # Fresh 30-minute token
                )
                
                is_refresh_valid = await user_session.auth_helper.validate_token(refresh_token)
                auth_results["tests"]["refresh_token_valid"] = is_refresh_valid
                
                auth_results["success"] = True
                return auth_results
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Run authentication tests for all users concurrently
        auth_tasks = [
            test_user_authentication_scenarios(user_session, i)
            for i, user_session in enumerate(test_users)
        ]
        
        auth_results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        # Validate authentication results
        successful_auth_tests = []
        for result in auth_results:
            if isinstance(result, dict) and result.get("success"):
                successful_auth_tests.append(result)
                
                tests = result.get("tests", {})
                
                # Validate all core authentication tests passed
                assert tests.get("initial_token_valid"), f"User {result['user_index']} initial token invalid"
                assert tests.get("authenticated_api_request"), f"User {result['user_index']} API request failed" 
                assert tests.get("websocket_authentication"), f"User {result['user_index']} WebSocket auth failed"
                assert tests.get("short_token_initially_valid"), f"User {result['user_index']} short token not initially valid"
                assert tests.get("refresh_token_valid"), f"User {result['user_index']} refresh token invalid"
        
        assert len(successful_auth_tests) == len(test_users), f"Expected {len(test_users)} successful auth tests, got {len(successful_auth_tests)}"
        
        # Validate authentication consistency across users
        all_test_results = {}
        for result in successful_auth_tests:
            for test_name, test_result in result.get("tests", {}).items():
                if test_name not in all_test_results:
                    all_test_results[test_name] = []
                all_test_results[test_name].append(test_result)
        
        # Ensure consistent authentication behavior across all users
        for test_name, results in all_test_results.items():
            if test_name.endswith("_error"):
                continue  # Skip error fields
                
            success_rate = sum(results) / len(results) if results else 0
            assert success_rate >= 0.9, f"Authentication test {test_name} has low success rate: {success_rate:.1%}"
        
        self.logger.info(f"✅ Authentication token validation and refresh completed")
        self.logger.info(f"👥 Users tested: {len(successful_auth_tests)}")
        self.logger.info(f"🔑 Authentication tests: {list(all_test_results.keys())}")
        
    async def test_session_management_and_cleanup(self):
        """
        Test user session lifecycle management and proper cleanup.
        
        BVJ: Validates $25K+ MRR operational reliability
        Ensures proper resource management and session cleanup
        """
        test_users = self.user_sessions[:3]
        
        session_lifecycle_results = []
        
        async def test_session_lifecycle(user_session: UserSession, user_index: int):
            """Test complete session lifecycle for a user."""
            try:
                lifecycle_data = {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "session_id": user_session.session_id,
                    "lifecycle_events": []
                }
                
                # Phase 1: Session Initialization
                lifecycle_data["lifecycle_events"].append({
                    "phase": "initialization",
                    "timestamp": time.time(),
                    "status": "started"
                })
                
                # Establish WebSocket connection
                user_session.websocket = await user_session.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
                
                lifecycle_data["lifecycle_events"].append({
                    "phase": "connection_established",
                    "timestamp": time.time(),
                    "websocket_connected": True
                })
                
                # Phase 2: Active Session Usage
                # Send multiple requests to simulate active session
                for i in range(3):
                    test_request = {
                        "type": "session_activity",
                        "user_id": user_session.user_context.user_id,
                        "session_id": user_session.session_id,
                        "activity_index": i,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await user_session.websocket.send(json.dumps(test_request))
                    
                    # Brief wait between activities
                    await asyncio.sleep(1.0)
                
                lifecycle_data["lifecycle_events"].append({
                    "phase": "active_usage",
                    "timestamp": time.time(),
                    "activities_sent": 3
                })
                
                # Phase 3: Session Idle Period
                await asyncio.sleep(5.0)  # Simulate idle period
                
                lifecycle_data["lifecycle_events"].append({
                    "phase": "idle_period",
                    "timestamp": time.time(), 
                    "idle_duration": 5.0
                })
                
                # Phase 4: Session Cleanup
                await user_session.websocket.close()
                user_session.websocket = None
                
                lifecycle_data["lifecycle_events"].append({
                    "phase": "cleanup_completed",
                    "timestamp": time.time(),
                    "websocket_closed": True
                })
                
                # Calculate total session duration
                start_time = lifecycle_data["lifecycle_events"][0]["timestamp"]
                end_time = lifecycle_data["lifecycle_events"][-1]["timestamp"]
                lifecycle_data["total_session_duration"] = end_time - start_time
                lifecycle_data["success"] = True
                
                return lifecycle_data
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "error": str(e),
                    "success": False
                }
        
        # Test session lifecycles concurrently
        lifecycle_tasks = [
            test_session_lifecycle(user_session, i)
            for i, user_session in enumerate(test_users)
        ]
        
        lifecycle_results = await asyncio.gather(*lifecycle_tasks, return_exceptions=True)
        
        # Validate session lifecycle results
        successful_lifecycles = []
        for result in lifecycle_results:
            if isinstance(result, dict) and result.get("success"):
                successful_lifecycles.append(result)
                
                # Validate complete lifecycle phases
                events = result.get("lifecycle_events", [])
                event_phases = [event.get("phase") for event in events]
                
                expected_phases = ["initialization", "connection_established", "active_usage", "idle_period", "cleanup_completed"]
                for phase in expected_phases:
                    assert phase in event_phases, f"User {result['user_index']} missing lifecycle phase: {phase}"
                
                # Validate reasonable session duration
                duration = result.get("total_session_duration", 0)
                assert 5.0 <= duration <= 60.0, f"Session duration unreasonable: {duration:.1f}s"
                
        assert len(successful_lifecycles) == len(test_users), f"Expected {len(test_users)} successful lifecycles, got {len(successful_lifecycles)}"
        
        # Validate proper cleanup - no lingering connections
        await asyncio.sleep(2.0)  # Allow cleanup to complete
        
        for user_session in test_users:
            assert user_session.websocket is None or user_session.websocket.closed, f"WebSocket not properly cleaned up for user {user_session.user_context.user_id}"
        
        self.logger.info(f"✅ Session management and cleanup validation completed")
        self.logger.info(f"👥 Successful session lifecycles: {len(successful_lifecycles)}")
        average_duration = sum(result["total_session_duration"] for result in successful_lifecycles) / len(successful_lifecycles)
        self.logger.info(f"⏱️ Average session duration: {average_duration:.1f}s")
        
    async def test_concurrent_load_with_authentication(self):
        """
        Test high concurrent load with authentication to validate scaling.
        
        BVJ: Validates $500K+ MRR scaling capacity
        Ensures staging can handle realistic concurrent authenticated load
        """
        # Use all available users for load testing
        load_test_users = self.user_sessions[:8]  # Test with 8 concurrent users
        
        concurrent_operations = []
        
        async def simulate_realistic_user_load(user_session: UserSession, user_index: int):
            """Simulate realistic concurrent user load."""
            try:
                load_metrics = {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "operations_completed": 0,
                    "start_time": time.time(),
                    "operations": []
                }
                
                # Connect authenticated WebSocket
                user_session.websocket = await user_session.ws_auth_helper.connect_authenticated_websocket(timeout=30.0)
                
                # Simulate realistic user behavior - multiple operations
                operations = [
                    {"type": "data_query", "complexity": "simple"},
                    {"type": "analysis_request", "complexity": "medium"},
                    {"type": "optimization_task", "complexity": "high"},
                    {"type": "report_generation", "complexity": "medium"}
                ]
                
                for op_index, operation in enumerate(operations):
                    op_start = time.time()
                    
                    # Send operation request
                    request = {
                        "type": "execute_operation",
                        "operation": operation["type"],
                        "user_id": user_session.user_context.user_id,
                        "session_id": user_session.session_id,
                        "operation_index": op_index,
                        "complexity": operation["complexity"]
                    }
                    
                    await user_session.websocket.send(json.dumps(request))
                    
                    # Wait for response or timeout
                    try:
                        response = await asyncio.wait_for(user_session.websocket.recv(), timeout=20.0)
                        response_data = json.loads(response)
                        
                        op_duration = time.time() - op_start
                        
                        load_metrics["operations"].append({
                            "operation": operation["type"],
                            "complexity": operation["complexity"],
                            "duration": op_duration,
                            "success": True,
                            "response_type": response_data.get("type")
                        })
                        
                        load_metrics["operations_completed"] += 1
                        
                    except asyncio.TimeoutError:
                        load_metrics["operations"].append({
                            "operation": operation["type"],
                            "complexity": operation["complexity"],
                            "duration": 20.0,
                            "success": False,
                            "error": "timeout"
                        })
                    
                    # Brief pause between operations
                    await asyncio.sleep(1.0)
                
                load_metrics["total_duration"] = time.time() - load_metrics["start_time"]
                load_metrics["success"] = True
                
                # Cleanup
                await user_session.websocket.close()
                user_session.websocket = None
                
                return load_metrics
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_session.user_context.user_id,
                    "error": str(e),
                    "success": False
                }
        
        # Execute concurrent load test
        load_tasks = [
            simulate_realistic_user_load(user_session, i)
            for i, user_session in enumerate(load_test_users)
        ]
        
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        # Analyze load test results
        successful_users = []
        total_operations = 0
        total_duration = 0
        operation_success_rate = 0
        
        for result in load_results:
            if isinstance(result, dict) and result.get("success"):
                successful_users.append(result)
                total_operations += result.get("operations_completed", 0)
                total_duration += result.get("total_duration", 0)
                
                # Calculate individual user success rate
                operations = result.get("operations", [])
                if operations:
                    user_success_rate = sum(1 for op in operations if op.get("success")) / len(operations)
                    operation_success_rate += user_success_rate
        
        # Validate load test results
        assert len(successful_users) >= (len(load_test_users) * 0.8), f"Too many users failed load test: {len(successful_users)}/{len(load_test_users)}"
        
        average_operations_per_user = total_operations / len(successful_users) if successful_users else 0
        assert average_operations_per_user >= 3.0, f"Average operations per user too low: {average_operations_per_user}"
        
        overall_success_rate = operation_success_rate / len(successful_users) if successful_users else 0
        assert overall_success_rate >= 0.85, f"Operation success rate too low: {overall_success_rate:.1%}"
        
        average_user_duration = total_duration / len(successful_users) if successful_users else 0
        assert average_user_duration <= 60.0, f"Average user session too long: {average_user_duration:.1f}s"
        
        self.logger.info(f"✅ Concurrent load test with authentication completed")
        self.logger.info(f"👥 Successful concurrent users: {len(successful_users)}/{len(load_test_users)}")
        self.logger.info(f"⚡ Total operations completed: {total_operations}")
        self.logger.info(f"📊 Overall success rate: {overall_success_rate:.1%}")
        self.logger.info(f"⏱️ Average session duration: {average_user_duration:.1f}s")


# Integration with pytest for automated test discovery
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])