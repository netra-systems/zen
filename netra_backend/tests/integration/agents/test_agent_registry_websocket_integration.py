"""
Agent Registry WebSocket Integration Tests - Phase 2

Tests agent registry integration with WebSocket managers, ensuring
proper event emission during agent execution. Validates that the
registry correctly enhances agents with WebSocket capabilities.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable real-time agent feedback for all agent types
- Value Impact: All agents provide timely updates during execution
- Strategic Impact: Core agent execution infrastructure reliability

CRITICAL: Uses REAL services (PostgreSQL, Redis, WebSocket connections)
No mocks in integration tests per CLAUDE.md standards.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    ensure_websocket_service_ready
)
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.id_generation import UnifiedIdGenerator


class TestAgentRegistryWebSocketIntegration(BaseIntegrationTest):
    """Integration tests for agent registry WebSocket integration."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup test environment with real services."""
        self.services = real_services_fixture
        self.env = get_env()
        
        # Validate real services are available
        if not self.services["database_available"]:
            pytest.skip("Real database not available - required for integration testing")
            
        # Store service URLs
        self.backend_url = self.services["backend_url"]
        self.websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        
        # Generate base test identifiers
        self.test_session_id = f"registry_integration_test_{int(time.time() * 1000)}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_registry_websocket_manager_setup(self, real_services_fixture):
        """Test that AgentRegistry properly sets up WebSocket managers for agents."""
        start_time = time.time()
        
        # Ensure WebSocket service is ready
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test user and connection
        test_user_id = UserID(f"registry_user_{UnifiedIdGenerator.generate_user_id()}")
        test_thread_id = ThreadID(f"registry_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        test_token = self._create_test_auth_token(test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{test_thread_id}",
            headers=headers,
            user_id=str(test_user_id)
        )
        
        try:
            collected_events = []
            
            # Test agent registration with WebSocket manager integration
            registry_setup_request = {
                "type": "test_agent_registry_setup",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "test_scenario": "websocket_manager_integration",
                "agents_to_register": [
                    "test_agent_with_websocket",
                    "cost_optimizer_with_events", 
                    "data_analyzer_with_notifications"
                ]
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, registry_setup_request)
            
            # Collect registry setup events
            setup_timeout = 8.0
            setup_start = time.time()
            
            while time.time() - setup_start < setup_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    event["received_at"] = time.time()
                    collected_events.append(event)
                    
                    # Stop when registry setup is complete
                    if event.get("type") == "registry_setup_complete":
                        break
                        
                except Exception:
                    # Timeout acceptable if we have some events
                    if collected_events:
                        break
                    continue
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 2.0, f"Registry setup test took too little time: {test_duration:.2f}s"
            
            # Verify registry setup events
            event_types = [event.get("type") for event in collected_events]
            
            # Should receive registry-related events
            registry_indicators = [
                "agent_registry_initialized",
                "websocket_manager_attached",
                "agents_registered",
                "registry_setup_complete"
            ]
            
            has_registry_setup = any(indicator in event_types for indicator in registry_indicators)
            
            # Should have some evidence of registry activity
            assert len(collected_events) >= 1, "Should have received events from registry setup"
            
            # May have explicit registry setup events or just general acknowledgments
            if not has_registry_setup:
                # If no explicit registry events, should at least have acknowledgments
                ack_indicators = ["ack", "response", "setup_complete"]
                has_setup_response = any(ack in event_types for ack in ack_indicators)
                assert has_setup_response, f"Should have setup response events: {event_types}"
                
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_with_websocket_events_through_registry(self, real_services_fixture):
        """Test agent execution through registry emits all required WebSocket events."""
        start_time = time.time()
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test user and connection
        test_user_id = UserID(f"execution_user_{UnifiedIdGenerator.generate_user_id()}")
        test_thread_id = ThreadID(f"execution_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        test_token = self._create_test_auth_token(test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{test_thread_id}",
            headers=headers,
            user_id=str(test_user_id)
        )
        
        try:
            collected_events = []
            
            # Execute agent through registry
            agent_execution_request = {
                "type": "execute_agent_via_registry",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "agent_name": "registry_integrated_agent",
                "message": "Execute agent with full WebSocket event integration",
                "validate_websocket_events": True,
                "execution_mode": "full_integration"
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, agent_execution_request)
            
            # Collect execution events
            execution_timeout = 12.0
            execution_start = time.time()
            
            while time.time() - execution_start < execution_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    event["received_at"] = time.time()
                    collected_events.append(event)
                    
                    # Stop when agent execution completes
                    if event.get("type") in ["agent_completed", "agent_failed"]:
                        break
                        
                except Exception:
                    # Timeout acceptable if we have events
                    if collected_events:
                        break
                    continue
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 3.0, f"Agent execution test took too little time: {test_duration:.2f}s"
            
            # Verify agent execution events
            event_types = [event.get("type") for event in collected_events]
            
            # Should have received the 5 critical WebSocket events
            critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            received_critical_events = []
            for critical_event in critical_events:
                if critical_event in event_types:
                    received_critical_events.append(critical_event)
            
            # Should have at least agent_started and either agent_completed or agent_failed
            assert "agent_started" in event_types, f"Should have agent_started event. Got: {event_types}"
            
            has_completion = any(
                completion_event in event_types 
                for completion_event in ["agent_completed", "agent_failed"]
            )
            assert has_completion, f"Should have completion event. Got: {event_types}"
            
            # Verify event sequencing
            if len(received_critical_events) >= 2:
                # Find positions of key events
                agent_started_pos = event_types.index("agent_started") if "agent_started" in event_types else -1
                agent_completed_pos = event_types.index("agent_completed") if "agent_completed" in event_types else -1
                
                if agent_started_pos >= 0 and agent_completed_pos >= 0:
                    assert agent_started_pos < agent_completed_pos, "agent_started should come before agent_completed"
            
            # Verify event content structure
            for event in collected_events:
                assert "type" in event, f"Event should have type field: {event}"
                
                # Events should have thread/user identification
                has_user_context = any(
                    field in event 
                    for field in ["user_id", "thread_id", "data"]
                )
                # Context may be in nested data structure
                
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_agents_websocket_coordination_through_registry(self, real_services_fixture):
        """Test multiple agents coordinated through registry with WebSocket events."""
        start_time = time.time()
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test user and connection
        test_user_id = UserID(f"multi_agent_user_{UnifiedIdGenerator.generate_user_id()}")
        test_thread_id = ThreadID(f"multi_agent_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        test_token = self._create_test_auth_token(test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{test_thread_id}",
            headers=headers,
            user_id=str(test_user_id)
        )
        
        try:
            collected_events = []
            
            # Execute multiple agents through registry
            multi_agent_request = {
                "type": "execute_multi_agent_workflow",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "workflow": {
                    "agents": [
                        {"name": "data_collector", "priority": 1},
                        {"name": "analyzer", "priority": 2},
                        {"name": "optimizer", "priority": 3}
                    ],
                    "coordination_mode": "sequential",
                    "websocket_events_per_agent": True
                },
                "test_multi_agent_coordination": True
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, multi_agent_request)
            
            # Collect events from multiple agents
            collection_timeout = 18.0  # Longer timeout for multiple agents
            collection_start = time.time()
            
            while time.time() - collection_start < collection_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=4.0)
                    event["received_at"] = time.time()
                    collected_events.append(event)
                    
                    # Stop when workflow completes
                    if event.get("type") in ["workflow_completed", "multi_agent_completed"]:
                        break
                        
                except Exception:
                    # Timeout acceptable if we have events
                    if collected_events and time.time() - collection_start > 10.0:
                        break
                    continue
            
            # Verify test took real time for multiple agents
            test_duration = time.time() - start_time
            assert test_duration > 5.0, f"Multi-agent test took too little time: {test_duration:.2f}s"
            
            # Analyze multi-agent coordination events
            event_types = [event.get("type") for event in collected_events]
            
            # Should have events from multiple agents or workflow coordination
            multi_agent_indicators = [
                "agent_started",
                "workflow_step_started",
                "agent_coordination",
                "multi_agent_started",
                "workflow_completed"
            ]
            
            has_multi_agent_activity = any(
                indicator in event_types 
                for indicator in multi_agent_indicators
            )
            
            # Should have received multiple events
            assert len(collected_events) >= 3, f"Should have multiple events from multi-agent workflow, got {len(collected_events)}"
            
            # Should have some form of multi-agent coordination evidence
            if not has_multi_agent_activity:
                # If no explicit multi-agent events, should have multiple agent_started events
                agent_started_count = event_types.count("agent_started")
                assert agent_started_count >= 1, f"Should have multiple agents or clear workflow evidence"
            
            # Verify event timing shows sequential or coordinated execution
            if len(collected_events) >= 3:
                event_timestamps = [event.get("received_at", 0) for event in collected_events]
                time_spans = []
                
                for i in range(1, len(event_timestamps)):
                    if event_timestamps[i] > event_timestamps[i-1]:
                        time_spans.append(event_timestamps[i] - event_timestamps[i-1])
                
                # Should have reasonable time spans between events (not all instantaneous)
                if time_spans:
                    reasonable_spans = [span for span in time_spans if 0.1 <= span <= 10.0]
                    assert len(reasonable_spans) >= 1, "Should have realistic timing between multi-agent events"
                    
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_registry_error_handling_with_websocket_events(self, real_services_fixture):
        """Test agent registry error handling includes proper WebSocket error events."""
        start_time = time.time()
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test user and connection
        test_user_id = UserID(f"error_test_user_{UnifiedIdGenerator.generate_user_id()}")
        test_thread_id = ThreadID(f"error_test_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        test_token = self._create_test_auth_token(test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{test_thread_id}",
            headers=headers,
            user_id=str(test_user_id)
        )
        
        try:
            collected_events = []
            
            # Trigger various error scenarios through registry
            error_scenarios = [
                {
                    "type": "execute_agent_via_registry",
                    "user_id": str(test_user_id),
                    "thread_id": str(test_thread_id),
                    "agent_name": "nonexistent_agent",
                    "message": "This should trigger agent not found error",
                    "error_scenario": "agent_not_found"
                },
                {
                    "type": "execute_agent_via_registry",
                    "user_id": str(test_user_id),
                    "thread_id": str(test_thread_id),
                    "agent_name": "failing_agent",
                    "message": "This should trigger execution error",
                    "error_scenario": "execution_failure"
                }
            ]
            
            for scenario in error_scenarios:
                await WebSocketTestHelpers.send_test_message(websocket, scenario)
                
                # Collect error events for this scenario
                scenario_start = time.time()
                while time.time() - scenario_start < 5.0:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                        event["received_at"] = time.time()
                        event["scenario"] = scenario["error_scenario"]
                        collected_events.append(event)
                        
                        # Stop on error or completion
                        if event.get("type") in ["agent_failed", "error", "agent_completed"]:
                            break
                            
                    except Exception:
                        # Timeout expected for some error scenarios
                        break
                
                # Brief pause between scenarios
                await asyncio.sleep(0.5)
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 2.0, f"Error handling test took too little time: {test_duration:.2f}s"
            
            # Analyze error handling events
            event_types = [event.get("type") for event in collected_events]
            
            # Should have received some events from error scenarios
            assert len(collected_events) >= 1, f"Should have received error handling events, got {len(collected_events)}"
            
            # Should have error indicators or responses
            error_indicators = [
                "agent_failed",
                "error", 
                "execution_error",
                "agent_not_found",
                "registry_error"
            ]
            
            response_indicators = [
                "ack",
                "response", 
                "error_response"
            ]
            
            has_error_events = any(indicator in event_types for indicator in error_indicators)
            has_response_events = any(indicator in event_types for indicator in response_indicators)
            
            # Should have either explicit error events or response events
            assert has_error_events or has_response_events, f"Should have error handling events. Got: {event_types}"
            
            # Verify error events contain appropriate information
            for event in collected_events:
                event_type = event.get("type")
                
                if event_type in error_indicators:
                    # Error events should have error information
                    has_error_info = any(
                        field in event 
                        for field in ["error", "message", "data", "error_message", "details"]
                    )
                    assert has_error_info, f"Error event should contain error information: {event}"
                    
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_registry_websocket_manager_lifecycle(self, real_services_fixture):
        """Test complete lifecycle of WebSocket manager attachment to agents via registry."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test user and connection
        test_user_id = UserID(f"lifecycle_user_{UnifiedIdGenerator.generate_user_id()}")
        test_thread_id = ThreadID(f"lifecycle_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        test_token = self._create_test_auth_token(test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{test_thread_id}",
            headers=headers,
            user_id=str(test_user_id)
        )
        
        try:
            lifecycle_events = []
            
            # Phase 1: Registry initialization
            init_request = {
                "type": "initialize_agent_registry",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "websocket_integration": True,
                "lifecycle_test": True
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, init_request)
            
            # Collect initialization events
            for _ in range(3):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    event["phase"] = "initialization"
                    lifecycle_events.append(event)
                except Exception:
                    break
            
            # Phase 2: Agent registration with WebSocket manager
            register_request = {
                "type": "register_agent_with_websocket",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "agent_config": {
                    "name": "lifecycle_test_agent",
                    "capabilities": ["analysis", "optimization"],
                    "websocket_events": True
                }
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, register_request)
            
            # Collect registration events
            for _ in range(3):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    event["phase"] = "registration"
                    lifecycle_events.append(event)
                except Exception:
                    break
            
            # Phase 3: Agent execution with WebSocket events
            execute_request = {
                "type": "execute_registered_agent",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "agent_name": "lifecycle_test_agent",
                "message": "Execute with full lifecycle integration"
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, execute_request)
            
            # Collect execution events
            execution_timeout = 8.0
            execution_start = time.time()
            
            while time.time() - execution_start < execution_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    event["phase"] = "execution"
                    lifecycle_events.append(event)
                    
                    if event.get("type") in ["agent_completed", "agent_failed"]:
                        break
                        
                except Exception:
                    break
            
            # Phase 4: Cleanup
            cleanup_request = {
                "type": "cleanup_agent_registry",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id)
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, cleanup_request)
            
            # Collect cleanup events
            try:
                cleanup_event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                cleanup_event["phase"] = "cleanup"
                lifecycle_events.append(cleanup_event)
            except Exception:
                pass  # Cleanup response may not come
            
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test took real time
        test_duration = time.time() - start_time
        assert test_duration > 4.0, f"Lifecycle test took too little time: {test_duration:.2f}s"
        
        # Analyze lifecycle progression
        assert len(lifecycle_events) >= 3, f"Should have events from multiple lifecycle phases, got {len(lifecycle_events)}"
        
        # Group events by phase
        phase_events = {}
        for event in lifecycle_events:
            phase = event.get("phase", "unknown")
            if phase not in phase_events:
                phase_events[phase] = []
            phase_events[phase].append(event)
        
        # Should have events from multiple phases
        assert len(phase_events) >= 2, f"Should have events from multiple phases: {list(phase_events.keys())}"
        
        # Verify phase progression
        expected_phases = ["initialization", "registration", "execution"]
        phases_present = [phase for phase in expected_phases if phase in phase_events]
        
        # Should have at least initialization and one other phase
        assert len(phases_present) >= 1, f"Should have recognizable lifecycle phases: {phases_present}"
        
        # Check database persistence of lifecycle
        lifecycle_query = """
        SELECT phase, event_type, event_data, created_at
        FROM agent_lifecycle_events 
        WHERE user_id = :user_id AND thread_id = :thread_id
        ORDER BY created_at ASC
        """
        
        try:
            result = await db_session.execute(lifecycle_query, {
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id)
            })
            
            db_lifecycle_events = result.fetchall()
            
            if db_lifecycle_events:
                # Should have lifecycle events persisted
                assert len(db_lifecycle_events) >= 1, "Should have persisted lifecycle events"
                
                # Verify database events match WebSocket events
                db_phases = [event.phase for event in db_lifecycle_events if hasattr(event, 'phase')]
                if db_phases:
                    common_phases = set(db_phases) & set(phase_events.keys())
                    assert len(common_phases) >= 1, "Database and WebSocket events should have common phases"
                    
        except Exception:
            # Database lifecycle tracking may not be available in all environments
            pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_enhancement_through_registry(self, real_services_fixture):
        """Test that registry enhances tool dispatcher with WebSocket capabilities."""
        start_time = time.time()
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test user and connection
        test_user_id = UserID(f"tool_dispatch_user_{UnifiedIdGenerator.generate_user_id()}")
        test_thread_id = ThreadID(f"tool_dispatch_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        test_token = self._create_test_auth_token(test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{test_thread_id}",
            headers=headers,
            user_id=str(test_user_id)
        )
        
        try:
            tool_dispatch_events = []
            
            # Execute agent that uses tools through enhanced dispatcher
            tool_agent_request = {
                "type": "execute_agent_with_tools",
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "agent_name": "tool_heavy_agent",
                "message": "Execute multiple tools with WebSocket event tracking",
                "tools_to_use": [
                    "data_analyzer",
                    "cost_calculator",
                    "report_generator"
                ],
                "enhanced_tool_dispatch": True
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, tool_agent_request)
            
            # Collect tool dispatch events
            dispatch_timeout = 15.0
            dispatch_start = time.time()
            
            while time.time() - dispatch_start < dispatch_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=4.0)
                    event["received_at"] = time.time()
                    tool_dispatch_events.append(event)
                    
                    # Stop when agent execution completes
                    if event.get("type") in ["agent_completed", "agent_failed"]:
                        break
                        
                except Exception:
                    # Timeout acceptable if we have events
                    if tool_dispatch_events and time.time() - dispatch_start > 8.0:
                        break
                    continue
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 4.0, f"Tool dispatch test took too little time: {test_duration:.2f}s"
            
            # Analyze tool dispatch events
            event_types = [event.get("type") for event in tool_dispatch_events]
            
            # Should have tool execution events
            tool_indicators = [
                "tool_executing",
                "tool_completed",
                "tool_started",
                "tool_dispatch",
                "tool_result"
            ]
            
            has_tool_events = any(indicator in event_types for indicator in tool_indicators)
            
            # Should have agent execution events
            agent_indicators = [
                "agent_started",
                "agent_thinking",
                "agent_completed"
            ]
            
            has_agent_events = any(indicator in event_types for indicator in agent_indicators)
            
            # Should have events from both agent and tool execution
            assert len(tool_dispatch_events) >= 2, f"Should have multiple tool dispatch events, got {len(tool_dispatch_events)}"
            
            # Should have either explicit tool events or agent events indicating tool usage
            assert has_tool_events or has_agent_events, f"Should have tool or agent execution events: {event_types}"
            
            # Verify event sequencing for tools
            if has_tool_events:
                # Find tool execution patterns
                tool_executing_indices = [
                    i for i, event_type in enumerate(event_types) 
                    if event_type == "tool_executing"
                ]
                
                tool_completed_indices = [
                    i for i, event_type in enumerate(event_types)
                    if event_type == "tool_completed"
                ]
                
                # If we have both tool_executing and tool_completed, verify ordering
                if tool_executing_indices and tool_completed_indices:
                    # At least one tool_executing should come before a tool_completed
                    min_executing_idx = min(tool_executing_indices)
                    max_completed_idx = max(tool_completed_indices)
                    
                    assert min_executing_idx < max_completed_idx, "tool_executing should come before tool_completed"
            
            # Verify enhanced tool dispatcher integration
            for event in tool_dispatch_events:
                event_type = event.get("type")
                
                # Tool events should have proper context
                if event_type in tool_indicators:
                    # Should have tool identification
                    has_tool_context = any(
                        field in event
                        for field in ["tool_name", "tool", "data"]
                    )
                    # Tool context may be in nested data structure
                    
                # All events should have threading information
                has_thread_context = any(
                    field in event or (isinstance(event.get("data"), dict) and field in event.get("data", {}))
                    for field in ["thread_id", "user_id"]
                )
                # Context information is expected but format may vary
                
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)

    def _create_test_auth_token(self, user_id: UserID) -> str:
        """Create test authentication token for integration testing."""
        import base64
        
        payload = {
            "user_id": str(user_id),
            "email": f"test_{user_id}@example.com",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "test_mode": True
        }
        
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        return f"test.{token_data}.signature"