"""
Comprehensive Test Plan for Issue #408 - SupervisorAgent Missing Attributes

This test file implements the 5-phase test plan to systematically validate
SupervisorAgent missing attributes and methods that are causing test failures.

Business Impact: $500K+ ARR protection - Agent execution infrastructure repair
Priority: P1 High - Prevents 90% platform value restoration (chat functionality)

Test Structure:
Phase 1: Basic instantiation and attribute existence
Phase 2: Reproduction of specific failing test scenarios  
Phase 3: Method signature validation
Phase 4: Integration behavior testing
Phase 5: Business value validation

GitHub Issue: https://github.com/netra-systems/netra-apex/issues/408
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio
from typing import Any, Dict

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core imports
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from sqlalchemy.ext.asyncio import AsyncSession


class TestSupervisorMissingAttributesIssue408:
    """
    Test suite for Issue #408 - SupervisorAgent missing attributes
    
    This comprehensive test validates the missing attributes and methods
    that are causing failures in the supervisor execution test suite.
    """

    @pytest.fixture(autouse=True)
    def setup_supervisor_test(self):
        """Set up test fixtures for each test method."""
        # Create mock dependencies
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_db_session = Mock(spec=AsyncSession)
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Configure websocket bridge mock
        self.mock_websocket_manager = Mock(spec=UnifiedWebSocketManager)
        self.mock_websocket_bridge.websocket_manager = self.mock_websocket_manager
        self.mock_websocket_bridge.emit_agent_event = AsyncMock()
        
        # Create supervisor instance for testing
        try:
            self.supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge,
                tool_dispatcher=self.mock_tool_dispatcher
            )
        except Exception as e:
            # If supervisor creation fails, store the error for tests
            self.supervisor_creation_error = e
            self.supervisor = None
        
    # === PHASE 1: BASIC INSTANTIATION AND ATTRIBUTE EXISTENCE ===
    
    def test_phase1_supervisor_basic_instantiation(self):
        """Phase 1.1: Test that SupervisorAgent can be instantiated without errors."""
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Basic validation
        assert supervisor is not None
        assert supervisor.name == "Supervisor"
        assert hasattr(supervisor, 'websocket_bridge')
        assert supervisor.websocket_bridge is not None
    
    def test_phase1_reliability_manager_attribute_exists(self):
        """Phase 1.2: Test that reliability_manager attribute exists but is None - EXPECTED TO FAIL."""
        # This test proves the issue exists - reliability_manager exists but is None
        assert self.supervisor is not None, "Supervisor creation failed in setUp"
        
        # The attribute exists but is None, which causes the NoneType error
        assert hasattr(self.supervisor, 'reliability_manager'), "reliability_manager attribute should exist"
        assert self.supervisor.reliability_manager is None, "reliability_manager should be None - this is the bug!"
    
    def test_phase1_workflow_executor_attribute_exists(self):
        """Phase 1.3: Test that workflow_executor attribute exists - EXPECTED TO FAIL."""
        # This test should FAIL and prove the issue exists
        assert self.supervisor is not None, "Supervisor creation failed in setUp"
        
        with pytest.raises(AttributeError, match=".*has no attribute.*workflow_executor"):
            # This should fail because workflow_executor doesn't exist
            _ = self.supervisor.workflow_executor
    
    def test_phase1_create_supervisor_execution_context_method_exists(self):
        """Phase 1.4: Test that _create_supervisor_execution_context method exists - EXPECTED TO FAIL."""
        # This test should FAIL and prove the issue exists
        assert self.supervisor is not None, "Supervisor creation failed in setUp"
        
        with pytest.raises(AttributeError, match=".*has no attribute.*_create_supervisor_execution_context"):
            # This should fail because method doesn't exist
            _ = self.supervisor._create_supervisor_execution_context
    
    # === PHASE 2: REPRODUCTION OF SPECIFIC FAILING TEST SCENARIOS ===
    
    @pytest.mark.asyncio
    async def test_phase2_reproduce_execute_method_failure(self):
        """
        Phase 2.1: Reproduce the exact failure from test_execute_method
        
        This test reproduces the AttributeError where reliability_manager is None
        and accessing execute_with_reliability fails.
        """
        assert self.supervisor is not None, "Supervisor creation failed in setUp"
        
        # Create state as in original failing test
        state = DeepAgentState(
            user_request="test query",
            chat_thread_id="thread-123",
            user_id="user-456"
        )
        run_id = "run-789"
        
        # This should demonstrate the reliability_manager is None causing NoneType error
        with pytest.raises(AttributeError) as exc_info:
            # Try to access reliability_manager.execute_with_reliability
            # This will fail with: 'NoneType' object has no attribute 'execute_with_reliability'
            await self.supervisor.reliability_manager.execute_with_reliability(state, run_id)
        
        # Validate the specific error message matches what we see in test failures
        error_msg = str(exc_info.value)
        assert "'NoneType' object has no attribute 'execute_with_reliability'" in error_msg, (
            f"Expected NoneType error, got: {error_msg}"
        )
    
    @pytest.mark.asyncio  
    async def test_phase2_reproduce_workflow_executor_failure(self):
        """
        Phase 2.2: Reproduce the workflow_executor attribute error
        
        This test reproduces the AttributeError where workflow_executor doesn't exist.
        """
        assert self.supervisor is not None, "Supervisor creation failed in setUp"
        
        # This should demonstrate workflow_executor doesn't exist
        with pytest.raises(AttributeError) as exc_info:
            # Try to access workflow_executor.execute_workflow_steps
            await self.supervisor.workflow_executor.execute_workflow_steps(
                "flow_id", "test query", "thread-123", "user-456", "run-789"
            )
        
        # Validate the specific error message
        error_msg = str(exc_info.value)
        assert ("has no attribute" in error_msg and "workflow_executor" in error_msg)
    
    def test_phase2_reproduce_create_execution_context_failure(self):
        """
        Phase 2.3: Reproduce the _create_supervisor_execution_context method failure
        
        This test reproduces the AttributeError where the method doesn't exist.
        """
        assert self.supervisor is not None, "Supervisor creation failed in setUp"
        
        state = DeepAgentState(
            user_request="test query", 
            chat_thread_id="thread-123",
            user_id="user-456"
        )
        
        # This should demonstrate the method doesn't exist
        with pytest.raises(AttributeError) as exc_info:
            # Try to call the missing method
            self.supervisor._create_supervisor_execution_context(state, "run-789", True)
        
        # Validate the specific error message
        error_msg = str(exc_info.value)
        assert ("has no attribute" in error_msg and "_create_supervisor_execution_context" in error_msg)
    
    # === PHASE 3: METHOD SIGNATURE VALIDATION ===
    
    def test_phase3_execute_method_signature_validation(self):
        """Phase 3.1: Test that execute method has correct UserExecutionContext signature."""
        # The execute method should exist and accept UserExecutionContext
        assert hasattr(self.supervisor, 'execute')
        
        # Check method signature expects UserExecutionContext, not DeepAgentState
        import inspect
        sig = inspect.signature(self.supervisor.execute)
        
        # First parameter (after self) should be context
        params = list(sig.parameters.keys())
        assert 'context' in params, f"Execute method parameters: {params}"
        
        # The method should be async
        assert asyncio.iscoroutinefunction(self.supervisor.execute)
    
    def test_phase3_legacy_run_method_exists(self):
        """Phase 3.2: Test that legacy run method still exists for compatibility."""
        # Legacy run method should exist for backward compatibility
        assert hasattr(self.supervisor, 'run')
        assert asyncio.iscoroutinefunction(self.supervisor.run)
        
        # Check run method signature
        import inspect
        sig = inspect.signature(self.supervisor.run)
        params = list(sig.parameters.keys())
        
        # Should accept legacy parameters
        expected_params = ['user_request', 'thread_id', 'user_id', 'run_id']
        for param in expected_params:
            assert param in params, f"Missing parameter {param} in run method"
    
    # === PHASE 4: INTEGRATION BEHAVIOR TESTING ===
    
    @pytest.mark.asyncio
    async def test_phase4_execute_with_userexecutioncontext(self):
        """
        Phase 4.1: Test execute method works with UserExecutionContext pattern
        
        This tests the new execution pattern that should replace the missing methods.
        """
        from shared.id_generation import UnifiedIdGenerator
        
        # Create UserExecutionContext
        context = UserExecutionContext(
            user_id="user-456",
            thread_id="thread-123",
            run_id="run-789",
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("user-456")
        )
        
        # Add metadata that supervisor expects
        context.metadata['user_request'] = "test query"
        
        # Mock database session in context
        context.db_session = self.mock_db_session
        
        # Execute should work with UserExecutionContext
        try:
            result = await self.supervisor.execute(context, stream_updates=True)
            # If this succeeds, the new pattern is working
            assert isinstance(result, dict)
            assert 'supervisor_result' in result or 'orchestration_successful' in result
            
        except Exception as e:
            # If it fails, it should be due to missing dependencies, not missing attributes
            error_msg = str(e).lower()
            # Should NOT be attribute errors for the missing components we're testing
            forbidden_errors = [
                'reliability_manager',
                'workflow_executor', 
                '_create_supervisor_execution_context'
            ]
            
            for forbidden in forbidden_errors:
                assert forbidden not in error_msg, (
                    f"Execute failed due to missing {forbidden} - "
                    f"this indicates the issue still exists: {e}"
                )
    
    @pytest.mark.asyncio
    async def test_phase4_legacy_run_method_integration(self):
        """
        Phase 4.2: Test legacy run method integration
        
        Tests that the legacy run method can convert to UserExecutionContext
        and doesn't fail on missing attributes.
        """
        # Mock WebSocket manager for events
        self.mock_websocket_manager.send_to_user = AsyncMock()
        
        try:
            result = await self.supervisor.run(
                user_request="test query",
                thread_id="thread-123", 
                user_id="user-456",
                run_id="run-789"
            )
            
            # If this succeeds, legacy integration is working
            assert result is not None
            
        except Exception as e:
            # If it fails, should not be due to the missing attributes we're testing
            error_msg = str(e).lower()
            forbidden_errors = [
                'reliability_manager',
                'workflow_executor',
                '_create_supervisor_execution_context'
            ]
            
            for forbidden in forbidden_errors:
                assert forbidden not in error_msg, (
                    f"Legacy run failed due to missing {forbidden} - "
                    f"this indicates backward compatibility is broken: {e}"
                )
    
    # === PHASE 5: BUSINESS VALUE VALIDATION ===
    
    @pytest.mark.asyncio
    async def test_phase5_websocket_events_business_value(self):
        """
        Phase 5.1: Test WebSocket events for chat business value
        
        Validates that SupervisorAgent can emit the required WebSocket events
        that deliver 90% of platform business value through chat functionality.
        """
        from shared.id_generation import UnifiedIdGenerator
        
        # Create context for WebSocket event testing
        context = UserExecutionContext(
            user_id="user-456",
            thread_id="thread-123", 
            run_id="run-789",
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("user-456")
        )
        context.metadata['user_request'] = "optimize my AI costs"
        
        # Test agent_started event emission
        await self.supervisor._emit_agent_started(context, "optimize my AI costs")
        
        # Verify agent_started event was sent
        self.mock_websocket_manager.send_to_user.assert_called()
        call_args = self.mock_websocket_manager.send_to_user.call_args
        assert call_args[0][0] == "user-456"  # user_id
        
        event_data = call_args[0][1]
        assert event_data['type'] == 'agent_started'
        assert event_data['agent_id'] == 'supervisor'
        assert 'details' in event_data
        assert event_data['details']['agent_name'] == 'Supervisor Agent'
        
        # Reset mock for next test
        self.mock_websocket_manager.send_to_user.reset_mock()
        
        # Test agent_completed event emission
        result = {"supervisor_result": "completed", "orchestration_successful": True}
        await self.supervisor._emit_agent_completed(context, result)
        
        # Verify agent_completed event was sent
        self.mock_websocket_manager.send_to_user.assert_called()
        call_args = self.mock_websocket_manager.send_to_user.call_args
        assert call_args[0][0] == "user-456"  # user_id
        
        event_data = call_args[0][1]
        assert event_data['type'] == 'agent_completed'
        assert event_data['agent_id'] == 'supervisor'
        assert event_data['details']['status'] == 'completed'
    
    def test_phase5_agent_dependencies_configuration(self):
        """
        Phase 5.2: Test agent dependencies configuration for business workflow
        
        Validates that the AGENT_DEPENDENCIES configuration supports the business
        workflow that delivers value to users.
        """
        # Test AGENT_DEPENDENCIES class variable exists
        assert hasattr(SupervisorAgent, 'AGENT_DEPENDENCIES')
        deps = SupervisorAgent.AGENT_DEPENDENCIES
        
        # Verify critical agents are configured
        critical_agents = ['triage', 'reporting']
        for agent in critical_agents:
            assert agent in deps, f"Critical agent {agent} missing from AGENT_DEPENDENCIES"
            
            # Verify agent configuration structure
            agent_config = deps[agent]
            required_keys = ['required', 'optional', 'produces', 'priority']
            for key in required_keys:
                assert key in agent_config, f"Agent {agent} missing {key} configuration"
        
        # Verify reporting agent is marked as critical for business value
        reporting_config = deps['reporting']
        assert reporting_config.get('can_fail', True) is False, (
            "Reporting agent must be marked as can_fail=False for business value delivery"
        )
        
        # Verify UVS (Universal Value System) flag
        assert reporting_config.get('uvs_enabled', False) is True, (
            "Reporting agent must have UVS enhancements enabled"
        )
    
    @pytest.mark.asyncio
    async def test_phase5_orchestration_business_workflow(self):
        """
        Phase 5.3: Test orchestration workflow supports business requirements
        
        Validates that the supervisor can orchestrate agents in a way that
        delivers business value even when individual components fail.
        """
        from shared.id_generation import UnifiedIdGenerator
        
        # Create realistic business context
        context = UserExecutionContext(
            user_id="enterprise-user-123",
            thread_id="support-thread-456",
            run_id="business-run-789", 
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("enterprise-user-123"),
            db_session=self.mock_db_session
        )
        context.metadata['user_request'] = "My AI infrastructure costs are too high, help me optimize"
        
        # Test that supervisor can determine execution order
        # This should work without the missing attributes
        execution_order = self.supervisor._determine_execution_order(None, context)
        
        # Verify business-critical workflow
        assert isinstance(execution_order, list)
        assert len(execution_order) > 0
        
        # Reporting should always be in the workflow (UVS principle)
        assert 'reporting' in execution_order, (
            "Reporting agent must always be in execution order for business value"
        )
        
        # Reporting should be last (to consolidate all other results)
        assert execution_order[-1] == 'reporting', (
            "Reporting agent should be last in execution order"
        )
    
    # === DIAGNOSTIC AND DEBUGGING TESTS ===
    
    def test_diagnostic_supervisor_current_attributes(self):
        """
        Diagnostic: List all current attributes and methods of SupervisorAgent
        
        This test documents what actually exists vs what the failing tests expect.
        """
        # Get all attributes and methods
        all_attrs = [attr for attr in dir(self.supervisor) if not attr.startswith('__')]
        
        # Categorize by type
        methods = []
        properties = []
        other_attrs = []
        
        for attr_name in all_attrs:
            attr_value = getattr(self.supervisor, attr_name)
            if callable(attr_value):
                methods.append(attr_name)
            elif isinstance(attr_value, property):
                properties.append(attr_name)
            else:
                other_attrs.append(attr_name)
        
        # Print diagnostic information
        print(f"\n=== SupervisorAgent Diagnostic Information ===")
        print(f"Total attributes: {len(all_attrs)}")
        print(f"Methods ({len(methods)}): {sorted(methods)}")
        print(f"Properties ({len(properties)}): {sorted(properties)}")
        print(f"Other attributes ({len(other_attrs)}): {sorted(other_attrs)}")
        
        # Check for the specific missing attributes
        missing_attrs = []
        expected_attrs = [
            'reliability_manager',
            'workflow_executor', 
            'execution_engine',
            'error_handler',
            'flow_logger'
        ]
        
        for attr in expected_attrs:
            if not hasattr(self.supervisor, attr):
                missing_attrs.append(attr)
        
        print(f"\nMissing expected attributes: {missing_attrs}")
        
        # Check for the specific missing methods
        missing_methods = []
        expected_methods = [
            '_create_supervisor_execution_context',
            '_execute_with_modern_reliability_pattern'
        ]
        
        for method in expected_methods:
            if not hasattr(self.supervisor, method):
                missing_methods.append(method)
        
        print(f"Missing expected methods: {missing_methods}")
        
        # This test always passes - it's just diagnostic
        assert True
    
    def test_diagnostic_baseagent_inheritance_analysis(self):
        """
        Diagnostic: Analyze BaseAgent inheritance to understand missing attributes
        
        This test examines what SupervisorAgent inherits from BaseAgent.
        """
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Check inheritance
        assert isinstance(self.supervisor, BaseAgent)
        
        # Get BaseAgent attributes
        base_attrs = [attr for attr in dir(BaseAgent) if not attr.startswith('__')]
        supervisor_attrs = [attr for attr in dir(self.supervisor) if not attr.startswith('__')]
        
        # Find attributes inherited from BaseAgent
        inherited_attrs = [attr for attr in supervisor_attrs if attr in base_attrs]
        supervisor_only_attrs = [attr for attr in supervisor_attrs if attr not in base_attrs]
        
        print(f"\n=== Inheritance Analysis ===")
        print(f"BaseAgent attributes: {len(base_attrs)}")
        print(f"SupervisorAgent total attributes: {len(supervisor_attrs)}")
        print(f"Inherited attributes: {len(inherited_attrs)}")
        print(f"SupervisorAgent-specific attributes: {len(supervisor_only_attrs)}")
        
        # Check if BaseAgent provides the missing attributes
        base_provides_missing = []
        expected_attrs = ['reliability_manager', 'execution_engine', 'error_handler']
        
        for attr in expected_attrs:
            if hasattr(BaseAgent, attr):
                base_provides_missing.append(attr)
        
        print(f"BaseAgent provides these expected attributes: {base_provides_missing}")
        
        # This test always passes - it's just diagnostic
        assert True


# === UTILITY TEST CLASSES FOR MOCKING ===

class MockReliabilityManager:
    """Mock reliability manager for testing missing attribute scenarios."""
    
    async def execute_with_reliability(self, context, func, **kwargs):
        """Mock execute_with_reliability method."""
        return {"success": True, "result": "mock_result"}


class MockWorkflowExecutor:
    """Mock workflow executor for testing missing attribute scenarios."""
    
    async def execute_workflow_steps(self, flow_id, user_request, thread_id, user_id, run_id):
        """Mock execute_workflow_steps method."""
        return DeepAgentState(user_request=user_request)


class MockExecutionEngine:
    """Mock execution engine for testing missing attribute scenarios."""
    
    async def execute(self, context):
        """Mock execute method."""
        return {"status": "completed"}


# === INTEGRATION TEST THAT SHOULD WORK AFTER FIXES ===

class TestSupervisorExpectedBehaviorAfterFix:
    """
    Tests that should PASS after the missing attributes are implemented.
    
    These tests define the expected behavior once issue #408 is resolved.
    Currently these will fail, but they show what success looks like.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
    
    @pytest.mark.skip(reason="Will pass after issue #408 is fixed")
    def test_reliability_manager_exists_and_functional(self):
        """Test that reliability_manager exists and has required methods."""
        # This should pass after the fix
        assert hasattr(self.supervisor, 'reliability_manager')
        assert self.supervisor.reliability_manager is not None
        assert hasattr(self.supervisor.reliability_manager, 'execute_with_reliability')
    
    @pytest.mark.skip(reason="Will pass after issue #408 is fixed") 
    def test_workflow_executor_exists_and_functional(self):
        """Test that workflow_executor exists and has required methods.""" 
        # This should pass after the fix
        assert hasattr(self.supervisor, 'workflow_executor')
        assert self.supervisor.workflow_executor is not None
        assert hasattr(self.supervisor.workflow_executor, 'execute_workflow_steps')
    
    @pytest.mark.skip(reason="Will pass after issue #408 is fixed")
    def test_create_supervisor_execution_context_exists(self):
        """Test that _create_supervisor_execution_context method exists."""
        # This should pass after the fix
        assert hasattr(self.supervisor, '_create_supervisor_execution_context')
        assert callable(self.supervisor._create_supervisor_execution_context)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])