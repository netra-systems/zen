"""
Base Agent Execution Integration Test Framework

This module provides the foundation for testing agent execution patterns,
tool dispatch integration, and WebSocket event delivery without requiring Docker services.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Validate core agent execution patterns and business value delivery
- Value Impact: Ensures agent orchestration works correctly for user chat experiences
- Strategic Impact: Prevents regressions in core value delivery mechanisms

CRITICAL REQUIREMENTS:
- NO MOCKS for internal agent logic, tool execution, or agent communication
- Focus on AGENT EXECUTION PATTERNS and tool dispatcher functionality  
- Test real agent orchestration, handoffs, and coordination
- Use real WebSocket events for all 5 critical agent events
- Validate tool execution effectiveness and business outcomes
- Test UserExecutionContext isolation patterns
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock
import pytest

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.logging_config import central_logger
from test_framework.base_integration_test import BaseIntegrationTest

logger = central_logger.get_logger(__name__)


class MockWebSocketManager:
    """Mock WebSocket manager for testing without external dependencies."""
    
    def __init__(self):
        self.emitted_events = []
        self.connected_users = set()
        
    async def emit_agent_event(self, event_type: str, data: Dict[str, Any], 
                              run_id: str, agent_name: str = None) -> bool:
        """Mock emit agent event to capture events for validation."""
        event = {
            'type': event_type,
            'data': data,
            'run_id': run_id,
            'agent_name': agent_name,
            'timestamp': time.time()
        }
        self.emitted_events.append(event)
        logger.info(f"MockWebSocket: Emitted {event_type} for {agent_name} in run {run_id}")
        return True
        
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user is connected."""
        return user_id in self.connected_users
        
    def add_connection(self, user_id: str):
        """Add user connection for testing."""
        self.connected_users.add(user_id)
        
    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific run."""
        return [event for event in self.emitted_events if event['run_id'] == run_id]
        
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [event for event in self.emitted_events if event['type'] == event_type]
        
    def clear_events(self):
        """Clear all events for next test."""
        self.emitted_events.clear()
        
    async def send_to_thread(self, thread_id: str, message: dict) -> bool:
        """Mock send_to_thread method required by AgentWebSocketBridge.
        
        This method is required by the AgentWebSocketBridge property setter
        validation. It captures the message for test verification.
        """
        event = {
            'type': 'thread_message',
            'thread_id': thread_id,
            'message': message,
            'timestamp': time.time()
        }
        self.emitted_events.append(event)
        logger.info(f"MockWebSocket: Sent to thread {thread_id}: {message}")
        return True
        

class MockLLMManager:
    """Mock LLM manager for testing without external API calls."""
    
    def __init__(self):
        self.model_name = "test-model"
        self.call_count = 0
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate mock response for testing."""
        self.call_count += 1
        return f"Mock response {self.call_count} for: {prompt[:50]}..."
        
    async def generate_structured_response(self, prompt: str, schema: dict, **kwargs) -> dict:
        """Generate mock structured response."""
        self.call_count += 1
        return {
            "result": f"Mock structured response {self.call_count}",
            "confidence": 0.85,
            "reasoning": "Mock reasoning for test"
        }
        
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": self.model_name,
            "call_count": self.call_count
        }


class BaseAgentExecutionTest(BaseIntegrationTest):
    """Base class for agent execution integration tests.
    
    This class provides utilities for testing real agent execution patterns
    without external dependencies, focusing on business logic validation.
    """
    
    def setup_method(self):
        """Set up test environment with real agent components."""
        super().setup_method()
        
        # Create mock infrastructure components (external dependencies only)
        self.mock_websocket_manager = MockWebSocketManager()
        self.mock_llm_manager = MockLLMManager()
        
        # Create real WebSocket bridge with mock manager
        self.websocket_bridge = AgentWebSocketBridge()
        self.websocket_bridge.websocket_manager = self.mock_websocket_manager
        
        # Set up test user and context
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        
        # Add user connection for WebSocket testing
        self.mock_websocket_manager.add_connection(self.test_user_id)
        
        logger.info(f"Test setup completed for user {self.test_user_id}")
        
    def teardown_method(self):
        """Clean up test resources."""
        super().teardown_method()
        self.mock_websocket_manager.clear_events()
        
    def create_user_execution_context(self, 
                                    user_request: str = "Test request",
                                    additional_metadata: Optional[Dict[str, Any]] = None) -> UserExecutionContext:
        """Create a test UserExecutionContext with realistic data.
        
        Args:
            user_request: The user's request for testing
            additional_metadata: Additional metadata for the context
            
        Returns:
            UserExecutionContext for testing
        """
        metadata = {
            "user_request": user_request,
            "request_type": "chat",
            "test_mode": True
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
            
        context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            websocket_connection_id=f"ws_{self.test_user_id}",
            metadata=metadata
        )
        
        return context
        
    def create_supervisor_agent(self) -> SupervisorAgent:
        """Create a real SupervisorAgent for testing.
        
        Returns:
            SupervisorAgent configured for testing
        """
        supervisor = SupervisorAgent.create(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        
        logger.info(f"Created SupervisorAgent for testing")
        return supervisor
        
    def validate_websocket_events(self, 
                                run_id: str,
                                expected_events: List[str],
                                min_events_per_type: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Validate that WebSocket events were emitted correctly.
        
        Args:
            run_id: Run ID to validate events for
            expected_events: List of expected event types
            min_events_per_type: Minimum events expected per type
            
        Returns:
            Dictionary mapping event types to their events
            
        Raises:
            AssertionError: If validation fails
        """
        all_events = self.mock_websocket_manager.get_events_for_run(run_id)
        events_by_type = {}
        
        # Group events by type
        for event in all_events:
            event_type = event['type']
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
            
        # Validate expected events exist
        for expected_type in expected_events:
            assert expected_type in events_by_type, \
                f"Expected event type '{expected_type}' not found. Available: {list(events_by_type.keys())}"
            
            actual_count = len(events_by_type[expected_type])
            assert actual_count >= min_events_per_type, \
                f"Expected at least {min_events_per_type} {expected_type} events, got {actual_count}"
                
        logger.info(f"WebSocket validation passed for run {run_id}: {len(all_events)} total events")
        return events_by_type
        
    def validate_agent_execution_timing(self, 
                                      events_by_type: Dict[str, List[Dict[str, Any]]],
                                      max_execution_time: float = 30.0) -> Dict[str, float]:
        """Validate agent execution timing and sequencing.
        
        Args:
            events_by_type: Events grouped by type
            max_execution_time: Maximum allowed execution time
            
        Returns:
            Dictionary with timing metrics
        """
        timing_metrics = {}
        
        # Find start and end events
        start_events = events_by_type.get('agent_started', [])
        completion_events = events_by_type.get('agent_completed', [])
        
        if start_events and completion_events:
            start_time = min(event['timestamp'] for event in start_events)
            end_time = max(event['timestamp'] for event in completion_events)
            
            execution_time = end_time - start_time
            timing_metrics['total_execution_time'] = execution_time
            
            assert execution_time <= max_execution_time, \
                f"Execution time {execution_time:.2f}s exceeded maximum {max_execution_time}s"
                
            # Validate event ordering
            thinking_events = events_by_type.get('agent_thinking', [])
            if thinking_events:
                thinking_times = [event['timestamp'] for event in thinking_events]
                assert min(thinking_times) >= start_time, "Thinking events occurred before agent started"
                assert max(thinking_times) <= end_time, "Thinking events occurred after agent completed"
                
        return timing_metrics
        
    def validate_user_context_isolation(self, context: UserExecutionContext) -> None:
        """Validate that UserExecutionContext maintains proper isolation.
        
        Args:
            context: Context to validate
        """
        # Verify context integrity
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id  
        assert context.run_id == self.test_run_id
        
        # Verify no placeholder values
        context.verify_isolation()
        
        # Verify metadata isolation
        assert isinstance(context.metadata, dict)
        assert 'user_request' in context.metadata
        
        logger.info(f"User context isolation validated for {context.get_correlation_id()}")
        
    def validate_tool_execution_results(self, 
                                      results: Dict[str, Any],
                                      expected_agents: List[str],
                                      business_value_indicators: List[str]) -> None:
        """Validate that tool execution delivered business value.
        
        Args:
            results: Agent execution results
            expected_agents: List of agents expected to execute  
            business_value_indicators: List of business value indicators to check
        """
        assert isinstance(results, dict), f"Results must be dict, got {type(results)}"
        
        # Validate supervisor completion
        assert results.get('supervisor_result') == 'completed', "Supervisor must complete successfully"
        assert results.get('orchestration_successful') is True, "Orchestration must succeed"
        assert results.get('user_isolation_verified') is True, "User isolation must be verified"
        
        # Validate agent execution results exist
        workflow_results = results.get('results', {})
        assert isinstance(workflow_results, dict), "Workflow results must exist"
        
        # Check for business value indicators
        for indicator in business_value_indicators:
            found = False
            for agent_result in workflow_results.values():
                if isinstance(agent_result, dict):
                    # Check if indicator exists in agent result or its nested data
                    if self._find_indicator_in_result(agent_result, indicator):
                        found = True
                        break
                        
            assert found, f"Business value indicator '{indicator}' not found in any agent results"
            
        logger.info(f"Tool execution validation passed with {len(workflow_results)} agent results")
        
    def _find_indicator_in_result(self, result: Dict[str, Any], indicator: str) -> bool:
        """Recursively search for business value indicator in result."""
        if indicator.lower() in str(result).lower():
            return True
            
        for value in result.values():
            if isinstance(value, dict):
                if self._find_indicator_in_result(value, indicator):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if self._find_indicator_in_result(item, indicator):
                            return True
                            
        return False
        
    async def execute_agent_with_validation(self, 
                                          agent: BaseAgent,
                                          context: UserExecutionContext,
                                          expected_events: List[str],
                                          business_value_indicators: List[str]) -> Dict[str, Any]:
        """Execute agent and validate results comprehensively.
        
        Args:
            agent: Agent to execute
            context: User execution context
            expected_events: Expected WebSocket events
            business_value_indicators: Expected business value indicators
            
        Returns:
            Agent execution results
        """
        # Clear previous events
        self.mock_websocket_manager.clear_events()
        
        # Execute agent
        start_time = time.time()
        results = await agent.execute(context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # Validate WebSocket events
        events_by_type = self.validate_websocket_events(
            context.run_id, expected_events
        )
        
        # Validate timing
        timing_metrics = self.validate_agent_execution_timing(events_by_type)
        timing_metrics['measured_execution_time'] = execution_time
        
        # Validate context isolation  
        self.validate_user_context_isolation(context)
        
        # Validate business value
        if hasattr(agent, 'name') and agent.name == 'Supervisor':
            # For supervisor, validate orchestration results
            self.validate_tool_execution_results(
                results, 
                expected_agents=['triage', 'reporting'],
                business_value_indicators=business_value_indicators
            )
        
        logger.info(f"Agent execution validation completed in {execution_time:.2f}s")
        return results

    def create_mock_agent_instance(self, agent_name: str, 
                                 execution_result: Optional[Dict[str, Any]] = None) -> BaseAgent:
        """Create a mock agent instance for testing agent interactions.
        
        Args:
            agent_name: Name of the agent
            execution_result: Optional result to return from execute()
            
        Returns:
            Mock BaseAgent instance
        """
        mock_agent = AsyncMock(spec=BaseAgent)
        mock_agent.name = agent_name
        mock_agent.description = f"Mock {agent_name} agent for testing"
        
        # Set default execution result
        if execution_result is None:
            execution_result = {
                "status": "completed",
                "agent_name": agent_name,
                "result": f"Mock {agent_name} executed successfully",
                "business_value": f"{agent_name} delivered expected value",
                "execution_time": 0.5 + (hash(agent_name) % 10) * 0.1  # Realistic timing
            }
            
        mock_agent.execute.return_value = execution_result
        
        return mock_agent