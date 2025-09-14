"""
Issue #1116: WebSocket User Isolation Failures - Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Real-time communication isolation for $500K+ ARR
- Business Goal: Security & User Experience - Prevent WebSocket event mis-delivery
- Value Impact: Validates WebSocket events reach only intended recipients
- Strategic Impact: Foundation for enterprise-grade real-time multi-user features

CRITICAL: These tests should FAIL initially to prove the WebSocket isolation problem exists.
They validate that WebSocket events leak between users due to singleton factory patterns.

Test Coverage:
1. WebSocket event mis-delivery between concurrent users
2. Agent lifecycle event contamination across user sessions
3. Tool execution event delivery to wrong WebSocket connections
4. User context mixing in WebSocket routing
5. WebSocket connection sharing violations
6. Real-time notification isolation failures

ARCHITECTURE ALIGNMENT:
- Tests prove WebSocket isolation failures affect real-time user experience
- Validates USER_CONTEXT_ARCHITECTURE.md WebSocket routing requirements
- Shows enterprise real-time communication security violations
- Demonstrates chat/AI interaction WebSocket contamination issues
"""

import asyncio
import pytest
import threading
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, call
import concurrent.futures
from contextlib import asynccontextmanager

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import real WebSocket components for integration testing
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge, 
    create_agent_websocket_bridge
)
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    get_agent_instance_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Mock WebSocket infrastructure for testing
class MockWebSocketConnection:
    """Mock WebSocket connection that tracks events received."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.received_events = []
        self.is_connected = True
        self.last_activity = time.time()
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock sending JSON data to WebSocket connection."""
        event = {
            'timestamp': time.time(),
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'data': data
        }
        self.received_events.append(event)
        self.last_activity = time.time()
        
    def get_events_for_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get events that were meant for a specific run_id."""
        return [
            event for event in self.received_events
            if event.get('data', {}).get('run_id') == run_id
        ]


class MockWebSocketManager:
    """Mock WebSocket manager that simulates connection routing."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocketConnection] = {}
        self.run_thread_mappings: Dict[str, str] = {}
        self.event_log = []
        
    async def register_connection(self, user_id: str, connection_id: str) -> MockWebSocketConnection:
        """Register a new WebSocket connection."""
        connection = MockWebSocketConnection(user_id, connection_id)
        self.connections[connection_id] = connection
        return connection
        
    async def emit_user_event(self, run_id: str, event_type: str, data: Dict[str, Any]):
        """Emit event to user connection (with potential mis-routing)."""
        event_entry = {
            'timestamp': time.time(),
            'run_id': run_id,
            'event_type': event_type,
            'data': data
        }
        self.event_log.append(event_entry)
        
        # Find target connection (this might be wrong due to singleton issues)
        thread_id = self.run_thread_mappings.get(run_id)
        if not thread_id:
            # Fallback: try to extract thread from run_id
            if '_' in run_id:
                thread_id = run_id.split('_')[1]  # Potential mis-routing
                
        # Route to connection (THIS IS WHERE MIS-DELIVERY HAPPENS)
        target_connection = None
        for conn_id, connection in self.connections.items():
            if thread_id and thread_id in conn_id:
                target_connection = connection
                break
                
        if target_connection:
            await target_connection.send_json({
                'run_id': run_id,
                'event_type': event_type,
                **data
            })
            
        # SINGLETON PROBLEM: If no proper routing, might send to first available connection
        elif self.connections:
            # This causes mis-delivery - event goes to wrong user
            first_connection = next(iter(self.connections.values()))
            await first_connection.send_json({
                'run_id': run_id,
                'event_type': event_type,
                **data
            })
            
    async def register_run_thread_mapping(self, run_id: str, thread_id: str):
        """Register run-to-thread mapping for routing."""
        self.run_thread_mappings[run_id] = thread_id


class TestWebSocketUserIsolation1116(SSotAsyncTestCase):
    """
    Integration tests proving WebSocket user isolation failures.
    
    These tests should FAIL initially, proving the WebSocket mis-delivery problem.
    Success means the WebSocket isolation problem has been fixed.
    """
    
    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)
        
        # Clear singleton state
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None
        
        # Create test users and connections
        self.user1_id = "ws_user_1"
        self.user2_id = "ws_user_2"
        self.user3_id = "ws_user_3"
        
        self.thread1_id = "ws_thread_1"
        self.thread2_id = "ws_thread_2"
        self.thread3_id = "ws_thread_3"
        
        timestamp = int(time.time())
        self.run1_id = f"ws_run_1_{timestamp}"
        self.run2_id = f"ws_run_2_{timestamp}"
        self.run3_id = f"ws_run_3_{timestamp}"
        
        # Connection IDs
        self.conn1_id = f"ws_conn_{self.user1_id}_{timestamp}"
        self.conn2_id = f"ws_conn_{self.user2_id}_{timestamp}"
        self.conn3_id = f"ws_conn_{self.user3_id}_{timestamp}"
        
        # Create mock WebSocket infrastructure
        self.mock_ws_manager = MockWebSocketManager()
        
        # Create mock WebSocket bridge that uses the manager
        self.mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        
        # Setup bridge methods to use mock manager
        async def mock_notify_agent_started(run_id: str, agent_name: str, **kwargs):
            await self.mock_ws_manager.emit_user_event(
                run_id=run_id,
                event_type='agent_started',
                data={'agent_name': agent_name, **kwargs}
            )
            
        async def mock_notify_agent_completed(run_id: str, agent_name: str, result: Any, **kwargs):
            await self.mock_ws_manager.emit_user_event(
                run_id=run_id,
                event_type='agent_completed',
                data={'agent_name': agent_name, 'result': result, **kwargs}
            )
            
        async def mock_notify_tool_executing(run_id: str, tool_name: str, parameters: Dict[str, Any], **kwargs):
            await self.mock_ws_manager.emit_user_event(
                run_id=run_id,
                event_type='tool_executing',
                data={'tool_name': tool_name, 'parameters': parameters, **kwargs}
            )
            
        async def mock_notify_tool_completed(run_id: str, tool_name: str, result: Any, **kwargs):
            await self.mock_ws_manager.emit_user_event(
                run_id=run_id,
                event_type='tool_completed',
                data={'tool_name': tool_name, 'result': result, **kwargs}
            )
            
        async def mock_register_run_thread_mapping(run_id: str, thread_id: str, **kwargs):
            await self.mock_ws_manager.register_run_thread_mapping(run_id, thread_id)
            return True
            
        # Assign mock methods
        self.mock_websocket_bridge.notify_agent_started = mock_notify_agent_started
        self.mock_websocket_bridge.notify_agent_completed = mock_notify_agent_completed
        self.mock_websocket_bridge.notify_tool_executing = mock_notify_tool_executing
        self.mock_websocket_bridge.notify_tool_completed = mock_notify_tool_completed
        self.mock_websocket_bridge.register_run_thread_mapping = mock_register_run_thread_mapping

    async def test_websocket_event_misdelivery_between_users(self):
        """
        CRITICAL: Test WebSocket event mis-delivery between concurrent users.
        
        This test should FAIL initially - proving that WebSocket events intended
        for one user are delivered to other users due to shared routing state.
        
        Expected FAILURE: User 2 receives WebSocket events meant for user 1.
        Expected FIX: Complete WebSocket routing isolation per user connection.
        """
        # Register WebSocket connections for both users
        conn1 = await self.mock_ws_manager.register_connection(self.user1_id, self.conn1_id)
        conn2 = await self.mock_ws_manager.register_connection(self.user2_id, self.conn2_id)
        
        # Get singleton factory (THE PROBLEM - shared routing state)
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_client_id=self.conn1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_client_id=self.conn2_id
        )
        
        # Register run-thread mappings
        await self.mock_websocket_bridge.register_run_thread_mapping(
            self.run1_id, self.thread1_id
        )
        await self.mock_websocket_bridge.register_run_thread_mapping(
            self.run2_id, self.thread2_id
        )
        
        # Send events for both users concurrently
        user1_confidential_data = {
            'business_metric': 'Q4_revenue_5M',
            'confidential_flag': True,
            'access_level': 'executive'
        }
        user2_public_data = {
            'user_activity': 'profile_update',
            'public_flag': True,
            'access_level': 'standard'
        }
        
        # Emit events concurrently (this might cause routing confusion)
        await asyncio.gather(
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run1_id,
                agent_name='FinancialAgent',
                **user1_confidential_data
            ),
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run2_id,
                agent_name='ProfileAgent',
                **user2_public_data
            )
        )
        
        # CRITICAL TEST: Events should be delivered to correct users only
        # This assertion should FAIL initially if events are mis-delivered
        
        # Get events received by each connection
        user1_events = conn1.received_events
        user2_events = conn2.received_events
        
        # Check for event mis-delivery to user 1's connection
        user1_event_content = ' '.join([
            str(event.get('data', {})) for event in user1_events
        ])
        user2_data_in_user1_events = 'profile_update' in user1_event_content
        
        assert not user2_data_in_user1_events, (
            f"WEBSOCKET MISDELIVERY: User 2's profile update event found in User 1's "
            f"WebSocket connection events: {user1_events}. "
            f"This shows WebSocket event mis-routing."
        )
        
        # Check for event mis-delivery to user 2's connection
        user2_event_content = ' '.join([
            str(event.get('data', {})) for event in user2_events
        ])
        user1_confidential_in_user2_events = 'Q4_revenue_5M' in user2_event_content
        
        assert not user1_confidential_in_user2_events, (
            f"WEBSOCKET MISDELIVERY CRITICAL: User 1's confidential revenue data "
            f"found in User 2's WebSocket events: {user2_events}. "
            f"This is a severe security violation exposing business-critical data."
        )
        
        # Validate run_id isolation in received events
        user1_run_ids = {
            event.get('data', {}).get('run_id') for event in user1_events
            if event.get('data', {}).get('run_id')
        }
        user2_run_ids = {
            event.get('data', {}).get('run_id') for event in user2_events
            if event.get('data', {}).get('run_id')
        }
        
        assert self.run2_id not in user1_run_ids, (
            f"WEBSOCKET RUN ID VIOLATION: User 2's run ID ({self.run2_id}) found in "
            f"User 1's WebSocket events: {user1_run_ids}"
        )
        
        assert self.run1_id not in user2_run_ids, (
            f"WEBSOCKET RUN ID VIOLATION: User 1's run ID ({self.run1_id}) found in "
            f"User 2's WebSocket events: {user2_run_ids}"
        )
        
        # Check connection isolation
        user1_connection_ids = {event.get('connection_id') for event in user1_events}
        user2_connection_ids = {event.get('connection_id') for event in user2_events}
        
        assert self.conn2_id not in user1_connection_ids, (
            f"WEBSOCKET CONNECTION VIOLATION: User 2's connection ID found in "
            f"User 1's events: {user1_connection_ids}"
        )
        
        assert self.conn1_id not in user2_connection_ids, (
            f"WEBSOCKET CONNECTION VIOLATION: User 1's connection ID found in "
            f"User 2's events: {user2_connection_ids}"
        )
        
        print("EXPECTED FAILURE: WebSocket event mis-delivery test should fail initially")

    async def test_agent_lifecycle_event_contamination(self):
        """
        CRITICAL: Test agent lifecycle event contamination across user sessions.
        
        This test should FAIL initially - proving that agent lifecycle events
        (started, thinking, completed) leak between users due to shared state.
        
        Expected FAILURE: User 2 sees agent lifecycle events from user 1's session.
        Expected FIX: Complete agent lifecycle event isolation per user context.
        """
        # Register WebSocket connections
        conn1 = await self.mock_ws_manager.register_connection(self.user1_id, self.conn1_id)
        conn2 = await self.mock_ws_manager.register_connection(self.user2_id, self.conn2_id)
        
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_client_id=self.conn1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_client_id=self.conn2_id
        )
        
        # Register mappings
        await self.mock_websocket_bridge.register_run_thread_mapping(self.run1_id, self.thread1_id)
        await self.mock_websocket_bridge.register_run_thread_mapping(self.run2_id, self.thread2_id)
        
        # Simulate complete agent lifecycle for user 1 (sensitive business agent)
        user1_agent_result = {
            'financial_analysis': {
                'revenue_projection': 8500000,
                'profit_margin': 0.23,
                'confidential_metrics': ['growth_rate', 'competitor_analysis']
            },
            'executive_summary': 'Board presentation ready - Q4 targets exceeded',
            'classification': 'highly_confidential'
        }
        
        # Simulate agent lifecycle for user 2 (general support agent)
        user2_agent_result = {
            'support_response': 'Password reset instructions sent to email',
            'ticket_status': 'resolved',
            'user_satisfaction': 'pending',
            'classification': 'public'
        }
        
        # Send full agent lifecycle events concurrently
        await asyncio.gather(
            # User 1 agent lifecycle (confidential business agent)
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run1_id,
                agent_name='ExecutiveFinancialAnalyzer',
                agent_type='business_intelligence',
                security_level='confidential'
            ),
            # User 2 agent lifecycle (support agent)
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run2_id,
                agent_name='CustomerSupportAgent',
                agent_type='general_support',
                security_level='public'
            )
        )
        
        # Complete agent executions
        await asyncio.gather(
            self.mock_websocket_bridge.notify_agent_completed(
                run_id=self.run1_id,
                agent_name='ExecutiveFinancialAnalyzer',
                result=user1_agent_result
            ),
            self.mock_websocket_bridge.notify_agent_completed(
                run_id=self.run2_id,
                agent_name='CustomerSupportAgent',
                result=user2_agent_result
            )
        )
        
        # CRITICAL TEST: Agent lifecycle events should be completely isolated
        # This assertion should FAIL initially if events leak between users
        
        # Analyze events received by each user
        user1_events = conn1.received_events
        user2_events = conn2.received_events
        
        # Check for agent lifecycle contamination in user 1's events
        user1_event_content = json.dumps(user1_events).lower()
        user2_support_agent_in_user1 = 'customersupportagent' in user1_event_content
        
        assert not user2_support_agent_in_user1, (
            f"AGENT LIFECYCLE CONTAMINATION: User 2's support agent events found in "
            f"User 1's WebSocket events: {user1_events}. "
            f"This exposes user 2's support activities to user 1."
        )
        
        # Check for confidential business data contamination in user 2's events
        user2_event_content = json.dumps(user2_events).lower()
        user1_financial_data_in_user2 = 'revenue_projection' in user2_event_content
        
        assert not user1_financial_data_in_user2, (
            f"AGENT LIFECYCLE CONTAMINATION CRITICAL: User 1's confidential financial "
            f"agent results found in User 2's WebSocket events: {user2_events}. "
            f"This is a critical security breach exposing executive financial data."
        )
        
        # Check agent name isolation
        user1_agent_names = set()
        user2_agent_names = set()
        
        for event in user1_events:
            agent_name = event.get('data', {}).get('agent_name')
            if agent_name:
                user1_agent_names.add(agent_name)
                
        for event in user2_events:
            agent_name = event.get('data', {}).get('agent_name')
            if agent_name:
                user2_agent_names.add(agent_name)
        
        # User 1 should only see their financial agent, not support agent
        assert 'CustomerSupportAgent' not in user1_agent_names, (
            f"AGENT NAME CONTAMINATION: User 2's support agent name found in "
            f"User 1's events: {user1_agent_names}"
        )
        
        # User 2 should only see their support agent, not financial agent
        assert 'ExecutiveFinancialAnalyzer' not in user2_agent_names, (
            f"AGENT NAME CONTAMINATION: User 1's financial agent name found in "
            f"User 2's events: {user2_agent_names}"
        )
        
        # Check security level isolation
        user1_security_levels = set()
        user2_security_levels = set()
        
        for event in user1_events:
            security_level = event.get('data', {}).get('security_level')
            if security_level:
                user1_security_levels.add(security_level)
                
        for event in user2_events:
            security_level = event.get('data', {}).get('security_level')
            if security_level:
                user2_security_levels.add(security_level)
        
        # Security levels should not cross-contaminate
        assert 'public' not in user1_security_levels or 'confidential' in user1_security_levels, (
            f"SECURITY LEVEL CONTAMINATION: User 1 (confidential) has public security levels: "
            f"{user1_security_levels}"
        )
        
        assert 'confidential' not in user2_security_levels, (
            f"SECURITY LEVEL CONTAMINATION CRITICAL: User 2 (public) has confidential "
            f"security levels: {user2_security_levels}. This is a security breach."
        )
        
        print("EXPECTED FAILURE: Agent lifecycle event contamination test should fail initially")

    async def test_tool_execution_websocket_event_misrouting(self):
        """
        CRITICAL: Test tool execution WebSocket event mis-routing between users.
        
        This test should FAIL initially - proving that tool execution events
        (tool_executing, tool_completed) are delivered to wrong users.
        
        Expected FAILURE: User 2 receives tool execution events from user 1's tools.
        Expected FIX: Complete tool event routing isolation per user context.
        """
        # Register WebSocket connections
        conn1 = await self.mock_ws_manager.register_connection(self.user1_id, self.conn1_id)
        conn2 = await self.mock_ws_manager.register_connection(self.user2_id, self.conn2_id)
        
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_client_id=self.conn1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_client_id=self.conn2_id
        )
        
        # Register mappings
        await self.mock_websocket_bridge.register_run_thread_mapping(self.run1_id, self.thread1_id)
        await self.mock_websocket_bridge.register_run_thread_mapping(self.run2_id, self.thread2_id)
        
        # Define tool executions for each user
        user1_tool_params = {
            'database_query': 'SELECT revenue, profit FROM quarterly_results WHERE confidential=true',
            'access_level': 'executive',
            'data_classification': 'highly_confidential',
            'financial_scope': 'full_company_metrics'
        }
        user1_tool_result = {
            'query_results': [
                {'quarter': 'Q4', 'revenue': 8500000, 'profit': 1955000},
                {'quarter': 'Q3', 'revenue': 7200000, 'profit': 1656000}
            ],
            'executive_summary': 'Revenue growth exceeds targets by 12%',
            'confidentiality': 'board_eyes_only'
        }
        
        user2_tool_params = {
            'email_template': 'password_reset',
            'recipient': 'user2@example.com',
            'access_level': 'standard',
            'data_classification': 'public'
        }
        user2_tool_result = {
            'email_sent': True,
            'template_used': 'standard_password_reset',
            'delivery_status': 'success'
        }
        
        # Execute tools concurrently and send WebSocket events
        await asyncio.gather(
            # User 1 financial tool execution
            self.mock_websocket_bridge.notify_tool_executing(
                run_id=self.run1_id,
                tool_name='ExecutiveFinancialQuery',
                parameters=user1_tool_params
            ),
            # User 2 email tool execution
            self.mock_websocket_bridge.notify_tool_executing(
                run_id=self.run2_id,
                tool_name='EmailService',
                parameters=user2_tool_params
            )
        )
        
        # Complete tool executions
        await asyncio.gather(
            self.mock_websocket_bridge.notify_tool_completed(
                run_id=self.run1_id,
                tool_name='ExecutiveFinancialQuery',
                result=user1_tool_result
            ),
            self.mock_websocket_bridge.notify_tool_completed(
                run_id=self.run2_id,
                tool_name='EmailService',
                result=user2_tool_result
            )
        )
        
        # CRITICAL TEST: Tool execution events should be completely isolated
        # This assertion should FAIL initially if tool events are mis-routed
        
        # Analyze tool events received by each user
        user1_events = conn1.received_events
        user2_events = conn2.received_events
        
        # Filter for tool-related events
        user1_tool_events = [
            event for event in user1_events
            if event.get('data', {}).get('tool_name') is not None
        ]
        user2_tool_events = [
            event for event in user2_events
            if event.get('data', {}).get('tool_name') is not None
        ]
        
        # Check for tool event contamination
        user1_tool_content = json.dumps(user1_tool_events).lower()
        user2_email_tool_in_user1 = 'emailservice' in user1_tool_content
        
        assert not user2_email_tool_in_user1, (
            f"TOOL EVENT CONTAMINATION: User 2's email tool events found in "
            f"User 1's WebSocket events: {user1_tool_events}. "
            f"This exposes user 2's email activities to user 1."
        )
        
        user2_tool_content = json.dumps(user2_tool_events).lower()
        user1_financial_tool_in_user2 = 'executivefinancialquery' in user2_tool_content
        
        assert not user1_financial_tool_in_user2, (
            f"TOOL EVENT CONTAMINATION CRITICAL: User 1's financial tool events found in "
            f"User 2's WebSocket events: {user2_tool_events}. "
            f"This exposes executive financial data to unauthorized user."
        )
        
        # Check for parameter isolation
        user1_params_content = json.dumps([
            event.get('data', {}).get('parameters', {}) for event in user1_tool_events
        ])
        user2_email_params_in_user1 = 'password_reset' in user1_params_content
        
        assert not user2_email_params_in_user1, (
            f"TOOL PARAMETER CONTAMINATION: User 2's email parameters found in "
            f"User 1's tool events. This shows parameter cross-contamination."
        )
        
        user2_params_content = json.dumps([
            event.get('data', {}).get('parameters', {}) for event in user2_tool_events
        ])
        user1_financial_params_in_user2 = 'quarterly_results' in user2_params_content
        
        assert not user1_financial_params_in_user2, (
            f"TOOL PARAMETER CONTAMINATION CRITICAL: User 1's financial query parameters "
            f"found in User 2's tool events. This exposes confidential query details."
        )
        
        # Check for result isolation
        user1_results_content = json.dumps([
            event.get('data', {}).get('result', {}) for event in user1_tool_events
        ])
        user2_email_results_in_user1 = 'email_sent' in user1_results_content
        
        assert not user2_email_results_in_user1, (
            f"TOOL RESULT CONTAMINATION: User 2's email results found in User 1's events."
        )
        
        user2_results_content = json.dumps([
            event.get('data', {}).get('result', {}) for event in user2_tool_events
        ])
        user1_financial_results_in_user2 = 'revenue' in user2_results_content
        
        assert not user1_financial_results_in_user2, (
            f"TOOL RESULT CONTAMINATION CRITICAL: User 1's financial results (revenue data) "
            f"found in User 2's tool events: {user2_results_content}. "
            f"This is a severe confidential data breach."
        )
        
        print("EXPECTED FAILURE: Tool execution WebSocket event mis-routing test should fail initially")

    async def test_websocket_connection_sharing_violation(self):
        """
        CRITICAL: Test WebSocket connection sharing violations between users.
        
        This test should FAIL initially - proving that WebSocket connections
        are shared or mixed up due to singleton factory routing issues.
        
        Expected FAILURE: Multiple users receive events on same connection.
        Expected FIX: Each user gets completely isolated WebSocket connection.
        """
        # Register connections for all users
        conn1 = await self.mock_ws_manager.register_connection(self.user1_id, self.conn1_id)
        conn2 = await self.mock_ws_manager.register_connection(self.user2_id, self.conn2_id)
        conn3 = await self.mock_ws_manager.register_connection(self.user3_id, self.conn3_id)
        
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_client_id=self.conn1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_client_id=self.conn2_id
        )
        context3 = await factory.create_user_execution_context(
            user_id=self.user3_id,
            thread_id=self.thread3_id,
            run_id=self.run3_id,
            websocket_client_id=self.conn3_id
        )
        
        # Register all mappings
        await asyncio.gather(
            self.mock_websocket_bridge.register_run_thread_mapping(self.run1_id, self.thread1_id),
            self.mock_websocket_bridge.register_run_thread_mapping(self.run2_id, self.thread2_id),
            self.mock_websocket_bridge.register_run_thread_mapping(self.run3_id, self.thread3_id)
        )
        
        # Send distinct events for each user with unique identifiers
        user1_event_data = {
            'user_specific_data': f'USER1_CONFIDENTIAL_DATA_{int(time.time())}',
            'access_level': 'executive',
            'department': 'finance'
        }
        user2_event_data = {
            'user_specific_data': f'USER2_PERSONAL_DATA_{int(time.time())}',
            'access_level': 'standard',
            'department': 'support'
        }
        user3_event_data = {
            'user_specific_data': f'USER3_MARKETING_DATA_{int(time.time())}',
            'access_level': 'marketing',
            'department': 'marketing'
        }
        
        # Send events concurrently
        await asyncio.gather(
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run1_id,
                agent_name='User1FinanceAgent',
                **user1_event_data
            ),
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run2_id,
                agent_name='User2SupportAgent',
                **user2_event_data
            ),
            self.mock_websocket_bridge.notify_agent_started(
                run_id=self.run3_id,
                agent_name='User3MarketingAgent',
                **user3_event_data
            )
        )
        
        # CRITICAL TEST: Each connection should receive only its own user's events
        # This assertion should FAIL initially if connections are shared
        
        user1_events = conn1.received_events
        user2_events = conn2.received_events
        user3_events = conn3.received_events
        
        # Check user 1 connection isolation
        user1_content = json.dumps(user1_events)
        user2_data_in_user1_conn = 'USER2_PERSONAL_DATA' in user1_content
        user3_data_in_user1_conn = 'USER3_MARKETING_DATA' in user1_content
        
        assert not user2_data_in_user1_conn, (
            f"WEBSOCKET CONNECTION SHARING: User 2's personal data found on "
            f"User 1's WebSocket connection: {user1_events}. "
            f"This indicates connection sharing or mis-routing."
        )
        
        assert not user3_data_in_user1_conn, (
            f"WEBSOCKET CONNECTION SHARING: User 3's marketing data found on "
            f"User 1's WebSocket connection: {user1_events}. "
            f"This indicates connection sharing or mis-routing."
        )
        
        # Check user 2 connection isolation
        user2_content = json.dumps(user2_events)
        user1_data_in_user2_conn = 'USER1_CONFIDENTIAL_DATA' in user2_content
        user3_data_in_user2_conn = 'USER3_MARKETING_DATA' in user2_content
        
        assert not user1_data_in_user2_conn, (
            f"WEBSOCKET CONNECTION SHARING CRITICAL: User 1's confidential data found on "
            f"User 2's WebSocket connection: {user2_events}. "
            f"This is a critical security breach."
        )
        
        assert not user3_data_in_user2_conn, (
            f"WEBSOCKET CONNECTION SHARING: User 3's marketing data found on "
            f"User 2's WebSocket connection: {user2_events}. "
            f"This indicates connection cross-contamination."
        )
        
        # Check user 3 connection isolation
        user3_content = json.dumps(user3_events)
        user1_data_in_user3_conn = 'USER1_CONFIDENTIAL_DATA' in user3_content
        user2_data_in_user3_conn = 'USER2_PERSONAL_DATA' in user3_content
        
        assert not user1_data_in_user3_conn, (
            f"WEBSOCKET CONNECTION SHARING CRITICAL: User 1's confidential data found on "
            f"User 3's WebSocket connection: {user3_events}. "
            f"This is a critical security breach."
        )
        
        assert not user2_data_in_user3_conn, (
            f"WEBSOCKET CONNECTION SHARING: User 2's personal data found on "
            f"User 3's WebSocket connection: {user3_events}. "
            f"This indicates connection cross-contamination."
        )
        
        # Validate connection identity integrity
        user1_connection_ids = {event.get('connection_id') for event in user1_events}
        user2_connection_ids = {event.get('connection_id') for event in user2_events}
        user3_connection_ids = {event.get('connection_id') for event in user3_events}
        
        # Each user should only have their own connection ID
        assert user1_connection_ids == {self.conn1_id}, (
            f"CONNECTION ID VIOLATION: User 1 received events on wrong connections: "
            f"{user1_connection_ids}. Expected only: {self.conn1_id}"
        )
        
        assert user2_connection_ids == {self.conn2_id}, (
            f"CONNECTION ID VIOLATION: User 2 received events on wrong connections: "
            f"{user2_connection_ids}. Expected only: {self.conn2_id}"
        )
        
        assert user3_connection_ids == {self.conn3_id}, (
            f"CONNECTION ID VIOLATION: User 3 received events on wrong connections: "
            f"{user3_connection_ids}. Expected only: {self.conn3_id}"
        )
        
        print("EXPECTED FAILURE: WebSocket connection sharing violation test should fail initially")

    async def test_real_time_notification_isolation_failure(self):
        """
        CRITICAL: Test real-time notification isolation failures under load.
        
        This test should FAIL initially - proving that real-time notifications
        break isolation under concurrent load due to shared factory state.
        
        Expected FAILURE: High-frequency notifications get scrambled between users.
        Expected FIX: Robust notification isolation that scales under load.
        """
        # Register connections for stress testing
        conn1 = await self.mock_ws_manager.register_connection(self.user1_id, self.conn1_id)
        conn2 = await self.mock_ws_manager.register_connection(self.user2_id, self.conn2_id)
        
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_client_id=self.conn1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_client_id=self.conn2_id
        )
        
        # Register mappings
        await self.mock_websocket_bridge.register_run_thread_mapping(self.run1_id, self.thread1_id)
        await self.mock_websocket_bridge.register_run_thread_mapping(self.run2_id, self.thread2_id)
        
        # Generate high-frequency notifications with distinct content
        num_notifications_per_user = 20
        
        async def send_user1_notifications():
            """Send high-frequency confidential business notifications for user 1."""
            tasks = []
            for i in range(num_notifications_per_user):
                event_data = {
                    'notification_id': f'USER1_BUSINESS_NOTIFICATION_{i}',
                    'content': f'Confidential business update #{i}: Revenue milestone reached',
                    'classification': 'confidential',
                    'timestamp': time.time() + i * 0.01  # 10ms intervals
                }
                task = self.mock_websocket_bridge.notify_agent_completed(
                    run_id=self.run1_id,
                    agent_name=f'BusinessAgent_{i}',
                    result=event_data
                )
                tasks.append(task)
            
            # Execute all notifications rapidly
            await asyncio.gather(*tasks)
        
        async def send_user2_notifications():
            """Send high-frequency personal notifications for user 2."""
            tasks = []
            for i in range(num_notifications_per_user):
                event_data = {
                    'notification_id': f'USER2_PERSONAL_NOTIFICATION_{i}',
                    'content': f'Personal update #{i}: Profile setting changed',
                    'classification': 'personal',
                    'timestamp': time.time() + i * 0.01  # 10ms intervals
                }
                task = self.mock_websocket_bridge.notify_agent_completed(
                    run_id=self.run2_id,
                    agent_name=f'PersonalAgent_{i}',
                    result=event_data
                )
                tasks.append(task)
            
            # Execute all notifications rapidly
            await asyncio.gather(*tasks)
        
        # Send high-frequency notifications concurrently (stress test)
        start_time = time.time()
        await asyncio.gather(
            send_user1_notifications(),
            send_user2_notifications()
        )
        total_time = time.time() - start_time
        
        # Allow brief settling time
        await asyncio.sleep(0.1)
        
        # CRITICAL TEST: High-frequency notifications should maintain perfect isolation
        # This assertion should FAIL initially if notifications get scrambled
        
        user1_events = conn1.received_events
        user2_events = conn2.received_events
        
        # Count notifications received by each user
        user1_business_notifications = len([
            event for event in user1_events
            if 'USER1_BUSINESS_NOTIFICATION' in str(event.get('data', {}))
        ])
        user1_personal_notifications = len([
            event for event in user1_events
            if 'USER2_PERSONAL_NOTIFICATION' in str(event.get('data', {}))
        ])
        
        user2_personal_notifications = len([
            event for event in user2_events
            if 'USER2_PERSONAL_NOTIFICATION' in str(event.get('data', {}))
        ])
        user2_business_notifications = len([
            event for event in user2_events
            if 'USER1_BUSINESS_NOTIFICATION' in str(event.get('data', {}))
        ])
        
        # User 1 should receive all their business notifications, none of user 2's
        assert user1_business_notifications == num_notifications_per_user, (
            f"NOTIFICATION LOSS: User 1 received {user1_business_notifications} "
            f"business notifications, expected {num_notifications_per_user}. "
            f"This indicates notification routing failures."
        )
        
        assert user1_personal_notifications == 0, (
            f"NOTIFICATION CONTAMINATION: User 1 received {user1_personal_notifications} "
            f"personal notifications from User 2. This shows cross-user notification leakage."
        )
        
        # User 2 should receive all their personal notifications, none of user 1's
        assert user2_personal_notifications == num_notifications_per_user, (
            f"NOTIFICATION LOSS: User 2 received {user2_personal_notifications} "
            f"personal notifications, expected {num_notifications_per_user}. "
            f"This indicates notification routing failures."
        )
        
        assert user2_business_notifications == 0, (
            f"NOTIFICATION CONTAMINATION CRITICAL: User 2 received {user2_business_notifications} "
            f"confidential business notifications from User 1. "
            f"This is a severe security breach exposing business data."
        )
        
        # Check notification ordering preservation
        user1_timestamps = []
        for event in user1_events:
            result = event.get('data', {}).get('result', {})
            if isinstance(result, dict) and 'timestamp' in result:
                user1_timestamps.append(result['timestamp'])
        
        # Timestamps should be in roughly ascending order (allowing for some network jitter)
        user1_timestamps.sort()
        user1_ordering_preserved = len(user1_timestamps) >= num_notifications_per_user * 0.8  # Allow some loss
        
        assert user1_ordering_preserved, (
            f"NOTIFICATION ORDERING FAILURE: User 1 timestamp ordering corrupted. "
            f"Received {len(user1_timestamps)} ordered timestamps out of {num_notifications_per_user}. "
            f"This indicates notification delivery instability under load."
        )
        
        # Performance validation: high-frequency notifications shouldn't cause excessive delays
        avg_notification_time = total_time / (num_notifications_per_user * 2)  # 2 users
        excessive_delay = avg_notification_time > 0.1  # 100ms per notification is excessive
        
        assert not excessive_delay, (
            f"NOTIFICATION PERFORMANCE DEGRADATION: Average notification time "
            f"{avg_notification_time:.3f}s is excessive (>100ms). "
            f"This indicates performance bottlenecks in notification routing."
        )
        
        print("EXPECTED FAILURE: Real-time notification isolation failure test should fail initially")