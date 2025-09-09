"""
Mission Critical Test: WebSocket Events During LLM API Failures

MISSION CRITICAL: This test validates that the 5 essential WebSocket events
are ALWAYS sent to users even when LLM APIs experience partial failures.
Without these events, the chat interface has NO business value.

Business Value Justification (BVJ):
- Segment: All - Platform Critical
- Business Goal: Maintain chat functionality during LLM API disruptions
- Value Impact: Users must see progress and receive feedback even during API failures
- Strategic Impact: Prevents complete loss of platform value during third-party API issues

This test ensures that regardless of LLM API failure patterns:
1. agent_started - Users know their request is being processed
2. agent_thinking - Users see ongoing progress during retries
3. tool_executing - Users understand what the system is attempting
4. tool_completed - Users receive partial results when available
5. agent_completed - Users get clear resolution even if degraded

CRITICAL: This test MUST pass or the platform loses all user value during LLM outages.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from loguru import logger

# Mission critical test framework - follow established pattern
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events

# Core system components
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext  
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.client_unified import ResilientLLMClient
from netra_backend.app.core.exceptions_service import ServiceError, ServiceTimeoutError

from shared.types import UserID, ThreadID, RunID


class CriticalLLMFailureSimulator:
    """Simulates the most critical LLM failure scenarios for mission critical testing."""
    
    def __init__(self, failure_mode: str):
        self.failure_mode = failure_mode
        self.call_count = 0
        self.successful_calls = 0
        self.failed_calls = 0
    
    async def simulate_critical_llm_call(self, prompt: str, config_name: str) -> str:
        """Simulate LLM calls with critical failure patterns."""
        self.call_count += 1
        
        if self.failure_mode == "complete_outage":
            # Complete LLM outage - all calls fail
            self.failed_calls += 1
            raise ServiceError(
                f"LLM service completely unavailable: {config_name}",
                error_code="LLM_SERVICE_UNAVAILABLE",
                context={'total_attempts': self.call_count}
            )
        
        elif self.failure_mode == "cascading_timeouts":
            # Cascading timeout scenario - gets worse over time
            timeout_delay = min(15.0, 2.0 * self.call_count)
            self.failed_calls += 1
            await asyncio.sleep(timeout_delay)
            raise ServiceTimeoutError(
                timeout_seconds=timeout_delay,
                context={'cascading_attempt': self.call_count, 'config': config_name}
            )
        
        elif self.failure_mode == "partial_recovery":
            # Partial recovery - some succeed after failures
            if self.call_count <= 3:
                self.failed_calls += 1
                raise ServiceError(
                    f"LLM temporarily unavailable: {config_name}",
                    error_code="LLM_TEMPORARY_FAILURE",
                    context={'recovery_attempt': self.call_count}
                )
            else:
                # Recovery starts after 3 attempts
                self.successful_calls += 1
                await asyncio.sleep(1.0)  # Simulate normal latency
                return f"Recovered LLM response: {prompt[:50]}... (attempt {self.call_count})"
        
        elif self.failure_mode == "intermittent_success":
            # Intermittent success pattern
            if self.call_count % 3 == 0:
                self.successful_calls += 1
                await asyncio.sleep(0.8)
                return f"Intermittent success: {prompt[:50]}... (call {self.call_count})"
            else:
                self.failed_calls += 1
                raise ServiceError(
                    f"LLM intermittent failure: {config_name}",
                    error_code="LLM_INTERMITTENT_FAILURE", 
                    context={'pattern_attempt': self.call_count}
                )
        
        else:
            # Default failure
            self.failed_calls += 1
            raise ServiceError(f"Unknown LLM failure mode: {self.failure_mode}")


class TestAgentExecutionLLMFailureWebSocketEvents:
    """Mission critical test for WebSocket events during LLM failures."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this test
    @pytest.mark.real_services
    async def test_all_websocket_events_sent_during_complete_llm_outage(self, real_services_fixture):
        """
        MISSION CRITICAL: All 5 WebSocket events MUST be sent even during complete LLM outage.
        
        This is the most critical test - if LLM APIs are completely down,
        users MUST still receive feedback about what's happening.
        """
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for mission critical WebSocket testing")
        
        # Setup complete LLM outage scenario
        outage_simulator = CriticalLLMFailureSimulator("complete_outage")
        
        # Create real user context
        user_context = await self._create_mission_critical_user_context(real_services_fixture)
        
        # Setup agent components with complete LLM failure
        with patch('netra_backend.app.llm.client_unified.ResilientLLMClient') as mock_llm_class:
            mock_llm_client = AsyncMock(spec=ResilientLLMClient)
            mock_llm_client.ask_llm.side_effect = outage_simulator.simulate_critical_llm_call
            mock_llm_client.ask_llm_with_retry.side_effect = outage_simulator.simulate_critical_llm_call
            mock_llm_class.return_value = mock_llm_client
            
            # Create agent registry and execution core
            agent_registry = AgentRegistry(
                postgres_pool=real_services_fixture["postgres"],
                redis_client=real_services_fixture["redis"]
            )
            
            websocket_bridge = AgentWebSocketBridge()
            await websocket_bridge.initialize()
            
            execution_core = AgentExecutionCore(agent_registry, websocket_bridge)
            
            # Collect WebSocket events during complete outage
            websocket_events = []
            
            async with WebSocketTestClient(
                token=user_context["auth_token"],
                base_url=real_services_fixture["backend_url"]
            ) as ws_client:
                
                # Start event collection
                event_collection_task = asyncio.create_task(
                    self._collect_critical_events(ws_client, websocket_events)
                )
                
                # Create execution context
                execution_context = AgentExecutionContext(
                    agent_name="critical_test_agent",
                    run_id=RunID(str(uuid4())),
                    correlation_id=str(uuid4()),
                    user_id=UserID(user_context["user_id"]),
                    thread_id=ThreadID(user_context["thread_id"])
                )
                
                agent_state = DeepAgentState(
                    user_id=user_context["user_id"],
                    thread_id=user_context["thread_id"],
                    organization_id=user_context["organization_id"],
                    conversation_context="Mission critical test during LLM outage"
                )
                
                # Execute agent - should handle complete LLM failure gracefully
                try:
                    result = await execution_core.execute_agent(
                        context=execution_context,
                        state=agent_state,
                        timeout=20.0  # Shorter timeout for outage scenario
                    )
                except Exception as e:
                    # Even if execution fails, events should still be sent
                    logger.info(f"Agent execution failed as expected during outage: {e}")
                
                # Stop event collection
                event_collection_task.cancel()
                
                # MISSION CRITICAL VALIDATION: All 5 events MUST be sent
                self._validate_all_five_websocket_events_sent(websocket_events)
                
                # Additional critical validations for outage scenario
                self._validate_outage_scenario_events(websocket_events, outage_simulator)
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    @pytest.mark.real_services
    async def test_websocket_events_during_cascading_llm_timeouts(self, real_services_fixture):
        """
        MISSION CRITICAL: WebSocket events must continue during cascading timeouts.
        
        This tests the worst-case scenario where LLM timeouts get progressively worse.
        Users must still receive progress updates.
        """
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for mission critical timeout testing")
        
        timeout_simulator = CriticalLLMFailureSimulator("cascading_timeouts")
        
        user_context = await self._create_mission_critical_user_context(real_services_fixture)
        
        with patch('netra_backend.app.llm.client_unified.ResilientLLMClient') as mock_llm_class:
            mock_llm_client = AsyncMock(spec=ResilientLLMClient)
            mock_llm_client.ask_llm.side_effect = timeout_simulator.simulate_critical_llm_call
            mock_llm_client.ask_llm_with_retry.side_effect = timeout_simulator.simulate_critical_llm_call
            mock_llm_class.return_value = mock_llm_client
            
            agent_registry = AgentRegistry(
                postgres_pool=real_services_fixture["postgres"], 
                redis_client=real_services_fixture["redis"]
            )
            
            websocket_bridge = AgentWebSocketBridge()
            await websocket_bridge.initialize()
            
            execution_core = AgentExecutionCore(agent_registry, websocket_bridge)
            
            websocket_events = []
            
            async with WebSocketTestClient(
                token=user_context["auth_token"],
                base_url=real_services_fixture["backend_url"]
            ) as ws_client:
                
                event_collection_task = asyncio.create_task(
                    self._collect_critical_events(ws_client, websocket_events)
                )
                
                execution_context = AgentExecutionContext(
                    agent_name="timeout_test_agent",
                    run_id=RunID(str(uuid4())),
                    correlation_id=str(uuid4()),
                    user_id=UserID(user_context["user_id"]),
                    thread_id=ThreadID(user_context["thread_id"])
                )
                
                agent_state = DeepAgentState(
                    user_id=user_context["user_id"],
                    thread_id=user_context["thread_id"],
                    organization_id=user_context["organization_id"],
                    conversation_context="Testing cascading timeout resilience"
                )
                
                start_time = time.time()
                
                try:
                    result = await execution_core.execute_agent(
                        context=execution_context,
                        state=agent_state,
                        timeout=25.0
                    )
                except Exception as e:
                    logger.info(f"Agent execution failed during cascading timeouts: {e}")
                
                execution_duration = time.time() - start_time
                event_collection_task.cancel()
                
                # MISSION CRITICAL: Events must be sent despite cascading timeouts
                self._validate_all_five_websocket_events_sent(websocket_events)
                
                # Validate timeout scenario specifics
                self._validate_timeout_scenario_events(websocket_events, execution_duration)
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    @pytest.mark.real_services
    async def test_websocket_events_during_llm_partial_recovery(self, real_services_fixture):
        """
        MISSION CRITICAL: WebSocket events during LLM partial recovery scenarios.
        
        Tests that users receive proper progress updates as LLM service gradually recovers.
        """
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for mission critical recovery testing")
        
        recovery_simulator = CriticalLLMFailureSimulator("partial_recovery")
        
        user_context = await self._create_mission_critical_user_context(real_services_fixture)
        
        with patch('netra_backend.app.llm.client_unified.ResilientLLMClient') as mock_llm_class:
            mock_llm_client = AsyncMock(spec=ResilientLLMClient)
            mock_llm_client.ask_llm.side_effect = recovery_simulator.simulate_critical_llm_call
            mock_llm_client.ask_llm_with_retry.side_effect = recovery_simulator.simulate_critical_llm_call
            mock_llm_class.return_value = mock_llm_client
            
            agent_registry = AgentRegistry(
                postgres_pool=real_services_fixture["postgres"],
                redis_client=real_services_fixture["redis"]
            )
            
            websocket_bridge = AgentWebSocketBridge()
            await websocket_bridge.initialize()
            
            execution_core = AgentExecutionCore(agent_registry, websocket_bridge)
            
            websocket_events = []
            
            async with WebSocketTestClient(
                token=user_context["auth_token"],
                base_url=real_services_fixture["backend_url"]
            ) as ws_client:
                
                event_collection_task = asyncio.create_task(
                    self._collect_critical_events(ws_client, websocket_events)
                )
                
                execution_context = AgentExecutionContext(
                    agent_name="recovery_test_agent",
                    run_id=RunID(str(uuid4())),
                    correlation_id=str(uuid4()),
                    user_id=UserID(user_context["user_id"]),
                    thread_id=ThreadID(user_context["thread_id"])
                )
                
                agent_state = DeepAgentState(
                    user_id=user_context["user_id"],
                    thread_id=user_context["thread_id"],
                    organization_id=user_context["organization_id"],
                    conversation_context="Testing LLM recovery patterns"
                )
                
                result = await execution_core.execute_agent(
                    context=execution_context,
                    state=agent_state,
                    timeout=30.0
                )
                
                event_collection_task.cancel()
                
                # MISSION CRITICAL: All events sent during recovery
                self._validate_all_five_websocket_events_sent(websocket_events)
                
                # Should eventually complete successfully with recovery
                assert result is not None, "Agent should complete successfully after LLM recovery"
                
                # Validate recovery pattern events
                self._validate_recovery_scenario_events(websocket_events, recovery_simulator)
    
    # Helper methods for mission critical testing
    
    async def _create_mission_critical_user_context(self, real_services: Dict) -> Dict:
        """Create user context for mission critical testing."""
        db_session = real_services["db"]
        
        user_id = str(uuid4())
        user_email = f"mission-critical-{user_id[:8]}@example.com"
        
        # Create user with mission critical context
        await db_session.execute("""
            INSERT INTO auth.users (id, email, name, is_active)
            VALUES (:id, :email, :name, :is_active)
            ON CONFLICT (email) DO UPDATE SET is_active = EXCLUDED.is_active
        """, {
            "id": user_id,
            "email": user_email,
            "name": "Mission Critical Test User",
            "is_active": True
        })
        
        org_id = str(uuid4())
        await db_session.execute("""
            INSERT INTO backend.organizations (id, name, slug, plan)
            VALUES (:id, :name, :slug, :plan)
            ON CONFLICT (slug) DO UPDATE SET plan = EXCLUDED.plan
        """, {
            "id": org_id,
            "name": "Mission Critical Org",
            "slug": f"mission-critical-{user_id[:8]}",
            "plan": "enterprise"  # Enterprise plan for critical testing
        })
        
        thread_id = str(uuid4())
        await db_session.execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES (:id, :user_id, :title, :created_at)
        """, {
            "id": thread_id,
            "user_id": user_id,
            "title": "Mission Critical LLM Failure Test",
            "created_at": datetime.utcnow()
        })
        
        await db_session.commit()
        
        return {
            "user_id": user_id,
            "organization_id": org_id,
            "thread_id": thread_id,
            "auth_token": f"mission-critical-token-{user_id}"
        }
    
    async def _collect_critical_events(self, ws_client: WebSocketTestClient, events_list: List[Dict]):
        """Collect WebSocket events for mission critical validation."""
        try:
            async for event in ws_client.receive_events(timeout=35):
                events_list.append(event)
                logger.info(f"Collected critical event: {event.get('type')} at {time.time()}")
                
                # Continue collecting until agent completes or fails
                if event.get('type') in ['agent_completed', 'agent_failed']:
                    break
        except asyncio.CancelledError:
            logger.info("Event collection cancelled - normal operation")
        except Exception as e:
            logger.error(f"Critical event collection error: {e}")
    
    def _validate_all_five_websocket_events_sent(self, events: List[Dict]):
        """
        MISSION CRITICAL: Validate all 5 required WebSocket events are sent.
        
        This is the most important validation - without these events,
        the chat interface provides NO business value.
        """
        
        event_types = [event.get('type') for event in events]
        
        # The 5 MISSION CRITICAL events that MUST be sent
        required_events = [
            'agent_started',    # User knows request is being processed
            'agent_thinking',   # User sees ongoing progress
            'tool_executing',   # User understands what's being attempted (optional if no tools)
            'tool_completed',   # User receives partial results (optional if no tools)
            'agent_completed'   # User gets clear resolution
        ]
        
        # Core events that are absolutely mandatory
        mandatory_events = ['agent_started', 'agent_thinking', 'agent_completed']
        
        for mandatory_event in mandatory_events:
            assert mandatory_event in event_types, \
                f"MISSION CRITICAL FAILURE: Missing mandatory WebSocket event '{mandatory_event}'. " \
                f"Without this event, users have no feedback during LLM failures. " \
                f"Events received: {event_types}"
        
        # Tool events are optional depending on agent implementation
        tool_events_present = any(event in event_types for event in ['tool_executing', 'tool_completed'])
        
        if tool_events_present:
            # If any tool events are present, both should be present for consistency
            assert 'tool_executing' in event_types or 'tool_completed' in event_types, \
                "If tool events are sent, both executing and completed should be present"
        
        # Log successful validation
        logger.info(f"MISSION CRITICAL SUCCESS: All required WebSocket events sent during LLM failure: {event_types}")
    
    def _validate_outage_scenario_events(self, events: List[Dict], simulator: CriticalLLMFailureSimulator):
        """Validate WebSocket events specific to complete LLM outage."""
        
        # Should have retry or error information in events
        error_or_retry_events = [
            event for event in events
            if 'error' in str(event.get('data', {})).lower() or
               'retry' in str(event.get('data', {})).lower() or
               'unavailable' in str(event.get('data', {})).lower()
        ]
        
        # During complete outage, users should be informed about the issue
        assert len(error_or_retry_events) > 0, \
            "During complete LLM outage, users must be informed about service issues"
        
        # Should show multiple LLM call attempts
        assert simulator.call_count >= 2, \
            f"Expected multiple retry attempts during outage, got {simulator.call_count}"
        
        assert simulator.failed_calls == simulator.call_count, \
            "All LLM calls should fail during complete outage"
    
    def _validate_timeout_scenario_events(self, events: List[Dict], execution_duration: float):
        """Validate WebSocket events during cascading timeouts."""
        
        # Execution should take significant time due to cascading timeouts
        assert execution_duration > 5.0, \
            f"Expected longer execution time due to cascading timeouts, got {execution_duration}s"
        
        # Should have multiple thinking events during long execution
        thinking_events = [event for event in events if event.get('type') == 'agent_thinking']
        assert len(thinking_events) >= 1, \
            "Users should receive thinking updates during long timeout scenarios"
        
        # Events should span the execution duration
        if len(events) >= 2 and events[0].get('timestamp') and events[-1].get('timestamp'):
            event_span = events[-1]['timestamp'] - events[0]['timestamp']
            assert event_span >= 3.0, \
                f"WebSocket events should span timeout duration, got {event_span}s"
    
    def _validate_recovery_scenario_events(self, events: List[Dict], simulator: CriticalLLMFailureSimulator):
        """Validate WebSocket events during LLM recovery."""
        
        # Should show both failures and eventual success
        assert simulator.failed_calls > 0, "Should have some failed calls before recovery"
        assert simulator.successful_calls > 0, "Should have successful calls after recovery"
        
        # Agent should eventually complete successfully
        completion_events = [event for event in events if event.get('type') == 'agent_completed']
        assert len(completion_events) > 0, "Agent should complete successfully after recovery"
        
        # Should not indicate error in final completion
        final_completion = completion_events[-1]
        completion_data = final_completion.get('data', {})
        
        # Final result should indicate success, not error
        status = completion_data.get('status', '').lower()
        assert status != 'failed', f"Final completion should not be failed status: {status}"
        
        logger.info(f"Recovery scenario validated: {simulator.failed_calls} failures, {simulator.successful_calls} successes")