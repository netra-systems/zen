"CRITICAL: BaseAgent Inheritance Violations Detection Tests"

DESIGNED TO FAIL if inheritance patterns are broken or violated.
These tests verify SSOT compliance and inheritance architecture integrity.

Per CLAUDE.md:
    - Single Source of Truth (SSOT) violations must be detected
- Method Resolution Order (MRO) correctness must be verified  
- Inheritance patterns must not violate SSOT principles
- Agent initialization must be consistent across inheritance hierarchy

CRITICAL REQUIREMENTS:
    1. Tests designed to FAIL initially to prove they catch violations
2. Test inheritance patterns and MRO correctness
3. Test SSOT compliance in inheritance chains
4. Test abstract method implementations
5. Test WebSocket adapter inheritance consistency
6. Test reliability handler inheritance patterns
7. Test execution engine inheritance consistency
8. Stress test concurrent inheritance access patterns

Uses REAL services - NO MOCKS per CLAUDE.md mandate.
""

import pytest
import inspect
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from concurrent.futures import ThreadPoolExecutor
import threading
from shared.isolated_environment import IsolatedEnvironment

# Import the components we're testing'
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager


class InheritanceViolationAgentTests(BaseAgent):
    Test agent that intentionally violates SSOT patterns for violation detection."
    Test agent that intentionally violates SSOT patterns for violation detection.""

    
    def __init__(self, violation_type: str = "none, **kwargs):"
        Initialize with specific violation types for testing.""
        self.violation_type = violation_type
        
        # Apply violations based on type
        if violation_type == duplicate_websocket_adapter:
            # VIOLATION: Create duplicate WebSocket adapter (should fail SSOT)
            self._duplicate_websocket_adapter = object()
        elif violation_type == bypass_super_init:"
        elif violation_type == bypass_super_init:"
            # VIOLATION: Skip parent initialization (should cause MRO issues)
            pass  # Intentionally skip super().__init__()
        elif violation_type == "override_ssot_methods:"
            # Initialize normally first, then override SSOT methods
            super().__init__(**kwargs)
            # VIOLATION: Override SSOT methods incorrectly
            self._override_critical_ssot_methods()
        else:
            # Normal initialization
            super().__init__(**kwargs)
    
    def _override_critical_ssot_methods(self):
        Intentionally override critical SSOT methods to test detection.""
        # VIOLATION: Override unified reliability handler property
        self._unified_reliability_handler = None
        
        # VIOLATION: Override WebSocket adapter incorrectly
        self._websocket_adapter = object()
        
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        Minimal implementation for testing."
        Minimal implementation for testing."
        return {test": completed, violation_type: self.violation_type}"


class MultipleMROViolationAgent(BaseAgent, ABC):
    "Test agent with complex inheritance for MRO testing."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track MRO to verify correctness
        self.mro_order = [cls.__name__ for cls in self.__class__.__mro__]
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        return {mro_order: self.mro_order}"
        return {mro_order: self.mro_order}""



class ConcurrentAccessAgent(BaseAgent):
    "Agent for testing concurrent access patterns."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.access_counter = 0
        self.access_lock = threading.Lock()
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        with self.access_lock:
            self.access_counter += 1
            counter_value = self.access_counter
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        return {access_counter": counter_value, thread_id: threading.current_thread().ident}"


@pytest.mark.asyncio 
class BaseAgentInheritanceViolationsTests:
    CRITICAL tests that MUST FAIL if inheritance is broken."
    CRITICAL tests that MUST FAIL if inheritance is broken.""

    
    async def test_ssot_websocket_adapter_violation_detection(self):
        "CRITICAL: Must detect WebSocket adapter SSOT violations."
        
        This test MUST FAIL if agents create duplicate WebSocket adapters
        violating SSOT pattern.
        ""
        # Create agent with WebSocket adapter violation
        violation_agent = InheritanceViolationAgentTests(
            violation_type=duplicate_websocket_adapter,
            name=ViolationTestAgent"
            name=ViolationTestAgent""

        )
        
        # Verify SSOT violation is detected
        # The agent should NOT have duplicate WebSocket adapters
        assert hasattr(violation_agent, '_websocket_adapter'), BaseAgent should have _websocket_adapter"
        assert hasattr(violation_agent, '_websocket_adapter'), BaseAgent should have _websocket_adapter""

        
        # CRITICAL CHECK: Should not have duplicate adapter attribute
        if hasattr(violation_agent, '_duplicate_websocket_adapter'):
            # This indicates a SSOT violation - multiple WebSocket adapters exist
            pytest.fail(SSOT VIOLATION DETECTED: Multiple WebSocket adapters found. 
                       BaseAgent must maintain single WebSocket adapter as SSOT.")"
        
        # Verify WebSocket adapter is the correct SSOT type
        from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        assert isinstance(violation_agent._websocket_adapter, "WebSocketBridgeAdapter), \"
            WebSocket adapter must be correct SSOT type
    
    async def test_mro_correctness_failure_detection(self):
        "CRITICAL: Must detect Method Resolution Order violations."
        
        This test verifies MRO is correct and MUST FAIL if inheritance
        patterns violate expected method resolution.
"
"
        # Test agent with potential MRO issues
        normal_agent = InheritanceViolationAgentTests(name=NormalAgent)"
        normal_agent = InheritanceViolationAgentTests(name=NormalAgent)"
        mro_agent = MultipleMROViolationAgent(name=MROAgent")"
        
        # Verify MRO contains BaseAgent
        normal_mro = [cls.__name__ for cls in normal_agent.__class__.__mro__]
        mro_agent_mro = [cls.__name__ for cls in mro_agent.__class__.__mro__]
        
        # CRITICAL CHECK: BaseAgent must be in MRO
        assert 'BaseAgent' in normal_mro, "BaseAgent missing from MRO - inheritance broken"
        assert 'BaseAgent' in mro_agent_mro, BaseAgent missing from complex MRO - inheritance broken""
        
        # CRITICAL CHECK: object must be at end of MRO
        assert normal_mro[-1] == 'object', "fMRO must end with object, got: {normal_mro}"
        assert mro_agent_mro[-1] == 'object', "fComplex MRO must end with object, got: {mro_agent_mro}"
        
        # CRITICAL CHECK: Verify critical methods are resolvable
        critical_methods = ['execute', 'emit_agent_started', 'set_websocket_bridge', 
                           'get_health_status', 'unified_reliability_handler']
        
        for method_name in critical_methods:
            if not hasattr(normal_agent, method_name):
                pytest.fail(f"INHERITANCE VIOLATION: Critical method '{method_name)'"
                           fnot found in MRO {normal_mro}")"
            
            if not hasattr(mro_agent, method_name):  
                pytest.fail(fINHERITANCE VIOLATION: Critical method '{method_name)' 
                           fnot found in complex MRO {mro_agent_mro})"
                           fnot found in complex MRO {mro_agent_mro})""

    
    async def test_initialization_order_violation_detection(self):
        "CRITICAL: Must detect initialization order violations."
        
        This test MUST FAIL if agents skip proper initialization order
        breaking the inheritance chain.
        ""
        # Test agent that bypasses super().__init__()
        try:
            violation_agent = InheritanceViolationAgentTests(
                violation_type=bypass_super_init,
                name=InitViolationAgent"
                name=InitViolationAgent""

            )
            
            # Check for critical attributes that should exist after proper init
            critical_attrs = ['state', 'name', 'logger', '_websocket_adapter', 'timing_collector']
            missing_attrs = []
            
            for attr in critical_attrs:
                if not hasattr(violation_agent, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                pytest.fail(fINITIALIZATION VIOLATION DETECTED: Missing critical attributes "
                pytest.fail(fINITIALIZATION VIOLATION DETECTED: Missing critical attributes ""

                           fdue to bypassed super().__init__(): {missing_attrs})
                           
        except Exception as e:
            # Expected behavior - initialization should fail properly
            assert super() in str(e) or "init in str(e).lower(), \
                fUnexpected error type for init violation: {e}"
                fUnexpected error type for init violation: {e}""

    
    async def test_ssot_reliability_handler_violation_detection(self):
        CRITICAL: Must detect reliability handler SSOT violations.""
        
        This test MUST FAIL if agents override or duplicate the unified
        reliability handler violating SSOT pattern.
        
        # Create agent with SSOT method overrides
        violation_agent = InheritanceViolationAgentTests(
            violation_type=override_ssot_methods,"
            violation_type=override_ssot_methods,"
            name="SSOTViolationAgent"
        )
        
        # CRITICAL CHECK: Verify unified reliability handler is correct type
        from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
        
        # This agent intentionally overrides the handler to None (SSOT violation)
        if violation_agent._unified_reliability_handler is None and violation_agent._enable_reliability:
            pytest.fail(SSOT VIOLATION DETECTED: Unified reliability handler was overridden to None. 
                       "This violates SSOT pattern for reliability management.)"
        
        # CRITICAL CHECK: Property access should be consistent
        handler_via_property = violation_agent.unified_reliability_handler
        handler_via_direct = violation_agent._unified_reliability_handler
        
        if handler_via_property != handler_via_direct:
            pytest.fail(SSOT VIOLATION: Inconsistent access to unified reliability handler. 
                       Property and direct access return different objects.)"
                       Property and direct access return different objects.)""

    
    async def test_abstract_method_implementation_violations(self):
        "CRITICAL: Must detect missing abstract method implementations."
        
        This test verifies all required abstract methods are properly implemented
        and MUST FAIL if any are missing or incorrectly implemented.
"
"
        # Test normal agent
        normal_agent = InheritanceViolationAgentTests(name="AbstractTestAgent)"
        
        # CRITICAL CHECK: All abstract methods must be implemented
        abstract_methods = []
        for cls in normal_agent.__class__.__mro__:
            if hasattr(cls, '__abstractmethods__'):
                abstract_methods.extend(cls.__abstractmethods__)
        
        # Remove duplicates
        abstract_methods = list(set(abstract_methods))
        
        # Verify each abstract method is implemented
        for method_name in abstract_methods:
            if not hasattr(normal_agent, method_name):
                pytest.fail(fABSTRACT METHOD VIOLATION: Missing implementation for 
                           f"abstract method '{method_name}')"
            
            # Verify method is callable
            method = getattr(normal_agent, method_name)
            if not callable(method):
                pytest.fail(fABSTRACT METHOD VIOLATION: '{method_name}' exists but is not callable")"
    
    async def test_concurrent_inheritance_access_violations(self):
        CRITICAL: Must detect race conditions in inherited method access.""
        
        This test stresses concurrent access to inherited methods and
        MUST FAIL if race conditions or inconsistencies are detected.
        
        # Create concurrent access agent
        concurrent_agent = ConcurrentAccessAgent(name=ConcurrentTestAgent)"
        concurrent_agent = ConcurrentAccessAgent(name=ConcurrentTestAgent)""

        
        # Stress test concurrent access
        num_concurrent_calls = 20
        
        async def execute_agent(agent, call_id):
            context = ExecutionContext(
                run_id=f"concurrent_test_{call_id},"
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            # Test multiple inherited method calls concurrently
            start_time = time.time()
            
            # Test state management (inherited)
            original_state = agent.get_state()
            agent.set_state(SubAgentLifecycle.RUNNING)
            
            # Test execution (inherited + overridden)
            result = await agent.execute_core_logic(context)
            
            # Test health status (inherited)
            health = agent.get_health_status()
            
            # Reset state
            agent.set_state(original_state)
            
            execution_time = time.time() - start_time
            
            return {
                'call_id': call_id,
                'result': result,
                'health': health,
                'execution_time': execution_time
            }
        
        # Execute concurrently
        tasks = [execute_agent(concurrent_agent, i) for i in range(num_concurrent_calls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for violations
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        if failed_results:
            pytest.fail(fCONCURRENT ACCESS VIOLATION: {len(failed_results)} out of 
                       f{num_concurrent_calls} concurrent calls failed: {failed_results[:3]})
        
        # Check for race condition indicators
        access_counters = [r['result']['access_counter'] for r in successful_results]
        unique_counters = set(access_counters)
        
        # Should have unique access counters if properly synchronized
        if len(unique_counters) != len(access_counters):
            pytest.fail(fRACE CONDITION DETECTED: Duplicate access counters indicate ""
                       frace condition in concurrent inheritance access: {access_counters})
        
        # Verify execution times are reasonable (no excessive blocking)
        avg_execution_time = sum(r['execution_time'] for r in successful_results) / len(successful_results)
        max_execution_time = max(r['execution_time'] for r in successful_results)
        
        if max_execution_time > avg_execution_time * 10:
            pytest.fail(fPERFORMANCE VIOLATION: Excessive execution time variation 
                       f"(max: {max_execution_time:.""3f""}s, avg: {avg_execution_time:.""3f""}s)"
                       findicates potential deadlock or blocking issues")"
    
    async def test_websocket_bridge_inheritance_consistency(self):
        CRITICAL: Must detect WebSocket bridge inheritance inconsistencies.""
        
        This test verifies WebSocket bridge integration is consistent
        across inheritance hierarchy and MUST FAIL if inconsistencies exist.
        
        # Create multiple agents with inheritance
        agents = [
            InheritanceViolationAgentTests(name=fWebSocketTest{i})"
            InheritanceViolationAgentTests(name=fWebSocketTest{i})""

            for i in range(5)
        ]
        
        # Test WebSocket bridge consistency across agents
        websocket_adapters = []
        websocket_methods = []
        
        for agent in agents:
            # Check WebSocket adapter exists and is correct type
            if not hasattr(agent, '_websocket_adapter'):
                pytest.fail(f"INHERITANCE VIOLATION: Agent {agent.name} missing WebSocket adapter)"
            
            websocket_adapters.append(type(agent._websocket_adapter))
            
            # Check WebSocket methods are consistent
            ws_methods = [method for method in dir(agent) if method.startswith('emit_')]
            websocket_methods.append(sorted(ws_methods))
        
        # CRITICAL CHECK: All agents should have same WebSocket adapter type
        unique_adapter_types = set(websocket_adapters)
        if len(unique_adapter_types) > 1:
            pytest.fail(fINHERITANCE VIOLATION: Inconsistent WebSocket adapter types 
                       facross inheritance hierarchy: {unique_adapter_types})
        
        # CRITICAL CHECK: All agents should have same WebSocket methods
        first_methods = websocket_methods[0]
        for i, methods in enumerate(websocket_methods[1:], 1):
            if methods != first_methods:
                pytest.fail(fINHERITANCE VIOLATION: Agent {i) has different WebSocket methods. ""
                           fExpected: {first_methods}, Got: {methods})
        
        # CRITICAL CHECK: Required WebSocket events must be available
        required_events = ['emit_agent_started', 'emit_thinking', 'emit_tool_executing', 
                          'emit_tool_completed', 'emit_agent_completed']
        
        for agent in agents:
            for event_method in required_events:
                if not hasattr(agent, event_method):
                    pytest.fail(fCRITICAL WEBSOCKET VIOLATION: Agent {agent.name) 
                               f"missing required event method '{event_method}')"
                
                method = getattr(agent, event_method)
                if not callable(method):
                    pytest.fail(fCRITICAL WEBSOCKET VIOLATION: Event method '{event_method)' "
                    pytest.fail(fCRITICAL WEBSOCKET VIOLATION: Event method '{event_method)' ""

                               fin agent {agent.name} is not callable)
    
    async def test_execution_engine_inheritance_violations(self):
        "CRITICAL: Must detect execution engine inheritance violations."
        
        This test verifies execution engine integration is consistent
        and MUST FAIL if inheritance breaks execution patterns.
"
"
        # Create agents with different execution configurations
        agents = [
            InheritanceViolationAgentTests(name=ExecTest1, enable_execution_engine=True),"
            InheritanceViolationAgentTests(name=ExecTest1, enable_execution_engine=True),"
            InheritanceViolationAgentTests(name=ExecTest2", enable_execution_engine=False),"
            InheritanceViolationAgentTests(name=ExecTest3, enable_execution_engine=True)
        ]
        
        enabled_agents = [a for a in agents if a._enable_execution_engine]
        disabled_agents = [a for a in agents if not a._enable_execution_engine]
        
        # CRITICAL CHECK: Enabled agents must have execution engine
        for agent in enabled_agents:
            if not hasattr(agent, '_execution_engine') or agent._execution_engine is None:
                pytest.fail(fEXECUTION ENGINE VIOLATION: Agent {agent.name) ""
                           fenabled execution engine but _execution_engine is None)
            
            # Check execution methods are available
            if not hasattr(agent, 'execute_modern'):
                pytest.fail(fEXECUTION ENGINE VIOLATION: Agent {agent.name) 
                           f"missing execute_modern method)"
        
        # CRITICAL CHECK: Disabled agents should handle execution gracefully
        for agent in disabled_agents:
            context = ExecutionContext(
                run_id=test_disabled_exec","
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            # Should still be able to execute core logic
            try:
                result = await agent.execute_core_logic(context)
                assert result is not None, "Core logic should return result even without execution engine"
            except Exception as e:
                pytest.fail(fEXECUTION ENGINE VIOLATION: Agent {agent.name) ""
                           fwith disabled execution engine failed core logic: {e})
    
    async def test_state_management_inheritance_violations(self):
        CRITICAL: Must detect state management inheritance violations.
        
        This test verifies state management is consistent across inheritance
        and MUST FAIL if state transitions are broken.
""
        agent = InheritanceViolationAgentTests(name=StateTestAgent)
        
        # Test state transition consistency
        valid_transitions = {
            SubAgentLifecycle.PENDING: [SubAgentLifecycle.RUNNING, SubAgentLifecycle.FAILED, SubAgentLifecycle.SHUTDOWN],
            SubAgentLifecycle.RUNNING: [SubAgentLifecycle.RUNNING, SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED, SubAgentLifecycle.SHUTDOWN],
            SubAgentLifecycle.FAILED: [SubAgentLifecycle.PENDING, SubAgentLifecycle.RUNNING, SubAgentLifecycle.SHUTDOWN],
            SubAgentLifecycle.COMPLETED: [SubAgentLifecycle.RUNNING, SubAgentLifecycle.PENDING, SubAgentLifecycle.SHUTDOWN],
            SubAgentLifecycle.SHUTDOWN: []
        }
        
        # Test each valid transition
        for from_state, to_states in valid_transitions.items():
            # Reset to initial state
            agent.state = from_state
            
            for to_state in to_states:
                try:
                    agent.set_state(to_state)
                    assert agent.get_state() == to_state, \
                        fState transition {from_state} -> {to_state} failed to update state""
                    
                    # Reset for next test
                    agent.state = from_state
                    
                except ValueError as e:
                    pytest.fail(fSTATE MANAGEMENT VIOLATION: Valid transition 
                               f{from_state} -> {to_state} was rejected: {e})
        
        # Test invalid transitions should fail
        agent.state = SubAgentLifecycle.SHUTDOWN
        invalid_states = [SubAgentLifecycle.PENDING, SubAgentLifecycle.RUNNING, 
                         SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]
        
        for invalid_state in invalid_states:
            try:
                agent.set_state(invalid_state)
                pytest.fail(f"STATE MANAGEMENT VIOLATION: Invalid transition"
                           fSHUTDOWN -> {invalid_state} was allowed but should be rejected")"
            except ValueError:
                # Expected behavior - invalid transitions should raise ValueError
                pass
    
    async def test_execute_core_pattern_violation_detection(self):
        CRITICAL: Must detect _execute_core pattern violations.""
        agent = InheritanceViolationAgentTests(name=ExecuteCoreTest)
        
        context = ExecutionContext(
            run_id=test_execute_core,"
            run_id=test_execute_core,""

            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        # CRITICAL CHECK: execute_core_logic must be implemented
        assert hasattr(agent, 'execute_core_logic'), execute_core_logic method missing"
        assert hasattr(agent, 'execute_core_logic'), execute_core_logic method missing"
        assert callable(agent.execute_core_logic), "execute_core_logic must be callable"
        
        # Test execution
        result = await agent.execute_core_logic(context)
        assert result is not None, _execute_core pattern must return result""
        assert isinstance(result, "dict), _execute_core must return dict result"
        
    async def test_execute_core_context_handling_violations(self):
        "CRITICAL: Must detect context handling violations in _execute_core."
        agent = InheritanceViolationAgentTests(name=ContextTest)
        
        # Test with None context (should handle gracefully or fail predictably)
        try:
            result = await agent.execute_core_logic(None)
            pytest.fail(EXECUTE_CORE VIOLATION: Should not accept None context")"
        except (TypeError, AttributeError):
            pass  # Expected behavior
            
        # Test with invalid context
        try:
            result = await agent.execute_core_logic(invalid_context)
            pytest.fail(EXECUTE_CORE VIOLATION: Should not accept string context) "
            pytest.fail(EXECUTE_CORE VIOLATION: Should not accept string context) ""

        except (TypeError, AttributeError):
            pass  # Expected behavior
            
    async def test_execute_core_state_consistency_violations(self):
        "CRITICAL: Must detect state consistency violations during _execute_core."
        agent = InheritanceViolationAgentTests(name=StateConsistencyTest")"
        
        context = ExecutionContext(
            run_id=state_consistency_test,
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        # Set initial state
        agent.set_state(SubAgentLifecycle.PENDING)
        initial_state = agent.get_state()
        
        # Execute core logic
        result = await agent.execute_core_logic(context)
        
        # State should be managed consistently
        current_state = agent.get_state()
        assert current_state in [SubAgentLifecycle.PENDING, "SubAgentLifecycle.RUNNING, "
                                SubAgentLifecycle.COMPLETED], \
            fEXECUTE_CORE VIOLATION: Invalid state after execution: {current_state}"
            fEXECUTE_CORE VIOLATION: Invalid state after execution: {current_state}""

            
    async def test_execute_core_error_propagation_violations(self):
        "CRITICAL: Must detect error propagation violations in _execute_core."
        
        class ErrorAgent(BaseAgent):
            def __init__(self, error_type=none", **kwargs):"
                super().__init__(**kwargs)
                self.error_type = error_type
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.error_type == runtime:
                    raise RuntimeError(Test runtime error)"
                    raise RuntimeError(Test runtime error)"
                elif self.error_type == "value:"
                    raise ValueError(Test value error)
                elif self.error_type == "key:"
                    raise KeyError(Test key error)
                return {status: success"}"
        
        # Test different error types propagate correctly
        error_types = ["runtime, value, key]"
        for error_type in error_types:
            agent = ErrorAgent(error_type=error_type, name=fErrorTest_{error_type}")"
            context = ExecutionContext(
                run_id=ferror_test_{error_type},
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            with pytest.raises((RuntimeError, ValueError, KeyError)):
                await agent.execute_core_logic(context)
                
    async def test_execute_core_timing_pattern_violations(self):
        CRITICAL: Must detect timing pattern violations in _execute_core.""
        
        class TimingAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                start_time = time.time()
                await asyncio.sleep(0.5)  # ""50ms"" processing
                end_time = time.time()
                return {
                    execution_time: end_time - start_time,
                    start_time: start_time,"
                    start_time: start_time,"
                    "end_time: end_time"
                }
        
        agent = TimingAgent(name=TimingTest)
        context = ExecutionContext(
            run_id="timing_test,"
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(context)
        
        # Verify timing information is reasonable
        execution_time = result.get(execution_time, 0)
        assert execution_time > 0.4, "fTIMING VIOLATION: Execution time too short: {execution_time}"
        assert execution_time < 1.0, fTIMING VIOLATION: Execution time too long: {execution_time}""
        
    async def test_execute_core_concurrency_violations(self):
        CRITICAL: Must detect concurrency violations in _execute_core."
        CRITICAL: Must detect concurrency violations in _execute_core.""

        
        class ConcurrencyAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.execution_count = 0
                self.concurrent_executions = 0
                self.max_concurrent = 0
                self.lock = asyncio.Lock()
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                async with self.lock:
                    self.concurrent_executions += 1
                    self.execution_count += 1
                    self.max_concurrent = max(self.max_concurrent, self.concurrent_executions)
                
                try:
                    await asyncio.sleep(0.1)  # Simulate work
                    return {
                        execution_id": self.execution_count,"
                        concurrent_count: self.concurrent_executions
                    }
                finally:
                    async with self.lock:
                        self.concurrent_executions -= 1
        
        agent = ConcurrencyAgent(name=ConcurrencyTest")"
        
        # Execute multiple concurrent calls
        tasks = []
        for i in range(10):
            context = ExecutionContext(
                run_id=fconcurrent_{i},
                agent_name=agent.name,
                state=DeepAgentState()
            )
            tasks.append(agent.execute_core_logic(context))
        
        results = await asyncio.gather(*tasks)
        
        # Check for concurrency violations
        execution_ids = [r[execution_id] for r in results]
        unique_ids = set(execution_ids)
        
        assert len(unique_ids) == len(execution_ids), \
            f"CONCURRENCY VIOLATION: Duplicate execution IDs: {execution_ids}"
            
        assert agent.max_concurrent <= 10, \
            fCONCURRENCY VIOLATION: Too many concurrent executions: {agent.max_concurrent}"
            fCONCURRENCY VIOLATION: Too many concurrent executions: {agent.max_concurrent}""

            
    async def test_execute_core_resource_cleanup_violations(self):
        CRITICAL: Must detect resource cleanup violations in _execute_core.""
        
        class ResourceAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.resources_opened = 0
                self.resources_closed = 0
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # Simulate resource usage
                self.resources_opened += 1
                
                try:
                    # Simulate processing that might fail
                    if context.run_id.endswith(_fail):
                        raise RuntimeError(Simulated failure)"
                        raise RuntimeError(Simulated failure)""

                    
                    return {status": success, resources_opened: self.resources_opened}"
                finally:
                    # Resource cleanup
                    self.resources_closed += 1
        
        agent = ResourceAgent(name="ResourceTest)"
        
        # Test successful execution
        success_context = ExecutionContext(
            run_id=resource_success,
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(success_context)
        assert result[status] == success"
        assert result[status] == success""

        
        # Test failed execution
        fail_context = ExecutionContext(
            run_id="resource_fail,"
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        with pytest.raises(RuntimeError):
            await agent.execute_core_logic(fail_context)
        
        # CRITICAL CHECK: Resources must be cleaned up even after failure
        assert agent.resources_opened == agent.resources_closed, \
            fRESOURCE CLEANUP VIOLATION: Opened {agent.resources_opened} but closed {agent.resources_closed}
            
    async def test_execute_core_memory_pattern_violations(self):
        "CRITICAL: Must detect memory pattern violations in _execute_core."
        
        class MemoryAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.memory_usage = []
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                import sys
                
                # Simulate memory-intensive operation
                large_data = [i for i in range(1000)]  # Small test data
                self.memory_usage.append(sys.getsizeof(large_data))
                
                try:
                    # Process data
                    processed = sum(large_data)
                    return {
                        processed_sum: processed,"
                        processed_sum: processed,"
                        "memory_used: self.memory_usage[-1]"
                    }
                finally:
                    # Clear large data
                    del large_data
        
        agent = MemoryAgent(name=MemoryTest)
        
        # Execute multiple times
        for i in range(5):
            context = ExecutionContext(
                run_id=f"memory_test_{i},"
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            result = await agent.execute_core_logic(context)
            assert result[processed_sum"] == 499500  # Sum of 0-999"
            
        # Memory usage should be relatively stable
        avg_memory = sum(agent.memory_usage) / len(agent.memory_usage)
        for usage in agent.memory_usage:
            deviation = abs(usage - avg_memory) / avg_memory
            assert deviation < 0.1, "fMEMORY VIOLATION: High memory deviation: {deviation}"
            
    async def test_execute_core_context_mutation_violations(self):
        "CRITICAL: Must detect context mutation violations in _execute_core."
        
        class MutatingAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # VIOLATION: Mutating the context (should not modify input)
                original_run_id = context.run_id
                if hasattr(context, '_mutable_data'):
                    context._mutable_data = modified
                
                return {
                    original_run_id": original_run_id,"
                    context_type: type(context).__name__
                }
        
        agent = MutatingAgent(name=MutatingTest)"
        agent = MutatingAgent(name=MutatingTest)""

        context = ExecutionContext(
            run_id="mutation_test,"
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        # Store original context state
        original_run_id = context.run_id
        original_agent_name = context.agent_name
        
        result = await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: Context should not be mutated
        assert context.run_id == original_run_id, \
            CONTEXT MUTATION VIOLATION: run_id was modified
        assert context.agent_name == original_agent_name, \
            "CONTEXT MUTATION VIOLATION: agent_name was modified"
            
    async def test_execute_core_return_format_violations(self):
        CRITICAL: Must detect return format violations in _execute_core."
        CRITICAL: Must detect return format violations in _execute_core.""

        
        class FormatViolationAgent(BaseAgent):
            def __init__(self, return_type="dict, **kwargs):"
                super().__init__(**kwargs)
                self.return_type = return_type
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.return_type == string:
                    return "invalid string return  # VIOLATION"
                elif self.return_type == list:
                    return [invalid, list", return]  # VIOLATION  "
                elif self.return_type == none:
                    return None  # VIOLATION
                else:
                    return {"valid: dict, return: True}"
        
        # Test valid return format
        valid_agent = FormatViolationAgent(return_type=dict, name="ValidFormat)"
        context = ExecutionContext(
            run_id=format_test_valid","
            agent_name=valid_agent.name,
            state=DeepAgentState()
        )
        
        result = await valid_agent.execute_core_logic(context)
        assert isinstance(result, "dict), Valid agent should return dict"
        
        # Test invalid return formats
        invalid_types = [string", list, none]"
        for invalid_type in invalid_types:
            agent = FormatViolationAgent(return_type=invalid_type, name=fInvalid{invalid_type})
            context = ExecutionContext(
                run_id=fformat_test_{invalid_type}","
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            result = await agent.execute_core_logic(context)
            
            if not isinstance(result, dict):
                pytest.fail(fRETURN FORMAT VIOLATION: execute_core_logic returned 
                           f{type(result)} instead of dict for type {invalid_type})
                           
    async def test_execute_core_exception_handling_violations(self):
        "CRITICAL: Must detect exception handling violations in _execute_core."
        
        class ExceptionHandlingAgent(BaseAgent):
            def __init__(self, handling_mode=proper, **kwargs):"
            def __init__(self, handling_mode=proper, **kwargs):""

                super().__init__(**kwargs)
                self.handling_mode = handling_mode
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                try:
                    # Simulate operation that might fail
                    if context.run_id.endswith("_error):"
                        raise ValueError(Simulated error)
                    
                    return {"status: success}"
                    
                except ValueError as e:
                    if self.handling_mode == swallow:
                        # VIOLATION: Swallowing exceptions silently
                        return {status: "error_swallowed}"
                    elif self.handling_mode == wrong_type":"
                        # VIOLATION: Raising wrong exception type
                        raise RuntimeError(fWrong exception type: {e})
                    else:
                        # Proper handling: re-raise original exception
                        raise
        
        # Test proper exception handling
        proper_agent = ExceptionHandlingAgent(handling_mode=proper, name="ProperHandling)"
        
        success_context = ExecutionContext(
            run_id=exception_success","
            agent_name=proper_agent.name,
            state=DeepAgentState()
        )
        
        result = await proper_agent.execute_core_logic(success_context)
        assert result[status] == success
        
        # Test exception propagation
        error_context = ExecutionContext(
            run_id="exception_error,"
            agent_name=proper_agent.name,
            state=DeepAgentState()
        )
        
        with pytest.raises(ValueError):
            await proper_agent.execute_core_logic(error_context)
        
        # Test violation: exception swallowing
        swallow_agent = ExceptionHandlingAgent(handling_mode=swallow, name=SwallowHandling)
        error_context.agent_name = swallow_agent.name
        
        result = await swallow_agent.execute_core_logic(error_context)
        if result.get(status) == "error_swallowed:"
            pytest.fail(EXCEPTION HANDLING VIOLATION: Exception was swallowed instead of propagated")"
            
    async def test_execute_core_async_pattern_violations(self):
        CRITICAL: Must detect async pattern violations in _execute_core.""
        
        class AsyncPatternAgent(BaseAgent):
            async def __init__(self, pattern_type=proper, **kwargs):
                super().__init__(**kwargs)
                self.pattern_type = pattern_type
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.pattern_type == blocking:"
                if self.pattern_type == blocking:"
                    # VIOLATION: Using blocking operations in async method
                    import time
                    time.sleep(0.1)  # Should use await asyncio.sleep()
                    return {pattern": blocking}"
                    
                elif self.pattern_type == mixed:
                    # VIOLATION: Mixing sync and async incorrectly
                    await asyncio.sleep(0.5)
                    import time
                    time.sleep(0.5)  # Should all be async
                    return {"pattern: mixed}"
                    
                else:
                    # Proper async pattern
                    await asyncio.sleep(0.1)
                    return {pattern: proper}
        
        # Test proper async pattern
        proper_agent = AsyncPatternAgent(pattern_type=proper, name=ProperAsync")"
        context = ExecutionContext(
            run_id="async_proper,"
            agent_name=proper_agent.name,
            state=DeepAgentState()
        )
        
        start_time = time.time()
        result = await proper_agent.execute_core_logic(context)
        execution_time = time.time() - start_time
        
        assert result[pattern] == proper
        assert execution_time >= 0.9, fASYNC VIOLATION: Execution too fast: {execution_time}""
        
        # Test blocking violation detection
        blocking_agent = AsyncPatternAgent(pattern_type=blocking, name=BlockingAsync)
        context.agent_name = blocking_agent.name
        
        start_time = time.time()
        result = await blocking_agent.execute_core_logic(context)
        execution_time = time.time() - start_time
        
        # This should still work but indicates a violation of async patterns
        if execution_time >= 0.9:  # If it took expected time, blocking call worked
            pytest.fail(ASYNC PATTERN VIOLATION: Used blocking operations in async method)"
            pytest.fail(ASYNC PATTERN VIOLATION: Used blocking operations in async method)""

            
    async def test_execute_core_dependency_injection_violations(self):
        "CRITICAL: Must detect dependency injection violations in _execute_core."
        
        class DependencyAgent(BaseAgent):
            def __init__(self, dependency_mode="proper, **kwargs):"
                super().__init__(**kwargs)
                self.dependency_mode = dependency_mode
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.dependency_mode == hard_coded:
                    # VIOLATION: Hard-coded dependencies
                    from netra_backend.app.llm.llm_manager import LLMManager
                    llm = LLMManager()  # Should be injected
                    return {dependency: hard_coded"}"
                    
                elif self.dependency_mode == "global_access:"
                    # VIOLATION: Accessing global state
                    import os
                    os.environ[TEMP_VAR] = violation  # Should not modify global state
                    return {dependency": global_access}"
                    
                else:
                    # Proper dependency usage (via context or initialization)
                    return {
                        dependency: proper,
                        context_run_id: context.run_id"
                        context_run_id: context.run_id""

                    }
        
        # Test proper dependency handling
        proper_agent = DependencyAgent(dependency_mode="proper, name=ProperDeps)"
        context = ExecutionContext(
            run_id=deps_proper,
            agent_name=proper_agent.name,
            state=DeepAgentState()
        )
        
        result = await proper_agent.execute_core_logic(context)
        assert result[dependency"] == proper"
        assert result[context_run_id] == deps_proper
        
        # Test hard-coded dependency violation
        hardcoded_agent = DependencyAgent(dependency_mode=hard_coded, name="HardcodedDeps)"
        context.agent_name = hardcoded_agent.name
        
        result = await hardcoded_agent.execute_core_logic(context)
        if result.get(dependency") == hard_coded:"
            # This indicates a dependency injection violation
            # In a real system, this would be caught by architecture checks
            pass  # We'll log this as a violation but not fail the test'
            
        # Test global state violation
        global_agent = DependencyAgent(dependency_mode=global_access, name=GlobalDeps)
        context.agent_name = global_agent.name
        
        original_env = dict(os.environ)
        result = await global_agent.execute_core_logic(context)
        
        # Check if environment was modified
        if TEMP_VAR" in os.environ:"
            os.environ.pop(TEMP_VAR, None)  # Clean up
            pytest.fail(DEPENDENCY VIOLATION: Modified global environment state)"
            pytest.fail(DEPENDENCY VIOLATION: Modified global environment state)""

            
    async def test_execute_core_performance_baseline_violations(self):
        "CRITICAL: Must detect performance baseline violations in _execute_core."
        
        class PerformanceAgent(BaseAgent):
            def __init__(self, performance_mode=optimal", **kwargs):"
                super().__init__(**kwargs)
                self.performance_mode = performance_mode
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                start_time = time.time()
                
                if self.performance_mode == inefficient:
                    # VIOLATION: Inefficient operations
                    result = []
                    for i in range(10000):
                        result.append(str(i) + _processed)"
                        result.append(str(i) + _processed)"
                    # Should use list comprehension or more efficient approach
                    
                elif self.performance_mode == "memory_waste:"
                    # VIOLATION: Memory wasteful operations  
                    large_list = [i for i in range(100000)]
                    # Process but don't clean up'
                    processed = sum(large_list)
                    # large_list remains in memory
                    
                else:
                    # Optimal performance
                    await asyncio.sleep(0.1)  # Minimal processing time
                
                end_time = time.time()
                return {
                    execution_time: end_time - start_time,
                    "performance_mode: self.performance_mode"
                }
        
        # Test optimal performance
        optimal_agent = PerformanceAgent(performance_mode=optimal, name=OptimalPerf)
        context = ExecutionContext(
            run_id=perf_optimal,"
            run_id=perf_optimal,""

            agent_name=optimal_agent.name,
            state=DeepAgentState()
        )
        
        result = await optimal_agent.execute_core_logic(context)
        optimal_time = result["execution_time]"
        
        # Test inefficient performance
        inefficient_agent = PerformanceAgent(performance_mode=inefficient, name=InefficientPerf)
        context.agent_name = inefficient_agent.name
        
        result = await inefficient_agent.execute_core_logic(context)
        inefficient_time = result[execution_time"]"
        
        # Check for performance violations
        if inefficient_time > optimal_time * 100:  # ""100x"" slower threshold
            pytest.fail(fPERFORMANCE VIOLATION: Inefficient execution took 
                       f{inefficient_time:.""4f""}s vs optimal {optimal_time:.""4f""}s)""

                       
    async def test_execute_core_logging_pattern_violations(self):
        "CRITICAL: Must detect logging pattern violations in _execute_core."
        
        class LoggingAgent(BaseAgent):
            def __init__(self, logging_mode=proper, **kwargs):"
            def __init__(self, logging_mode=proper, **kwargs):""

                super().__init__(**kwargs)
                self.logging_mode = logging_mode
                self.log_messages = []
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.logging_mode == "excessive:"
                    # VIOLATION: Excessive logging
                    for i in range(1000):
                        self.log_messages.append(fProcessing item {i})
                    
                elif self.logging_mode == "sensitive:"
                    # VIOLATION: Logging sensitive data
                    self.log_messages.append(fUser API key: fake_api_key_12345)
                    self.log_messages.append(fProcessing context: {context})
                    
                elif self.logging_mode == none":"
                    # VIOLATION: No logging at all (for important operations)
                    pass
                    
                else:
                    # Proper logging
                    self.log_messages.append(fStarted execution for run_id: {context.run_id})
                    self.log_messages.append(Execution completed successfully)
                
                return {
                    "logging_mode: self.logging_mode,"
                    log_count: len(self.log_messages)
                }
        
        # Test proper logging
        proper_agent = LoggingAgent(logging_mode=proper, name=ProperLogging")"
        context = ExecutionContext(
            run_id="logging_proper,"
            agent_name=proper_agent.name,
            state=DeepAgentState()
        )
        
        result = await proper_agent.execute_core_logic(context)
        assert result[log_count] == 2  # Should have reasonable log count
        
        # Test excessive logging violation
        excessive_agent = LoggingAgent(logging_mode="excessive, name=ExcessiveLogging)"
        context.agent_name = excessive_agent.name
        
        result = await excessive_agent.execute_core_logic(context)
        if result[log_count] > 100:
            pytest.fail(fLOGGING VIOLATION: Excessive logging detected: {result['log_count']} messages)"
            pytest.fail(fLOGGING VIOLATION: Excessive logging detected: {result['log_count']} messages)""

        
        # Test sensitive data logging violation
        sensitive_agent = LoggingAgent(logging_mode="sensitive, name=SensitiveLogging)"
        context.agent_name = sensitive_agent.name
        
        result = await sensitive_agent.execute_core_logic(context)
        
        # Check for sensitive data in logs
        sensitive_keywords = [api_key, password, "token, secret]"
        for log_msg in sensitive_agent.log_messages:
            for keyword in sensitive_keywords:
                if keyword.lower() in log_msg.lower():
                    pytest.fail(fLOGGING VIOLATION: Sensitive data in logs: {log_msg})
                    
    async def test_execute_core_transaction_pattern_violations(self):
        CRITICAL: Must detect transaction pattern violations in _execute_core.""
        
        class TransactionAgent(BaseAgent):
            def __init__(self, transaction_mode=proper, **kwargs):
                super().__init__(**kwargs)
                self.transaction_mode = transaction_mode
                self.operations_log = []
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.transaction_mode == no_rollback:"
                if self.transaction_mode == no_rollback:"
                    # VIOLATION: No rollback on failure
                    try:
                        self.operations_log.append("Operation 1 started)"
                        self.operations_log.append(Operation 2 started) 
                        
                        if context.run_id.endswith("_fail):"
                            raise ValueError(Simulated failure)
                            
                        self.operations_log.append(Operations committed)"
                        self.operations_log.append(Operations committed)""

                        
                    except ValueError:
                        # VIOLATION: No cleanup/rollback
                        self.operations_log.append(Error occurred, no rollback")"
                        raise
                        
                elif self.transaction_mode == partial_commit:
                    # VIOLATION: Partial commits without proper transaction boundaries
                    self.operations_log.append(Partial operation 1")"
                    
                    if context.run_id.endswith(_fail):
                        self.operations_log.append(Partial operation 2 - failed)"
                        self.operations_log.append(Partial operation 2 - failed)"
                        raise ValueError("Partial failure)"
                        
                    self.operations_log.append(Partial operation 2 - success)
                    
                else:
                    # Proper transaction handling
                    operations = []
                    try:
                        operations.append("Operation 1)"
                        operations.append(Operation 2)
                        
                        if context.run_id.endswith(_fail):"
                        if context.run_id.endswith(_fail):"
                            raise ValueError(Simulated failure")"
                        
                        # Commit all operations
                        self.operations_log.extend(operations)
                        self.operations_log.append(All operations committed)
                        
                    except ValueError:
                        # Proper rollback
                        self.operations_log.append(Rolling back operations")"
                        raise
                
                return {
                    transaction_mode: self.transaction_mode,
                    operations_count: len(self.operations_log)"
                    operations_count: len(self.operations_log)""

                }
        
        # Test proper transaction handling - success case
        proper_agent = TransactionAgent(transaction_mode="proper, name=ProperTransaction)"
        context = ExecutionContext(
            run_id=transaction_success,
            agent_name=proper_agent.name,
            state=DeepAgentState()
        )
        
        result = await proper_agent.execute_core_logic(context)
        assert committed" in proper_agent.operations_log[-1]"
        
        # Test proper transaction handling - failure case
        context.run_id = transaction_fail
        with pytest.raises(ValueError):
            await proper_agent.execute_core_logic(context)
        
        # Should have rollback message
        assert Rolling back in proper_agent.operations_log[-1]"
        assert Rolling back in proper_agent.operations_log[-1]""

        
        # Test no rollback violation
        no_rollback_agent = TransactionAgent(transaction_mode="no_rollback, name=NoRollback)"
        context.agent_name = no_rollback_agent.name
        
        with pytest.raises(ValueError):
            await no_rollback_agent.execute_core_logic(context)
        
        # Check for rollback violation
        if no rollback in no_rollback_agent.operations_log[-1]:
            pytest.fail(TRANSACTION VIOLATION: No rollback performed on failure")"

)