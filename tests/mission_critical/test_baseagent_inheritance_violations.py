"""CRITICAL: BaseAgent Inheritance Violations Detection Tests

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
"""

import pytest
import inspect
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from concurrent.futures import ThreadPoolExecutor
import threading

# Import the components we're testing
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager


class TestInheritanceViolationAgent(BaseAgent):
    """Test agent that intentionally violates SSOT patterns for violation detection."""
    
    def __init__(self, violation_type: str = "none", **kwargs):
        """Initialize with specific violation types for testing."""
        self.violation_type = violation_type
        
        # Apply violations based on type
        if violation_type == "duplicate_websocket_adapter":
            # VIOLATION: Create duplicate WebSocket adapter (should fail SSOT)
            self._duplicate_websocket_adapter = object()
        elif violation_type == "bypass_super_init":
            # VIOLATION: Skip parent initialization (should cause MRO issues)
            pass  # Intentionally skip super().__init__()
        elif violation_type == "override_ssot_methods":
            # Initialize normally first, then override SSOT methods
            super().__init__(**kwargs)
            # VIOLATION: Override SSOT methods incorrectly
            self._override_critical_ssot_methods()
        else:
            # Normal initialization
            super().__init__(**kwargs)
    
    def _override_critical_ssot_methods(self):
        """Intentionally override critical SSOT methods to test detection."""
        # VIOLATION: Override unified reliability handler property
        self._unified_reliability_handler = None
        
        # VIOLATION: Override WebSocket adapter incorrectly
        self._websocket_adapter = object()
        
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Minimal implementation for testing."""
        return {"test": "completed", "violation_type": self.violation_type}


class MultipleMROViolationAgent(BaseAgent, ABC):
    """Test agent with complex inheritance for MRO testing."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track MRO to verify correctness
        self.mro_order = [cls.__name__ for cls in self.__class__.__mro__]
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        return {"mro_order": self.mro_order}


class ConcurrentAccessAgent(BaseAgent):
    """Agent for testing concurrent access patterns."""
    
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
        
        return {"access_counter": counter_value, "thread_id": threading.current_thread().ident}


@pytest.mark.asyncio 
class TestBaseAgentInheritanceViolations:
    """CRITICAL tests that MUST FAIL if inheritance is broken."""
    
    async def test_ssot_websocket_adapter_violation_detection(self):
        """CRITICAL: Must detect WebSocket adapter SSOT violations.
        
        This test MUST FAIL if agents create duplicate WebSocket adapters
        violating SSOT pattern.
        """
        # Create agent with WebSocket adapter violation
        violation_agent = TestInheritanceViolationAgent(
            violation_type="duplicate_websocket_adapter",
            name="ViolationTestAgent"
        )
        
        # Verify SSOT violation is detected
        # The agent should NOT have duplicate WebSocket adapters
        assert hasattr(violation_agent, '_websocket_adapter'), "BaseAgent should have _websocket_adapter"
        
        # CRITICAL CHECK: Should not have duplicate adapter attribute
        if hasattr(violation_agent, '_duplicate_websocket_adapter'):
            # This indicates a SSOT violation - multiple WebSocket adapters exist
            pytest.fail("SSOT VIOLATION DETECTED: Multiple WebSocket adapters found. "
                       "BaseAgent must maintain single WebSocket adapter as SSOT.")
        
        # Verify WebSocket adapter is the correct SSOT type
        from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        assert isinstance(violation_agent._websocket_adapter, WebSocketBridgeAdapter), \
            "WebSocket adapter must be correct SSOT type"
    
    async def test_mro_correctness_failure_detection(self):
        """CRITICAL: Must detect Method Resolution Order violations.
        
        This test verifies MRO is correct and MUST FAIL if inheritance
        patterns violate expected method resolution.
        """
        # Test agent with potential MRO issues
        normal_agent = TestInheritanceViolationAgent(name="NormalAgent")
        mro_agent = MultipleMROViolationAgent(name="MROAgent")
        
        # Verify MRO contains BaseAgent
        normal_mro = [cls.__name__ for cls in normal_agent.__class__.__mro__]
        mro_agent_mro = [cls.__name__ for cls in mro_agent.__class__.__mro__]
        
        # CRITICAL CHECK: BaseAgent must be in MRO
        assert 'BaseAgent' in normal_mro, "BaseAgent missing from MRO - inheritance broken"
        assert 'BaseAgent' in mro_agent_mro, "BaseAgent missing from complex MRO - inheritance broken"
        
        # CRITICAL CHECK: object must be at end of MRO
        assert normal_mro[-1] == 'object', f"MRO must end with object, got: {normal_mro}"
        assert mro_agent_mro[-1] == 'object', f"Complex MRO must end with object, got: {mro_agent_mro}"
        
        # CRITICAL CHECK: Verify critical methods are resolvable
        critical_methods = ['execute', 'emit_agent_started', 'set_websocket_bridge', 
                           'get_health_status', 'unified_reliability_handler']
        
        for method_name in critical_methods:
            if not hasattr(normal_agent, method_name):
                pytest.fail(f"INHERITANCE VIOLATION: Critical method '{method_name}' "
                           f"not found in MRO {normal_mro}")
            
            if not hasattr(mro_agent, method_name):  
                pytest.fail(f"INHERITANCE VIOLATION: Critical method '{method_name}' "
                           f"not found in complex MRO {mro_agent_mro}")
    
    async def test_initialization_order_violation_detection(self):
        """CRITICAL: Must detect initialization order violations.
        
        This test MUST FAIL if agents skip proper initialization order
        breaking the inheritance chain.
        """
        # Test agent that bypasses super().__init__()
        try:
            violation_agent = TestInheritanceViolationAgent(
                violation_type="bypass_super_init",
                name="InitViolationAgent"
            )
            
            # Check for critical attributes that should exist after proper init
            critical_attrs = ['state', 'name', 'logger', '_websocket_adapter', 'timing_collector']
            missing_attrs = []
            
            for attr in critical_attrs:
                if not hasattr(violation_agent, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                pytest.fail(f"INITIALIZATION VIOLATION DETECTED: Missing critical attributes "
                           f"due to bypassed super().__init__(): {missing_attrs}")
                           
        except Exception as e:
            # Expected behavior - initialization should fail properly
            assert "super()" in str(e) or "init" in str(e).lower(), \
                f"Unexpected error type for init violation: {e}"
    
    async def test_ssot_reliability_handler_violation_detection(self):
        """CRITICAL: Must detect reliability handler SSOT violations.
        
        This test MUST FAIL if agents override or duplicate the unified
        reliability handler violating SSOT pattern.
        """
        # Create agent with SSOT method overrides
        violation_agent = TestInheritanceViolationAgent(
            violation_type="override_ssot_methods",
            name="SSOTViolationAgent"
        )
        
        # CRITICAL CHECK: Verify unified reliability handler is correct type
        from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
        
        # This agent intentionally overrides the handler to None (SSOT violation)
        if violation_agent._unified_reliability_handler is None and violation_agent._enable_reliability:
            pytest.fail("SSOT VIOLATION DETECTED: Unified reliability handler was overridden to None. "
                       "This violates SSOT pattern for reliability management.")
        
        # CRITICAL CHECK: Property access should be consistent
        handler_via_property = violation_agent.unified_reliability_handler
        handler_via_direct = violation_agent._unified_reliability_handler
        
        if handler_via_property != handler_via_direct:
            pytest.fail("SSOT VIOLATION: Inconsistent access to unified reliability handler. "
                       "Property and direct access return different objects.")
    
    async def test_abstract_method_implementation_violations(self):
        """CRITICAL: Must detect missing abstract method implementations.
        
        This test verifies all required abstract methods are properly implemented
        and MUST FAIL if any are missing or incorrectly implemented.
        """
        # Test normal agent
        normal_agent = TestInheritanceViolationAgent(name="AbstractTestAgent")
        
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
                pytest.fail(f"ABSTRACT METHOD VIOLATION: Missing implementation for "
                           f"abstract method '{method_name}'")
            
            # Verify method is callable
            method = getattr(normal_agent, method_name)
            if not callable(method):
                pytest.fail(f"ABSTRACT METHOD VIOLATION: '{method_name}' exists but is not callable")
    
    async def test_concurrent_inheritance_access_violations(self):
        """CRITICAL: Must detect race conditions in inherited method access.
        
        This test stresses concurrent access to inherited methods and
        MUST FAIL if race conditions or inconsistencies are detected.
        """
        # Create concurrent access agent
        concurrent_agent = ConcurrentAccessAgent(name="ConcurrentTestAgent")
        
        # Stress test concurrent access
        num_concurrent_calls = 20
        
        async def execute_agent(agent, call_id):
            context = ExecutionContext(
                run_id=f"concurrent_test_{call_id}",
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
            pytest.fail(f"CONCURRENT ACCESS VIOLATION: {len(failed_results)} out of "
                       f"{num_concurrent_calls} concurrent calls failed: {failed_results[:3]}")
        
        # Check for race condition indicators
        access_counters = [r['result']['access_counter'] for r in successful_results]
        unique_counters = set(access_counters)
        
        # Should have unique access counters if properly synchronized
        if len(unique_counters) != len(access_counters):
            pytest.fail(f"RACE CONDITION DETECTED: Duplicate access counters indicate "
                       f"race condition in concurrent inheritance access: {access_counters}")
        
        # Verify execution times are reasonable (no excessive blocking)
        avg_execution_time = sum(r['execution_time'] for r in successful_results) / len(successful_results)
        max_execution_time = max(r['execution_time'] for r in successful_results)
        
        if max_execution_time > avg_execution_time * 10:
            pytest.fail(f"PERFORMANCE VIOLATION: Excessive execution time variation "
                       f"(max: {max_execution_time:.3f}s, avg: {avg_execution_time:.3f}s) "
                       f"indicates potential deadlock or blocking issues")
    
    async def test_websocket_bridge_inheritance_consistency(self):
        """CRITICAL: Must detect WebSocket bridge inheritance inconsistencies.
        
        This test verifies WebSocket bridge integration is consistent
        across inheritance hierarchy and MUST FAIL if inconsistencies exist.
        """
        # Create multiple agents with inheritance
        agents = [
            TestInheritanceViolationAgent(name=f"WebSocketTest{i}")
            for i in range(5)
        ]
        
        # Test WebSocket bridge consistency across agents
        websocket_adapters = []
        websocket_methods = []
        
        for agent in agents:
            # Check WebSocket adapter exists and is correct type
            if not hasattr(agent, '_websocket_adapter'):
                pytest.fail(f"INHERITANCE VIOLATION: Agent {agent.name} missing WebSocket adapter")
            
            websocket_adapters.append(type(agent._websocket_adapter))
            
            # Check WebSocket methods are consistent
            ws_methods = [method for method in dir(agent) if method.startswith('emit_')]
            websocket_methods.append(sorted(ws_methods))
        
        # CRITICAL CHECK: All agents should have same WebSocket adapter type
        unique_adapter_types = set(websocket_adapters)
        if len(unique_adapter_types) > 1:
            pytest.fail(f"INHERITANCE VIOLATION: Inconsistent WebSocket adapter types "
                       f"across inheritance hierarchy: {unique_adapter_types}")
        
        # CRITICAL CHECK: All agents should have same WebSocket methods
        first_methods = websocket_methods[0]
        for i, methods in enumerate(websocket_methods[1:], 1):
            if methods != first_methods:
                pytest.fail(f"INHERITANCE VIOLATION: Agent {i} has different WebSocket methods. "
                           f"Expected: {first_methods}, Got: {methods}")
        
        # CRITICAL CHECK: Required WebSocket events must be available
        required_events = ['emit_agent_started', 'emit_thinking', 'emit_tool_executing', 
                          'emit_tool_completed', 'emit_agent_completed']
        
        for agent in agents:
            for event_method in required_events:
                if not hasattr(agent, event_method):
                    pytest.fail(f"CRITICAL WEBSOCKET VIOLATION: Agent {agent.name} "
                               f"missing required event method '{event_method}'")
                
                method = getattr(agent, event_method)
                if not callable(method):
                    pytest.fail(f"CRITICAL WEBSOCKET VIOLATION: Event method '{event_method}' "
                               f"in agent {agent.name} is not callable")
    
    async def test_execution_engine_inheritance_violations(self):
        """CRITICAL: Must detect execution engine inheritance violations.
        
        This test verifies execution engine integration is consistent
        and MUST FAIL if inheritance breaks execution patterns.
        """
        # Create agents with different execution configurations
        agents = [
            TestInheritanceViolationAgent(name="ExecTest1", enable_execution_engine=True),
            TestInheritanceViolationAgent(name="ExecTest2", enable_execution_engine=False),
            TestInheritanceViolationAgent(name="ExecTest3", enable_execution_engine=True)
        ]
        
        enabled_agents = [a for a in agents if a._enable_execution_engine]
        disabled_agents = [a for a in agents if not a._enable_execution_engine]
        
        # CRITICAL CHECK: Enabled agents must have execution engine
        for agent in enabled_agents:
            if not hasattr(agent, '_execution_engine') or agent._execution_engine is None:
                pytest.fail(f"EXECUTION ENGINE VIOLATION: Agent {agent.name} "
                           f"enabled execution engine but _execution_engine is None")
            
            # Check execution methods are available
            if not hasattr(agent, 'execute_modern'):
                pytest.fail(f"EXECUTION ENGINE VIOLATION: Agent {agent.name} "
                           f"missing execute_modern method")
        
        # CRITICAL CHECK: Disabled agents should handle execution gracefully
        for agent in disabled_agents:
            context = ExecutionContext(
                run_id="test_disabled_exec",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            # Should still be able to execute core logic
            try:
                result = await agent.execute_core_logic(context)
                assert result is not None, "Core logic should return result even without execution engine"
            except Exception as e:
                pytest.fail(f"EXECUTION ENGINE VIOLATION: Agent {agent.name} "
                           f"with disabled execution engine failed core logic: {e}")
    
    async def test_state_management_inheritance_violations(self):
        """CRITICAL: Must detect state management inheritance violations.
        
        This test verifies state management is consistent across inheritance
        and MUST FAIL if state transitions are broken.
        """
        agent = TestInheritanceViolationAgent(name="StateTestAgent")
        
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
                        f"State transition {from_state} -> {to_state} failed to update state"
                    
                    # Reset for next test
                    agent.state = from_state
                    
                except ValueError as e:
                    pytest.fail(f"STATE MANAGEMENT VIOLATION: Valid transition "
                               f"{from_state} -> {to_state} was rejected: {e}")
        
        # Test invalid transitions should fail
        agent.state = SubAgentLifecycle.SHUTDOWN
        invalid_states = [SubAgentLifecycle.PENDING, SubAgentLifecycle.RUNNING, 
                         SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]
        
        for invalid_state in invalid_states:
            try:
                agent.set_state(invalid_state)
                pytest.fail(f"STATE MANAGEMENT VIOLATION: Invalid transition "
                           f"SHUTDOWN -> {invalid_state} was allowed but should be rejected")
            except ValueError:
                # Expected behavior - invalid transitions should raise ValueError
                pass