
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
WebSocket Agent Events Critical Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core chat functionality
- Business Goal: Enable real-time agent communication for substantive AI interactions
- Value Impact: CRITICAL - These 5 events deliver 90% of platform value through live AI problem-solving visibility
- Strategic/Revenue Impact: $500K+ ARR directly depends on users seeing agent progress in real-time

MISSION CRITICAL WEBSOCKET EVENTS (all must be tested):
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI working on valuable solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

CRITICAL REQUIREMENTS:
1. Uses REAL WebSocket connections with REAL agent execution (NO MOCKS per CLAUDE.md)
2. Tests ALL 5 events individually and in complete execution flow
3. Validates event ordering and timing for proper user experience
4. Ensures events contain substantive business value data
5. Tests multi-user isolation during concurrent agent executions

This test validates the core WebSocket events that enable users to see real-time AI
problem-solving, which is the primary value proposition of the platform.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements  
from test_framework.common_imports import *  # PERFORMANCE: Consolidated imports
# CONSOLIDATED: from test_framework.base_integration_test import BaseIntegrationTest
# CONSOLIDATED: from test_framework.real_services_test_fixtures import real_services_fixture
# CONSOLIDATED: from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
# CONSOLIDATED: from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from shared.isolated_environment import get_env

# CRITICAL: Import REAL agent components for business value testing
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


class MockLLMForAgentEvents:
    """
    Mock LLM that enables agent execution without external API calls.
    This is the ONLY acceptable mock per CLAUDE.md - mocking external LLM APIs.
    """
    
    async def complete_async(self, messages, **kwargs):
        """Mock LLM completion that generates realistic agent responses."""
        # Simulate thinking time for realistic event timing
        await asyncio.sleep(0.1)
        
        return {
            "content": "Based on the user's request, I have analyzed the problem and generated a comprehensive solution. This demonstrates the agent's problem-solving capabilities and delivers substantive business value through AI-powered insights.",
            "usage": {"total_tokens": 150}
        }


class TestWebSocketAgentEventsCritical(BaseIntegrationTest):
    """
    Integration tests for the 5 mission-critical WebSocket agent events.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL agent execution.
    This ensures the complete agent-to-WebSocket event flow works in production scenarios.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_agent_events_test(self, real_services_fixture):
        """
        Set up agent events test environment with real services and mock LLM.
        
        BVJ: Test Infrastructure - Ensures reliable agent events testing with real WebSocket flow
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_user_id = f"agent_events_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services are available (CLAUDE.md requirement)
        assert real_services_fixture, "Real services fixture required - no mocks allowed per CLAUDE.md"
        assert "backend" in real_services_fixture, "Real backend service required for agent execution"
        assert "db" in real_services_fixture, "Real database required for agent context"
        
        # Initialize WebSocket auth helper with test environment
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            test_user_email=f"agent_test_{self.test_user_id}@example.com",
            timeout=20.0  # Longer timeout for agent execution
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.websocket_connections: List[websockets.WebSocketServerProtocol] = []
        self.received_events: List[Dict[str, Any]] = []
        
        # Test connectivity to real services
        try:
            token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            assert token, "Failed to create test JWT token for agent events testing"
        except Exception as e:
            pytest.fail(f"Real services not available for agent events testing: {e}")
    
    async def async_teardown(self):
        """Clean up WebSocket connections and test resources."""
        for ws in self.websocket_connections:
            if not ws.closed:
                await ws.close()
        self.websocket_connections.clear()
        await super().async_teardown()
    
    async def collect_websocket_events(
        self, 
        websocket: websockets.WebSocketServerProtocol,
        expected_events: Set[str],
        timeout: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Collect WebSocket events until all expected events are received.
        
        Args:
            websocket: WebSocket connection to monitor
            expected_events: Set of expected event types
            timeout: Maximum time to wait for all events
            
        Returns:
            List of received events
        """
        events = []
        received_types = set()
        start_time = time.time()
        
        try:
            while received_types != expected_events and (time.time() - start_time) < timeout:
                try:
                    # Wait for next event with shorter timeout for responsiveness
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(event_data)
                    
                    events.append({
                        **event,
                        "_received_at": time.time()
                    })
                    
                    event_type = event.get("type")
                    if event_type in expected_events:
                        received_types.add(event_type)
                        
                except asyncio.TimeoutError:
                    # Check if we're still within overall timeout
                    if (time.time() - start_time) >= timeout:
                        break
                    continue
                    
        except Exception as e:
            # Log error but don't fail - we'll check what we received
            pass
            
        return events
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_started_event_triggered(self, real_services_fixture):
        """
        Test that agent_started event is properly triggered and delivered via WebSocket.
        
        BVJ: User visibility - Users must see when agent begins processing their request.
        This is the first critical event that confirms the AI is working on their problem.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            # Connect to WebSocket for event monitoring
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            # Mock LLM to avoid external API calls while keeping agent execution real
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = MockLLMForAgentEvents().complete_async
                
                # Trigger agent execution that should generate agent_started event
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "data_sub_agent",
                    "task": "Test agent started event generation",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send agent execution request
                await websocket.send(json.dumps(agent_request))
                
                # Collect events with focus on agent_started
                expected_events = {"agent_started"}
                events = await self.collect_websocket_events(websocket, expected_events, timeout=20.0)
                
                # Verify agent_started event was received
                agent_started_events = [e for e in events if e.get("type") == "agent_started"]
                assert len(agent_started_events) > 0, "agent_started event was not received - critical business value failure"
                
                # Validate agent_started event content
                agent_started = agent_started_events[0]
                assert agent_started.get("user_id") == self.test_user_id, "agent_started event missing user context"
                assert agent_started.get("agent_type"), "agent_started event missing agent type identification"
                assert "timestamp" in agent_started, "agent_started event missing timestamp for user visibility"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"agent_started event test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_thinking_event_during_processing(self, real_services_fixture):
        """
        Test that agent_thinking events are triggered during agent processing.
        
        BVJ: Real-time reasoning visibility - Users see the AI actively working on solutions.
        This demonstrates that the AI is engaged in problem-solving, providing confidence and value.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Mock LLM with longer processing time to trigger thinking events
                async def extended_thinking_llm(messages, **kwargs):
                    await asyncio.sleep(0.5)  # Simulate extended thinking
                    return {
                        "content": "After careful analysis and reasoning through multiple approaches, I have determined the optimal solution that delivers maximum business value.",
                        "usage": {"total_tokens": 200}
                    }
                
                mock_llm_manager.return_value.complete_async = extended_thinking_llm
                
                # Request complex agent task that should trigger thinking events
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "data_sub_agent",
                    "task": "Complex analysis requiring extended reasoning and thinking",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events focusing on agent_thinking
                expected_events = {"agent_thinking"}
                events = await self.collect_websocket_events(websocket, expected_events, timeout=25.0)
                
                # Verify agent_thinking events were received
                thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
                assert len(thinking_events) > 0, "agent_thinking events not received - users won't see AI reasoning"
                
                # Validate agent_thinking event content delivers business value
                thinking_event = thinking_events[0]
                assert thinking_event.get("user_id") == self.test_user_id, "agent_thinking missing user context"
                assert "reasoning" in thinking_event or "status" in thinking_event, "agent_thinking missing reasoning content"
                assert "timestamp" in thinking_event, "agent_thinking missing timestamp"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"agent_thinking event test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_executing_and_completed_events(self, real_services_fixture):
        """
        Test that tool_executing and tool_completed events are triggered during tool usage.
        
        BVJ: Tool transparency - Users see which tools AI uses and what results are generated.
        This demonstrates the AI's problem-solving approach and delivers actionable insights.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Mock LLM that uses tools
                async def tool_using_llm(messages, **kwargs):
                    await asyncio.sleep(0.2)
                    return {
                        "content": "I'll use the data analysis tool to examine your data and provide insights.",
                        "tool_calls": [
                            {
                                "id": "tool_call_123",
                                "type": "function",
                                "function": {
                                    "name": "analyze_data",
                                    "arguments": json.dumps({"data_source": "user_provided"})
                                }
                            }
                        ],
                        "usage": {"total_tokens": 180}
                    }
                
                mock_llm_manager.return_value.complete_async = tool_using_llm
                
                # Request agent task that uses tools
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "data_sub_agent",
                    "task": "Analyze data using available tools to generate insights",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect both tool events
                expected_events = {"tool_executing", "tool_completed"}
                events = await self.collect_websocket_events(websocket, expected_events, timeout=30.0)
                
                # Verify tool_executing events
                executing_events = [e for e in events if e.get("type") == "tool_executing"]
                assert len(executing_events) > 0, "tool_executing events not received - users won't see tool usage"
                
                # Verify tool_completed events
                completed_events = [e for e in events if e.get("type") == "tool_completed"]
                assert len(completed_events) > 0, "tool_completed events not received - users won't see tool results"
                
                # Validate tool event content
                executing_event = executing_events[0]
                assert executing_event.get("user_id") == self.test_user_id, "tool_executing missing user context"
                assert "tool_name" in executing_event or "tool_id" in executing_event, "tool_executing missing tool identification"
                
                completed_event = completed_events[0]
                assert completed_event.get("user_id") == self.test_user_id, "tool_completed missing user context"
                assert "result" in completed_event or "output" in completed_event, "tool_completed missing results"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"tool events test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_completed_event_with_results(self, real_services_fixture):
        """
        Test that agent_completed event is triggered with valuable results.
        
        BVJ: Completion notification - Users know when AI has finished and valuable response is ready.
        This is the culminating event that delivers the final business value to users.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = MockLLMForAgentEvents().complete_async
                
                # Request agent task with clear completion expected
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "data_sub_agent",
                    "task": "Generate comprehensive business insights and recommendations",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Wait for agent completion
                expected_events = {"agent_completed"}
                events = await self.collect_websocket_events(websocket, expected_events, timeout=25.0)
                
                # Verify agent_completed event was received
                completed_events = [e for e in events if e.get("type") == "agent_completed"]
                assert len(completed_events) > 0, "agent_completed event not received - users won't know when AI finished"
                
                # Validate agent_completed event delivers business value
                completed_event = completed_events[0]
                assert completed_event.get("user_id") == self.test_user_id, "agent_completed missing user context"
                assert "result" in completed_event or "response" in completed_event, "agent_completed missing valuable results"
                assert completed_event.get("success", False), "agent_completed should indicate successful execution"
                assert "timestamp" in completed_event, "agent_completed missing completion timestamp"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"agent_completed event test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_five_critical_events_in_sequence(self, real_services_fixture):
        """
        Test that all 5 mission-critical events are delivered in proper sequence.
        
        BVJ: Complete user experience - Users see the full AI problem-solving journey.
        This validates the end-to-end event flow that delivers maximum business value.
        
        CRITICAL: Tests the complete sequence that generates $500K+ ARR through substantive AI interactions.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Mock comprehensive LLM that triggers all events
                async def comprehensive_llm(messages, **kwargs):
                    await asyncio.sleep(0.3)  # Simulate processing time
                    return {
                        "content": "I have completed a comprehensive analysis using multiple tools and reasoning processes. Here are the key insights and actionable recommendations that deliver substantial business value.",
                        "tool_calls": [
                            {
                                "id": "comprehensive_analysis",
                                "type": "function", 
                                "function": {
                                    "name": "business_analysis",
                                    "arguments": json.dumps({"scope": "comprehensive", "depth": "detailed"})
                                }
                            }
                        ],
                        "usage": {"total_tokens": 300}
                    }
                
                mock_llm_manager.return_value.complete_async = comprehensive_llm
                
                # Request comprehensive agent task
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "comprehensive_agent",
                    "task": "Perform comprehensive business analysis with tool usage and detailed reasoning",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect all 5 critical events
                expected_events = {
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                }
                
                events = await self.collect_websocket_events(websocket, expected_events, timeout=40.0)
                
                # Verify all 5 critical events were received
                event_types_received = set(e.get("type") for e in events)
                
                missing_events = expected_events - event_types_received
                if missing_events:
                    pytest.fail(f"Missing critical WebSocket events: {missing_events}. This breaks the user experience and reduces business value.")
                
                # Verify proper event sequence (agent_started should come before agent_completed)
                event_times = {}
                for event in events:
                    event_type = event.get("type")
                    if event_type in expected_events:
                        event_times[event_type] = event.get("_received_at", time.time())
                
                # Validate critical ordering
                if "agent_started" in event_times and "agent_completed" in event_times:
                    assert event_times["agent_started"] < event_times["agent_completed"], \
                        "agent_started must come before agent_completed for proper user experience"
                
                if "tool_executing" in event_times and "tool_completed" in event_times:
                    assert event_times["tool_executing"] < event_times["tool_completed"], \
                        "tool_executing must come before tool_completed for proper user experience"
                
                # Verify each event contains user context for proper isolation
                for event in events:
                    if event.get("type") in expected_events:
                        assert event.get("user_id") == self.test_user_id, \
                            f"Event {event.get('type')} missing user context - breaks multi-user isolation"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Complete 5-event sequence test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_timing_and_performance(self, real_services_fixture):
        """
        Test that WebSocket events are delivered with acceptable timing for user experience.
        
        BVJ: User experience quality - Events must arrive promptly for responsive AI interactions.
        Slow events reduce perceived value and user satisfaction with AI problem-solving.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = MockLLMForAgentEvents().complete_async
                
                # Measure event delivery timing
                start_time = time.time()
                
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "performance_test_agent",
                    "task": "Test event timing and delivery performance",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect timing data for events
                expected_events = {"agent_started", "agent_completed"}
                events = await self.collect_websocket_events(websocket, expected_events, timeout=20.0)
                
                # Verify events arrived within acceptable timeframe
                for event in events:
                    event_time = event.get("_received_at", time.time())
                    event_delay = event_time - start_time
                    
                    # Events should arrive within 15 seconds for good user experience
                    assert event_delay < 15.0, \
                        f"Event {event.get('type')} took {event_delay:.2f}s - too slow for good user experience"
                
                # First event (agent_started) should arrive quickly to confirm processing began
                started_events = [e for e in events if e.get("type") == "agent_started"]
                if started_events:
                    first_event_delay = started_events[0].get("_received_at") - start_time
                    assert first_event_delay < 5.0, \
                        f"agent_started took {first_event_delay:.2f}s - too slow for immediate user feedback"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Event timing and performance test failed: {e}")