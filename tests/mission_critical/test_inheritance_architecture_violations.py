"""Mission Critical Test Suite: Inheritance Architecture Violations

This test suite demonstrates critical architecture violations in agent inheritance patterns
that violate SSOT principles and create execution confusion.

CRITICAL: These tests MUST FAIL to expose the architectural problems that need fixing.
"""

import asyncio
import inspect
from typing import Dict, List, Set
import pytest

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.interface import BaseExecutionInterface, ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestInheritanceArchitectureViolations:
    """Test suite exposing critical inheritance architecture violations."""
    
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
    
    def test_multiple_inheritance_creates_mro_complexity(self, data_agent):
        """Test that multiple inheritance creates complex Method Resolution Order."""
        mro = data_agent.__class__.__mro__
        
        # Check that both BaseSubAgent and BaseExecutionInterface are in MRO
        assert BaseSubAgent in mro, "BaseSubAgent not in MRO"
        assert BaseExecutionInterface in mro, "BaseExecutionInterface not in MRO"
        
        # VIOLATION: Complex MRO with multiple base classes
        # The MRO should be simple and linear, not complex with multiple inheritance paths
        base_classes = [cls for cls in mro if cls.__module__.startswith('netra_backend')]
        assert len(base_classes) <= 3, f"Too many base classes in MRO: {len(base_classes)}"
    
    def test_duplicate_execution_methods_exist(self, data_agent):
        """Test that duplicate execution methods exist due to multiple inheritance."""
        # Both classes define execution-related methods
        has_execute = hasattr(data_agent, 'execute')
        has_execute_core_logic = hasattr(data_agent, 'execute_core_logic')
        
        # VIOLATION: Both execution methods exist, creating confusion
        assert not (has_execute and has_execute_core_logic), \
            "Both execute() and execute_core_logic() exist - SSOT violation"
    
    def test_websocket_methods_duplicated_across_inheritance(self, data_agent):
        """Test that WebSocket methods are duplicated across inheritance hierarchy."""
        # Collect all WebSocket-related methods from the inheritance chain
        websocket_methods = set()
        for cls in data_agent.__class__.__mro__:
            if cls.__module__.startswith('netra_backend'):
                for name, method in inspect.getmembers(cls, inspect.ismethod):
                    if 'websocket' in name.lower() or 'emit_' in name:
                        websocket_methods.add((cls.__name__, name))
        
        # Check for duplicate method names across different classes
        method_names = {}
        for cls_name, method_name in websocket_methods:
            if method_name not in method_names:
                method_names[method_name] = []
            method_names[method_name].append(cls_name)
        
        # VIOLATION: Same methods defined in multiple classes
        duplicates = {name: classes for name, classes in method_names.items() if len(classes) > 1}
        assert not duplicates, f"Duplicate WebSocket methods across classes: {duplicates}"
    
    def test_initialization_order_confusion(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that multiple __init__ calls create initialization confusion."""
        class TestAgent(BaseSubAgent, BaseExecutionInterface):
            init_calls = []
            
            def __init__(self, llm_manager, tool_dispatcher):
                # Track which __init__ methods are called and in what order
                TestAgent.init_calls = []
                
                # Both parent __init__ methods must be called
                BaseSubAgent.__init__(self, llm_manager, name="TestAgent")
                TestAgent.init_calls.append("BaseSubAgent")
                
                BaseExecutionInterface.__init__(self, "TestAgent")
                TestAgent.init_calls.append("BaseExecutionInterface")
            
            async def execute_core_logic(self, context):
                return {}
            
            async def validate_preconditions(self, context):
                return True
        
        agent = TestAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # VIOLATION: Multiple initialization creates complexity
        assert len(TestAgent.init_calls) == 1, \
            f"Multiple __init__ calls required: {TestAgent.init_calls}"
    
    def test_conflicting_attribute_ownership(self, data_agent, validation_agent):
        """Test that attributes are owned by multiple parent classes."""
        # Check which class owns common attributes
        for agent in [data_agent, validation_agent]:
            # These attributes might be defined in multiple places
            attributes_to_check = ['websocket_manager', 'agent_name', 'logger']
            
            for attr in attributes_to_check:
                if hasattr(agent, attr):
                    # Find all classes in MRO that define this attribute
                    defining_classes = []
                    for cls in agent.__class__.__mro__:
                        if cls.__module__.startswith('netra_backend'):
                            if attr in cls.__dict__:
                                defining_classes.append(cls.__name__)
                    
                    # VIOLATION: Attribute defined in multiple classes
                    assert len(defining_classes) <= 1, \
                        f"Attribute '{attr}' defined in multiple classes: {defining_classes}"
    
    @pytest.mark.asyncio
    async def test_execution_path_ambiguity(self, data_agent):
        """Test that execution path is ambiguous due to multiple inheritance."""
        state = DeepAgentState()
        
        # Check which execution method is actually called
        execution_methods = []
        
        # Override methods to track execution
        original_execute = data_agent.execute
        original_execute_core = getattr(data_agent, 'execute_core_logic', None)
        
        async def tracked_execute(*args, **kwargs):
            execution_methods.append('execute')
            return await original_execute(*args, **kwargs)
        
        async def tracked_execute_core(*args, **kwargs):
            execution_methods.append('execute_core_logic')
            if original_execute_core:
                return await original_execute_core(*args, **kwargs)
            return {}
        
        data_agent.execute = tracked_execute
        if hasattr(data_agent, 'execute_core_logic'):
            data_agent.execute_core_logic = tracked_execute_core
        
        try:
            # Execute the agent
            await data_agent.execute(state)
        except Exception:
            pass  # We're testing structure, not functionality
        
        # VIOLATION: Multiple execution paths possible
        assert len(execution_methods) == 1, \
            f"Multiple execution methods called: {execution_methods}"
    
    def test_interface_contract_violations(self, data_agent):
        """Test that interface contracts are violated by inheritance structure."""
        # BaseExecutionInterface requires these abstract methods
        required_methods = ['execute_core_logic', 'validate_preconditions']
        
        for method_name in required_methods:
            method = getattr(data_agent, method_name, None)
            if method:
                # Check if it's actually implemented or just inherited as abstract
                is_abstract = getattr(method, '__isabstractmethod__', False)
                
                # VIOLATION: Abstract methods might not be properly implemented
                assert not is_abstract, \
                    f"Abstract method '{method_name}' not properly implemented"
    
    def test_single_responsibility_principle_violation(self, data_agent):
        """Test that agents violate Single Responsibility Principle."""
        # Count responsibilities by analyzing method purposes
        responsibilities = {
            'execution': [],
            'websocket': [],
            'state_management': [],
            'lifecycle': [],
            'observability': [],
            'communication': []
        }
        
        for name, method in inspect.getmembers(data_agent, inspect.ismethod):
            if name.startswith('_'):
                continue
                
            if 'execute' in name:
                responsibilities['execution'].append(name)
            elif 'websocket' in name.lower() or 'emit_' in name:
                responsibilities['websocket'].append(name)
            elif 'state' in name.lower():
                responsibilities['state_management'].append(name)
            elif any(word in name for word in ['start', 'stop', 'shutdown', 'init']):
                responsibilities['lifecycle'].append(name)
            elif any(word in name for word in ['log', 'metric', 'trace']):
                responsibilities['observability'].append(name)
            elif any(word in name for word in ['send', 'receive', 'notify']):
                responsibilities['communication'].append(name)
        
        # VIOLATION: Too many responsibilities in a single class
        active_responsibilities = sum(1 for r in responsibilities.values() if r)
        assert active_responsibilities <= 2, \
            f"Agent has {active_responsibilities} responsibilities - violates SRP"
    
    def test_inheritance_depth_exceeds_recommended(self, data_agent):
        """Test that inheritance depth exceeds recommended levels."""
        # Calculate inheritance depth
        depth = 0
        current_class = data_agent.__class__
        while current_class != object:
            depth += 1
            # Move up the inheritance chain
            if len(current_class.__bases__) > 0:
                current_class = current_class.__bases__[0]
            else:
                break
        
        # VIOLATION: Deep inheritance hierarchy
        assert depth <= 3, f"Inheritance depth {depth} exceeds recommended maximum of 3"
    
    def test_method_resolution_order_conflicts(self):
        """Test for potential MRO conflicts with diamond inheritance."""
        # Create a test case that exposes MRO issues
        class ConflictTestAgent(BaseSubAgent, BaseExecutionInterface):
            def __init__(self):
                # This might fail due to MRO conflicts
                super().__init__()
            
            async def execute_core_logic(self, context):
                return {}
            
            async def validate_preconditions(self, context):
                return True
        
        # VIOLATION: MRO conflicts possible
        try:
            agent = ConflictTestAgent()
            # If we get here, there might be silent MRO issues
            mro = ConflictTestAgent.__mro__
            
            # Check for diamond inheritance pattern
            base_classes = set()
            for cls in mro:
                for base in cls.__bases__:
                    if base in base_classes and base != object:
                        assert False, f"Diamond inheritance detected with {base.__name__}"
                    base_classes.add(base)
        except TypeError as e:
            # This is expected with improper multiple inheritance
            assert False, f"MRO conflict detected: {e}"


class TestMissionCriticalInheritanceFixes:
    """Tests that must pass after fixing inheritance issues."""
    
    @pytest.mark.skip(reason="Will pass after inheritance is fixed")
    def test_single_inheritance_pattern(self):
        """Test that agents use single inheritance pattern."""
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        
        for AgentClass in [DataSubAgent, ValidationSubAgent]:
            # Should only inherit from BaseSubAgent
            bases = AgentClass.__bases__
            assert len(bases) == 1, f"{AgentClass.__name__} should have single inheritance"
            assert bases[0] == BaseSubAgent, f"{AgentClass.__name__} should only inherit from BaseSubAgent"
    
    @pytest.mark.skip(reason="Will pass after inheritance is fixed")  
    def test_no_duplicate_methods(self):
        """Test that no duplicate methods exist after fix."""
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        
        agent = DataSubAgent(LLMManager(), ToolDispatcher())
        
        # Should have only one execution method
        has_execute = hasattr(agent, 'execute')
        has_execute_core_logic = hasattr(agent, 'execute_core_logic')
        
        assert has_execute and not has_execute_core_logic, \
            "Should only have execute() method, not execute_core_logic()"
    
    @pytest.mark.skip(reason="Will pass after inheritance is fixed")
    def test_clear_responsibility_boundaries(self):
        """Test that responsibilities are clearly separated."""
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        
        agent = DataSubAgent(LLMManager(), ToolDispatcher())
        
        # Agent should focus on its core logic
        # WebSocket handling should be delegated to bridge
        # State management should be in dedicated mixin
        
        core_methods = [m for m in dir(agent) if not m.startswith('_')]
        
        # Should have focused set of public methods
        assert len(core_methods) < 20, "Too many public methods - responsibilities not focused"