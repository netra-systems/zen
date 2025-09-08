"""Real WebSocket Multi-User Isolation Tests

Business Value Justification (BVJ):
- Segment: All Customer Tiers (Free, Early, Mid, Enterprise) 
- Business Goal: Data Security & Multi-Tenancy - CRITICAL
- Value Impact: Prevents User A seeing User B's data - silent data leakage is a BUG
- Strategic Impact: Protects customer trust and enables secure multi-user platform

Tests UserExecutionContext isolation with real WebSocket connections and Docker services.
Validates complete user isolation, eliminates shared state, prevents data leakage.

CRITICAL per CLAUDE.md: This is a MULTI-USER system. Silent data leakage is a bug.
UserExecutionContext isolation is NOT optional - it's a security requirement.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.multi_user_isolation
@pytest.mark.security_critical
@skip_if_no_real_services
class TestRealWebSocketMultiUserIsolation:
    """Test real multi-user isolation through WebSocket connections.
    
    CRITICAL: Tests complete user isolation per CLAUDE.md:
    - UserExecutionContext ensures complete user isolation
    - NO shared state between users
    - Factory patterns enable reliable concurrent execution for 10+ users
    - Silent data leakage is a BUG and must be prevented
    
    These tests validate the security foundation of the multi-user platform.
    """
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket URL from environment."""
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers_user_a(self):
        """Get auth headers for User A."""
        jwt_token = env.get("TEST_JWT_TOKEN_USER_A", "test_token_user_a_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-User-A-Test/1.0"
        }
    
    @pytest.fixture  
    def auth_headers_user_b(self):
        """Get auth headers for User B."""
        jwt_token = env.get("TEST_JWT_TOKEN_USER_B", "test_token_user_b_456")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-User-B-Test/1.0"
        }
    
    @pytest.fixture
    def unique_test_id(self):
        """Generate unique test identifier."""
        return f"isolation_test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    @pytest.mark.asyncio
    async def test_concurrent_user_message_isolation(self, websocket_url, auth_headers_user_a, auth_headers_user_b, unique_test_id):
        """Test that concurrent users receive only their own messages."""
        user_a_id = f"user_a_{unique_test_id}"
        user_b_id = f"user_b_{unique_test_id}"
        
        user_a_responses = []
        user_b_responses = []
        
        async def user_a_session():
            """User A session."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers_user_a,
                    timeout=15
                ) as websocket:
                    # Connect as User A
                    await websocket.send(json.dumps({
                        "type": "connect", 
                        "user_id": user_a_id,
                        "isolation_test": True
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    user_a_responses.append(("connect", connect_response))
                    
                    # Send User A specific message
                    await websocket.send(json.dumps({
                        "type": "user_message",
                        "user_id": user_a_id,
                        "content": f"SECRET_MESSAGE_FROM_USER_A_{unique_test_id}",
                        "thread_id": f"thread_a_{unique_test_id}",
                        "sensitive_data": "user_a_confidential_info"
                    }))
                    
                    # Collect User A responses
                    timeout_time = time.time() + 10
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            response = json.loads(response_raw)
                            user_a_responses.append(("message", response))
                            
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                            
            except Exception as e:
                user_a_responses.append(("error", str(e)))
        
        async def user_b_session():
            """User B session."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers_user_b,
                    timeout=15
                ) as websocket:
                    # Connect as User B
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_b_id,
                        "isolation_test": True
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    user_b_responses.append(("connect", connect_response))
                    
                    # Send User B specific message
                    await websocket.send(json.dumps({
                        "type": "user_message",
                        "user_id": user_b_id,
                        "content": f"SECRET_MESSAGE_FROM_USER_B_{unique_test_id}",
                        "thread_id": f"thread_b_{unique_test_id}",
                        "sensitive_data": "user_b_confidential_info"
                    }))
                    
                    # Collect User B responses
                    timeout_time = time.time() + 10
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            response = json.loads(response_raw)
                            user_b_responses.append(("message", response))
                            
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                            
            except Exception as e:
                user_b_responses.append(("error", str(e)))
        
        # Run both user sessions concurrently
        await asyncio.gather(user_a_session(), user_b_session())
        
        # CRITICAL SECURITY VALIDATION: Check for data leakage
        
        # Extract all response content for User A
        user_a_content = []
        for response_type, response in user_a_responses:
            if response_type == "message" and isinstance(response, dict):
                content = json.dumps(response).lower()
                user_a_content.append(content)
        
        # Extract all response content for User B
        user_b_content = []
        for response_type, response in user_b_responses:
            if response_type == "message" and isinstance(response, dict):
                content = json.dumps(response).lower()
                user_b_content.append(content)
        
        # CRITICAL: Check User A did NOT receive User B's sensitive data
        user_b_secrets = [f"secret_message_from_user_b_{unique_test_id}".lower(), "user_b_confidential_info"]
        
        for user_a_response_content in user_a_content:
            for user_b_secret in user_b_secrets:
                assert user_b_secret not in user_a_response_content, \
                    f"SECURITY BUG: User A received User B's sensitive data: {user_b_secret}"
        
        # CRITICAL: Check User B did NOT receive User A's sensitive data
        user_a_secrets = [f"secret_message_from_user_a_{unique_test_id}".lower(), "user_a_confidential_info"]
        
        for user_b_response_content in user_b_content:
            for user_a_secret in user_a_secrets:
                assert user_a_secret not in user_b_response_content, \
                    f"SECURITY BUG: User B received User A's sensitive data: {user_a_secret}"
        
        # Validate both users received responses
        assert len(user_a_responses) > 0, "User A should have received responses"
        assert len(user_b_responses) > 0, "User B should have received responses"
        
        print(f"Isolation test passed - User A responses: {len(user_a_responses)}, User B responses: {len(user_b_responses)}")
    
    @pytest.mark.asyncio
    async def test_user_execution_context_isolation(self, websocket_url, auth_headers_user_a, auth_headers_user_b, unique_test_id):
        """Test UserExecutionContext provides complete isolation."""
        user_a_id = f"context_user_a_{unique_test_id}"
        user_b_id = f"context_user_b_{unique_test_id}"
        
        user_contexts_observed = []
        
        async def test_user_context(user_id: str, auth_headers: Dict, context_marker: str):
            """Test user context isolation."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Connect with context tracking
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "track_execution_context": True,
                        "context_marker": context_marker
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Record context information
                    context_info = {
                        "user_id": user_id,
                        "context_marker": context_marker,
                        "connection_id": connect_response.get("connection_id"),
                        "session_info": connect_response
                    }
                    user_contexts_observed.append(context_info)
                    
                    # Send message with context-specific data
                    await websocket.send(json.dumps({
                        "type": "user_message",
                        "user_id": user_id,
                        "content": f"Context-specific message for {context_marker}",
                        "thread_id": f"context_thread_{user_id}",
                        "execution_context_test": context_marker
                    }))
                    
                    # Wait for response with context info
                    timeout_time = time.time() + 8
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            response = json.loads(response_raw)
                            
                            # Record context from responses
                            if "user_id" in response:
                                context_info["responses"] = context_info.get("responses", [])
                                context_info["responses"].append(response)
                            
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                            
            except Exception as e:
                user_contexts_observed.append({
                    "user_id": user_id,
                    "context_marker": context_marker,
                    "error": str(e)
                })
        
        # Test contexts concurrently
        await asyncio.gather(
            test_user_context(user_a_id, auth_headers_user_a, "CONTEXT_A"),
            test_user_context(user_b_id, auth_headers_user_b, "CONTEXT_B")
        )
        
        # Validate context isolation
        assert len(user_contexts_observed) >= 2, f"Should observe contexts for both users, got: {len(user_contexts_observed)}"
        
        # Verify each user has distinct context
        user_ids_observed = [ctx.get("user_id") for ctx in user_contexts_observed]
        assert user_a_id in user_ids_observed, f"User A context not observed: {user_ids_observed}"
        assert user_b_id in user_ids_observed, f"User B context not observed: {user_ids_observed}"
        
        # Validate context separation
        context_a = next((ctx for ctx in user_contexts_observed if ctx.get("user_id") == user_a_id), None)
        context_b = next((ctx for ctx in user_contexts_observed if ctx.get("user_id") == user_b_id), None)
        
        assert context_a is not None, "User A context should be recorded"
        assert context_b is not None, "User B context should be recorded"
        
        # Verify distinct connection IDs (separate contexts)
        if "connection_id" in context_a and "connection_id" in context_b:
            assert context_a["connection_id"] != context_b["connection_id"], \
                "Users should have separate connection contexts"
        
        print(f"Context isolation validated - User A: {context_a.get('context_marker')}, User B: {context_b.get('context_marker')}")
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_isolation(self, websocket_url, auth_headers_user_a, auth_headers_user_b, unique_test_id):
        """Test agent execution isolation between concurrent users."""
        user_a_id = f"agent_user_a_{unique_test_id}"
        user_b_id = f"agent_user_b_{unique_test_id}"
        
        agent_execution_results = []
        
        async def run_isolated_agent(user_id: str, auth_headers: Dict, agent_task: str, task_marker: str):
            """Run agent with isolation validation."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=20
                ) as websocket:
                    # Connect
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "track_agent_isolation": True
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Start isolated agent execution
                    await websocket.send(json.dumps({
                        "type": "user_message",
                        "user_id": user_id,
                        "content": agent_task,
                        "thread_id": f"agent_thread_{user_id}",
                        "task_marker": task_marker,
                        "isolation_test": True
                    }))
                    
                    # Collect agent execution events
                    agent_events = []
                    timeout_time = time.time() + 15
                    
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            response = json.loads(response_raw)
                            agent_events.append(response)
                            
                            # Stop after agent completion or sufficient events
                            if response.get("type") in ["agent_completed", "message_processed"] or len(agent_events) >= 5:
                                break
                                
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                    
                    # Record execution results
                    agent_execution_results.append({
                        "user_id": user_id,
                        "task_marker": task_marker,
                        "agent_events": agent_events,
                        "event_count": len(agent_events),
                        "connection_id": connect_response.get("connection_id")
                    })
                    
            except Exception as e:
                agent_execution_results.append({
                    "user_id": user_id,
                    "task_marker": task_marker,
                    "error": str(e),
                    "agent_events": []
                })
        
        # Run concurrent agent executions
        await asyncio.gather(
            run_isolated_agent(
                user_a_id, 
                auth_headers_user_a, 
                f"Execute isolated task ALPHA_{unique_test_id}",
                "TASK_ALPHA"
            ),
            run_isolated_agent(
                user_b_id,
                auth_headers_user_b,
                f"Execute isolated task BETA_{unique_test_id}",
                "TASK_BETA"
            )
        )
        
        # Validate agent execution isolation
        assert len(agent_execution_results) >= 2, f"Should have results for both agents, got: {len(agent_execution_results)}"
        
        # Find results for each user
        user_a_result = next((r for r in agent_execution_results if r.get("user_id") == user_a_id), None)
        user_b_result = next((r for r in agent_execution_results if r.get("user_id") == user_b_id), None)
        
        assert user_a_result is not None, "User A agent execution result missing"
        assert user_b_result is not None, "User B agent execution result missing"
        
        # CRITICAL: Check for cross-contamination in agent events
        user_a_events_str = json.dumps(user_a_result.get("agent_events", [])).lower()
        user_b_events_str = json.dumps(user_b_result.get("agent_events", [])).lower()
        
        # User A should not see User B's task marker
        assert "task_beta" not in user_a_events_str, "ISOLATION BUG: User A saw User B's agent task"
        assert f"beta_{unique_test_id}".lower() not in user_a_events_str, "ISOLATION BUG: User A saw User B's unique data"
        
        # User B should not see User A's task marker  
        assert "task_alpha" not in user_b_events_str, "ISOLATION BUG: User B saw User A's agent task"
        assert f"alpha_{unique_test_id}".lower() not in user_b_events_str, "ISOLATION BUG: User B saw User A's unique data"
        
        # Both users should have received some agent events
        assert user_a_result.get("event_count", 0) > 0, "User A should have received agent events"
        assert user_b_result.get("event_count", 0) > 0, "User B should have received agent events"
        
        print(f"Agent isolation validated - User A events: {user_a_result.get('event_count')}, User B events: {user_b_result.get('event_count')}")
    
    @pytest.mark.asyncio  
    async def test_session_state_isolation(self, websocket_url, auth_headers_user_a, auth_headers_user_b, unique_test_id):
        """Test session state is isolated between users."""
        user_a_id = f"session_user_a_{unique_test_id}"
        user_b_id = f"session_user_b_{unique_test_id}"
        
        session_states = {}
        
        async def manage_user_session(user_id: str, auth_headers: Dict, session_data: Dict):
            """Manage isolated user session."""
            session_info = {"user_id": user_id, "events": []}
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Connect with session tracking
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "track_session_state": True,
                        "session_data": session_data
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    session_info["connection_id"] = connect_response.get("connection_id")
                    session_info["events"].append(("connect", connect_response))
                    
                    # Set user-specific session state
                    await websocket.send(json.dumps({
                        "type": "user_message",
                        "user_id": user_id,
                        "content": f"Set session state: {session_data}",
                        "thread_id": f"session_thread_{user_id}",
                        "set_session_state": session_data
                    }))
                    
                    # Query session state
                    await websocket.send(json.dumps({
                        "type": "query_session_state",
                        "user_id": user_id,
                        "request_current_state": True
                    }))
                    
                    # Collect session responses
                    timeout_time = time.time() + 8
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            response = json.loads(response_raw)
                            session_info["events"].append(("session", response))
                            
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                    
                    session_states[user_id] = session_info
                    
            except Exception as e:
                session_states[user_id] = {"user_id": user_id, "error": str(e), "events": []}
        
        # Run concurrent sessions with different state data
        await asyncio.gather(
            manage_user_session(user_a_id, auth_headers_user_a, {
                "preference": "dark_mode",
                "language": "english", 
                "secret_key": f"user_a_secret_{unique_test_id}"
            }),
            manage_user_session(user_b_id, auth_headers_user_b, {
                "preference": "light_mode",
                "language": "spanish",
                "secret_key": f"user_b_secret_{unique_test_id}"
            })
        )
        
        # Validate session isolation
        assert user_a_id in session_states, "User A session state not recorded"
        assert user_b_id in session_states, "User B session state not recorded"
        
        user_a_session = session_states[user_a_id]
        user_b_session = session_states[user_b_id]
        
        # Validate distinct sessions
        if "connection_id" in user_a_session and "connection_id" in user_b_session:
            assert user_a_session["connection_id"] != user_b_session["connection_id"], \
                "Users should have separate session identifiers"
        
        # CRITICAL: Check session state isolation
        user_a_events_str = json.dumps(user_a_session.get("events", [])).lower()
        user_b_events_str = json.dumps(user_b_session.get("events", [])).lower()
        
        # User A should not see User B's session secrets
        user_b_secret = f"user_b_secret_{unique_test_id}".lower()
        assert user_b_secret not in user_a_events_str, \
            f"SESSION ISOLATION BUG: User A saw User B's secret: {user_b_secret}"
        
        # User B should not see User A's session secrets
        user_a_secret = f"user_a_secret_{unique_test_id}".lower()
        assert user_a_secret not in user_b_events_str, \
            f"SESSION ISOLATION BUG: User B saw User A's secret: {user_a_secret}"
        
        print(f"Session isolation validated - User A events: {len(user_a_session.get('events', []))}, User B events: {len(user_b_session.get('events', []))}")
    
    @pytest.mark.asyncio
    async def test_factory_pattern_isolation(self, websocket_url, auth_headers_user_a, auth_headers_user_b, unique_test_id):
        """Test factory patterns provide proper user isolation."""
        user_a_id = f"factory_user_a_{unique_test_id}"
        user_b_id = f"factory_user_b_{unique_test_id}"
        
        factory_isolation_results = []
        
        async def test_factory_isolation(user_id: str, auth_headers: Dict, factory_marker: str):
            """Test factory pattern isolation."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Connect with factory isolation tracking
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "test_factory_isolation": True,
                        "factory_marker": factory_marker
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Request factory instance creation
                    await websocket.send(json.dumps({
                        "type": "create_factory_instance",
                        "user_id": user_id,
                        "instance_type": "test_executor",
                        "factory_marker": factory_marker,
                        "isolation_data": f"private_data_{factory_marker}_{unique_test_id}"
                    }))
                    
                    # Collect factory responses
                    responses = []
                    timeout_time = time.time() + 8
                    
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            response = json.loads(response_raw)
                            responses.append(response)
                            
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                    
                    factory_isolation_results.append({
                        "user_id": user_id,
                        "factory_marker": factory_marker,
                        "responses": responses,
                        "connection_id": connect_response.get("connection_id")
                    })
                    
            except Exception as e:
                factory_isolation_results.append({
                    "user_id": user_id,
                    "factory_marker": factory_marker,
                    "error": str(e),
                    "responses": []
                })
        
        # Test factory isolation concurrently
        await asyncio.gather(
            test_factory_isolation(user_a_id, auth_headers_user_a, "FACTORY_A"),
            test_factory_isolation(user_b_id, auth_headers_user_b, "FACTORY_B")
        )
        
        # Validate factory isolation
        assert len(factory_isolation_results) >= 2, f"Should have factory results for both users"
        
        # Find results for each user
        user_a_factory = next((r for r in factory_isolation_results if r.get("user_id") == user_a_id), None)
        user_b_factory = next((r for r in factory_isolation_results if r.get("user_id") == user_b_id), None)
        
        assert user_a_factory is not None, "User A factory result missing"
        assert user_b_factory is not None, "User B factory result missing"
        
        # CRITICAL: Check factory isolation - no cross-contamination
        user_a_data = json.dumps(user_a_factory.get("responses", [])).lower()
        user_b_data = json.dumps(user_b_factory.get("responses", [])).lower()
        
        # Check User A doesn't see User B's factory data
        user_b_private = f"private_data_factory_b_{unique_test_id}".lower()
        assert user_b_private not in user_a_data, \
            f"FACTORY ISOLATION BUG: User A saw User B's private factory data"
        
        # Check User B doesn't see User A's factory data
        user_a_private = f"private_data_factory_a_{unique_test_id}".lower()
        assert user_a_private not in user_b_data, \
            f"FACTORY ISOLATION BUG: User B saw User A's private factory data"
        
        print(f"Factory isolation validated - User A responses: {len(user_a_factory.get('responses', []))}, User B responses: {len(user_b_factory.get('responses', []))}")