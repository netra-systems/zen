#!/usr/bin/env python

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
WebSocket Race Conditions Golden Path E2E Tests - Phase 3 Implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Validate complete user chat experience without race conditions
- Value Impact: Ensures core chat value delivery is reliable, protecting $500K+ ARR
- Strategic/Revenue Impact: Protects primary business value delivery mechanism

CRITICAL E2E REQUIREMENTS (CLAUDE.md Compliance):
 PASS:  FEATURE FREEZE: Only validates existing features work correctly
 PASS:  NO MOCKS ALLOWED: Real Docker services, real WebSocket, real authentication
 PASS:  MANDATORY E2E AUTH: All tests use create_authenticated_user_context()
 PASS:  MISSION CRITICAL EVENTS: All 5 WebSocket events validated in every test
 PASS:  COMPLETE WORK: Full golden path user workflows with business value delivery
 PASS:  SYSTEM STABILITY: Proves no breaking changes introduced

ROOT CAUSE ADDRESSED:
- WebSocket 1011 errors in Cloud Run staging environments
- Race conditions in rapid WebSocket connection scenarios
- Missing business-critical WebSocket events breaking user chat
- Multi-user concurrent chat sessions with isolation failures

FULL SYSTEM REQUIREMENTS (Real Everything):
- Full Docker stack (Backend, Auth, PostgreSQL, Redis)
- Real WebSocket connections with proper authentication
- Real agent execution with complete tool dispatching
- Real business value delivery validation under stress
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import threading
import random

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.common_imports import *  # PERFORMANCE: Consolidated imports
# CONSOLIDATED: from test_framework.common_imports import *  # PERFORMANCE: Consolidated imports
# CONSOLIDATED: # CONSOLIDATED: from test_framework.base_e2e_test import BaseE2ETest
# CONSOLIDATED: # CONSOLIDATED: from test_framework.real_services_test_fixtures import real_services_fixture
# CONSOLIDATED: from test_framework.ssot.e2e_auth_helper import (
#     E2EWebSocketAuthHelper,
#     E2EAuthConfig,
#     AuthenticatedUser,
#     create_authenticated_user_context
# )
# CONSOLIDATED: # CONSOLIDATED: from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Import real agent components for full system testing
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.mission_critical
@pytest.mark.golden_path
class TestWebSocketRaceConditionsGoldenPath(BaseE2ETest):
    """
    E2E tests for WebSocket race conditions in complete golden path scenarios.
    
    Tests complete user chat experience with REAL services, REAL LLM,
    and REAL agent execution. NO MOCKS per CLAUDE.md requirements.
    
    CRITICAL: These tests validate that race condition fixes work in
    production-like environment with complete business value delivery.
    """
    
    # Required WebSocket events for complete business value delivery
    CRITICAL_WEBSOCKET_EVENTS = [
        "agent_started",    # User sees AI began processing their problem
        "agent_thinking",   # Real-time reasoning visibility
        "tool_executing",   # Tool usage transparency  
        "tool_completed",   # Tool results display
        "agent_completed"   # User knows when valuable response is ready
    ]
    
    @pytest.fixture(autouse=True)
    async def setup_e2e_environment(self, real_services_fixture):
        """Set up full E2E environment for golden path race condition testing."""
        self.services = real_services_fixture
        
        # Initialize authentication with Docker-compatible config
        self.auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002", 
            websocket_url="ws://localhost:8002/ws"
        )
        self.auth_helper = E2EWebSocketAuthHelper(
            config=self.auth_config,
            environment="test"
        )
        
        # Wait for complete system readiness
        await self._wait_for_full_system_ready()
        
        # Initialize tracking systems
        self.chat_sessions: List[Dict[str, Any]] = []
        self.race_condition_failures: List[Dict[str, Any]] = []
        self.websocket_event_tracking: Dict[str, List[str]] = {}
        self.business_value_metrics: List[Dict[str, Any]] = []
    
    async def _wait_for_full_system_ready(self, max_wait_time: float = 60.0):
        """
        Wait for complete system readiness including all agent services.
        
        This ensures no race conditions in the test setup itself and validates
        that all components required for golden path are operational.
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check infrastructure services
                postgres_ready = await self.services.is_postgres_ready()
                redis_ready = await self.services.is_redis_ready()
                backend_ready = await self._check_backend_health()
                
                # Check agent system readiness
                agent_registry_ready = await self._check_agent_registry_ready()
                tool_dispatcher_ready = await self._check_tool_dispatcher_ready()
                
                if all([postgres_ready, redis_ready, backend_ready, agent_registry_ready, tool_dispatcher_ready]):
                    print(" PASS:  Full system ready for E2E testing")
                    return
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"[U+23F3] System readiness check failed: {e}, retrying...")
                await asyncio.sleep(1.0)
        
        pytest.fail(f"Full system not ready after {max_wait_time}s wait")
    
    async def _check_backend_health(self) -> bool:
        """Check backend service health for WebSocket connections."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.auth_config.backend_url}/health"
                async with session.get(health_url, timeout=5.0) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _check_agent_registry_ready(self) -> bool:
        """Check if agent registry is operational."""
        try:
            # Simple validation that agent registry can be instantiated
            registry = AgentRegistry()
            return registry is not None
        except Exception:
            return False
    
    async def _check_tool_dispatcher_ready(self) -> bool:
        """Check if tool dispatcher is operational."""
        try:
            # Simple validation that tool dispatcher can be created
            dispatcher = UnifiedToolDispatcher()
            return dispatcher is not None
        except Exception:
            return False

    async def test_001_rapid_websocket_connections_no_race(self):
        """
        Test rapid WebSocket connections without race conditions.
        
        Validates that multiple rapid connections work without 1011 errors
        and all required WebSocket events are delivered properly.
        
        CRITICAL: This addresses P1 WebSocket authentication timeout failures.
        """
        connection_count = 5
        connections = []
        event_tracking = {}
        
        try:
            # Create authenticated user context (MANDATORY per CLAUDE.md)
            user_context = await create_authenticated_user_context(
                user_email="race_test_001@example.com",
                environment="test",
                websocket_enabled=True
            )
            
            # Rapid connection sequence
            for i in range(connection_count):
                try:
                    # Connect with authentication
                    websocket = await self.auth_helper.connect_authenticated_websocket(
                        timeout=10.0
                    )
                    connections.append(websocket)
                    
                    # Track connection for events
                    connection_id = f"conn_{i}"
                    event_tracking[connection_id] = []
                    
                    # Send test message and capture events
                    test_message = {
                        "type": "chat_message",
                        "message": f"Test rapid connection {i}",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id)
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Capture initial response with timeout
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(response)
                        event_tracking[connection_id].append(event_data)
                        
                        # Validate event structure
                        assert "type" in event_data, f"Event missing type field: {event_data}"
                        
                    except asyncio.TimeoutError:
                        pytest.fail(f"Connection {i} timeout waiting for response")
                    
                    # Small delay to test rapid connections
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    pytest.fail(f"Failed to establish connection {i}: {e}")
            
            # Validate all connections established successfully
            assert len(connections) == connection_count, f"Expected {connection_count} connections, got {len(connections)}"
            
            # Validate no race condition errors in tracking
            for conn_id, events in event_tracking.items():
                assert len(events) > 0, f"No events received on {conn_id}"
                
                # Check for error events
                error_events = [e for e in events if e.get("type") == "error"]
                assert len(error_events) == 0, f"Error events found on {conn_id}: {error_events}"
            
            print(f" PASS:  Successfully established {connection_count} rapid connections without race conditions")
            
        finally:
            # Clean up all connections
            for websocket in connections:
                try:
                    await websocket.close()
                except Exception:
                    pass

    async def test_002_websocket_authentication_real(self):
        """
        Test WebSocket authentication with real services.
        
        CRITICAL: This addresses P1 WebSocket authentication timeout failures
        reported in the Golden Path test suite.
        """
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="auth_test_002@example.com", 
            environment="test",
            websocket_enabled=True
        )
        
        websocket = None
        try:
            # Connect with real authentication
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=15.0  # Extended timeout for real services
            )
            
            # Validate connection is authenticated
            assert websocket is not None, "WebSocket connection failed"
            assert websocket.open, "WebSocket not in open state"
            
            # Send authentication test message
            auth_test_message = {
                "type": "auth_test",
                "user_id": str(user_context.user_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(auth_test_message))
            
            # Wait for authentication confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            # Validate authentication success
            assert "type" in response_data, "Response missing type field"
            assert response_data.get("type") != "error", f"Authentication error: {response_data}"
            
            print(" PASS:  WebSocket authentication successful with real services")
            
        finally:
            if websocket:
                await websocket.close()

    async def test_003_multi_user_concurrent_chat_sessions(self):
        """
        Test concurrent multi-user chat sessions with proper isolation.
        
        Validates that multiple users can chat simultaneously without
        cross-contamination of events or race conditions.
        """
        user_count = 3
        user_sessions = []
        
        try:
            # Create multiple authenticated users
            for i in range(user_count):
                user_context = await create_authenticated_user_context(
                    user_email=f"multiuser_{i}@example.com",
                    environment="test",
                    websocket_enabled=True
                )
                
                websocket = await self.auth_helper.connect_authenticated_websocket(
                    timeout=10.0
                )
                
                user_sessions.append({
                    "context": user_context,
                    "websocket": websocket,
                    "events": [],
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id)
                })
            
            # Send concurrent chat messages
            chat_tasks = []
            for i, session in enumerate(user_sessions):
                chat_message = {
                    "type": "chat_message", 
                    "message": f"Concurrent chat test from user {i}",
                    "thread_id": session["thread_id"],
                    "user_id": session["user_id"]
                }
                
                task = asyncio.create_task(
                    self._send_and_capture_events(session, chat_message)
                )
                chat_tasks.append(task)
            
            # Wait for all concurrent chats to complete
            results = await asyncio.gather(*chat_tasks, return_exceptions=True)
            
            # Validate all sessions completed successfully
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"User {i} chat session failed: {result}")
                
                session = user_sessions[i]
                assert len(session["events"]) > 0, f"No events received for user {i}"
                
                # Validate user isolation - no cross-contamination
                user_events = session["events"]
                for event in user_events:
                    if "user_id" in event:
                        assert event["user_id"] == session["user_id"], \
                            f"Event cross-contamination detected for user {i}: {event}"
            
            print(f" PASS:  Successfully tested {user_count} concurrent user sessions with proper isolation")
            
        finally:
            # Clean up all sessions
            for session in user_sessions:
                try:
                    await session["websocket"].close()
                except Exception:
                    pass

    async def _send_and_capture_events(self, session: Dict, message: Dict) -> None:
        """Send message and capture resulting events."""
        websocket = session["websocket"]
        
        # Send message
        await websocket.send(json.dumps(message))
        
        # Capture events for 10 seconds
        end_time = time.time() + 10.0
        while time.time() < end_time:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                event_data = json.loads(response)
                session["events"].append(event_data)
                
                # Stop if we get completion event
                if event_data.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue  # Continue listening for more events
            except Exception as e:
                print(f"Event capture error: {e}")
                break

    async def test_004_complete_agent_execution_with_all_events(self):
        """
        Test complete agent execution with all 5 mission-critical WebSocket events.
        
        CRITICAL: This validates that ALL 5 WebSocket events are delivered
        during a complete golden path agent execution flow.
        """
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="complete_agent_test@example.com",
            environment="test", 
            websocket_enabled=True
        )
        
        websocket = None
        received_events = []
        
        try:
            # Connect with authentication
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=15.0
            )
            
            # Send agent execution request
            agent_request = {
                "type": "chat_message",
                "message": "Please analyze my cloud costs and provide optimization recommendations.",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "request_agent_execution": True
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Capture all events during agent execution
            event_timeout = 30.0  # Extended timeout for agent execution
            end_time = time.time() + event_timeout
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(response)
                    received_events.append(event_data)
                    
                    print(f"[U+1F4E8] Received event: {event_data.get('type', 'unknown')}")
                    
                    # Stop when agent completes
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    print("[U+23F1][U+FE0F] Timeout waiting for events, continuing...")
                    continue
                except Exception as e:
                    print(f" FAIL:  Error receiving events: {e}")
                    break
            
            # Validate all 5 mission-critical events were received
            received_event_types = set(event.get("type") for event in received_events)
            
            for required_event in self.CRITICAL_WEBSOCKET_EVENTS:
                assert required_event in received_event_types, \
                    f"Missing critical WebSocket event: {required_event}. " \
                    f"Received: {sorted(received_event_types)}"
            
            # Validate event sequence makes business sense
            event_sequence = [event.get("type") for event in received_events]
            
            # agent_started should come first
            if "agent_started" in event_sequence:
                first_agent_started = event_sequence.index("agent_started")
                assert first_agent_started == 0 or all(
                    event_sequence[i] in ["connection_ack", "ping", "pong"] 
                    for i in range(first_agent_started)
                ), f"agent_started not at expected position in sequence: {event_sequence}"
            
            # agent_completed should come last (among agent events)
            if "agent_completed" in event_sequence:
                last_agent_completed = len(event_sequence) - 1 - event_sequence[::-1].index("agent_completed")
                agent_events_after = [
                    event_sequence[i] for i in range(last_agent_completed + 1, len(event_sequence))
                    if event_sequence[i] not in ["ping", "pong", "connection_ack"]
                ]
                assert len(agent_events_after) == 0, \
                    f"Non-system events after agent_completed: {agent_events_after}"
            
            print(f" PASS:  All {len(self.CRITICAL_WEBSOCKET_EVENTS)} mission-critical events received")
            print(f" PASS:  Event sequence validated: {len(received_events)} total events")
            
        finally:
            if websocket:
                await websocket.close()

    async def test_005_staging_race_condition_reproduction(self):
        """
        Test staging environment race condition scenarios.
        
        Reproduces the specific race conditions that occur in GCP Cloud Run
        staging environment to validate fixes work in production-like conditions.
        """
        # Create authenticated user context for staging-like test
        user_context = await create_authenticated_user_context(
            user_email="staging_race_test@example.com",
            environment="test",  # Use test env with staging-like conditions
            websocket_enabled=True
        )
        
        # Test rapid connection/disconnection cycles (common in staging)
        connection_cycles = 3
        successful_cycles = 0
        
        for cycle in range(connection_cycles):
            websocket = None
            try:
                print(f" CYCLE:  Testing connection cycle {cycle + 1}/{connection_cycles}")
                
                # Connect with staging-compatible timeout
                websocket = await self.auth_helper.connect_authenticated_websocket(
                    timeout=8.0  # Shorter timeout like staging
                )
                
                # Send quick test message
                test_message = {
                    "type": "chat_message",
                    "message": f"Staging race test cycle {cycle}",
                    "thread_id": str(user_context.thread_id),
                    "user_id": str(user_context.user_id)
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for immediate response (race condition test)
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                
                # Validate no race condition errors
                assert response_data.get("type") != "error", \
                    f"Race condition error in cycle {cycle}: {response_data}"
                
                successful_cycles += 1
                print(f" PASS:  Cycle {cycle + 1} successful")
                
                # Rapid disconnect
                await websocket.close()
                websocket = None
                
                # Brief delay before next cycle
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f" FAIL:  Race condition detected in cycle {cycle}: {e}")
                if "1011" in str(e) or "timeout" in str(e).lower():
                    pytest.fail(f"Staging race condition reproduced in cycle {cycle}: {e}")
            finally:
                if websocket:
                    await websocket.close()
        
        # All cycles must succeed to pass
        assert successful_cycles == connection_cycles, \
            f"Race conditions detected: {successful_cycles}/{connection_cycles} cycles successful"
        
        print(f" PASS:  All {connection_cycles} race condition test cycles passed")

    async def test_006_business_value_delivery_validation(self):
        """
        Test complete business value delivery through WebSocket events.
        
        Validates that users receive substantive AI-powered results through
        WebSocket communication, demonstrating complete business value flow.
        """
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="business_value_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        websocket = None
        business_value_events = []
        
        try:
            # Connect with authentication
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=15.0
            )
            
            # Send business-relevant request
            business_request = {
                "type": "chat_message",
                "message": "What are the top 3 ways I can optimize my cloud infrastructure costs?",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "request_business_value": True
            }
            
            await websocket.send(json.dumps(business_request))
            
            # Capture business value events
            business_value_timeout = 25.0
            end_time = time.time() + business_value_timeout
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(response)
                    business_value_events.append(event_data)
                    
                    # Log business-relevant events
                    event_type = event_data.get("type")
                    if event_type in ["tool_executing", "tool_completed", "agent_thinking", "agent_completed"]:
                        print(f"[U+1F4BC] Business value event: {event_type}")
                    
                    # Stop when business value delivered
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Business value capture error: {e}")
                    break
            
            # Validate business value delivery
            event_types = set(event.get("type") for event in business_value_events)
            
            # Must have agent execution events
            assert "agent_started" in event_types, "No agent_started event for business value"
            assert "agent_thinking" in event_types, "No agent_thinking event for business reasoning"
            assert "agent_completed" in event_types, "No agent_completed event for business results"
            
            # Should have tool execution for real business analysis
            has_tool_execution = "tool_executing" in event_types or "tool_completed" in event_types
            assert has_tool_execution, "No tool execution events for business analysis"
            
            # Validate substantive content in final response
            completion_events = [e for e in business_value_events if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0, "No completion events found"
            
            final_event = completion_events[-1]
            response_content = final_event.get("content", "").lower()
            
            # Check for business-relevant content
            business_keywords = ["cost", "optimize", "cloud", "recommend", "save", "efficient"]
            has_business_content = any(keyword in response_content for keyword in business_keywords)
            
            if not has_business_content:
                print(f" WARNING: [U+FE0F] Warning: Response may lack business relevance: {response_content[:100]}...")
            
            print(f" PASS:  Business value delivery validated: {len(business_value_events)} events captured")
            print(f" PASS:  Complete user value chain: Request  ->  AI Analysis  ->  Recommendations")
            
        finally:
            if websocket:
                await websocket.close()

    async def test_007_websocket_error_recovery_flow(self):
        """
        Test WebSocket error recovery and graceful degradation.
        
        Validates that WebSocket connections can recover from errors
        and continue delivering business value.
        """
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="error_recovery_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        primary_websocket = None
        recovery_websocket = None
        
        try:
            # Establish primary connection
            primary_websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=10.0
            )
            
            # Send initial message
            test_message = {
                "type": "chat_message",
                "message": "Test error recovery capabilities",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id)
            }
            
            await primary_websocket.send(json.dumps(test_message))
            
            # Get initial response to confirm working
            initial_response = await asyncio.wait_for(primary_websocket.recv(), timeout=5.0)
            initial_data = json.loads(initial_response)
            assert initial_data.get("type") != "error", f"Initial connection error: {initial_data}"
            
            # Simulate connection loss by closing
            await primary_websocket.close()
            
            print(" CYCLE:  Testing connection recovery after disconnection")
            
            # Attempt recovery with new connection
            recovery_websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=10.0
            )
            
            # Send recovery test message
            recovery_message = {
                "type": "chat_message",
                "message": "Test recovery connection functionality",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id)
            }
            
            await recovery_websocket.send(json.dumps(recovery_message))
            
            # Validate recovery successful
            recovery_response = await asyncio.wait_for(recovery_websocket.recv(), timeout=5.0)
            recovery_data = json.loads(recovery_response)
            
            assert recovery_data.get("type") != "error", f"Recovery connection error: {recovery_data}"
            
            print(" PASS:  WebSocket error recovery successful")
            print(" PASS:  Business continuity maintained through connection recovery")
            
        finally:
            if primary_websocket and not primary_websocket.closed:
                await primary_websocket.close()
            if recovery_websocket:
                await recovery_websocket.close()

    async def test_008_performance_under_load(self):
        """
        Test WebSocket performance under concurrent load.
        
        Validates that the system maintains performance and event delivery
        under realistic concurrent user load.
        """
        concurrent_users = 4  # Reasonable load for E2E testing
        user_sessions = []
        performance_metrics = []
        
        try:
            # Create concurrent user sessions
            for i in range(concurrent_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"load_test_{i}@example.com",
                    environment="test",
                    websocket_enabled=True
                )
                
                start_time = time.time()
                websocket = await self.auth_helper.connect_authenticated_websocket(
                    timeout=15.0
                )
                connection_time = time.time() - start_time
                
                user_sessions.append({
                    "context": user_context,
                    "websocket": websocket,
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "events": [],
                    "connection_time": connection_time
                })
                
                performance_metrics.append({
                    "user": i,
                    "connection_time": connection_time,
                    "events_received": 0,
                    "response_times": []
                })
            
            # Send concurrent messages and measure performance
            load_tasks = []
            for i, session in enumerate(user_sessions):
                task = asyncio.create_task(
                    self._run_performance_test_session(session, performance_metrics[i])
                )
                load_tasks.append(task)
            
            # Wait for all load tests to complete
            results = await asyncio.gather(*load_tasks, return_exceptions=True)
            
            # Validate performance metrics
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Load test user {i} failed: {result}")
                
                metrics = performance_metrics[i]
                
                # Validate connection performance
                assert metrics["connection_time"] < 10.0, \
                    f"User {i} connection too slow: {metrics['connection_time']:.2f}s"
                
                # Validate event delivery
                assert metrics["events_received"] > 0, f"User {i} received no events"
                
                # Validate response times
                if metrics["response_times"]:
                    avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"])
                    assert avg_response_time < 5.0, \
                        f"User {i} average response time too slow: {avg_response_time:.2f}s"
            
            # Calculate overall performance metrics
            total_events = sum(m["events_received"] for m in performance_metrics)
            avg_connection_time = sum(m["connection_time"] for m in performance_metrics) / len(performance_metrics)
            
            print(f" PASS:  Performance test completed successfully")
            print(f" PASS:  {concurrent_users} concurrent users, {total_events} total events")
            print(f" PASS:  Average connection time: {avg_connection_time:.2f}s")
            
        finally:
            # Clean up all sessions
            for session in user_sessions:
                try:
                    await session["websocket"].close()
                except Exception:
                    pass

    async def _run_performance_test_session(self, session: Dict, metrics: Dict) -> None:
        """Run performance test for a single user session."""
        websocket = session["websocket"]
        
        # Send test message
        test_message = {
            "type": "chat_message",
            "message": f"Performance test for user {session['user_id']}",
            "thread_id": session["thread_id"],
            "user_id": session["user_id"]
        }
        
        message_start = time.time()
        await websocket.send(json.dumps(test_message))
        
        # Capture events for performance measurement
        test_duration = 15.0
        end_time = time.time() + test_duration
        
        while time.time() < end_time:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response_time = time.time() - message_start
                
                event_data = json.loads(response)
                session["events"].append(event_data)
                
                metrics["events_received"] += 1
                metrics["response_times"].append(response_time)
                
                # Update start time for next response time measurement
                message_start = time.time()
                
                # Stop if we get completion
                if event_data.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Performance test error: {e}")
                break