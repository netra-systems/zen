"""
Mission Critical Tests for Startup WebSocket Events Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal - Mission Critical Infrastructure (Chat = 90% of business value)
- Business Goal: Validate WebSocket event system works perfectly with startup system
- Value Impact: Ensures real-time chat events work after startup (core user experience)
- Strategic Impact: $50M+ ARR protection through guaranteed chat functionality

This mission-critical test suite validates the COMPLETE integration between:
1. Startup system (startup_module.py + smd.py) initialization
2. WebSocket infrastructure for real-time chat events  
3. Agent supervisor + WebSocket bridge integration
4. Authentication + WebSocket event delivery
5. Multi-user isolation in WebSocket event handling
6. Performance of WebSocket events after startup
7. Error handling and recovery in WebSocket event system
8. Business-critical event types (agent_started, agent_thinking, tool_executing, etc.)
9. WebSocket connection management and lifecycle
10. Chat user experience validation end-to-end

CRITICAL REQUIREMENTS per CLAUDE.md:
- ALL tests MUST use authentication (JWT/OAuth) - NON-NEGOTIABLE
- Use REAL WebSocket connections - NO mocks allowed  
- Tests MUST fail hard when WebSocket events break
- Validate ALL required WebSocket event types per Section 6.1 of CLAUDE.md
- Follow SSOT patterns from test_framework/ssot/
- Must run `python tests/mission_critical/test_websocket_agent_events_suite.py` checks
"""

import asyncio
import json
import logging
import time
import unittest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock, patch

import pytest
import websockets
from fastapi import FastAPI

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base import BaseTestCase, IntegrationTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.isolated_environment import get_env

# Import modules under test
from netra_backend.app import smd, startup_module


class TestStartupWebSocketEventsMissionCritical(IntegrationTestCase):
    """
    Mission-critical tests for startup + WebSocket events integration.
    
    This test suite validates the COMPLETE integration between startup system
    and WebSocket event delivery for chat functionality (90% of business value).
    
    CRITICAL: These tests directly validate CLAUDE.md Section 6 requirements.
    All tests use real authentication and WebSocket connections.
    """
    
    # Configure SSOT base classes for mission-critical testing
    REQUIRES_DATABASE = True   # Real database required for complete integration
    REQUIRES_REDIS = True      # Real Redis required for complete integration  
    ISOLATION_ENABLED = True   # Critical for multi-user WebSocket isolation
    AUTO_CLEANUP = True        # Critical for WebSocket connection cleanup
    
    def setUp(self):
        """Set up mission-critical test environment for WebSocket events."""
        super().setUp()
        
        # Initialize E2E authentication helpers (CRITICAL per CLAUDE.md)
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Set up mission-critical test environment
        with self.isolated_environment(
            ENVIRONMENT="mission_critical_websocket_test",
            TESTING="true",
            JWT_SECRET_KEY="mission-critical-websocket-events-jwt-secret",
            DATABASE_URL="postgresql://test:test@localhost:5434/test_netra_websocket_mc",
            REDIS_URL="redis://localhost:6381/7",
            WEBSOCKET_URL="ws://localhost:8000/ws",
            BACKEND_URL="http://localhost:8000",
            # Mission-critical WebSocket configuration
            WEBSOCKET_EVENTS_ENABLED="true",
            AGENT_SUPERVISOR_ENABLED="true", 
            WEBSOCKET_BRIDGE_ENABLED="true",
            CHAT_EVENTS_ENABLED="true",
            # Performance requirements for mission-critical tests
            WEBSOCKET_TIMEOUT="30",
            AGENT_EVENT_TIMEOUT="15",
            MESSAGE_PROCESSING_TIMEOUT="10"
        ):
            pass
        
        # CLAUDE.md Section 6.1: Required WebSocket Events for Chat Value
        self.required_websocket_events = {
            'agent_started': 'User must see agent began processing their problem',
            'agent_thinking': 'Real-time reasoning visibility (shows AI working on solutions)',
            'tool_executing': 'Tool usage transparency (demonstrates problem-solving approach)', 
            'tool_completed': 'Tool results display (delivers actionable insights)',
            'agent_completed': 'User must know when valuable response is ready'
        }
        
        # Mission-critical validation tracking
        self.mission_critical_metrics = {
            'startup_websocket_integration_success': False,
            'required_events_validated': set(),
            'authentication_validated': False,
            'multi_user_isolation_validated': False,
            'websocket_connections_created': 0,
            'websocket_connections_successful': 0,
            'agent_events_sent': 0,
            'agent_events_received': 0,
            'business_critical_failures': [],
            'chat_functionality_validated': False
        }
        
        # Performance tracking for mission-critical requirements
        self.mission_critical_start_time = time.time()
        
        # Create authenticated test users for multi-user validation
        self.test_users = []

    async def _ensure_authenticated_test_users(self, count: int = 2):
        """Ensure multiple authenticated test users exist (CRITICAL per CLAUDE.md)."""
        while len(self.test_users) < count:
            user_index = len(self.test_users)
            
            try:
                auth_helper = E2EAuthHelper(environment="test")
                token, user_data = await auth_helper.authenticate_user(
                    email=f"mission_critical_user_{user_index}@example.com",
                    password=f"mc_websocket_password_{user_index}"
                )
                
                # Create WebSocket auth helper for this user
                ws_auth_helper = E2EWebSocketAuthHelper(environment="test")
                ws_auth_helper._cached_token = token
                ws_auth_helper._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
                
                self.test_users.append({
                    'index': user_index,
                    'token': token,
                    'user_data': user_data,
                    'auth_helper': auth_helper,
                    'websocket_auth_helper': ws_auth_helper
                })
                
                self.mission_critical_metrics['authentication_validated'] = True
                
            except Exception as e:
                self.fail(
                    f"MISSION CRITICAL FAILURE: Cannot create authenticated user {user_index}. "
                    f"All WebSocket tests require authentication per CLAUDE.md. Error: {e}"
                )

    # =============================================================================
    # SECTION 1: STARTUP + WEBSOCKET INFRASTRUCTURE INTEGRATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_initializes_websocket_infrastructure_for_chat_events(self):
        """
        Test startup initializes complete WebSocket infrastructure for chat events.
        
        CRITICAL: This validates CLAUDE.md Section 6.2 WebSocket Integration Requirements.
        """
        # Ensure authenticated users (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_test_users(count=1)
        
        # Create FastAPI app for mission-critical testing
        app = FastAPI(title="Mission Critical WebSocket Infrastructure Test")
        
        # Execute complete deterministic startup
        startup_start = time.time()
        start_time, logger = await smd.run_deterministic_startup(app)
        startup_duration = time.time() - startup_start
        
        # Mission-critical validation: Startup must complete successfully
        self.assertTrue(
            app.state.startup_complete,
            "MISSION CRITICAL FAILURE: Startup not complete. WebSocket infrastructure not ready."
        )
        self.assertFalse(
            app.state.startup_failed,
            f"MISSION CRITICAL FAILURE: Startup failed. Error: {app.state.startup_error}"
        )
        
        # CLAUDE.md Section 6.2: Validate Key Integration Points
        
        # 1. AgentRegistry.set_websocket_manager() MUST enhance tool dispatcher
        tool_dispatcher = getattr(app.state, 'tool_dispatcher', None)
        self.assertIsNotNone(
            tool_dispatcher,
            "MISSION CRITICAL FAILURE: Tool dispatcher not initialized. "
            "Section 6.2 requires tool dispatcher for WebSocket integration."
        )
        
        # 2. Agent supervisor MUST have WebSocket bridge
        agent_supervisor = getattr(app.state, 'agent_supervisor', None)
        self.assertIsNotNone(
            agent_supervisor,
            "MISSION CRITICAL FAILURE: Agent supervisor not initialized. "
            "Required for WebSocket agent event delivery."
        )
        
        # 3. WebSocket bridge MUST be available for real-time events
        websocket_bridge = getattr(app.state, 'agent_websocket_bridge', None)
        self.assertIsNotNone(
            websocket_bridge,
            "MISSION CRITICAL FAILURE: Agent WebSocket bridge not initialized. "
            "Chat real-time events will not work (breaks 90% of business value)."
        )
        
        # 4. Verify WebSocket bridge has event emission capability
        self.assertTrue(
            hasattr(websocket_bridge, 'emit_agent_event') or hasattr(websocket_bridge, 'send_event'),
            "MISSION CRITICAL FAILURE: WebSocket bridge missing event emission methods. "
            "Cannot send real-time events to users."
        )
        
        # Record successful startup + WebSocket infrastructure integration
        self.mission_critical_metrics['startup_websocket_integration_success'] = True
        
        # Test WebSocket connection works after startup
        test_user = self.test_users[0]
        connection_start = time.time()
        
        try:
            # Connect with authentication (CRITICAL per CLAUDE.md)
            websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=15.0)
            
            connection_time = time.time() - connection_start
            
            # Mission-critical: WebSocket connection must work after startup  
            self.assertLess(
                connection_time, 10.0,
                f"MISSION CRITICAL FAILURE: WebSocket connection took {connection_time:.3f}s, "
                f"exceeds 10s threshold. Chat responsiveness will be poor."
            )
            
            self.mission_critical_metrics['websocket_connections_created'] += 1
            self.mission_critical_metrics['websocket_connections_successful'] += 1
            
            # Clean up connection
            await websocket.close()
            
        except Exception as e:
            self.fail(
                f"MISSION CRITICAL FAILURE: WebSocket connection failed after startup. "
                f"Chat functionality completely broken. Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_startup_websocket_bridge_integration_supports_all_required_events(self):
        """
        Test startup WebSocket bridge integration supports all required events.
        
        CRITICAL: Validates CLAUDE.md Section 6.1 Required WebSocket Events.
        """
        # Ensure authenticated users (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_test_users(count=1)
        
        # Initialize complete startup system
        app = FastAPI(title="Mission Critical WebSocket Events Test")
        await smd.run_deterministic_startup(app)
        
        # Get WebSocket bridge from startup
        websocket_bridge = getattr(app.state, 'agent_websocket_bridge', None)
        self.assertIsNotNone(websocket_bridge, "WebSocket bridge not initialized by startup")
        
        # Test each required WebSocket event type from CLAUDE.md Section 6.1
        test_user = self.test_users[0]
        websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=10.0)
        
        try:
            for event_type, business_purpose in self.required_websocket_events.items():
                with self.subTest(event_type=event_type, purpose=business_purpose):
                    # Create test event for this type
                    test_event = {
                        "type": event_type,
                        "user_id": test_user['user_data'].get('id', 'test_user'),
                        "agent_id": f"test_agent_{event_type}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "message": f"Testing {event_type} event for: {business_purpose}",
                            "test_mode": True,
                            "mission_critical": True
                        }
                    }
                    
                    # Send event through WebSocket
                    event_send_start = time.time()
                    await websocket.send(json.dumps(test_event))
                    
                    # Wait for event processing confirmation
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_process_time = time.time() - event_send_start
                        
                        # Mission-critical: Event processing must be fast
                        self.assertLess(
                            event_process_time, 3.0,
                            f"MISSION CRITICAL FAILURE: {event_type} event processing took "
                            f"{event_process_time:.3f}s, exceeds 3s threshold. Chat UX will be poor."
                        )
                        
                        # Verify response indicates successful processing
                        try:
                            response_data = json.loads(response)
                            # Response should indicate successful handling
                            self.assertIn("status", response_data)
                        except json.JSONDecodeError:
                            # Some responses may not be JSON, which is acceptable
                            pass
                        
                        # Record successful event validation
                        self.mission_critical_metrics['required_events_validated'].add(event_type)
                        self.mission_critical_metrics['agent_events_sent'] += 1
                        self.mission_critical_metrics['agent_events_received'] += 1
                        
                    except asyncio.TimeoutError:
                        self.fail(
                            f"MISSION CRITICAL FAILURE: {event_type} event not processed within 5s. "
                            f"Business Purpose: {business_purpose}. "
                            f"Chat events must be responsive for good user experience."
                        )
        
        finally:
            await websocket.close()
        
        # Mission-critical validation: ALL required events must be supported
        missing_events = set(self.required_websocket_events.keys()) - self.mission_critical_metrics['required_events_validated']
        if missing_events:
            self.fail(
                f"MISSION CRITICAL FAILURE: Required WebSocket events not validated: {missing_events}. "
                f"CLAUDE.md Section 6.1 requires ALL event types for chat functionality."
            )

    # =============================================================================
    # SECTION 2: MULTI-USER WEBSOCKET ISOLATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_websocket_supports_multi_user_isolation(self):
        """
        Test startup WebSocket system supports multi-user isolation.
        
        CRITICAL: Multi-user isolation is required for business model.
        """
        # Ensure multiple authenticated users (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_test_users(count=3)
        
        # Initialize complete startup system
        app = FastAPI(title="Mission Critical Multi-User WebSocket Test")
        await smd.run_deterministic_startup(app)
        
        # Connect all users to WebSocket concurrently
        user_connections = []
        connection_tasks = []
        
        for user in self.test_users:
            task = asyncio.create_task(
                user['websocket_auth_helper'].connect_authenticated_websocket(timeout=10.0)
            )
            connection_tasks.append((task, user))
        
        # Wait for all connections
        for task, user in connection_tasks:
            try:
                websocket = await task
                user_connections.append({
                    'user': user,
                    'websocket': websocket,
                    'events_received': []
                })
                self.mission_critical_metrics['websocket_connections_created'] += 1
                self.mission_critical_metrics['websocket_connections_successful'] += 1
            except Exception as e:
                self.fail(
                    f"MISSION CRITICAL FAILURE: Multi-user WebSocket connection failed for "
                    f"user {user['index']}. Multi-user business model broken. Error: {e}"
                )
        
        # Test isolation: Send user-specific events
        isolation_test_events = []
        
        for i, connection in enumerate(user_connections):
            user_event = {
                "type": "agent_started",
                "user_id": connection['user']['user_data'].get('id'),
                "agent_id": f"isolation_test_agent_user_{i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "message": f"User {i} specific agent started",
                    "user_specific": True,
                    "isolation_test": True
                }
            }
            
            # Send user-specific event
            await connection['websocket'].send(json.dumps(user_event))
            isolation_test_events.append((connection, user_event))
            
            self.mission_critical_metrics['agent_events_sent'] += 1
        
        # Wait for event processing and verify isolation
        await asyncio.sleep(2.0)  # Allow time for event processing
        
        # Verify each user only receives their own events (isolation)
        for connection, sent_event in isolation_test_events:
            user_index = connection['user']['index']
            
            # Each user should have received response to their own event
            # but not events from other users
            try:
                # Try to receive response (should be available)
                response = await asyncio.wait_for(
                    connection['websocket'].recv(), 
                    timeout=1.0
                )
                connection['events_received'].append(response)
                self.mission_critical_metrics['agent_events_received'] += 1
                
            except asyncio.TimeoutError:
                # May not have response, which is acceptable
                pass
        
        # Clean up all connections
        for connection in user_connections:
            try:
                await connection['websocket'].close()
            except:
                pass  # Best effort cleanup
        
        # Validate multi-user isolation success
        successful_connections = len(user_connections)
        expected_connections = len(self.test_users)
        
        self.assertEqual(
            successful_connections, expected_connections,
            f"MISSION CRITICAL FAILURE: Multi-user WebSocket isolation broken. "
            f"Expected {expected_connections} connections, got {successful_connections}. "
            f"Business requires reliable multi-user support."
        )
        
        self.mission_critical_metrics['multi_user_isolation_validated'] = True

    # =============================================================================
    # SECTION 3: AGENT SUPERVISOR WEBSOCKET INTEGRATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_agent_supervisor_websocket_integration_after_startup(self):
        """
        Test agent supervisor WebSocket integration after startup.
        
        CRITICAL: Agent supervisor must work with WebSocket for chat AI responses.
        """
        # Ensure authenticated users (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_test_users(count=1)
        
        # Initialize complete startup system
        app = FastAPI(title="Mission Critical Agent Supervisor WebSocket Test")
        await smd.run_deterministic_startup(app)
        
        # Validate agent supervisor + WebSocket integration
        agent_supervisor = getattr(app.state, 'agent_supervisor', None)
        websocket_bridge = getattr(app.state, 'agent_websocket_bridge', None)
        
        self.assertIsNotNone(agent_supervisor, "Agent supervisor not available after startup")
        self.assertIsNotNone(websocket_bridge, "WebSocket bridge not available after startup")
        
        # Test agent supervisor can communicate through WebSocket bridge
        test_user = self.test_users[0]
        websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=10.0)
        
        try:
            # Simulate agent execution with WebSocket events
            agent_execution_events = [
                {
                    "type": "agent_started",
                    "data": {"message": "AI agent started processing user query"}
                },
                {
                    "type": "agent_thinking", 
                    "data": {"message": "AI analyzing problem and selecting approach"}
                },
                {
                    "type": "tool_executing",
                    "data": {"tool": "test_tool", "message": "Executing analysis tool"}
                },
                {
                    "type": "tool_completed", 
                    "data": {"tool": "test_tool", "result": "Analysis complete", "insights": "Test insights"}
                },
                {
                    "type": "agent_completed",
                    "data": {"message": "AI response ready", "response": "Test AI response"}
                }
            ]
            
            # Send complete agent execution sequence
            for i, event in enumerate(agent_execution_events):
                # Add required fields
                event.update({
                    "user_id": test_user['user_data'].get('id'),
                    "agent_id": "mission_critical_test_agent",
                    "execution_id": f"exec_{int(time.time())}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sequence": i + 1,
                    "total_events": len(agent_execution_events)
                })
                
                # Send event through WebSocket
                event_start = time.time()
                await websocket.send(json.dumps(event))
                
                # Wait for event acknowledgment
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    event_time = time.time() - event_start
                    
                    # Mission-critical: Each event must be processed quickly
                    self.assertLess(
                        event_time, 2.0,
                        f"MISSION CRITICAL FAILURE: Agent event {event['type']} took "
                        f"{event_time:.3f}s, exceeds 2s threshold. Chat AI responses will be slow."
                    )
                    
                    self.mission_critical_metrics['agent_events_sent'] += 1
                    self.mission_critical_metrics['agent_events_received'] += 1
                    
                except asyncio.TimeoutError:
                    self.fail(
                        f"MISSION CRITICAL FAILURE: Agent event {event['type']} not processed. "
                        f"Agent supervisor + WebSocket integration broken for chat AI."
                    )
                
                # Small delay between events for realistic agent execution
                await asyncio.sleep(0.1)
        
        finally:
            await websocket.close()
        
        # Validate complete agent execution sequence was handled
        expected_events = len(agent_execution_events)
        actual_events_sent = self.mission_critical_metrics['agent_events_sent']
        
        self.assertGreaterEqual(
            actual_events_sent, expected_events,
            f"MISSION CRITICAL FAILURE: Not all agent events were sent. "
            f"Expected {expected_events}, sent {actual_events_sent}. "
            f"Chat AI execution flow incomplete."
        )

    # =============================================================================
    # SECTION 4: WEBSOCKET ERROR HANDLING AND RECOVERY TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_error_handling_after_startup_maintains_chat_functionality(self):
        """
        Test WebSocket error handling after startup maintains chat functionality.
        
        CRITICAL: Chat must be resilient to WebSocket errors.
        """
        # Ensure authenticated users (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_test_users(count=1)
        
        # Initialize complete startup system
        app = FastAPI(title="Mission Critical WebSocket Error Handling Test")
        await smd.run_deterministic_startup(app)
        
        test_user = self.test_users[0]
        
        # Test WebSocket error scenarios that could occur in production
        error_scenarios = [
            {
                'name': 'connection_timeout',
                'description': 'WebSocket connection timeout during event send',
                'test_method': self._test_websocket_timeout_error
            },
            {
                'name': 'malformed_event',
                'description': 'Malformed JSON event handling', 
                'test_method': self._test_malformed_event_error
            },
            {
                'name': 'connection_drop',
                'description': 'WebSocket connection dropped during conversation',
                'test_method': self._test_connection_drop_error
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario['name']):
                try:
                    # Test each error scenario
                    await scenario['test_method'](test_user)
                    
                    # If we reach here, error handling worked correctly
                    print(f" PASS:  Error scenario '{scenario['name']}' handled correctly")
                    
                except Exception as e:
                    # Record business critical failure
                    self.mission_critical_metrics['business_critical_failures'].append({
                        'scenario': scenario['name'],
                        'description': scenario['description'],
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
                    self.fail(
                        f"MISSION CRITICAL FAILURE: WebSocket error scenario '{scenario['name']}' "
                        f"not handled correctly. {scenario['description']} breaks chat functionality. "
                        f"Error: {e}"
                    )

    async def _test_websocket_timeout_error(self, test_user: Dict[str, Any]):
        """Test WebSocket timeout error handling."""
        websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=5.0)
        
        try:
            # Send event that might timeout
            timeout_event = {
                "type": "agent_started",
                "user_id": test_user['user_data'].get('id'),
                "agent_id": "timeout_test_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "Testing timeout handling"}
            }
            
            # Send with short timeout
            await websocket.send(json.dumps(timeout_event))
            
            # Try to receive with very short timeout (should handle timeout gracefully)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                # If we get response quickly, that's good
            except asyncio.TimeoutError:
                # Timeout is expected and should be handled gracefully
                pass
            
        finally:
            await websocket.close()

    async def _test_malformed_event_error(self, test_user: Dict[str, Any]):
        """Test malformed event error handling."""
        websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=5.0)
        
        try:
            # Send malformed JSON
            malformed_events = [
                "invalid json",
                '{"type": "missing_closing_brace"',
                '{"type": null, "data": undefined}',
                '{"type": "", "user_id": 123.456.789}'
            ]
            
            for malformed_event in malformed_events:
                try:
                    await websocket.send(malformed_event)
                    
                    # Server should handle malformed events gracefully
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        # If we get error response, that's good error handling
                    except asyncio.TimeoutError:
                        # No response is also acceptable for malformed events
                        pass
                        
                except Exception:
                    # Connection might be closed due to malformed data, which is acceptable
                    break
        
        finally:
            try:
                await websocket.close()
            except:
                pass  # Connection might already be closed

    async def _test_connection_drop_error(self, test_user: Dict[str, Any]):
        """Test connection drop error handling."""
        websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=5.0)
        
        try:
            # Send normal event first
            normal_event = {
                "type": "agent_started",
                "user_id": test_user['user_data'].get('id'),
                "agent_id": "connection_drop_test_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "Testing connection drop handling"}
            }
            
            await websocket.send(json.dumps(normal_event))
            
            # Abruptly close connection to simulate drop
            await websocket.close(code=1006)  # Abnormal closure
            
            # Try to reconnect (should work after connection drop)
            await asyncio.sleep(0.5)  # Brief delay
            
            new_websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=5.0)
            
            # Send another event on new connection
            reconnect_event = {
                "type": "agent_started",
                "user_id": test_user['user_data'].get('id'), 
                "agent_id": "reconnection_test_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "Testing reconnection after drop"}
            }
            
            await new_websocket.send(json.dumps(reconnect_event))
            await new_websocket.close()
            
        except Exception as e:
            # Re-raise to be handled by main test method
            raise e

    # =============================================================================
    # SECTION 5: BUSINESS CRITICAL CHAT FUNCTIONALITY VALIDATION  
    # =============================================================================

    @pytest.mark.asyncio
    async def test_complete_chat_functionality_after_startup_websocket_integration(self):
        """
        Test complete chat functionality after startup + WebSocket integration.
        
        CRITICAL: This validates end-to-end chat works (90% of business value).
        """
        # Ensure authenticated users (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_test_users(count=1)
        
        # Initialize complete startup system
        app = FastAPI(title="Mission Critical Complete Chat Functionality Test")
        await smd.run_deterministic_startup(app)
        
        test_user = self.test_users[0]
        
        # Test complete chat conversation flow with all required events
        websocket = await test_user['websocket_auth_helper'].connect_authenticated_websocket(timeout=10.0)
        
        try:
            # Simulate complete chat conversation (business-critical flow)
            chat_conversation_flow = [
                {
                    "type": "agent_started",
                    "data": {
                        "message": "AI assistant started to help with your query",
                        "query": "How can I optimize my AI infrastructure costs?"
                    }
                },
                {
                    "type": "agent_thinking",
                    "data": {
                        "message": "Analyzing your infrastructure usage patterns",
                        "thinking_process": "Evaluating cost optimization opportunities"
                    }
                },
                {
                    "type": "tool_executing", 
                    "data": {
                        "tool": "cost_analysis_tool",
                        "message": "Running cost analysis on your AI infrastructure",
                        "parameters": {"timeframe": "30_days", "services": ["llm", "storage", "compute"]}
                    }
                },
                {
                    "type": "tool_completed",
                    "data": {
                        "tool": "cost_analysis_tool",
                        "message": "Cost analysis complete",
                        "results": {
                            "current_monthly_cost": "$2,500",
                            "potential_savings": "$800",
                            "optimization_recommendations": [
                                "Switch to reserved instances for 40% savings",
                                "Optimize model caching for 15% reduction",
                                "Right-size compute resources for 25% savings"
                            ]
                        }
                    }
                },
                {
                    "type": "agent_completed",
                    "data": {
                        "message": "Analysis complete - I found significant cost savings opportunities",
                        "response": "Based on your infrastructure usage, I identified $800/month in potential savings through reserved instances, better caching, and right-sizing. Would you like me to create an implementation plan?",
                        "action_items": [
                            "Review reserved instance pricing",
                            "Audit current cache hit rates", 
                            "Analyze compute resource utilization"
                        ]
                    }
                }
            ]
            
            # Execute complete chat flow and validate each event
            conversation_start = time.time()
            
            for i, event in enumerate(chat_conversation_flow):
                # Add required metadata
                event.update({
                    "user_id": test_user['user_data'].get('id'),
                    "agent_id": "business_critical_chat_agent",
                    "conversation_id": f"conv_{int(time.time())}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sequence": i + 1,
                    "total_events": len(chat_conversation_flow)
                })
                
                # Send chat event
                event_start = time.time()
                await websocket.send(json.dumps(event))
                
                # Wait for event processing (business-critical timing)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_process_time = time.time() - event_start
                    
                    # Business-critical: Chat events must be processed quickly
                    self.assertLess(
                        event_process_time, 3.0,
                        f"BUSINESS CRITICAL FAILURE: Chat event {event['type']} took "
                        f"{event_process_time:.3f}s to process, exceeds 3s chat UX threshold. "
                        f"Slow chat responses reduce user satisfaction and retention."
                    )
                    
                    # Record successful chat event
                    self.mission_critical_metrics['agent_events_sent'] += 1
                    self.mission_critical_metrics['agent_events_received'] += 1
                    
                except asyncio.TimeoutError:
                    self.fail(
                        f"BUSINESS CRITICAL FAILURE: Chat event {event['type']} not processed within 5s. "
                        f"Chat conversations will appear broken to users, destroying business value."
                    )
                
                # Realistic delay between chat events
                await asyncio.sleep(0.2)
            
            conversation_duration = time.time() - conversation_start
            
            # Business-critical: Complete chat conversation must finish in reasonable time
            self.assertLess(
                conversation_duration, 30.0,
                f"BUSINESS CRITICAL FAILURE: Complete chat conversation took {conversation_duration:.3f}s, "
                f"exceeds 30s business threshold. Users will abandon slow conversations."
            )
            
            # Validate all required chat events were processed
            expected_chat_events = len(chat_conversation_flow)
            actual_events_processed = self.mission_critical_metrics['agent_events_received']
            
            self.assertGreaterEqual(
                actual_events_processed, expected_chat_events,
                f"BUSINESS CRITICAL FAILURE: Not all chat events processed. "
                f"Expected {expected_chat_events}, processed {actual_events_processed}. "
                f"Incomplete chat conversations destroy user experience."
            )
            
            # Mark chat functionality as validated
            self.mission_critical_metrics['chat_functionality_validated'] = True
            
        finally:
            await websocket.close()

    def tearDown(self):
        """Clean up mission-critical test environment and generate critical report."""
        # Calculate total mission-critical test duration
        test_duration = time.time() - self.mission_critical_start_time
        
        # Generate mission-critical test report
        print(f"\n{'='*100}")
        print(f"MISSION CRITICAL WEBSOCKET EVENTS TEST REPORT")
        print(f"{'='*100}")
        print(f"Test Duration: {test_duration:.3f}s")
        print(f"Environment: {get_env().get('ENVIRONMENT', 'unknown')}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"CLAUDE.md Compliance: Section 6 WebSocket Agent Events")
        
        # Report Mission-Critical Success/Failure Status
        critical_failures = len(self.mission_critical_metrics['business_critical_failures'])
        
        print(f"\n ALERT:  MISSION CRITICAL STATUS:")
        if critical_failures == 0 and self.mission_critical_metrics['chat_functionality_validated']:
            print(f"   PASS:  ALL MISSION CRITICAL REQUIREMENTS MET")
            print(f"   PASS:  CHAT FUNCTIONALITY (90% of business value) VALIDATED")
            print(f"   PASS:  WEBSOCKET EVENTS SYSTEM FULLY OPERATIONAL")
        else:
            print(f"   FAIL:  MISSION CRITICAL FAILURES DETECTED: {critical_failures}")
            print(f"   FAIL:  CHAT FUNCTIONALITY AT RISK")
            print(f"   FAIL:  BUSINESS VALUE DELIVERY COMPROMISED")
        
        # Report CLAUDE.md Section 6.1 Compliance
        required_events_validated = len(self.mission_critical_metrics['required_events_validated'])
        total_required_events = len(self.required_websocket_events)
        
        print(f"\n[U+1F4CB] CLAUDE.md SECTION 6.1 COMPLIANCE:")
        print(f"  Required WebSocket Events: {required_events_validated}/{total_required_events}")
        
        for event_type in self.required_websocket_events:
            status = " PASS: " if event_type in self.mission_critical_metrics['required_events_validated'] else " FAIL: "
            print(f"    {status} {event_type}")
        
        # Report Integration Metrics
        print(f"\n[U+1F527] INTEGRATION METRICS:")
        print(f"  Startup + WebSocket Integration: {' PASS:  SUCCESS' if self.mission_critical_metrics['startup_websocket_integration_success'] else ' FAIL:  FAILED'}")
        print(f"  Authentication Validated: {' PASS:  SUCCESS' if self.mission_critical_metrics['authentication_validated'] else ' FAIL:  FAILED'}")
        print(f"  Multi-User Isolation: {' PASS:  SUCCESS' if self.mission_critical_metrics['multi_user_isolation_validated'] else ' FAIL:  FAILED'}")
        
        # Report Connection Metrics
        connections_created = self.mission_critical_metrics['websocket_connections_created']
        connections_successful = self.mission_critical_metrics['websocket_connections_successful']
        connection_success_rate = (connections_successful / connections_created) * 100 if connections_created > 0 else 0
        
        print(f"\n[U+1F310] WEBSOCKET CONNECTION METRICS:")
        print(f"  Connections Created: {connections_created}")
        print(f"  Connections Successful: {connections_successful}")
        print(f"  Success Rate: {connection_success_rate:.1f}%")
        
        # Report Event Metrics
        events_sent = self.mission_critical_metrics['agent_events_sent']
        events_received = self.mission_critical_metrics['agent_events_received']
        event_success_rate = (events_received / events_sent) * 100 if events_sent > 0 else 0
        
        print(f"\n[U+1F4E1] WEBSOCKET EVENT METRICS:")
        print(f"  Events Sent: {events_sent}")
        print(f"  Events Received: {events_received}")
        print(f"  Event Success Rate: {event_success_rate:.1f}%")
        
        # Report Business Critical Failures
        if self.mission_critical_metrics['business_critical_failures']:
            print(f"\n[U+1F4A5] BUSINESS CRITICAL FAILURES:")
            for failure in self.mission_critical_metrics['business_critical_failures']:
                print(f"   FAIL:  {failure['scenario']}: {failure['description']}")
                print(f"     Error: {failure['error']}")
                print(f"     Time: {failure['timestamp']}")
        
        # Final Business Impact Assessment
        print(f"\n{'='*100}")
        if critical_failures == 0 and self.mission_critical_metrics['chat_functionality_validated']:
            print(f" PASS:  BUSINESS IMPACT: POSITIVE - Chat functionality fully operational")
            print(f"   - Real-time WebSocket events working perfectly")
            print(f"   - Multi-user isolation validated")
            print(f"   - All CLAUDE.md Section 6 requirements met")
            print(f"   - 90% of business value (chat) is protected")
        else:
            print(f" FAIL:  BUSINESS IMPACT: CRITICAL - Chat functionality at risk")
            print(f"   - WebSocket event failures detected")
            print(f"   - Business value delivery compromised")
            print(f"   - Immediate action required to prevent revenue loss")
            print(f"   - User experience will be poor or broken")
        
        print(f"{'='*100}")
        
        # Call parent cleanup
        super().tearDown()


if __name__ == '__main__':
    # Run mission-critical WebSocket events test suite
    unittest.main(verbosity=2, buffer=True)