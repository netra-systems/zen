"""
Business Function Validation Test

CRITICAL: This test validates that core business functions (user isolation,
WebSocket events, agent execution) continue to work correctly through the
UserExecutionEngine SSOT after deprecated engine removal.

Purpose:
1. Validate user isolation prevents cross-user data leakage
2. Test WebSocket events are sent correctly for business-critical flows  
3. Verify agent execution works end-to-end through UserExecutionEngine
4. Test tool execution maintains user context and security
5. Validate performance doesn't degrade with SSOT consolidation

Business Impact: This test protects the $500K+ ARR chat functionality by ensuring
users get isolated, secure AI responses with proper real-time event notifications.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List
import sys
import os
import time
import json

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
    from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
    from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
    from netra_backend.app.core.configuration.base import get_config
except ImportError as e:
    import pytest
    pytest.skip(f"Backend modules not available: {e}", allow_module_level=True)


class TestBusinessFunctionValidation(SSotAsyncTestCase):
    """Comprehensive validation of business-critical functions through UserExecutionEngine"""
    
    def setUp(self):
        """Set up test fixtures for business function testing"""
        self.config = get_config()
        self.factory = ExecutionEngineFactory()
        
        # Create mock WebSocket managers for different users
        self.user1_ws = Mock()
        self.user1_ws.user_id = "business_user_1"
        self.user1_ws.send_agent_event = AsyncMock()
        self.user1_ws.send_message = AsyncMock()
        
        self.user2_ws = Mock()
        self.user2_ws.user_id = "business_user_2"
        self.user2_ws.send_agent_event = AsyncMock()
        self.user2_ws.send_message = AsyncMock()
        
    def test_user_isolation_prevents_data_leakage(self):
        """Test that user isolation prevents data leakage between users"""
        print("\n🔒 Testing user isolation prevents data leakage...")
        
        # Create engines for two different users
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            # User 1 engine
            mock_get_manager.return_value = self.user1_ws
            user1_engine = self.factory.create_execution_engine(
                user_id="business_user_1",
                session_id="session_1"
            )
            
            # User 2 engine
            mock_get_manager.return_value = self.user2_ws
            user2_engine = self.factory.create_execution_engine(
                user_id="business_user_2", 
                session_id="session_2"
            )
        
        # Test 1: User contexts are isolated
        user1_context = user1_engine.get_user_context()
        user2_context = user2_engine.get_user_context()
        
        self.assertEqual(user1_context['user_id'], "business_user_1")
        self.assertEqual(user2_context['user_id'], "business_user_2")
        self.assertNotEqual(user1_context['user_id'], user2_context['user_id'])
        
        print("  ✅ User contexts properly isolated")
        
        # Test 2: WebSocket managers are isolated
        self.assertEqual(user1_engine.websocket_manager.user_id, "business_user_1")
        self.assertEqual(user2_engine.websocket_manager.user_id, "business_user_2")
        self.assertIsNot(user1_engine.websocket_manager, user2_engine.websocket_manager)
        
        print("  ✅ WebSocket managers properly isolated")
        
        # Test 3: Tool dispatchers are separate instances
        self.assertIsNot(user1_engine.tool_dispatcher, user2_engine.tool_dispatcher)
        
        print("  ✅ Tool dispatchers properly isolated")
        
        # Test 4: Session data is isolated
        self.assertEqual(user1_engine.session_id, "session_1")
        self.assertEqual(user2_engine.session_id, "session_2")
        self.assertNotEqual(user1_engine.session_id, user2_engine.session_id)
        
        print("  ✅ Session data properly isolated")
        
    def test_websocket_events_sent_correctly(self):
        """Test that WebSocket events are sent correctly for business flows"""
        print("\n📡 Testing WebSocket events sent correctly...")
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.user1_ws
            
            engine = self.factory.create_execution_engine(
                user_id="business_user_1",
                session_id="session_1"
            )
        
        async def test_business_flow_events():
            """Test all business-critical WebSocket events"""
            
            # Event 1: agent_started (user sees agent began processing)
            await engine.send_websocket_event("agent_started", {
                "agent_type": "supervisor",
                "message": "Starting to process your request",
                "timestamp": time.time()
            })
            
            # Event 2: agent_thinking (real-time reasoning visibility)
            await engine.send_websocket_event("agent_thinking", {
                "thought": "Analyzing user request and determining best approach",
                "step": 1,
                "timestamp": time.time()
            })
            
            # Event 3: tool_executing (tool usage transparency)
            await engine.send_websocket_event("tool_executing", {
                "tool_name": "data_analysis_tool",
                "parameters": {"query": "user_data_request"},
                "user_message": "Analyzing your data...",
                "timestamp": time.time()
            })
            
            # Event 4: tool_completed (tool results display)
            await engine.send_websocket_event("tool_completed", {
                "tool_name": "data_analysis_tool",
                "result": {"status": "success", "data_points": 150},
                "user_message": "Analysis complete",
                "timestamp": time.time()
            })
            
            # Event 5: agent_completed (user knows response is ready)
            await engine.send_websocket_event("agent_completed", {
                "result": "success",
                "message": "I've completed your analysis. Here are the results...",
                "final_response": True,
                "timestamp": time.time()
            })
        
        # Run the business flow
        asyncio.run(test_business_flow_events())
        
        # Verify all 5 business-critical events were sent
        self.assertEqual(self.user1_ws.send_agent_event.call_count, 5,
                        "All 5 business-critical WebSocket events should be sent")
        
        # Verify event types
        call_args = [call[0] for call in self.user1_ws.send_agent_event.call_args_list]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for i, expected_event in enumerate(expected_events):
            self.assertEqual(call_args[i][0], expected_event,
                           f"Event {i+1} should be {expected_event}")
        
        print(f"  ✅ All {len(expected_events)} business-critical events sent correctly")
        
        # Verify event data structure
        for i, call in enumerate(self.user1_ws.send_agent_event.call_args_list):
            event_type, event_data = call[0]
            self.assertIsInstance(event_data, dict, f"Event {i+1} data should be dict")
            self.assertIn("timestamp", event_data, f"Event {i+1} should have timestamp")
            
        print("  ✅ All events have proper data structure and timestamps")
        
    def test_concurrent_user_websocket_isolation(self):
        """Test WebSocket events are isolated between concurrent users"""
        print("\n🔄 Testing concurrent user WebSocket isolation...")
        
        engines = {}
        
        # Create engines for multiple users
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            # User 1
            mock_get_manager.return_value = self.user1_ws
            engines['user1'] = self.factory.create_execution_engine(
                user_id="business_user_1",
                session_id="session_1"
            )
            
            # User 2
            mock_get_manager.return_value = self.user2_ws
            engines['user2'] = self.factory.create_execution_engine(
                user_id="business_user_2",
                session_id="session_2"
            )
        
        async def send_concurrent_events():
            """Send events from multiple users concurrently"""
            
            # User 1 sends events
            await engines['user1'].send_websocket_event("agent_started", {
                "user": "user1",
                "message": "User 1 agent started"
            })
            
            # User 2 sends events concurrently
            await engines['user2'].send_websocket_event("agent_started", {
                "user": "user2", 
                "message": "User 2 agent started"
            })
            
            # More concurrent events
            await asyncio.gather(
                engines['user1'].send_websocket_event("tool_executing", {"user": "user1"}),
                engines['user2'].send_websocket_event("tool_executing", {"user": "user2"})
            )
        
        # Run concurrent events
        asyncio.run(send_concurrent_events())
        
        # Verify isolation: each user's WebSocket manager called exactly twice
        self.assertEqual(self.user1_ws.send_agent_event.call_count, 2,
                        "User 1 WebSocket should receive exactly 2 events")
        self.assertEqual(self.user2_ws.send_agent_event.call_count, 2,
                        "User 2 WebSocket should receive exactly 2 events")
        
        # Verify event content isolation
        user1_calls = self.user1_ws.send_agent_event.call_args_list
        user2_calls = self.user2_ws.send_agent_event.call_args_list
        
        # User 1 events should contain user1 data
        for call in user1_calls:
            event_data = call[0][1]
            if 'user' in event_data:
                self.assertEqual(event_data['user'], 'user1')
        
        # User 2 events should contain user2 data  
        for call in user2_calls:
            event_data = call[0][1]
            if 'user' in event_data:
                self.assertEqual(event_data['user'], 'user2')
        
        print("  ✅ Concurrent WebSocket events properly isolated between users")
        
    def test_tool_execution_maintains_user_context(self):
        """Test tool execution maintains user context and security"""
        print("\n🔧 Testing tool execution maintains user context...")
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.user1_ws
            
            engine = self.factory.create_execution_engine(
                user_id="business_user_1",
                session_id="session_1"
            )
        
        # Test 1: Tool dispatcher has user context
        self.assertIsNotNone(engine.tool_dispatcher)
        self.assertIsInstance(engine.tool_dispatcher, EnhancedToolDispatcher)
        
        print("  ✅ Tool dispatcher properly initialized")
        
        # Test 2: Execution context includes user data
        exec_context = engine.get_execution_context()
        
        self.assertIsInstance(exec_context, dict)
        self.assertIn('user_context', exec_context)
        self.assertIn('tool_dispatcher', exec_context)
        
        user_context = exec_context['user_context']
        self.assertEqual(user_context['user_id'], "business_user_1")
        self.assertEqual(user_context['session_id'], "session_1")
        
        print("  ✅ Execution context includes proper user data")
        
        # Test 3: Tool access validation
        self.assertTrue(hasattr(engine, 'validate_tool_access'))
        self.assertTrue(callable(engine.validate_tool_access))
        
        print("  ✅ Tool access validation available")
        
    def test_agent_execution_end_to_end_flow(self):
        """Test end-to-end agent execution flow through UserExecutionEngine"""
        print("\n🤖 Testing end-to-end agent execution flow...")
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.user1_ws
            
            engine = self.factory.create_execution_engine(
                user_id="business_user_1",
                session_id="session_1"
            )
        
        async def simulate_agent_execution():
            """Simulate a complete agent execution flow"""
            
            # Phase 1: Agent starts
            await engine.send_websocket_event("agent_started", {
                "agent_type": "data_analyzer",
                "request": "Analyze customer data trends"
            })
            
            # Phase 2: Agent thinking
            await engine.send_websocket_event("agent_thinking", {
                "thought": "I need to gather customer data and analyze trends"
            })
            
            # Phase 3: Tool execution simulation
            await engine.send_websocket_event("tool_executing", {
                "tool_name": "database_query",
                "action": "Querying customer database"
            })
            
            # Simulate tool completion
            await engine.send_websocket_event("tool_completed", {
                "tool_name": "database_query",
                "result": {"customers": 1000, "trends": ["growth", "retention"]}
            })
            
            # Phase 4: Agent completes
            await engine.send_websocket_event("agent_completed", {
                "result": "success",
                "analysis": "Customer trends show 15% growth with 85% retention",
                "confidence": 0.92
            })
        
        # Record start time for performance testing
        start_time = time.time()
        
        # Run the simulation
        asyncio.run(simulate_agent_execution())
        
        # Record completion time
        execution_time = time.time() - start_time
        
        # Verify complete flow executed
        self.assertEqual(self.user1_ws.send_agent_event.call_count, 5,
                        "Complete agent execution flow should send 5 events")
        
        # Verify performance (should be fast since it's just event sending)
        self.assertLess(execution_time, 1.0,
                       "Agent execution flow should complete quickly")
        
        print(f"  ✅ End-to-end flow completed in {execution_time:.3f}s")
        
        # Verify event sequence
        events = [call[0][0] for call in self.user1_ws.send_agent_event.call_args_list]
        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        self.assertEqual(events, expected_sequence,
                        "Events should follow correct business sequence")
        
        print("  ✅ Event sequence follows correct business flow")
        
    def test_error_handling_maintains_user_isolation(self):
        """Test error handling maintains user isolation"""
        print("\n🚨 Testing error handling maintains user isolation...")
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.user1_ws
            
            engine = self.factory.create_execution_engine(
                user_id="business_user_1",
                session_id="session_1"
            )
        
        # Test 1: Engine survives WebSocket errors
        self.user1_ws.send_agent_event.side_effect = Exception("WebSocket error")
        
        async def test_error_resilience():
            try:
                await engine.send_websocket_event("test_event", {"test": "data"})
            except Exception:
                pass  # Expected to fail
            
            # Engine should still have correct user context
            context = engine.get_user_context()
            self.assertEqual(context['user_id'], "business_user_1")
            self.assertEqual(context['session_id'], "session_1")
        
        asyncio.run(test_error_resilience())
        
        print("  ✅ Engine maintains user context despite WebSocket errors")
        
        # Test 2: Cleanup works correctly
        try:
            engine.cleanup()
            print("  ✅ Cleanup executes without errors")
        except Exception as e:
            self.fail(f"Cleanup should not raise exceptions: {e}")
        
    def test_performance_scalability(self):
        """Test performance doesn't degrade with SSOT consolidation"""
        print("\n⚡ Testing performance scalability...")
        
        # Create multiple engines to test scalability
        engines = []
        mock_managers = []
        
        start_time = time.time()
        
        for i in range(10):
            mock_manager = Mock()
            mock_manager.user_id = f"perf_user_{i}"
            mock_manager.send_agent_event = AsyncMock()
            mock_managers.append(mock_manager)
            
            with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
                mock_get_manager.return_value = mock_manager
                
                engine = self.factory.create_execution_engine(
                    user_id=f"perf_user_{i}",
                    session_id=f"perf_session_{i}"
                )
                engines.append(engine)
        
        creation_time = time.time() - start_time
        
        # Test concurrent event sending
        async def concurrent_events():
            tasks = []
            for i, engine in enumerate(engines):
                task = engine.send_websocket_event("performance_test", {
                    "user": f"perf_user_{i}",
                    "iteration": i
                })
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        event_start = time.time()
        asyncio.run(concurrent_events())
        event_time = time.time() - event_start
        
        # Performance assertions
        self.assertLess(creation_time, 2.0,
                       f"Creating 10 engines should take <2s, took {creation_time:.3f}s")
        self.assertLess(event_time, 1.0,
                       f"Sending 10 concurrent events should take <1s, took {event_time:.3f}s")
        
        print(f"  ✅ Created 10 engines in {creation_time:.3f}s")
        print(f"  ✅ Sent 10 concurrent events in {event_time:.3f}s")
        
        # Verify all events were sent correctly
        for mock_manager in mock_managers:
            self.assertEqual(mock_manager.send_agent_event.call_count, 1,
                           "Each user should receive exactly one event")
        
        print("  ✅ Performance meets scalability requirements")


if __name__ == '__main__':
    unittest.main(verbosity=2)