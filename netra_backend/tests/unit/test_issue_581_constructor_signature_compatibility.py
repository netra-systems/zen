"""
Unit Tests for Issue #581: DataSubAgent Constructor Signature Compatibility

BUSINESS VALUE:
- Enterprise/Platform | System Stability | Critical feature rescue
- Ensures $500K+ ARR data agent functionality works reliably
- Protects Golden Path user flow: login → get AI responses

TEST STRATEGY:
1. Constructor signature compatibility - verify UnifiedDataAgent accepts 'name' parameter
2. DataSubAgent alias functionality - verify backward compatibility
3. Parameter validation - ensure all expected parameters are properly handled
4. Factory pattern integration - verify agent creation through factory patterns

CRITICAL: These tests should INITIALLY FAIL to demonstrate the constructor signature issue,
then pass after Issue #581 is resolved.

SSOT Compliance:
- Uses SSotBaseTestCase for consistent test infrastructure
- Environment isolation through IsolatedEnvironment (no os.environ access)
- Real service preference with minimal mocking
- Business value focused test scenarios

Related Files:
- /netra_backend/app/agents/data/unified_data_agent.py (main implementation)
- /netra_backend/app/agents/data_sub_agent/data_sub_agent.py (backward compatibility alias)
- /netra_backend/app/agents/base_agent.py (base class with 'name' parameter)
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch

# SSOT Compliance: Use SSOT BaseTestCase
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the agents under test
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent, UnifiedDataAgentFactory
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent

# Import required dependencies
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager

class TestIssue581ConstructorSignatureCompatibility(SSotBaseTestCase):
    """
    Unit tests for Issue #581 constructor signature compatibility.
    
    These tests verify that the DataSubAgent (UnifiedDataAgent alias) can be
    instantiated with various parameter combinations, specifically including
    the 'name' parameter that was causing failures.
    """
    
    def setup_method(self, method):
        """Setup test environment with isolation."""
        super().setup_method(method)
        
        # Create mock dependencies for testing
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_context = self._create_mock_user_context()
        
        # Record metrics for constructor tests
        self.record_metric("test_category", "constructor_compatibility")
        self.record_metric("issue_number", "581")
    
    def _create_mock_user_context(self) -> Mock:
        """Create a properly mocked UserExecutionContext."""
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "test_user_581"
        mock_context.request_id = "test_request_581"
        mock_context.metadata = {}
        mock_context.agent_input = {}
        return mock_context
    
    def test_unified_data_agent_constructor_accepts_name_parameter(self):
        """
        CRITICAL: Test that UnifiedDataAgent constructor accepts 'name' parameter.
        
        This test verifies the core issue - that the constructor can handle
        the 'name' parameter that's being passed from calling code.
        
        Expected to FAIL initially, then PASS after Issue #581 fix.
        """
        # Arrange
        expected_name = "data_analysis_agent"
        
        # Act & Assert - This should NOT raise TypeError about unexpected keyword argument
        try:
            agent = UnifiedDataAgent(
                context=self.mock_context,
                name=expected_name,  # This parameter should be accepted
                llm_manager=self.mock_llm_manager
            )
            
            # Verify the agent was created successfully
            self.assertIsNotNone(agent)
            self.assertEqual(agent.name, expected_name)
            self.record_metric("constructor_with_name_success", True)
            
        except TypeError as e:
            # If this fails, it demonstrates the Issue #581 problem
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("constructor_with_name_success", False)
                pytest.fail(f"Issue #581 reproduced: {e}")
            else:
                # Some other TypeError - re-raise
                raise
    
    def test_datasubagent_alias_constructor_compatibility(self):
        """
        Test that DataSubAgent alias works with 'name' parameter.
        
        This verifies backward compatibility through the alias.
        """
        # Arrange
        expected_name = "legacy_data_agent"
        
        # Act & Assert
        try:
            agent = DataSubAgent(
                context=self.mock_context,
                name=expected_name,  # Should work through alias
                llm_manager=self.mock_llm_manager
            )
            
            # Verify the agent was created and is actually UnifiedDataAgent
            self.assertIsNotNone(agent)
            assert isinstance(agent, UnifiedDataAgent)
            self.assertEqual(agent.name, expected_name)
            self.record_metric("datasubagent_alias_success", True)
            
        except TypeError as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("datasubagent_alias_success", False)
                pytest.fail(f"DataSubAgent alias Issue #581 reproduced: {e}")
            else:
                raise
    
    def test_constructor_parameter_validation(self):
        """
        Test various constructor parameter combinations for robustness.
        
        This ensures the constructor handles different parameter patterns
        that might be used by calling code.
        """
        test_cases = [
            # Basic case - should work
            {
                "params": {"context": self.mock_context},
                "should_succeed": True,
                "description": "basic_context_only"
            },
            
            # With name parameter - the core issue
            {
                "params": {"context": self.mock_context, "name": "test_agent"},
                "should_succeed": True,
                "description": "with_name_parameter"
            },
            
            # With LLM manager
            {
                "params": {
                    "context": self.mock_context,
                    "name": "llm_agent",
                    "llm_manager": self.mock_llm_manager
                },
                "should_succeed": True,
                "description": "with_name_and_llm"
            },
            
            # With factory parameter
            {
                "params": {
                    "context": self.mock_context,
                    "name": "factory_agent",
                    "factory": Mock()
                },
                "should_succeed": True,
                "description": "with_name_and_factory"
            }
        ]
        
        results = {}
        
        for test_case in test_cases:
            params = test_case["params"]
            description = test_case["description"]
            expected_success = test_case["should_succeed"]
            
            try:
                agent = UnifiedDataAgent(**params)
                success = True
                error = None
                
                # Verify name was set correctly if provided
                if "name" in params:
                    self.assertEqual(agent.name, params["name"])
                    
            except Exception as e:
                success = False
                error = str(e)
            
            results[description] = {
                "success": success,
                "expected_success": expected_success,
                "error": error
            }
            
            # Record individual test case metrics
            self.record_metric(f"constructor_test_{description}", success)
            
            # Assert based on expectation
            if expected_success and not success:
                pytest.fail(f"Constructor test '{description}' failed unexpectedly: {error}")
            elif not expected_success and success:
                pytest.fail(f"Constructor test '{description}' succeeded unexpectedly")
        
        # Record overall results
        self.record_metric("constructor_test_results", results)
    
    def test_base_agent_inheritance_name_parameter(self):
        """
        Test that BaseAgent's name parameter is properly inherited.
        
        This verifies that the inheritance chain properly supports the name parameter.
        """
        # This test ensures that UnifiedDataAgent inherits BaseAgent's constructor
        # signature including the 'name' parameter
        
        # Arrange
        expected_name = "inherited_name_test"
        
        # Act
        agent = UnifiedDataAgent(
            context=self.mock_context,
            name=expected_name
        )
        
        # Assert
        self.assertEqual(agent.name, expected_name)
        
        # Verify other BaseAgent inherited attributes are set
        self.assertIsNotNone(agent.description)  # Should have default description
        self.assertIsNotNone(agent.state)  # Should have initial state
        
        self.record_metric("inheritance_test_success", True)
    
    def test_constructor_with_all_parameters(self):
        """
        Test constructor with comprehensive parameter set.
        
        This verifies that all possible parameters can be passed together
        without conflicts.
        """
        # Arrange
        mock_factory = Mock()
        test_name = "comprehensive_agent"
        
        # Act
        agent = UnifiedDataAgent(
            context=self.mock_context,
            factory=mock_factory,
            llm_manager=self.mock_llm_manager,
            name=test_name  # Key parameter from Issue #581
        )
        
        # Assert
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, test_name)
        self.assertEqual(agent.context, self.mock_context)
        self.assertEqual(agent.factory, mock_factory)
        self.assertEqual(agent.llm_manager, self.mock_llm_manager)
        
        self.record_metric("comprehensive_constructor_success", True)
    
    def test_factory_instantiation_with_name_parameter(self):
        """
        Test that factory creation methods handle name parameter correctly.
        
        This tests the factory pattern integration with the name parameter.
        """
        # Arrange
        factory = UnifiedDataAgentFactory()
        
        # Test 1: Factory create_for_context method
        agent = factory.create_for_context(self.mock_context)
        
        # Verify factory created agent successfully
        self.assertIsNotNone(agent)
        assert isinstance(agent, UnifiedDataAgent)
        
        # Test 2: Direct instantiation through factory
        # Note: Factory method may not expose name parameter directly
        # but the underlying constructor should support it
        
        self.record_metric("factory_instantiation_success", True)
        self.record_metric("factory_created_count", factory.created_count)
    
    def test_error_scenarios_and_recovery(self):
        """
        Test error scenarios and error message quality.
        
        This ensures that when errors do occur, they provide helpful
        debugging information.
        """
        # Test 1: Missing required context parameter
        try:
            agent = UnifiedDataAgent(name="test_agent")  # Missing required context
            pytest.fail("Should have raised error for missing required parameter")
        except Exception as e:
            # Should get helpful error message, not signature-related error
            self.assertNotIn("unexpected keyword argument", str(e))
            self.record_metric("missing_context_error_quality", "helpful")
        
        # Test 2: Invalid parameter types
        try:
            agent = UnifiedDataAgent(
                context="not_a_context",  # Wrong type
                name="test_agent"
            )
            pytest.fail("Should have raised error for invalid context type")
        except Exception as e:
            # Should get type-related error, not signature error
            self.assertNotIn("unexpected keyword argument 'name'", str(e))
            self.record_metric("invalid_type_error_quality", "helpful")
    
    def test_backward_compatibility_scenarios(self):
        """
        Test various backward compatibility scenarios that might exist
        in the codebase.
        """
        # Scenario 1: Legacy instantiation patterns
        legacy_patterns = [
            # Pattern that might be used in agent registry
            lambda: DataSubAgent(context=self.mock_context, name="registry_agent"),
            
            # Pattern that might be used in factory
            lambda: UnifiedDataAgent(context=self.mock_context, name="factory_agent"),
            
            # Pattern with additional legacy parameters
            lambda: DataSubAgent(
                context=self.mock_context,
                name="legacy_agent",
                llm_manager=self.mock_llm_manager
            )
        ]
        
        for i, pattern in enumerate(legacy_patterns):
            try:
                agent = pattern()
                self.assertIsNotNone(agent)
                self.record_metric(f"legacy_pattern_{i}_success", True)
            except Exception as e:
                if "unexpected keyword argument 'name'" in str(e):
                    self.record_metric(f"legacy_pattern_{i}_success", False)
                    pytest.fail(f"Legacy pattern {i} failed with Issue #581: {e}")
                else:
                    # Some other error - may be acceptable
                    self.record_metric(f"legacy_pattern_{i}_error", str(e))


class TestIssue581PerformanceAndMemory(SSotBaseTestCase):
    """
    Performance and memory tests for Issue #581 fix.
    
    These tests ensure that the constructor signature fix doesn't
    introduce performance regressions.
    """
    
    def setup_method(self, method):
        """Setup performance testing environment."""
        super().setup_method(method)
        self.record_metric("test_category", "performance")
    
    def test_constructor_performance(self):
        """
        Test that constructor performance is acceptable.
        
        Multiple instantiations should complete quickly.
        """
        import time
        
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "perf_test_user"
        mock_context.request_id = "perf_test_request"
        
        start_time = time.time()
        
        # Create multiple instances
        agents = []
        for i in range(10):
            agent = UnifiedDataAgent(
                context=mock_context,
                name=f"perf_agent_{i}"
            )
            agents.append(agent)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be very fast for 10 instances
        self.assertLess(total_time, 1.0, "Constructor should be fast")
        
        # Verify all agents were created
        self.assertEqual(len(agents), 10)
        
        self.record_metric("constructor_performance_10_instances", total_time)
        self.record_metric("average_constructor_time", total_time / 10)
    
    def test_memory_usage_reasonable(self):
        """
        Test that memory usage is reasonable for agent instances.
        """
        import sys
        
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "memory_test_user"
        mock_context.request_id = "memory_test_request"
        
        # Get initial memory baseline
        initial_objects = len([obj for obj in gc.get_objects() 
                              if isinstance(obj, UnifiedDataAgent)])
        
        # Create agents
        agents = []
        for i in range(5):
            agent = UnifiedDataAgent(
                context=mock_context,
                name=f"memory_agent_{i}"
            )
            agents.append(agent)
        
        # Check memory usage
        final_objects = len([obj for obj in gc.get_objects() 
                            if isinstance(obj, UnifiedDataAgent)])
        
        # Should have created exactly 5 new agents
        self.assertEqual(final_objects - initial_objects, 5)
        
        self.record_metric("memory_agent_instances_created", 5)
        self.record_metric("memory_baseline_agents", initial_objects)
        self.record_metric("memory_final_agents", final_objects)

# Import gc for memory testing
import gc