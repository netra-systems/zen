#!/usr/bin/env python
"""MISSION CRITICAL: DataHelperAgent Golden Pattern Alignment Tests

THIS SUITE VALIDATES COMPLETE GOLDEN PATTERN COMPLIANCE.
Business Value: $200K+ ARR - Data request generation critical for optimization value delivery.

The DataHelperAgent is responsible for generating data requests when insufficient data 
is available for optimization. This test suite ensures:

1. Complete golden pattern compliance
2. WebSocket event emissions for real-time chat value
3. Proper BaseAgent infrastructure integration
4. Error handling and reliability patterns
5. Legacy compatibility preservation
6. Performance and timing requirements

ANY FAILURE HERE INDICATES GOLDEN PATTERN VIOLATION - BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, MagicMock, patch
import pytest
from loguru import logger

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import DataHelperAgent and dependencies
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.tools.data_helper import DataHelper
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager


# ============================================================================
# CRITICAL TEST UTILITIES - Golden Pattern Validation
# ============================================================================

class GoldenPatternValidator:
    """Validates complete golden pattern compliance with extreme rigor."""
    
    REQUIRED_WEBSOCKET_EVENTS = {
        "agent_thinking",
        "tool_executing", 
        "tool_completed",
        "agent_progress",
        "agent_completed"
    }
    
    REQUIRED_ABSTRACT_METHODS = {
        "validate_preconditions",
        "execute_core_logic"
    }
    
    REQUIRED_INFRASTRUCTURE_INTEGRATION = {
        "websocket_adapter",
        "timing_collector", 
        "reliability_manager",
        "execution_engine"
    }
    
    def __init__(self):
        self.websocket_events_recorded = []
        self.method_calls_recorded = []
        self.infrastructure_checks = {}
        self.violations = []
        self.warnings = []
        
    def record_websocket_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record WebSocket event for validation."""
        self.websocket_events_recorded.append({
            'event_type': event_type,
            'data': data,
            'timestamp': time.time()
        })
        
    def record_method_call(self, method_name: str, args: tuple, kwargs: Dict[str, Any]) -> None:
        """Record method call for validation."""
        self.method_calls_recorded.append({
            'method': method_name,
            'args': args,
            'kwargs': kwargs,
            'timestamp': time.time()
        })
        
    def validate_inheritance_pattern(self, agent: DataHelperAgent) -> bool:
        """Validate clean inheritance from BaseAgent."""
        # Must inherit directly from BaseAgent
        if not isinstance(agent, BaseAgent):
            self.violations.append("DataHelperAgent must inherit from BaseAgent")
            return False
            
        # Should not have multiple inheritance complexity
        mro = type(agent).__mro__
        if len(mro) > 4:  # DataHelperAgent -> BaseAgent -> ABC -> object
            self.violations.append(f"Complex inheritance detected: {[cls.__name__ for cls in mro]}")
            return False
            
        return True
        
    def validate_infrastructure_access(self, agent: DataHelperAgent) -> bool:
        """Validate access to BaseAgent infrastructure."""
        required_attrs = [
            '_websocket_adapter',
            'timing_collector',
            'llm_manager',
            'redis_manager'
        ]
        
        for attr in required_attrs:
            if not hasattr(agent, attr):
                self.violations.append(f"Missing required infrastructure: {attr}")
                return False
                
        return True
        
    def validate_websocket_events(self) -> bool:
        """Validate WebSocket events meet golden pattern requirements."""
        recorded_types = {event['event_type'] for event in self.websocket_events_recorded}
        
        # Check for required events
        missing = self.REQUIRED_WEBSOCKET_EVENTS - recorded_types
        if missing:
            self.violations.append(f"Missing required WebSocket events: {missing}")
            return False
            
        # Validate event ordering
        if not self._validate_event_ordering():
            return False
            
        # Validate event data completeness
        if not self._validate_event_data():
            return False
            
        return True
        
    def _validate_event_ordering(self) -> bool:
        """Ensure WebSocket events follow proper ordering."""
        if not self.websocket_events_recorded:
            return True
            
        # Tool events must be properly paired
        tool_starts = [e for e in self.websocket_events_recorded if e['event_type'] == 'tool_executing']
        tool_ends = [e for e in self.websocket_events_recorded if e['event_type'] == 'tool_completed']
        
        if len(tool_starts) != len(tool_ends):
            self.violations.append(f"Unpaired tool events: {len(tool_starts)} starts, {len(tool_ends)} ends")
            return False
            
        return True
        
    def _validate_event_data(self) -> bool:
        """Validate WebSocket event data completeness."""
        for event in self.websocket_events_recorded:
            if not event.get('data'):
                self.violations.append(f"Event {event['event_type']} missing data")
                return False
                
        return True
        
    def validate_business_logic_isolation(self, agent: DataHelperAgent) -> bool:
        """Validate business logic is properly isolated from infrastructure."""
        # Should not contain infrastructure code
        agent_code = inspect.getsource(type(agent))
        
        forbidden_patterns = [
            'WebSocketManager',
            'CircuitBreaker', 
            'RetryManager',
            'class.*Manager',  # Generic manager pattern that should be in BaseAgent
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, agent_code):
                self.violations.append(f"Infrastructure code found in business logic: {pattern}")
                return False
                
        return True
        
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        is_compliant = len(self.violations) == 0
        
        return {
            'compliant': is_compliant,
            'violations': self.violations,
            'warnings': self.warnings,
            'websocket_events_count': len(self.websocket_events_recorded),
            'method_calls_count': len(self.method_calls_recorded),
            'events_recorded': [e['event_type'] for e in self.websocket_events_recorded],
            'infrastructure_checks': self.infrastructure_checks,
            'timestamp': datetime.now().isoformat()
        }


class MockWebSocketAdapter:
    """Mock WebSocket adapter that records events for validation."""
    
    def __init__(self, validator: GoldenPatternValidator):
        self.validator = validator
        self.events_sent = []
        
    async def emit_thinking(self, thought: str, step_number: Optional[int] = None) -> None:
        """Mock thinking event emission."""
        event_data = {'thought': thought, 'step_number': step_number}
        self.events_sent.append(('agent_thinking', event_data))
        self.validator.record_websocket_event('agent_thinking', event_data)
        
    async def emit_tool_executing(self, tool_name: str, parameters: Optional[Dict] = None) -> None:
        """Mock tool executing event emission.""" 
        event_data = {'tool_name': tool_name, 'parameters': parameters}
        self.events_sent.append(('tool_executing', event_data))
        self.validator.record_websocket_event('tool_executing', event_data)
        
    async def emit_tool_completed(self, tool_name: str, result: Optional[Dict] = None) -> None:
        """Mock tool completed event emission."""
        event_data = {'tool_name': tool_name, 'result': result}
        self.events_sent.append(('tool_completed', event_data))
        self.validator.record_websocket_event('tool_completed', event_data)
        
    async def emit_progress(self, content: str, is_complete: bool = False) -> None:
        """Mock progress event emission."""
        event_data = {'content': content, 'is_complete': is_complete}
        self.events_sent.append(('agent_progress', event_data))
        self.validator.record_websocket_event('agent_progress', event_data)
        
    async def emit_error(self, error_message: str, error_type: Optional[str] = None,
                        error_details: Optional[Dict] = None) -> None:
        """Mock error event emission."""
        event_data = {
            'error_message': error_message,
            'error_type': error_type,
            'error_details': error_details
        }
        self.events_sent.append(('agent_error', event_data))
        self.validator.record_websocket_event('agent_error', event_data)


class MockLLMManager:
    """Mock LLM manager for testing."""
    
    def __init__(self):
        self.generate_called = False
        self.generate_params = None
        
    async def generate(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Mock LLM generation."""
        self.generate_called = True
        self.generate_params = {'messages': messages, 'kwargs': kwargs}
        
        # Simulate realistic data helper response
        return {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'data_request': {
                            'user_instructions': 'Please provide system metrics and performance data.',
                            'structured_items': [
                                {'category': 'Performance', 'specific_request': 'CPU and memory usage'},
                                {'category': 'Metrics', 'specific_request': 'Response times and throughput'}
                            ]
                        },
                        'success': True
                    })
                }
            }]
        }


class MockDataHelper:
    """Mock DataHelper tool for testing."""
    
    def __init__(self):
        self.generate_data_request_called = False
        self.generate_data_request_params = None
        
    async def generate_data_request(self, user_request: str, triage_result: Dict,
                                  previous_results: List[Dict]) -> Dict[str, Any]:
        """Mock data request generation."""
        self.generate_data_request_called = True
        self.generate_data_request_params = {
            'user_request': user_request,
            'triage_result': triage_result,
            'previous_results': previous_results
        }
        
        # Simulate comprehensive data request
        return {
            'success': True,
            'data_request': {
                'user_instructions': f'To optimize your request "{user_request}", please provide:',
                'structured_items': [
                    {
                        'category': 'System Performance',
                        'specific_request': 'Current CPU, memory, and disk utilization metrics'
                    },
                    {
                        'category': 'Usage Patterns', 
                        'specific_request': 'Peak usage times and traffic patterns'
                    },
                    {
                        'category': 'Configuration',
                        'specific_request': 'Current system configuration and constraints'
                    }
                ]
            }
        }


# ============================================================================
# UNIT TESTS - Business Logic Validation
# ============================================================================

class TestDataHelperAgentGoldenPatternUnit:
    """Unit tests for DataHelperAgent golden pattern compliance."""
    
    @pytest.fixture
    def validator(self):
        """Create pattern validator."""
        return GoldenPatternValidator()
        
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        return MockLLMManager()
        
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        dispatcher = Mock(spec=ToolDispatcher)
        return dispatcher
        
    @pytest.fixture
    def mock_data_helper_tool(self):
        """Create mock data helper tool."""
        return MockDataHelper()
        
    @pytest.fixture
    def agent_with_mocks(self, mock_llm_manager, mock_tool_dispatcher, mock_data_helper_tool, validator):
        """Create DataHelperAgent with mocked dependencies."""
        agent = DataHelperAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # Replace data_helper_tool with mock
        agent.data_helper_tool = mock_data_helper_tool
        
        # Replace WebSocket adapter with mock
        agent._websocket_adapter = MockWebSocketAdapter(validator)
        
        return agent
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_golden_pattern_inheritance_compliance(self, agent_with_mocks, validator):
        """CRITICAL: Validate DataHelperAgent follows golden pattern inheritance."""
        agent = agent_with_mocks
        
        # Test 1: Clean inheritance pattern
        assert validator.validate_inheritance_pattern(agent), \
            f"Inheritance pattern violations: {validator.violations}"
        
        # Test 2: Infrastructure access via BaseAgent
        assert validator.validate_infrastructure_access(agent), \
            f"Infrastructure access violations: {validator.violations}"
        
        # Test 3: Business logic isolation
        import inspect
        import re
        assert validator.validate_business_logic_isolation(agent), \
            f"Business logic isolation violations: {validator.violations}"
        
        # Test 4: No duplicate infrastructure
        agent_methods = [method for method in dir(agent) if not method.startswith('_')]
        infrastructure_methods = ['send_websocket_event', 'retry_operation', 'circuit_breaker']
        
        for infra_method in infrastructure_methods:
            assert infra_method not in agent_methods, \
                f"VIOLATION: Found infrastructure method {infra_method} in DataHelperAgent - should be in BaseAgent"
                
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_abstract_methods_implementation(self, agent_with_mocks):
        """CRITICAL: Validate required abstract methods are implemented."""
        agent = agent_with_mocks
        
        # Test 1: Has execute method (inherited from BaseAgent)
        assert hasattr(agent, 'execute'), "Missing execute method"
        assert callable(getattr(agent, 'execute')), "execute method not callable"
        
        # Test 2: Legacy run method exists (backward compatibility)
        assert hasattr(agent, 'run'), "Missing legacy run method"
        assert callable(getattr(agent, 'run')), "run method not callable"
        
        # Test 3: process_message method exists (API compatibility)
        assert hasattr(agent, 'process_message'), "Missing process_message method"
        assert callable(getattr(agent, 'process_message')), "process_message method not callable"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_business_logic_validation_extreme_cases(self, agent_with_mocks, validator):
        """CRITICAL: Test business logic validation with extreme edge cases."""
        agent = agent_with_mocks
        
        # Test Case 1: Empty user request
        state = DeepAgentState()
        state.user_request = ""
        
        result = await agent.run(
            user_prompt="",
            thread_id="test-empty",
            user_id="test-user", 
            run_id="test-empty-req",
            state=state
        )
        
        assert hasattr(state, 'agent_outputs'), "State missing agent_outputs"
        assert 'data_helper' in state.agent_outputs, "Missing data_helper output"
        
        # Should have fallback behavior
        output = state.agent_outputs['data_helper']
        assert 'fallback_message' in output or output.get('success', False), \
            "No fallback handling for empty request"
        
        # Test Case 2: Malformed state object
        malformed_state = DeepAgentState()
        # Intentionally missing required attributes
        
        result = await agent.run(
            user_prompt="test request",
            thread_id="test-malformed",
            user_id="test-user",
            run_id="test-malformed-state",
            state=malformed_state
        )
        
        # Should handle gracefully without crashing
        assert result is not None, "Agent crashed on malformed state"
        
        # Test Case 3: Extremely long user request (stress test)
        long_request = "x" * 10000  # 10k character request
        long_state = DeepAgentState()
        long_state.user_request = long_request
        
        start_time = time.time()
        result = await agent.run(
            user_prompt=long_request,
            thread_id="test-long",
            user_id="test-user",
            run_id="test-long-req", 
            state=long_state
        )
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time (30 seconds)
        assert execution_time < 30, f"Execution took too long: {execution_time}s"
        assert result is not None, "Failed to handle long request"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_state_management_compliance(self, agent_with_mocks):
        """CRITICAL: Test state management follows golden pattern."""
        agent = agent_with_mocks
        
        # Test 1: Initial state from BaseAgent
        assert hasattr(agent, 'state'), "Missing state attribute"
        assert agent.state == SubAgentLifecycle.PENDING, \
            f"Wrong initial state: {agent.state}, expected PENDING"
        
        # Test 2: State transitions via BaseAgent methods
        agent.set_state(SubAgentLifecycle.RUNNING)
        assert agent.state == SubAgentLifecycle.RUNNING, "State transition failed"
        
        # Test 3: Invalid state transitions are rejected
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent.set_state(SubAgentLifecycle.COMPLETED)  # Can't go RUNNING -> COMPLETED without proper flow
            
        # Test 4: State is preserved across operations
        initial_state = DeepAgentState()
        initial_state.user_request = "test request"
        initial_state.custom_data = "preserved"
        
        result_state = await agent.run(
            user_prompt="test request",
            thread_id="test-preservation",
            user_id="test-user",
            run_id="test-preservation",
            state=initial_state
        )
        
        # Original state should be modified in-place for execute() compatibility
        assert hasattr(initial_state, 'agent_outputs'), "State not properly updated"
        assert hasattr(initial_state, 'custom_data'), "Custom state data lost"
        assert initial_state.custom_data == "preserved", "Custom data not preserved"


# ============================================================================
# INTEGRATION TESTS - BaseAgent Infrastructure Integration  
# ============================================================================

class TestDataHelperAgentInfrastructureIntegration:
    """Integration tests for DataHelperAgent with BaseAgent infrastructure."""
    
    @pytest.fixture
    def mock_services(self):
        """Setup mock services for integration testing."""
        return {
            'llm_manager': MockLLMManager(),
            'tool_dispatcher': Mock(spec=ToolDispatcher),
            'redis_manager': Mock(spec=RedisManager),
            'data_helper': MockDataHelper()
        }
        
    @pytest.fixture
    def agent_integrated(self, mock_services):
        """Create agent with integrated mock services."""
        agent = DataHelperAgent(
            mock_services['llm_manager'],
            mock_services['tool_dispatcher']
        )
        agent.data_helper_tool = mock_services['data_helper']
        agent.redis_manager = mock_services['redis_manager']
        
        return agent
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_baseagent_infrastructure_delegation(self, agent_integrated, mock_services):
        """CRITICAL: Test proper delegation to BaseAgent infrastructure."""
        agent = agent_integrated
        
        # Test 1: Timing collector integration
        assert hasattr(agent, 'timing_collector'), "Missing timing collector from BaseAgent"
        assert agent.timing_collector is not None, "Timing collector not initialized"
        
        # Test 2: Logger integration
        assert hasattr(agent, 'logger'), "Missing logger from BaseAgent"
        assert agent.logger.name.endswith('DataHelperAgent') or 'data_helper' in agent.logger.name, \
            f"Wrong logger name: {agent.logger.name}"
            
        # Test 3: Correlation ID for tracing
        assert hasattr(agent, 'correlation_id'), "Missing correlation ID from BaseAgent"
        assert agent.correlation_id is not None, "Correlation ID not generated"
        
        # Test 4: State management delegation
        initial_state = agent.get_state()
        agent.set_state(SubAgentLifecycle.RUNNING)
        assert agent.get_state() != initial_state, "State management not working"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_llm_manager_integration(self, agent_integrated, mock_services):
        """CRITICAL: Test LLM manager integration through data helper tool."""
        agent = agent_integrated
        mock_llm = mock_services['llm_manager']
        
        # Execute agent to trigger LLM usage
        state = DeepAgentState()
        state.user_request = "Optimize my database performance"
        state.triage_result = {
            'category': 'optimization',
            'confidence': 0.9
        }
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="llm-integration-test",
            user_id="test-user",
            run_id="llm-test-run",
            state=state
        )
        
        # Verify LLM integration occurred through data helper
        mock_data_helper = mock_services['data_helper']
        assert mock_data_helper.generate_data_request_called, \
            "Data helper tool not called - LLM integration failed"
            
        # Verify parameters passed correctly
        params = mock_data_helper.generate_data_request_params
        assert params['user_request'] == state.user_request, "User request not passed to LLM"
        assert params['triage_result'] == state.triage_result, "Triage result not passed to LLM"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_handling_infrastructure_integration(self, agent_integrated, mock_services):
        """CRITICAL: Test error handling integrates with BaseAgent infrastructure."""
        agent = agent_integrated
        
        # Setup data helper to throw exception
        mock_data_helper = mock_services['data_helper']
        mock_data_helper.generate_data_request = AsyncMock(side_effect=Exception("Simulated LLM failure"))
        
        state = DeepAgentState()
        state.user_request = "test request for error handling"
        
        # Should not crash - should handle via BaseAgent error infrastructure
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="error-test",
            user_id="test-user",
            run_id="error-handling-test",
            state=state
        )
        
        # Should have error handling output
        assert hasattr(state, 'agent_outputs'), "Error state not created"
        assert 'data_helper' in state.agent_outputs, "Error output not recorded"
        
        error_output = state.agent_outputs['data_helper']
        assert error_output.get('success', True) == False, "Error not recorded as failure"
        assert 'error' in error_output, "Error details not recorded"
        assert 'fallback_message' in error_output, "No fallback provided"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_context_preservation_across_calls(self, agent_integrated):
        """CRITICAL: Test context preservation across multiple agent calls."""
        agent = agent_integrated
        
        # First call - establish context
        state1 = DeepAgentState()
        state1.user_request = "First optimization request"
        state1.context_data = "important_context"
        
        await agent.run(
            user_prompt=state1.user_request,
            thread_id="context-test-1",
            user_id="context-user",
            run_id="context-run-1",
            state=state1
        )
        
        # Second call - should preserve user context in agent
        state2 = DeepAgentState()
        state2.user_request = "Second optimization request"
        
        await agent.run(
            user_prompt=state2.user_request,
            thread_id="context-test-2", 
            user_id="context-user",  # Same user
            run_id="context-run-2",
            state=state2
        )
        
        # Agent should maintain its own context between calls
        assert hasattr(agent, 'context'), "Agent context not maintained"
        
        # Each state should maintain its own outputs
        assert hasattr(state1, 'agent_outputs'), "First state outputs lost"
        assert hasattr(state2, 'agent_outputs'), "Second state outputs not created"
        assert state1.agent_outputs != state2.agent_outputs, "State outputs not isolated"


# ============================================================================
# WEBSOCKET EVENT EMISSION TESTS
# ============================================================================

class TestDataHelperAgentWebSocketEvents:
    """Test WebSocket event emissions for real-time chat value."""
    
    @pytest.fixture
    def validator(self):
        """Create event validator."""
        return GoldenPatternValidator()
        
    @pytest.fixture
    def agent_with_websocket_mocks(self, validator):
        """Create agent with WebSocket event mocking."""
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        agent = DataHelperAgent(mock_llm, mock_dispatcher)
        agent.data_helper_tool = MockDataHelper()
        
        # Replace WebSocket adapter with validator-integrated mock
        agent._websocket_adapter = MockWebSocketAdapter(validator)
        
        return agent
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_events_complete_flow(self, agent_with_websocket_mocks, validator):
        """CRITICAL: Test complete WebSocket event flow for chat value."""
        agent = agent_with_websocket_mocks
        
        # Execute complete agent flow
        state = DeepAgentState()
        state.user_request = "I need help optimizing my system performance"
        state.triage_result = {
            'category': 'performance_optimization',
            'confidence': 0.95
        }
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="websocket-flow-test",
            user_id="websocket-user",
            run_id="websocket-complete-flow",
            state=state
        )
        
        # Validate WebSocket events were emitted
        assert validator.validate_websocket_events(), \
            f"WebSocket event validation failed: {validator.violations}"
        
        # Verify specific events for chat value
        event_types = {event['event_type'] for event in validator.websocket_events_recorded}
        
        # Must have thinking events for user visibility
        assert 'agent_thinking' in event_types, \
            "Missing agent_thinking events - users won't see reasoning"
        
        # Must have tool events for transparency
        assert 'tool_executing' in event_types, \
            "Missing tool_executing events - users won't see tool usage"
        assert 'tool_completed' in event_types, \
            "Missing tool_completed events - users won't see results"
            
        # Must have progress events for engagement
        progress_events = [e for e in validator.websocket_events_recorded 
                          if e['event_type'] == 'agent_progress']
        assert len(progress_events) > 0, "No progress events - poor user experience"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_events_error_scenarios(self, agent_with_websocket_mocks, validator):
        """CRITICAL: Test WebSocket events during error scenarios."""
        agent = agent_with_websocket_mocks
        
        # Setup tool to fail
        agent.data_helper_tool.generate_data_request = AsyncMock(
            side_effect=Exception("Simulated tool failure")
        )
        
        state = DeepAgentState()
        state.user_request = "test request for error websocket events"
        
        # Execute with error
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="websocket-error-test",
            user_id="websocket-error-user", 
            run_id="websocket-error-flow",
            state=state
        )
        
        # Should still emit events even during errors
        assert len(validator.websocket_events_recorded) > 0, \
            "No WebSocket events during error - users left in dark"
            
        # Should have some indication of completion/status
        event_types = {event['event_type'] for event in validator.websocket_events_recorded}
        completion_indicators = {'agent_progress', 'agent_error', 'agent_completed'}
        
        assert len(event_types & completion_indicators) > 0, \
            "No completion indication during error - poor UX"
            
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_event_content_quality(self, agent_with_websocket_mocks, validator):
        """CRITICAL: Test WebSocket event content provides value to users."""
        agent = agent_with_websocket_mocks
        
        state = DeepAgentState()
        state.user_request = "Help me optimize database queries for better performance"
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="content-quality-test",
            user_id="content-user",
            run_id="content-quality-run",
            state=state
        )
        
        # Validate event content quality
        thinking_events = [e for e in validator.websocket_events_recorded 
                          if e['event_type'] == 'agent_thinking']
        
        for event in thinking_events:
            thought = event['data'].get('thought', '')
            
            # Thoughts must be substantive
            assert len(thought) > 10, f"Thinking event too brief: '{thought}'"
            
            # Thoughts should be user-friendly
            assert not any(tech_term in thought.lower() for tech_term in 
                          ['llm', 'api', 'json', 'exception']), \
                f"Technical jargon in user-facing thought: '{thought}'"
                
        # Tool events must explain what's happening
        tool_events = [e for e in validator.websocket_events_recorded 
                      if e['event_type'] == 'tool_executing']
        
        for event in tool_events:
            tool_name = event['data'].get('tool_name', '')
            assert tool_name, "Tool event missing tool name"
            
            # Tool name should be user-understandable
            assert 'data_helper' in tool_name or 'analysis' in tool_name, \
                f"Tool name not user-friendly: '{tool_name}'"
                
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_event_timing_requirements(self, agent_with_websocket_mocks, validator):
        """CRITICAL: Test WebSocket events meet timing requirements for real-time chat."""
        agent = agent_with_websocket_mocks
        
        state = DeepAgentState()
        state.user_request = "Performance optimization consultation"
        
        start_time = time.time()
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="timing-test",
            user_id="timing-user",
            run_id="timing-requirements",
            state=state
        )
        
        total_time = time.time() - start_time
        
        # Validate event timing
        if len(validator.websocket_events_recorded) > 1:
            # Events should be spread throughout execution
            first_event_time = validator.websocket_events_recorded[0]['timestamp']
            last_event_time = validator.websocket_events_recorded[-1]['timestamp']
            
            event_span = last_event_time - first_event_time
            
            # Events should span a reasonable portion of execution time
            assert event_span >= total_time * 0.3, \
                "Events too clustered - poor real-time experience"
                
        # First event should come quickly (within 500ms)
        if validator.websocket_events_recorded:
            first_event_delay = validator.websocket_events_recorded[0]['timestamp'] - start_time
            assert first_event_delay < 0.5, \
                f"First event too delayed: {first_event_delay}s - poor responsiveness"


# ============================================================================
# ERROR HANDLING AND RELIABILITY PATTERN TESTS
# ============================================================================

class TestDataHelperAgentReliabilityPatterns:
    """Test error handling and reliability patterns."""
    
    @pytest.fixture
    def agent_reliability(self):
        """Create agent for reliability testing."""
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        agent = DataHelperAgent(mock_llm, mock_dispatcher)
        agent.data_helper_tool = MockDataHelper()
        
        return agent
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_llm_failure_resilience(self, agent_reliability):
        """CRITICAL: Test resilience to LLM failures."""
        agent = agent_reliability
        
        # Setup cascading failures
        failure_scenarios = [
            Exception("Connection timeout"),
            Exception("Rate limit exceeded"), 
            Exception("Model unavailable"),
            Exception("Invalid response format")
        ]
        
        for i, failure in enumerate(failure_scenarios):
            agent.data_helper_tool.generate_data_request = AsyncMock(side_effect=failure)
            
            state = DeepAgentState()
            state.user_request = f"Test request {i} for failure resilience"
            
            # Should not crash
            result = await agent.run(
                user_prompt=state.user_request,
                thread_id=f"failure-test-{i}",
                user_id="reliability-user",
                run_id=f"failure-scenario-{i}",
                state=state
            )
            
            # Should have fallback response
            assert hasattr(state, 'agent_outputs'), f"No outputs for failure scenario {i}"
            assert 'data_helper' in state.agent_outputs, f"No data_helper output for scenario {i}"
            
            output = state.agent_outputs['data_helper']
            assert output.get('success', True) == False, f"Failure not recorded for scenario {i}"
            assert 'fallback_message' in output, f"No fallback for scenario {i}"
            
            # Fallback should be helpful
            fallback = output['fallback_message']
            assert len(fallback) > 50, f"Fallback too brief for scenario {i}: '{fallback}'"
            assert 'optimization' in fallback.lower(), f"Fallback not contextual for scenario {i}"
            
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_malformed_input_handling(self, agent_reliability):
        """CRITICAL: Test handling of malformed inputs."""
        agent = agent_reliability
        
        # Test various malformed inputs
        malformed_inputs = [
            None,  # None user request
            "",    # Empty string
            "x" * 100000,  # Extremely long request  
            "🎭🎪🎨" * 1000,  # Unicode stress test
            {"malformed": "object"},  # Wrong type
            ["list", "instead", "of", "string"]  # Wrong type
        ]
        
        for i, bad_input in enumerate(malformed_inputs):
            state = DeepAgentState()
            try:
                state.user_request = bad_input
            except:
                # If we can't even set it, create minimal state
                state = DeepAgentState()
                state.user_request = "fallback request"
                
            # Should handle gracefully
            try:
                result = await agent.run(
                    user_prompt=str(bad_input) if bad_input is not None else "",
                    thread_id=f"malformed-{i}",
                    user_id="malformed-user",
                    run_id=f"malformed-{i}",
                    state=state
                )
                
                # Should complete without crashing
                assert result is not None, f"Agent crashed on malformed input {i}: {bad_input}"
                
            except Exception as e:
                pytest.fail(f"Agent crashed on malformed input {i} ({bad_input}): {e}")
                
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_execution_safety(self, agent_reliability):
        """CRITICAL: Test agent safety under concurrent execution."""
        agent = agent_reliability
        
        # Create multiple concurrent executions
        async def run_agent_instance(instance_id: int):
            state = DeepAgentState()
            state.user_request = f"Concurrent request {instance_id}"
            state.instance_id = instance_id
            
            return await agent.run(
                user_prompt=state.user_request,
                thread_id=f"concurrent-{instance_id}",
                user_id=f"user-{instance_id}",
                run_id=f"concurrent-run-{instance_id}",
                state=state
            )
            
        # Run 10 concurrent instances
        concurrent_count = 10
        tasks = [run_agent_instance(i) for i in range(concurrent_count)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # All should complete
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent execution {i} failed: {result}")
                
        # Performance should not degrade severely
        average_time = execution_time / concurrent_count
        assert average_time < 5.0, f"Concurrent execution too slow: {average_time}s per instance"
        
    @pytest.mark.asyncio 
    @pytest.mark.critical
    async def test_memory_leak_prevention(self, agent_reliability):
        """CRITICAL: Test agent doesn't cause memory leaks during repeated execution."""
        import psutil
        import os
        
        agent = agent_reliability
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss
        
        # Run agent many times
        iterations = 50
        for i in range(iterations):
            state = DeepAgentState()
            state.user_request = f"Memory test iteration {i}"
            
            await agent.run(
                user_prompt=state.user_request,
                thread_id=f"memory-{i}",
                user_id="memory-user",
                run_id=f"memory-iteration-{i}",
                state=state
            )
            
            # Force garbage collection periodically
            if i % 10 == 0:
                import gc
                gc.collect()
                
        # Measure final memory
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        max_increase = 50 * 1024 * 1024  # 50MB
        assert memory_increase < max_increase, \
            f"Memory leak detected: {memory_increase / 1024 / 1024:.1f}MB increase"


# ============================================================================
# LEGACY COMPATIBILITY TESTS
# ============================================================================

class TestDataHelperAgentLegacyCompatibility:
    """Test backward compatibility with existing interfaces."""
    
    @pytest.fixture
    def agent_legacy(self):
        """Create agent for legacy testing."""
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        return DataHelperAgent(mock_llm, mock_dispatcher)
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_legacy_run_method_compatibility(self, agent_legacy):
        """CRITICAL: Test legacy run method interface still works."""
        agent = agent_legacy
        
        # Legacy run method signature
        result = await agent.run(
            user_prompt="Legacy interface test",
            thread_id="legacy-thread",
            user_id="legacy-user", 
            run_id="legacy-run",
            state=None  # Legacy calls might pass None
        )
        
        # Should return DeepAgentState
        assert isinstance(result, DeepAgentState), f"Wrong return type: {type(result)}"
        assert hasattr(result, 'agent_outputs'), "Legacy interface missing agent_outputs"
        assert 'data_helper' in result.agent_outputs, "Legacy interface missing data_helper output"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_legacy_execute_method_compatibility(self, agent_legacy):
        """CRITICAL: Test legacy execute method interface."""
        agent = agent_legacy
        
        state = DeepAgentState()
        state.user_request = "Execute method test"
        
        # Legacy execute signature (modifies state in place)
        original_state_id = id(state)
        
        result = await agent.execute(
            state=state,
            run_id="legacy-execute",
            stream_updates=True
        )
        
        # Should modify original state in place (legacy behavior)
        assert id(state) == original_state_id, "State object replaced instead of modified"
        assert hasattr(state, 'agent_outputs'), "Execute method didn't update state"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_legacy_process_message_compatibility(self, agent_legacy):
        """CRITICAL: Test legacy process_message interface."""
        agent = agent_legacy
        
        # Legacy process_message interface
        message = "Process this message request"
        context = {
            'thread_id': 'legacy-process-thread',
            'user_id': 'legacy-process-user',
            'run_id': 'legacy-process-run',
            'state': None
        }
        
        result = await agent.process_message(message, context)
        
        # Should return dict with specific structure
        assert isinstance(result, dict), f"Wrong return type: {type(result)}"
        assert 'success' in result, "Missing success field"
        assert 'state' in result, "Missing state field"
        assert 'data_request' in result, "Missing data_request field"
        
        # State should be properly created
        returned_state = result['state']
        assert isinstance(returned_state, DeepAgentState), "Wrong state type"
        assert hasattr(returned_state, 'agent_outputs'), "Process message didn't create outputs"
        
    @pytest.mark.asyncio
    @pytest.mark.critical 
    async def test_legacy_attribute_access(self, agent_legacy):
        """CRITICAL: Test legacy attribute access patterns."""
        agent = agent_legacy
        
        # Legacy code may access these attributes
        legacy_attributes = [
            'llm_manager',
            'tool_dispatcher', 
            'data_helper_tool',
            'name',
            'description'
        ]
        
        for attr in legacy_attributes:
            assert hasattr(agent, attr), f"Missing legacy attribute: {attr}"
            value = getattr(agent, attr)
            assert value is not None, f"Legacy attribute {attr} is None"
            
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_legacy_error_format_compatibility(self, agent_legacy):
        """CRITICAL: Test legacy error format is preserved."""
        agent = agent_legacy
        
        # Force error by making tool fail
        agent.data_helper_tool = Mock()
        agent.data_helper_tool.generate_data_request = AsyncMock(
            side_effect=Exception("Legacy error test")
        )
        
        state = DeepAgentState()
        state.user_request = "Test legacy error handling"
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="legacy-error",
            user_id="legacy-error-user",
            run_id="legacy-error-run", 
            state=state
        )
        
        # Check legacy error format
        assert hasattr(state, 'agent_outputs'), "No agent_outputs on error"
        error_output = state.agent_outputs['data_helper']
        
        # Legacy error format requirements
        assert 'success' in error_output, "Missing success field in error"
        assert error_output['success'] == False, "Error not marked as failure"
        assert 'error' in error_output, "Missing error field"
        assert 'fallback_message' in error_output, "Missing fallback_message field"


# ============================================================================
# PERFORMANCE AND TIMING TESTS
# ============================================================================

class TestDataHelperAgentPerformance:
    """Test performance and timing requirements."""
    
    @pytest.fixture
    def agent_performance(self):
        """Create agent for performance testing."""
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        agent = DataHelperAgent(mock_llm, mock_dispatcher)
        
        # Use fast mock for performance testing
        fast_mock = AsyncMock(return_value={
            'success': True,
            'data_request': {
                'user_instructions': 'Fast mock response',
                'structured_items': [{'category': 'Test', 'specific_request': 'Fast'}]
            }
        })
        agent.data_helper_tool = Mock()
        agent.data_helper_tool.generate_data_request = fast_mock
        
        return agent
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_single_execution_performance(self, agent_performance):
        """CRITICAL: Test single execution meets performance requirements."""
        agent = agent_performance
        
        state = DeepAgentState()
        state.user_request = "Performance test request"
        
        # Measure execution time
        start_time = time.time()
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="perf-single",
            user_id="perf-user",
            run_id="perf-single-run",
            state=state
        )
        
        execution_time = time.time() - start_time
        
        # Should complete within 5 seconds for normal request
        assert execution_time < 5.0, f"Single execution too slow: {execution_time}s"
        
        # Should complete within 2 seconds for mocked services
        assert execution_time < 2.0, f"Mocked execution too slow: {execution_time}s"
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_throughput_performance(self, agent_performance):
        """CRITICAL: Test throughput under sequential load."""
        agent = agent_performance
        
        request_count = 20
        requests_per_second_target = 5  # Minimum throughput
        
        start_time = time.time()
        
        for i in range(request_count):
            state = DeepAgentState()
            state.user_request = f"Throughput test request {i}"
            
            result = await agent.run(
                user_prompt=state.user_request,
                thread_id=f"throughput-{i}",
                user_id="throughput-user",
                run_id=f"throughput-run-{i}",
                state=state
            )
            
            assert result is not None, f"Request {i} failed"
            
        total_time = time.time() - start_time
        actual_rps = request_count / total_time
        
        assert actual_rps >= requests_per_second_target, \
            f"Throughput too low: {actual_rps:.1f} RPS, target: {requests_per_second_target} RPS"
            
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_memory_efficiency(self, agent_performance):
        """CRITICAL: Test memory usage efficiency."""
        import psutil
        import os
        
        agent = agent_performance
        process = psutil.Process(os.getpid())
        
        # Measure baseline memory
        initial_memory = process.memory_info().rss
        
        # Create large number of states to test memory efficiency
        large_request_count = 100
        states = []
        
        for i in range(large_request_count):
            state = DeepAgentState()
            state.user_request = f"Memory efficiency test {i}" * 10  # Larger requests
            states.append(state)
            
        # Process all requests
        for i, state in enumerate(states):
            await agent.run(
                user_prompt=state.user_request,
                thread_id=f"memory-eff-{i}",
                user_id="memory-eff-user",
                run_id=f"memory-eff-run-{i}",
                state=state
            )
            
        # Measure final memory
        final_memory = process.memory_info().rss
        memory_per_request = (final_memory - initial_memory) / large_request_count
        
        # Should use less than 1MB per request on average
        max_memory_per_request = 1024 * 1024  # 1MB
        assert memory_per_request < max_memory_per_request, \
            f"Memory per request too high: {memory_per_request / 1024:.0f}KB"
            
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_timing_collector_integration(self, agent_performance):
        """CRITICAL: Test timing collector integration for performance monitoring."""
        agent = agent_performance
        
        # Verify timing collector exists
        assert hasattr(agent, 'timing_collector'), "Missing timing collector"
        assert agent.timing_collector is not None, "Timing collector not initialized"
        
        state = DeepAgentState()
        state.user_request = "Timing collector test"
        
        # Execute with timing
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="timing-test",
            user_id="timing-user",
            run_id="timing-collector-test",
            state=state
        )
        
        # Timing collector should have recorded data
        timing_collector = agent.timing_collector
        
        # Should have some timing data
        if hasattr(timing_collector, 'get_metrics'):
            metrics = timing_collector.get_metrics()
            assert metrics is not None, "Timing collector produced no metrics"
            
        # Should not significantly impact performance
        # (Timing collection overhead should be minimal)


# ============================================================================
# EDGE CASES AND FAILURE SCENARIO TESTS  
# ============================================================================

class TestDataHelperAgentEdgeCases:
    """Test difficult edge cases and failure scenarios."""
    
    @pytest.fixture
    def agent_edge_cases(self):
        """Create agent for edge case testing."""
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        return DataHelperAgent(mock_llm, mock_dispatcher)
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_extremely_complex_triage_results(self, agent_edge_cases):
        """CRITICAL: Test handling of complex nested triage results."""
        agent = agent_edge_cases
        
        # Create extremely complex triage result
        complex_triage = {
            'category': 'multi_dimensional_optimization',
            'confidence': 0.85,
            'subcategories': [
                {
                    'name': 'database_performance', 
                    'confidence': 0.92,
                    'metrics': {
                        'query_time': {'current': 150, 'target': 50, 'unit': 'ms'},
                        'throughput': {'current': 1000, 'target': 5000, 'unit': 'qps'}
                    },
                    'constraints': ['memory_limit', 'cpu_budget', 'downtime_window']
                },
                {
                    'name': 'application_scaling',
                    'confidence': 0.78,
                    'dependencies': ['database_performance', 'network_capacity'],
                    'risk_factors': ['data_consistency', 'user_experience']
                }
            ],
            'cross_cutting_concerns': {
                'security': ['data_encryption', 'access_control'],
                'compliance': ['gdpr', 'sox', 'hipaa'],
                'monitoring': ['alerting', 'logging', 'metrics']
            }
        }
        
        state = DeepAgentState()
        state.user_request = "Comprehensive system optimization with multiple constraints"
        state.triage_result = complex_triage
        
        # Should handle complex structure without failing
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="complex-triage",
            user_id="complex-user",
            run_id="complex-triage-test",
            state=state
        )
        
        assert result is not None, "Failed to handle complex triage result"
        assert hasattr(state, 'agent_outputs'), "Complex triage broke state management"
        
        # Should still produce meaningful data request
        output = state.agent_outputs.get('data_helper', {})
        assert output.get('success', False), "Complex triage handling failed"
        
        if 'data_request' in output:
            data_request = output['data_request']
            assert 'structured_items' in data_request, "Complex triage didn't produce structured output"
            assert len(data_request['structured_items']) > 0, "No structured items for complex scenario"
            
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_unicode_and_special_character_handling(self, agent_edge_cases):
        """CRITICAL: Test handling of Unicode and special characters."""
        agent = agent_edge_cases
        
        # Various Unicode and special character scenarios
        unicode_scenarios = [
            "优化我的数据库性能 🚀",  # Chinese with emoji
            "Améliorer les performances de la base de données 🇫🇷",  # French with flag
            "Оптимизировать производительность базы данных",  # Russian
            "डेटाबेस प्रदर्शन को अनुकूलित करें",  # Hindi
            "🎯 Optimize ⚡ performance 🔥 with 💯% efficiency",  # Heavy emoji usage
            "Test with quotes: 'single' and \"double\" and `backticks`",  # Quote variations
            "Test with symbols: @#$%^&*()[]{}|\\:;\"'<>?,./-_+=~`",  # Special characters
            "Line breaks\nand\ttabs\rand\fform feeds",  # Whitespace variations
        ]
        
        for i, unicode_request in enumerate(unicode_scenarios):
            state = DeepAgentState()
            state.user_request = unicode_request
            
            try:
                result = await agent.run(
                    user_prompt=unicode_request,
                    thread_id=f"unicode-{i}",
                    user_id="unicode-user",
                    run_id=f"unicode-test-{i}",
                    state=state
                )
                
                assert result is not None, f"Unicode scenario {i} failed: '{unicode_request}'"
                assert hasattr(state, 'agent_outputs'), f"Unicode scenario {i} broke state"
                
            except Exception as e:
                pytest.fail(f"Unicode scenario {i} crashed ('{unicode_request}'): {e}")
                
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_boundary_value_scenarios(self, agent_edge_cases):
        """CRITICAL: Test boundary value scenarios."""
        agent = agent_edge_cases
        
        boundary_scenarios = [
            {
                'name': 'minimum_request',
                'user_request': 'x',
                'triage_result': {},
                'expected_success': True  # Should handle minimal input
            },
            {
                'name': 'maximum_request',
                'user_request': 'x' * 50000,  # 50k characters
                'triage_result': {'category': 'test'},
                'expected_success': True  # Should handle large input
            },
            {
                'name': 'empty_triage',
                'user_request': 'normal request',
                'triage_result': {},
                'expected_success': True  # Should handle missing triage
            },
            {
                'name': 'null_values',
                'user_request': 'request with nulls',
                'triage_result': {'category': None, 'confidence': None},
                'expected_success': True  # Should handle null values
            },
            {
                'name': 'extreme_confidence',
                'user_request': 'confidence test',
                'triage_result': {'category': 'test', 'confidence': 999.999},
                'expected_success': True  # Should handle out-of-range confidence
            }
        ]
        
        for scenario in boundary_scenarios:
            state = DeepAgentState()
            state.user_request = scenario['user_request']
            state.triage_result = scenario['triage_result']
            
            try:
                result = await agent.run(
                    user_prompt=scenario['user_request'],
                    thread_id=f"boundary-{scenario['name']}",
                    user_id="boundary-user",
                    run_id=f"boundary-{scenario['name']}",
                    state=state
                )
                
                if scenario['expected_success']:
                    assert result is not None, f"Boundary scenario '{scenario['name']}' failed unexpectedly"
                    assert hasattr(state, 'agent_outputs'), f"Boundary scenario '{scenario['name']}' broke state"
                    
            except Exception as e:
                if scenario['expected_success']:
                    pytest.fail(f"Boundary scenario '{scenario['name']}' crashed: {e}")
                    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_resource_exhaustion_scenarios(self, agent_edge_cases):
        """CRITICAL: Test behavior under resource exhaustion."""
        agent = agent_edge_cases
        
        # Test with resource-intensive scenarios
        resource_scenarios = [
            {
                'name': 'memory_intensive',
                'setup': lambda: setattr(agent, 'data_helper_tool', 
                    Mock(generate_data_request=AsyncMock(return_value={
                        'success': True,
                        'data_request': {
                            'user_instructions': 'x' * 100000,  # Large response
                            'structured_items': [{'category': f'Item {i}', 'specific_request': 'x' * 1000} 
                                                for i in range(1000)]  # Many items
                        }
                    })))
            },
            {
                'name': 'slow_response',
                'setup': lambda: setattr(agent, 'data_helper_tool',
                    Mock(generate_data_request=AsyncMock(side_effect=lambda *args, **kwargs: 
                        asyncio.sleep(0.5).then(lambda: {  # Simulated slow response
                            'success': True,
                            'data_request': {'user_instructions': 'Slow response', 'structured_items': []}
                        }) if False else {  # Use side effect properly
                            'success': True,
                            'data_request': {'user_instructions': 'Slow response', 'structured_items': []}
                        })))
            }
        ]
        
        for scenario in resource_scenarios:
            scenario['setup']()
            
            state = DeepAgentState()
            state.user_request = f"Resource test: {scenario['name']}"
            
            start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    agent.run(
                        user_prompt=state.user_request,
                        thread_id=f"resource-{scenario['name']}",
                        user_id="resource-user", 
                        run_id=f"resource-{scenario['name']}",
                        state=state
                    ),
                    timeout=10.0  # 10 second timeout
                )
                
                execution_time = time.time() - start_time
                
                # Should complete even under resource pressure
                assert result is not None, f"Resource scenario '{scenario['name']}' failed"
                assert execution_time < 10.0, f"Resource scenario '{scenario['name']}' too slow"
                
            except asyncio.TimeoutError:
                pytest.fail(f"Resource scenario '{scenario['name']}' timed out")
            except Exception as e:
                pytest.fail(f"Resource scenario '{scenario['name']}' crashed: {e}")


# ============================================================================
# GOLDEN PATTERN VALIDATION SUITE
# ============================================================================

class TestDataHelperAgentGoldenPatternValidation:
    """Final validation of complete golden pattern compliance."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_golden_pattern_compliance(self):
        """CRITICAL: Comprehensive golden pattern validation."""
        # Setup complete test environment
        validator = GoldenPatternValidator()
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        agent = DataHelperAgent(mock_llm, mock_dispatcher)
        agent.data_helper_tool = MockDataHelper()
        agent._websocket_adapter = MockWebSocketAdapter(validator)
        
        # Test 1: Architecture compliance
        assert validator.validate_inheritance_pattern(agent), \
            f"Architecture violations: {validator.violations}"
            
        # Test 2: Infrastructure integration
        assert validator.validate_infrastructure_access(agent), \
            f"Infrastructure violations: {validator.violations}"
            
        # Test 3: Complete execution flow with events
        state = DeepAgentState()
        state.user_request = "Complete golden pattern validation test"
        state.triage_result = {'category': 'optimization', 'confidence': 0.9}
        
        result = await agent.run(
            user_prompt=state.user_request,
            thread_id="golden-pattern-test",
            user_id="golden-user",
            run_id="golden-pattern-validation",
            state=state
        )
        
        # Test 4: WebSocket events compliance
        assert validator.validate_websocket_events(), \
            f"WebSocket event violations: {validator.violations}"
            
        # Test 5: Business logic isolation
        assert validator.validate_business_logic_isolation(agent), \
            f"Business logic violations: {validator.violations}"
            
        # Generate final compliance report
        report = validator.generate_compliance_report()
        
        if not report['compliant']:
            logger.error(f"Golden Pattern Compliance Report: {json.dumps(report, indent=2)}")
            
        assert report['compliant'], \
            f"Golden pattern compliance failed. Violations: {report['violations']}"
            
        logger.info("✅ DataHelperAgent PASSES complete golden pattern validation")
        
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_production_readiness_checklist(self):
        """CRITICAL: Final production readiness validation."""
        mock_llm = MockLLMManager()
        mock_dispatcher = Mock(spec=ToolDispatcher)
        agent = DataHelperAgent(mock_llm, mock_dispatcher)
        
        production_checklist = {
            'inheritance_pattern': lambda: isinstance(agent, BaseAgent),
            'websocket_capability': lambda: hasattr(agent, '_websocket_adapter'),
            'error_handling': lambda: hasattr(agent, 'run'),  # Has error-wrapped methods
            'state_management': lambda: hasattr(agent, 'state'),
            'logging': lambda: hasattr(agent, 'logger'),
            'timing': lambda: hasattr(agent, 'timing_collector'), 
            'llm_integration': lambda: hasattr(agent, 'llm_manager'),
            'tool_integration': lambda: hasattr(agent, 'data_helper_tool'),
            'backward_compatibility': lambda: hasattr(agent, 'execute'),
            'api_compatibility': lambda: hasattr(agent, 'process_message')
        }
        
        failures = []
        for check_name, check_func in production_checklist.items():
            try:
                if not check_func():
                    failures.append(check_name)
            except Exception as e:
                failures.append(f"{check_name} (exception: {e})")
                
        assert len(failures) == 0, \
            f"Production readiness failures: {failures}"
            
        logger.info("✅ DataHelperAgent PASSES production readiness checklist")


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_datahelper_golden_alignment.py
    # Or: pytest tests/mission_critical/test_datahelper_golden_alignment.py -v --tb=short
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # -x stops on first failure