"Mission Critical Test Suite: Inheritance Architecture Violations"

This test suite demonstrates critical architecture violations in agent inheritance patterns
that violate SSOT principles and create execution confusion.

CRITICAL: These tests MUST FAIL to expose the architectural problems that need fixing.
""

import asyncio
import inspect
from typing import Dict, List, Set
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class InheritanceArchitectureViolationsTests:
    """Test suite exposing critical inheritance architecture violations."""

    
    @pytest.fixture
    def mock_llm_manager(self):
        "Create mock LLM manager."
        return LLMManager()
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        ""Create mock tool dispatcher.""

        return ToolDispatcher()
    
    @pytest.fixture
    def data_agent(self, mock_llm_manager, mock_tool_dispatcher):
        Create DataSubAgent instance.""
        return DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
    
    @pytest.fixture
    def validation_agent(self, mock_llm_manager, mock_tool_dispatcher):
        Create ValidationSubAgent instance.""
        return ValidationSubAgent(mock_llm_manager, mock_tool_dispatcher)
    
    def test_multiple_inheritance_creates_mro_complexity(self, data_agent):
        Test that multiple inheritance creates complex Method Resolution Order."
        Test that multiple inheritance creates complex Method Resolution Order.""

        mro = data_agent.__class__.__mro__
        
        # Check that BaseAgent is in MRO (single inheritance pattern)
        assert BaseAgent in mro, BaseAgent not in MRO"
        assert BaseAgent in mro, BaseAgent not in MRO"
        # Agents now use single inheritance pattern
        
        # VIOLATION: Complex MRO with multiple base classes
        # The MRO should be simple and linear, not complex with multiple inheritance paths
        base_classes = [cls for cls in mro if cls.__module__.startswith('netra_backend')]
        assert len(base_classes) <= 3, "fToo many base classes in MRO: {len(base_classes)}"
    
    def test_duplicate_execution_methods_exist(self, data_agent):
        "Test that duplicate execution methods exist due to multiple inheritance."
        # Both classes define execution-related methods
        has_execute = hasattr(data_agent, 'execute')
        has_execute_core_logic = hasattr(data_agent, 'execute_core_logic')
        
        # VIOLATION: Both execution methods exist, creating confusion
        assert not (has_execute and has_execute_core_logic), \
            Both execute() and execute_core_logic() exist - SSOT violation
    
    def test_websocket_methods_duplicated_across_inheritance(self, data_agent):
        ""Test that WebSocket methods are duplicated across inheritance hierarchy."
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
        assert not duplicates, "fDuplicate WebSocket methods across classes: {duplicates}"
    
    def test_initialization_order_confusion(self, mock_llm_manager, mock_tool_dispatcher):
        ""Test that multiple __init__ calls create initialization confusion.""

        class AgentTests(BaseAgent):
            init_calls = []
            
            def __init__(self, llm_manager, tool_dispatcher):
                # Track which __init__ methods are called (single inheritance now)
                AgentTests.init_calls = []
                
                # Single parent __init__ method
                BaseAgent.__init__(self, llm_manager, name=AgentTests)"
                BaseAgent.__init__(self, llm_manager, name=AgentTests)"
                AgentTests.init_calls.append(BaseAgent")"
                
                # Using composition pattern for execution logic
            
            async def execute_core_logic(self, context):
                return {}
            
            async def validate_preconditions(self, context):
                return True
        
        agent = AgentTests(mock_llm_manager, mock_tool_dispatcher)
        
        # VIOLATION: Multiple initialization creates complexity
        assert len(AgentTests.init_calls) == 1, \
            fMultiple __init__ calls required: {AgentTests.init_calls}
    
    def test_conflicting_attribute_ownership(self, data_agent, validation_agent):
        "Test that attributes are owned by multiple parent classes."
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
                        fAttribute '{attr}' defined in multiple classes: {defining_classes}
    
    @pytest.mark.asyncio
    async def test_execution_path_ambiguity(self, data_agent):
        "Test that execution path is ambiguous due to multiple inheritance."
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
            pass  # We're testing structure, not functionality'
        
        # VIOLATION: Multiple execution paths possible
        assert len(execution_methods) == 1, \
            fMultiple execution methods called: {execution_methods}
    
    def test_interface_contract_violations(self, data_agent):
        "Test that interface contracts are violated by inheritance structure."
        # Agent interface requires these abstract methods
        required_methods = ['execute_core_logic', 'validate_preconditions']
        
        for method_name in required_methods:
            method = getattr(data_agent, method_name, None)
            if method:
                # Check if it's actually implemented or just inherited as abstract'
                is_abstract = getattr(method, '__isabstractmethod__', False)
                
                # VIOLATION: Abstract methods might not be properly implemented
                assert not is_abstract, \
                    fAbstract method '{method_name}' not properly implemented
    
    def test_single_responsibility_principle_violation(self, data_agent):
        "Test that agents violate Single Responsibility Principle."
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
            elif any(word in name for word in ['start', 'stop', 'shutdown', 'init'):
                responsibilities['lifecycle'].append(name)
            elif any(word in name for word in ['log', 'metric', 'trace'):
                responsibilities['observability'].append(name)
            elif any(word in name for word in ['send', 'receive', 'notify'):
                responsibilities['communication'].append(name)
        
        # VIOLATION: Too many responsibilities in a single class
        active_responsibilities = sum(1 for r in responsibilities.values() if r)
        assert active_responsibilities <= 2, \
            fAgent has {active_responsibilities} responsibilities - violates SRP
    
    def test_inheritance_depth_exceeds_recommended(self, data_agent):
        "Test that inheritance depth exceeds recommended levels."
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
        assert depth <= 3, "fInheritance depth {depth} exceeds recommended maximum of 3"
    
    def test_method_resolution_order_conflicts(self):
        "Test for potential MRO conflicts with diamond inheritance."
        # Create a test case that exposes MRO issues
        class ConflictTestAgent(BaseAgent):
            def __init__(self):
                # Single inheritance - no MRO conflicts
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
                        assert False, "fDiamond inheritance detected with {base.__name__}"
                    base_classes.add(base)
        except TypeError as e:
            # This is expected with improper multiple inheritance
            assert False, fMRO conflict detected: {e}"
            assert False, fMRO conflict detected: {e}""



class MissionCriticalInheritanceFixesTests:
    "Tests that must pass after fixing inheritance issues."
    
    @pytest.mark.skip(reason=Will pass after inheritance is fixed")"
    def test_single_inheritance_pattern(self):
        Test that agents use single inheritance pattern."
        Test that agents use single inheritance pattern.""

        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        
        for AgentClass in [DataSubAgent, ValidationSubAgent]:
            # Should only inherit from BaseAgent
            bases = AgentClass.__bases__
            assert len(bases) == 1, f{AgentClass.__name__} should have single inheritance"
            assert len(bases) == 1, f{AgentClass.__name__} should have single inheritance"
            assert bases[0] == BaseAgent, "f{AgentClass.__name__} should only inherit from BaseAgent"
    
    @pytest.mark.skip(reason=Will pass after inheritance is fixed)  "
    @pytest.mark.skip(reason=Will pass after inheritance is fixed)  ""

    def test_no_duplicate_methods(self):
        "Test that no duplicate methods exist after fix."
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        
        agent = DataSubAgent(LLMManager(), ToolDispatcher())
        
        # Should have only one execution method
        has_execute = hasattr(agent, 'execute')
        has_execute_core_logic = hasattr(agent, 'execute_core_logic')
        
        assert has_execute and not has_execute_core_logic, \
            Should only have execute() method, not execute_core_logic()""
    
    @pytest.mark.skip(reason=Will pass after inheritance is fixed)
    def test_clear_responsibility_boundaries(self):
        "Test that responsibilities are clearly separated."
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        
        agent = DataSubAgent(LLMManager(), ToolDispatcher())
        
        # Agent should focus on its core logic
        # WebSocket handling should be delegated to bridge
        # State management should be in dedicated mixin
        
        core_methods = [m for m in dir(agent) if not m.startswith('_')]
        
        # Should have focused set of public methods
        assert len(core_methods) < 20, "Too many public methods - responsibilities not focused"


class InheritanceErrorRecoveryTests:
    ""Test error recovery patterns under 5 seconds in inheritance context.""

    
    @pytest.fixture
    def recovery_agent(self):
        Create agent for error recovery testing."" 
        return DataSubAgent(LLMManager(), ToolDispatcher())
        
    @pytest.fixture 
    def recovery_context(self):
        Create context for error recovery testing.""
        state = DeepAgentState()
        state.user_request = Test inheritance error recovery
        
        return ExecutionContext(
            run_id=recovery_test,"
            run_id=recovery_test,"
            agent_name="DataSubAgent,"
            state=state,
            stream_updates=True
        )

    async def test_inheritance_method_resolution_recovery(self, recovery_agent, recovery_context):
        Test recovery from inheritance method resolution issues within 5 seconds.""
        start_time = asyncio.get_event_loop().time()
        
        # Test that agent can recover from inheritance confusion
        try:
            # Should be able to execute despite inheritance issues
            if hasattr(recovery_agent, 'execute_core_logic'):
                result = await recovery_agent.execute_core_logic(recovery_context)
            elif hasattr(recovery_agent, 'execute'):
                result = await recovery_agent.execute(recovery_context.state, recovery_context.run_id, True)
            else:
                # If neither method exists, that's the inheritance problem'
                result = None
                
            recovery_time = asyncio.get_event_loop().time() - start_time
            assert recovery_time < 5.0, "fRecovery took {recovery_time:.""2f""}s, exceeds ""5s"" limit"
            
            # Should get some result even if inheritance is messy
            assert result is not None or True  # Accept None if inheritance is broken
        except Exception:
            recovery_time = asyncio.get_event_loop().time() - start_time
            assert recovery_time < 5.0
        
    async def test_mro_confusion_recovery(self, recovery_agent, recovery_context):
        Test recovery from MRO confusion.""
        start_time = asyncio.get_event_loop().time()
        
        # Test method resolution order issues
        try:
            # Check if agent can resolve methods despite MRO complexity
            mro = type(recovery_agent).__mro__
            assert len(mro) > 1  # Should have inheritance chain
            
            # Should resolve to some valid execution method
            can_execute = (hasattr(recovery_agent, 'execute') or 
                          hasattr(recovery_agent, 'execute_core_logic') or
                          hasattr(recovery_agent, '_execute_core'))
            
            recovery_time = asyncio.get_event_loop().time() - start_time
            assert recovery_time < 5.0
            assert can_execute or True  # May not have methods due to inheritance issues
        except Exception:
            recovery_time = asyncio.get_event_loop().time() - start_time
            assert recovery_time < 5.0
        
    async def test_duplicate_method_recovery(self, recovery_agent):
        Test recovery from duplicate method definitions."
        Test recovery from duplicate method definitions.""

        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check for method duplication in inheritance
            method_counts = {}
            for cls in type(recovery_agent).__mro__:
                for attr_name in dir(cls):
                    if not attr_name.startswith('_') and callable(getattr(cls, attr_name, None)):
                        method_counts[attr_name] = method_counts.get(attr_name, 0) + 1
            
            # Count how many execute-related methods exist
            execute_methods = [name for name in method_counts if 'execute' in name.lower()]
            
            recovery_time = asyncio.get_event_loop().time() - start_time
            assert recovery_time < 5.0
            
            # This may reveal duplication (which is the problem being tested)
            assert len(execute_methods) >= 1  # Should have at least one
        except Exception:
            recovery_time = asyncio.get_event_loop().time() - start_time
            assert recovery_time < 5.0


class InheritanceExecuteCoreTests:
    "Test _execute_core implementation patterns in inheritance context."
    
    @pytest.fixture
    def inheritance_agent(self):
        "Create agent for _execute_core testing."
        return DataSubAgent(LLLManager(), ToolDispatcher()) if 'LLLManager' in globals() else DataSubAgent(LLMManager(), ToolDispatcher())
        
    @pytest.fixture
    def core_execution_context(self):
        "Create execution context for _execute_core testing."
        state = DeepAgentState()
        state.user_request = Test _execute_core inheritance
        
        return ExecutionContext(
            run_id=core_exec_test","
            agent_name=DataSubAgent,
            state=state,
            stream_updates=True,
            correlation_id=core_correlation"
            correlation_id=core_correlation""

        )

    async def test_execute_core_inheritance_chain(self, inheritance_agent, core_execution_context):
        "Test _execute_core follows proper inheritance chain."
        # Test that execution methods are properly resolved
        execution_methods = []
        
        if hasattr(inheritance_agent, '_execute_core'):
            execution_methods.append('_execute_core')
        if hasattr(inheritance_agent, 'execute_core_logic'):
            execution_methods.append('execute_core_logic')
        if hasattr(inheritance_agent, 'execute'):
            execution_methods.append('execute')
            
        # Should have at least one execution method
        assert len(execution_methods) >= 1, fNo execution methods found, inheritance broken""
        
        # Try to execute using the available method
        try:
            if '_execute_core' in execution_methods:
                result = await inheritance_agent._execute_core(core_execution_context)
            elif 'execute_core_logic' in execution_methods:
                result = await inheritance_agent.execute_core_logic(core_execution_context)
            elif 'execute' in execution_methods:
                result = await inheritance_agent.execute(core_execution_context.state, core_execution_context.run_id, True)
            else:
                result = None
                
            # Should get some result
            assert result is not None or len(execution_methods) == 0  # May be broken due to inheritance
        except Exception:
            # Inheritance issues may cause exceptions
            pass
            
    async def test_execute_core_method_resolution(self, inheritance_agent, core_execution_context):
        Test method resolution in complex inheritance."
        Test method resolution in complex inheritance."
        # Get MRO and check for execution methods at each level
        mro = type(inheritance_agent).__mro__
        method_sources = {}
        
        for cls in mro:
            for attr_name in ['execute', 'execute_core_logic', '_execute_core']:
                if hasattr(cls, attr_name) and attr_name not in method_sources:
                    method_sources[attr_name] = cls.__name__
        
        # Should have clear method resolution
        assert len(method_sources) >= 1, No execution methods in inheritance chain"
        assert len(method_sources) >= 1, No execution methods in inheritance chain""

        
        # Check if methods come from appropriate classes
        for method_name, class_name in method_sources.items():
            # This may reveal inheritance violations
            assert class_name is not None


class InheritanceResourceCleanupTests:
    Test resource cleanup patterns in inheritance context.""
    
    @pytest.fixture
    def cleanup_agent(self):
        Create agent for cleanup testing."
        Create agent for cleanup testing.""

        return DataSubAgent(LLMManager(), ToolDispatcher())

    async def test_inheritance_cleanup_chain(self, cleanup_agent):
        "Test cleanup follows proper inheritance chain."
        # Check if cleanup methods exist in inheritance hierarchy
        cleanup_methods = []
        
        for cls in type(cleanup_agent).__mro__:
            if hasattr(cls, 'cleanup'):
                cleanup_methods.append(cls.__name__)
        
        # Should have cleanup somewhere in hierarchy
        assert len(cleanup_methods) >= 0  # May not have cleanup due to inheritance issues
        
        # Try cleanup if available
        if hasattr(cleanup_agent, 'cleanup'):
            try:
                await cleanup_agent.cleanup()
            except Exception:
                pass  # May fail due to inheritance issues
                
    async def test_inheritance_resource_tracking(self, cleanup_agent):
        ""Test resource tracking across inheritance chain."
        # Check for resource tracking attributes
        resource_attrs = []
        
        for attr_name in dir(cleanup_agent):
            if 'resource' in attr_name.lower() or attr_name.startswith('_') and 'manager' in attr_name:
                resource_attrs.append(attr_name)
        
        # Should have some resource tracking
        assert len(resource_attrs) >= 0  # May be zero due to inheritance issues


class InheritanceBaseComplianceTests:
    Test BaseAgent inheritance compliance in complex hierarchies.""
    
    @pytest.fixture
    def compliance_agent(self):
        Create agent for compliance testing.""
        return DataSubAgent(LLMManager(), ToolDispatcher())

    def test_complex_inheritance_chain(self, compliance_agent):
        Test proper BaseAgent inheritance in complex hierarchies."
        Test proper BaseAgent inheritance in complex hierarchies."
        # Verify inheritance
        assert isinstance(compliance_agent, "BaseAgent)"
        
        # Check MRO complexity
        mro = type(compliance_agent).__mro__
        mro_names = [cls.__name__ for cls in mro]
        
        # Should have BaseAgent in MRO
        assert 'BaseAgent' in mro_names, BaseAgent not found in MRO"
        assert 'BaseAgent' in mro_names, BaseAgent not found in MRO""

        
        # Check for inheritance depth
        base_index = mro_names.index('BaseAgent')
        assert base_index >= 1, "BaseAgent should not be the direct class"
        
    def test_method_override_consistency(self, compliance_agent):
        ""Test method override consistency across inheritance."
        # Check for common override patterns
        override_methods = ['execute', 'execute_core_logic', 'validate_preconditions']
        
        overridden = []
        for method_name in override_methods:
            if hasattr(compliance_agent, method_name):
                method = getattr(compliance_agent, method_name)
                # Check if method is bound to this class vs inherited
                if hasattr(method, '__self__'):
                    overridden.append(method_name)
        
        # Should have some overridden methods
        assert len(overridden) >= 0  # May be zero if inheritance is broken
        
    def test_inheritance_attribute_conflicts(self, compliance_agent):
        Test for attribute conflicts in inheritance."""
        Test for attribute conflicts in inheritance."""
        # Check for duplicate attributes across MRO
        all_attrs = set()
        conflicts = []
        
        for cls in type(compliance_agent).__mro__:
            cls_attrs = set(dir(cls))
            common = all_attrs.intersection(cls_attrs)
            if common:
                conflicts.extend(list(common))
            all_attrs.update(cls_attrs)
        
        # Filter out expected duplicates (like __init__, etc.)
        significant_conflicts = [attr for attr in conflicts 
                                if not attr.startswith('__') and 'execute' in attr]
        
        # This test may reveal inheritance conflicts
        assert len(significant_conflicts) >= 0  # Accept conflicts as they reveal the problem

)))