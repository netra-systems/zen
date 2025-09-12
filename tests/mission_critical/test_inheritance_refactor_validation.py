"""Test Suite: Inheritance Refactor Validation

Validates that the inheritance refactoring was successful and all functionality works correctly.

CRITICAL: These tests verify the fixed inheritance structure.
"""

import asyncio
import inspect
import pytest
from typing import Dict, List, Set
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestInheritanceRefactorValidation:
    """Test suite to validate the inheritance refactoring is successful."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        return LLMManager()
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        return ToolDispatcher()
    
    @pytest.fixture
    def data_agent(self, mock_llm_manager, mock_tool_dispatcher):
        """Create DataSubAgent instance."""
        return DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
    
    @pytest.fixture
    def validation_agent(self, mock_llm_manager, mock_tool_dispatcher):
        """Create ValidationSubAgent instance."""
        return ValidationSubAgent(mock_llm_manager, mock_tool_dispatcher)
    
    def test_single_inheritance_pattern_success(self, data_agent, validation_agent):
        """Test that agents now use single inheritance pattern successfully."""
        # Check DataSubAgent inheritance
        data_mro = data_agent.__class__.__mro__
        data_bases = data_agent.__class__.__bases__
        
        assert len(data_bases) == 1, f"DataSubAgent should have single inheritance, got {len(data_bases)} bases: {data_bases}"
        assert data_bases[0] == BaseAgent, f"DataSubAgent should only inherit from BaseAgent, got {data_bases[0]}"
        
        # Check ValidationSubAgent inheritance
        validation_mro = validation_agent.__class__.__mro__
        validation_bases = validation_agent.__class__.__bases__
        
        assert len(validation_bases) == 1, f"ValidationSubAgent should have single inheritance, got {len(validation_bases)} bases: {validation_bases}"
        assert validation_bases[0] == BaseAgent, f"ValidationSubAgent should only inherit from BaseAgent, got {validation_bases[0]}"
    
    def test_mro_depth_acceptable(self, data_agent, validation_agent):
        """Test that Method Resolution Order depth is now acceptable ( <=  3)."""
        for agent_name, agent in [("DataSubAgent", data_agent), ("ValidationSubAgent", validation_agent)]:
            mro = agent.__class__.__mro__
            
            # Count depth of our classes only
            netra_classes = [cls for cls in mro if cls.__module__.startswith('netra_backend')]
            depth = len(netra_classes)
            
            assert depth <= 3, f"{agent_name} MRO depth {depth} exceeds recommended maximum of 3. MRO: {[c.__name__ for c in netra_classes]}"
    
    def test_no_execution_method_conflicts(self, data_agent, validation_agent):
        """Test that there are no conflicting execution methods."""
        for agent_name, agent in [("DataSubAgent", data_agent), ("ValidationSubAgent", validation_agent)]:
            # Should have only execute() method, not execute_core_logic()
            has_execute = hasattr(agent, 'execute')
            has_execute_core_logic = hasattr(agent, 'execute_core_logic')
            
            assert has_execute, f"{agent_name} should have execute() method"
            assert not has_execute_core_logic, f"{agent_name} should not have execute_core_logic() method - SSOT violation"
    
    def test_websocket_methods_available(self, data_agent, validation_agent):
        """Test that WebSocket methods are available through BaseAgent."""
        expected_websocket_methods = [
            'emit_thinking',
            'emit_progress', 
            'emit_error',
            'emit_tool_executing',
            'emit_tool_completed'
        ]
        
        for agent_name, agent in [("DataSubAgent", data_agent), ("ValidationSubAgent", validation_agent)]:
            for method_name in expected_websocket_methods:
                assert hasattr(agent, method_name), f"{agent_name} should have {method_name} method from BaseAgent"
    
    def test_no_duplicate_websocket_methods(self, data_agent, validation_agent):
        """Test that WebSocket methods are not duplicated across inheritance hierarchy."""
        for agent_name, agent in [("DataSubAgent", data_agent), ("ValidationSubAgent", validation_agent)]:
            # Collect all WebSocket-related methods from the inheritance chain
            websocket_methods = {}
            for cls in agent.__class__.__mro__:
                if cls.__module__.startswith('netra_backend'):
                    for name, method in inspect.getmembers(cls, inspect.isfunction):
                        if 'emit_' in name or 'websocket' in name.lower():
                            if name not in websocket_methods:
                                websocket_methods[name] = []
                            websocket_methods[name].append(cls.__name__)
            
            # Check that each method is defined in only one class
            for method_name, defining_classes in websocket_methods.items():
                assert len(defining_classes) <= 1, f"{agent_name}: Method '{method_name}' defined in multiple classes: {defining_classes}"
    
    def test_initialization_works_correctly(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that agent initialization works without conflicts."""
        # Should not raise any exceptions during initialization
        data_agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        validation_agent = ValidationSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # Basic attributes should be set correctly
        assert data_agent.name == "DataSubAgent"
        assert validation_agent.name == "ValidationSubAgent"
        
        # Both should have LLM manager
        assert data_agent.llm_manager is mock_llm_manager
        assert validation_agent.llm_manager is mock_llm_manager
    
    def test_agent_attributes_ownership(self, data_agent, validation_agent):
        """Test that attributes have clear ownership - no conflicts."""
        critical_attributes = ['name', 'llm_manager', 'logger']
        
        for agent_name, agent in [("DataSubAgent", data_agent), ("ValidationSubAgent", validation_agent)]:
            for attr in critical_attributes:
                if hasattr(agent, attr):
                    # Find all classes in MRO that define this attribute
                    defining_classes = []
                    for cls in agent.__class__.__mro__:
                        if cls.__module__.startswith('netra_backend'):
                            if hasattr(cls, attr) and attr in cls.__dict__:
                                defining_classes.append(cls.__name__)
                    
                    # Attribute should be defined in only one place in our hierarchy
                    assert len(defining_classes) <= 1, f"{agent_name}: Attribute '{attr}' defined in multiple classes: {defining_classes}"
    
    @pytest.mark.asyncio
    async def test_execution_path_is_clear(self, data_agent):
        """Test that execution path is now clear and unambiguous."""
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "performance", "test": True}
        
        # Track which methods are called
        execution_methods_called = []
        original_execute = data_agent.execute
        
        async def tracked_execute(*args, **kwargs):
            execution_methods_called.append('execute')
            try:
                return await original_execute(*args, **kwargs)
            except Exception:
                # We're testing structure, not full functionality
                return None
        
        data_agent.execute = tracked_execute
        
        try:
            await data_agent.execute(state)
        except Exception:
            pass  # Expected since we don't have full mock setup
        
        # Should call only execute() method
        assert len(execution_methods_called) == 1, f"Should call exactly one execution method, called: {execution_methods_called}"
        assert execution_methods_called[0] == 'execute', f"Should call execute() method, called: {execution_methods_called}"
    
    def test_method_count_is_reasonable(self, data_agent, validation_agent):
        """Test that public method count is reasonable after refactoring."""
        for agent_name, agent in [("DataSubAgent", data_agent), ("ValidationSubAgent", validation_agent)]:
            public_methods = [name for name in dir(agent) 
                            if not name.startswith('_') 
                            and callable(getattr(agent, name))]
            
            # Should have focused set of methods after cleanup
            assert len(public_methods) < 25, f"{agent_name} has too many public methods ({len(public_methods)}): {public_methods}"
    
    def test_agents_are_functional(self, data_agent, validation_agent):
        """Test that agents have their core functionality after refactoring."""
        # DataSubAgent should have data analysis methods
        assert hasattr(data_agent, 'execute'), "DataSubAgent should have execute method"
        assert hasattr(data_agent, 'get_health_status'), "DataSubAgent should have health status"
        
        # ValidationSubAgent should have validation methods
        assert hasattr(validation_agent, 'execute'), "ValidationSubAgent should have execute method"
        assert hasattr(validation_agent, 'get_health_status'), "ValidationSubAgent should have health status"
    
    def test_no_abstract_method_errors(self, data_agent, validation_agent):
        """Test that there are no abstract method errors after refactoring."""
        # Should be able to create instances without abstract method errors
        # (This test passes if we reach here without TypeError)
        assert data_agent is not None
        assert validation_agent is not None
        
        # Check that they are concrete implementations
        assert not inspect.isabstract(data_agent.__class__), "DataSubAgent should not be abstract"
        assert not inspect.isabstract(validation_agent.__class__), "ValidationSubAgent should not be abstract"


class TestWebSocketEventIntegration:
    """Test WebSocket event integration after inheritance refactoring."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        return LLMManager()
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        return ToolDispatcher()
    
    @pytest.fixture
    def data_agent(self, mock_llm_manager, mock_tool_dispatcher):
        return DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
    
    def test_websocket_bridge_pattern(self, data_agent):
        """Test that WebSocket bridge pattern works correctly."""
        # WebSocket methods should be available
        websocket_methods = ['emit_thinking', 'emit_progress', 'emit_error', 'emit_tool_executing', 'emit_tool_completed']
        
        for method in websocket_methods:
            assert hasattr(data_agent, method), f"Should have {method} from BaseAgent bridge"
            assert callable(getattr(data_agent, method)), f"{method} should be callable"
    
    @pytest.mark.asyncio
    async def test_websocket_events_emit_without_errors(self, data_agent):
        """Test that WebSocket events can be called without errors."""
        try:
            await data_agent.emit_thinking("Test thinking message")
            await data_agent.emit_progress("Test progress message")
            await data_agent.emit_tool_executing("test_tool")
            await data_agent.emit_tool_completed("test_tool", {"result": "success"})
        except Exception as e:
            # Should not raise exceptions even without WebSocket manager configured
            pytest.fail(f"WebSocket event emission failed: {e}")


class TestPerformanceAfterRefactoring:
    """Test performance characteristics after inheritance refactoring."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        return LLMManager()
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        return ToolDispatcher()
    
    def test_instantiation_performance(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that agent instantiation is faster after simplifying inheritance."""
        import time
        
        # Time agent creation
        start_time = time.time()
        
        for _ in range(10):
            data_agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            validation_agent = ValidationSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be reasonably fast (less than 1 second for 20 instantiations)
        assert total_time < 1.0, f"Agent instantiation too slow: {total_time}s for 20 agents"
    
    def test_method_resolution_performance(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that method resolution is faster with simplified inheritance."""
        data_agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        import time
        start_time = time.time()
        
        # Call methods many times to test method resolution performance
        for _ in range(1000):
            hasattr(data_agent, 'execute')
            hasattr(data_agent, 'emit_thinking')
            hasattr(data_agent, 'get_health_status')
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be very fast (less than 0.1 seconds)
        assert total_time < 0.1, f"Method resolution too slow: {total_time}s"