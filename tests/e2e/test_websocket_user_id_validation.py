"""
E2E TESTS - Complete WebSocket User ID Validation Bug Reproduction

These E2E tests validate complete end-to-end WebSocket flows with problematic user ID patterns
that currently cause "Invalid user_id format" errors in production-like scenarios.

Business Value Justification:
- Segment: All User Segments + Platform/Internal
- Business Goal: Bug Fix & Complete User Experience Reliability
- Value Impact: Ensures deployment/staging users can successfully connect via WebSocket for AI chat
- Strategic Impact: Prevents production outages caused by ID validation failures

ROOT CAUSE: Missing regex pattern ^e2e-[a-zA-Z]+-[a-zA-Z0-9_-]+$ in ID validation

CRITICAL BUG CONTEXT:
- Issue: WebSocket error "Invalid user_id format: e2e-staging_pipeline"
- End-to-End Impact: Complete WebSocket connection failure  ->  No AI chat capability
- GitHub Issue: https://github.com/netra-systems/netra-apex/issues/105

E2E SCOPE:
- REAL authentication (JWT/OAuth) - MANDATORY per CLAUDE.md
- REAL WebSocket connections to backend services  
- REAL database connections and user sessions
- REAL agent execution with WebSocket events
- NO MOCKS (except where explicitly noted for test isolation)

EXPECTED BEHAVIOR:
- Tests 1-2: MUST FAIL initially (proving complete end-to-end bug impact)
- Tests 3-4: MUST PASS (proving complete system works after fix)

CRITICAL: ALL E2E tests MUST use authentication - no exceptions per CLAUDE.md requirements.
"""

import pytest
import asyncio
import websockets
import json
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import httpx

# CRITICAL: E2E auth helper for MANDATORY authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EAuthConfig,
    create_authenticated_user
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

# Shared types that contain the bug
from shared.types.core_types import ensure_user_id, UserID
from shared.isolated_environment import get_env

# Agent execution for complete flow testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestWebSocketUserIDValidationE2E(BaseE2ETest):
    """
    E2E tests for complete WebSocket user ID validation bug reproduction.
    
    Tests the complete stack from authentication through WebSocket connection
    to agent execution with real services and databases.
    
    CRITICAL: Uses REAL authentication per CLAUDE.md E2E requirements.
    """
    
    @pytest.fixture
    def auth_config(self) -> E2EAuthConfig:
        """Create E2E auth configuration for testing."""
        return E2EAuthConfig(
            auth_service_url=get_env("TEST_AUTH_SERVICE_URL", "http://localhost:8083"),
            backend_url=get_env("TEST_BACKEND_URL", "http://localhost:8002"),  
            websocket_url=get_env("TEST_WEBSOCKET_URL", "ws://localhost:8002/ws"),
            test_user_email="e2e_validation_test@example.com",
            test_user_password="secure_test_password_123",
            timeout=30.0
        )
    
    @pytest.fixture
    def failing_deployment_users(self) -> List[Dict[str, str]]:
        """Deployment user patterns that currently fail E2E WebSocket flows."""
        return [
            {
                "user_id": "e2e-staging_pipeline",
                "email": "e2e-staging_pipeline@deployment.example.com",
                "environment": "staging"
            },
            {
                "user_id": "e2e-production_deploy", 
                "email": "e2e-production_deploy@deployment.example.com",
                "environment": "production"
            },
            {
                "user_id": "e2e-test_environment",
                "email": "e2e-test_environment@deployment.example.com", 
                "environment": "test"
            },
            {
                "user_id": "e2e-dev_pipeline_v2",
                "email": "e2e-dev_pipeline_v2@deployment.example.com",
                "environment": "development"  
            }
        ]
    
    @pytest.fixture
    def valid_deployment_users(self) -> List[Dict[str, str]]:
        """Valid user patterns for regression testing."""
        return [
            {
                "user_id": "test-user-regression",
                "email": "test-user-regression@example.com",
                "environment": "test"
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": "uuid-user@example.com", 
                "environment": "test"
            },
            {
                "user_id": "concurrent_user_99",
                "email": "concurrent_user_99@example.com",
                "environment": "test"
            }
        ]

    @pytest.mark.asyncio
    @pytest.mark.real_services  # Requires real backend services
    async def test_complete_chat_flow_e2e_staging_user(self, auth_config):
        """
        TEST 1: CRITICAL - Complete end-to-end chat flow with failing user pattern.
        
        This test MUST FAIL initially, proving the bug blocks complete user workflows.
        Tests: Authentication  ->  WebSocket Connection  ->  Agent Execution  ->  Chat Response
        
        EXPECTED: FAILURE (before fix) - WebSocket connection fails at user ID validation
        """
        failing_user_data = {
            "user_id": "e2e-staging_pipeline",
            "email": "e2e-staging_pipeline@deployment.example.com",
            "password": "secure_deployment_password"
        }
        
        # STEP 1: Create authenticated user (MANDATORY per CLAUDE.md)
        auth_helper = E2EAuthHelper(auth_config)
        
        try:
            # Create user with deployment pattern
            user_result = await create_authenticated_user(
                user_id=failing_user_data["user_id"],
                email=failing_user_data["email"], 
                password=failing_user_data["password"],
                auth_config=auth_config
            )
            
            assert user_result["authenticated"] is True
            assert user_result["user_id"] == failing_user_data["user_id"]
            jwt_token = user_result["token"]
            
        except Exception as e:
            if "Invalid user_id format" in str(e):
                pytest.fail(
                    f"CRITICAL: User creation failed for '{failing_user_data['user_id']}' "
                    f"due to ID validation bug: {e}. This blocks complete deployment workflows."
                )
            else:
                raise
        
        # STEP 2: Establish WebSocket connection with authentication
        websocket_url = f"{auth_config.websocket_url}?token={jwt_token}"
        
        try:
            async with websockets.connect(
                websocket_url,
                timeout=auth_config.timeout,
                extra_headers={"Authorization": f"Bearer {jwt_token}"}
            ) as websocket:
                
                # STEP 3: Send connection message  
                connection_msg = {
                    "type": "connection",
                    "data": {
                        "user_id": failing_user_data["user_id"],
                        "token": jwt_token,
                        "connection_id": f"e2e_test_{int(time.time())}"
                    }
                }
                
                await websocket.send(json.dumps(connection_msg))
                
                # Wait for connection confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                connection_result = json.loads(response)
                
                assert connection_result.get("status") == "connected"
                assert connection_result.get("user_id") == failing_user_data["user_id"]
                
                # STEP 4: Test agent execution via WebSocket
                agent_request = {
                    "type": "agent_execution",
                    "data": {
                        "message": "Test deployment user agent execution",
                        "agent_type": "data_agent",
                        "run_id": str(uuid.uuid4())
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # STEP 5: Verify WebSocket events are received
                events_received = []
                timeout_counter = 0
                max_timeout = 30  # 30 seconds for agent execution
                
                while timeout_counter < max_timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        event = json.loads(message)
                        events_received.append(event)
                        
                        # Check for completion
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        timeout_counter += 1
                        continue
                
                # Verify required WebSocket events were received
                event_types = [event.get("type") for event in events_received]
                required_events = ["agent_started", "agent_completed"]
                
                for required_event in required_events:
                    assert required_event in event_types, (
                        f"Required WebSocket event '{required_event}' not received. "
                        f"Events received: {event_types}"
                    )
                
                # If we reach here, the complete flow worked
                assert len(events_received) > 0, "No WebSocket events received during agent execution"
                
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                pytest.fail(
                    f"WebSocket authentication failed for user '{failing_user_data['user_id']}' "
                    f"due to user ID validation bug. This blocks deployment user workflows."
                )
            else:
                raise
        except ValueError as e:
            if "Invalid user_id format" in str(e):
                # This is the expected failure before the fix
                pytest.fail(
                    f"EXPECTED FAILURE CONFIRMED: Complete chat flow fails for deployment "
                    f"user '{failing_user_data['user_id']}' due to ID validation bug: {e}"
                )
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_agent_execution_with_deployment_users(
        self, failing_deployment_users, auth_config
    ):
        """
        TEST 2: Agent execution WebSocket events with multiple deployment user patterns.
        
        Tests that agent execution generates proper WebSocket events for deployment users.
        
        EXPECTED: SUCCESS after fix - all deployment users should work
        """
        auth_helper = E2EAuthHelper(auth_config)
        
        for user_data in failing_deployment_users[:2]:  # Test first 2 to avoid timeout
            user_id = user_data["user_id"]
            
            try:
                # Create authenticated deployment user
                user_result = await create_authenticated_user(
                    user_id=user_id,
                    email=user_data["email"],
                    password="deployment_password_123",
                    auth_config=auth_config
                )
                
                jwt_token = user_result["token"]
                
                # Test WebSocket connection and agent execution
                websocket_url = f"{auth_config.websocket_url}?token={jwt_token}"
                
                async with websockets.connect(
                    websocket_url,
                    timeout=15.0,
                    extra_headers={"Authorization": f"Bearer {jwt_token}"}
                ) as websocket:
                    
                    # Connect
                    connection_msg = {
                        "type": "connection", 
                        "data": {
                            "user_id": user_id,
                            "token": jwt_token,
                            "connection_id": f"deploy_test_{int(time.time())}"
                        }
                    }
                    
                    await websocket.send(json.dumps(connection_msg))
                    await websocket.recv()  # Connection confirmation
                    
                    # Execute simple agent task
                    agent_request = {
                        "type": "agent_execution",
                        "data": {
                            "message": f"Test execution for deployment user {user_id}",
                            "agent_type": "data_agent",
                            "run_id": str(uuid.uuid4())
                        }
                    }
                    
                    await websocket.send(json.dumps(agent_request))
                    
                    # Collect WebSocket events
                    events = []
                    timeout_count = 0
                    
                    while timeout_count < 20:  # 20 second timeout
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            event = json.loads(message)
                            events.append(event)
                            
                            if event.get("type") == "agent_completed":
                                break
                                
                        except asyncio.TimeoutError:
                            timeout_count += 1
                    
                    # Verify agent events were received
                    assert len(events) > 0, f"No events received for deployment user {user_id}"
                    
                    event_types = [e.get("type") for e in events]
                    assert "agent_started" in event_types, f"Missing agent_started event for {user_id}"
                    
            except Exception as e:
                if "Invalid user_id format" in str(e):
                    pytest.fail(
                        f"Deployment user '{user_id}' should work after fix but "
                        f"still fails with ID validation error: {e}"
                    )
                else:
                    raise

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_multi_user_websocket_connections(self, valid_deployment_users, auth_config):
        """
        TEST 3: REGRESSION PREVENTION - Multiple valid users with concurrent WebSocket connections.
        
        Ensures existing user patterns continue to work with concurrent connections.
        
        EXPECTED: SUCCESS (always)
        """
        auth_helper = E2EAuthHelper(auth_config)
        active_connections = []
        
        try:
            # Create multiple authenticated users
            authenticated_users = []
            
            for user_data in valid_deployment_users:
                user_result = await create_authenticated_user(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    password="regression_test_password",
                    auth_config=auth_config
                )
                authenticated_users.append(user_result)
            
            # Establish concurrent WebSocket connections
            for user_result in authenticated_users:
                websocket_url = f"{auth_config.websocket_url}?token={user_result['token']}"
                
                websocket = await websockets.connect(
                    websocket_url,
                    timeout=10.0,
                    extra_headers={"Authorization": f"Bearer {user_result['token']}"}
                )
                
                # Send connection message
                connection_msg = {
                    "type": "connection",
                    "data": {
                        "user_id": user_result["user_id"],
                        "token": user_result["token"],
                        "connection_id": f"regression_{int(time.time())}"
                    }
                }
                
                await websocket.send(json.dumps(connection_msg))
                response = await websocket.recv()
                connection_result = json.loads(response)
                
                assert connection_result.get("status") == "connected"
                assert connection_result.get("user_id") == user_result["user_id"]
                
                active_connections.append(websocket)
            
            # Verify all connections are stable
            assert len(active_connections) == len(valid_deployment_users)
            
        except Exception as e:
            pytest.fail(
                f"REGRESSION: Valid user patterns should work but failed: {e}"
            )
        finally:
            # Clean up connections
            for websocket in active_connections:
                try:
                    await websocket.close()
                except:
                    pass

    @pytest.mark.asyncio
    @pytest.mark.real_services 
    async def test_websocket_pipeline_end_to_end(self, auth_config):
        """
        TEST 4: Complete pipeline test simulating deployment environment.
        
        Tests the complete deployment pipeline workflow with WebSocket integration.
        
        EXPECTED: SUCCESS after fix
        """
        deployment_pipeline_user = {
            "user_id": "e2e-pipeline_deployment_final",
            "email": "pipeline_deployment@test.example.com",
            "password": "pipeline_secure_password_123"
        }
        
        auth_helper = E2EAuthHelper(auth_config)
        
        # PHASE 1: User Creation & Authentication
        user_result = await create_authenticated_user(
            user_id=deployment_pipeline_user["user_id"],
            email=deployment_pipeline_user["email"],
            password=deployment_pipeline_user["password"],
            auth_config=auth_config
        )
        
        assert user_result["authenticated"] is True
        jwt_token = user_result["token"]
        
        # PHASE 2: WebSocket Connection Establishment
        websocket_url = f"{auth_config.websocket_url}?token={jwt_token}"
        
        async with websockets.connect(
            websocket_url,
            timeout=15.0,
            extra_headers={"Authorization": f"Bearer {jwt_token}"}
        ) as websocket:
            
            # PHASE 3: Connection Handshake
            connection_msg = {
                "type": "connection",
                "data": {
                    "user_id": deployment_pipeline_user["user_id"],
                    "token": jwt_token,
                    "connection_id": f"pipeline_final_{int(time.time())}"
                }
            }
            
            await websocket.send(json.dumps(connection_msg))
            connection_response = await websocket.recv()
            connection_result = json.loads(connection_response)
            
            assert connection_result.get("status") == "connected"
            
            # PHASE 4: Pipeline Agent Execution Simulation
            pipeline_tasks = [
                {
                    "message": "Analyze deployment configuration",
                    "agent_type": "data_agent",
                    "expected_events": ["agent_started", "agent_thinking", "agent_completed"]
                },
                {
                    "message": "Validate system health",
                    "agent_type": "optimization_agent", 
                    "expected_events": ["agent_started", "agent_completed"]
                }
            ]
            
            for task in pipeline_tasks:
                # Send agent execution request
                agent_request = {
                    "type": "agent_execution",
                    "data": {
                        "message": task["message"],
                        "agent_type": task["agent_type"],
                        "run_id": str(uuid.uuid4())
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events for this task
                task_events = []
                timeout_count = 0
                
                while timeout_count < 25:  # 25 second timeout per task
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        event = json.loads(message)
                        task_events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        timeout_count += 1
                
                # Verify expected events were received
                event_types = [e.get("type") for e in task_events]
                
                for expected_event in task["expected_events"]:
                    assert expected_event in event_types, (
                        f"Pipeline task '{task['message']}' missing expected "
                        f"WebSocket event '{expected_event}'. Events: {event_types}"
                    )
        
        # If we reach here, the complete pipeline worked successfully
        assert True, "Complete pipeline deployment test succeeded"


if __name__ == "__main__":
    # Run with real services and verbose output
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short", 
        "-m", "real_services",
        "--real-services"
    ])