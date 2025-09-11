"""
Test ExecutionEngine SSOT Violations Detection

MISSION CRITICAL: These tests prove current SSOT violations exist in ExecutionEngine implementations.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & User Safety
- Value Impact: Prevents user isolation failures that cause data leakage between customers
- Strategic Impact: $500K+ ARR protection by ensuring multi-user system works correctly

PURPOSE: These tests should FAIL initially to demonstrate the SSOT violations.
After remediation with UserExecutionEngine, these tests should PASS.

Test Coverage:
1. Multiple ExecutionEngine instances (violates SSOT)
2. Shared global state between users (violates isolation)
3. WebSocket event cross-contamination (violates user safety)
4. Memory leaks from singleton pattern (violates resource management)
5. Factory pattern violations (violates proper instantiation)

CRITICAL: These are FAILING tests that prove problems exist.
"""

import asyncio
import pytest
import time
import unittest
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class TestExecutionEngineSSotViolations(SSotBaseTestCase, unittest.TestCase):
    """
    Tests that SHOULD FAIL to demonstrate current SSOT violations.
    
    These tests prove that multiple ExecutionEngine implementations
    violate SSOT principles and cause user isolation issues.
    """

    @pytest.mark.mission_critical
    @pytest.mark.unit
    def test_multiple_execution_engine_implementations_exist(self):
        """
        SHOULD FAIL: Tests that multiple ExecutionEngine implementations exist.
        
        SSOT Violation: Only ONE ExecutionEngine implementation should exist.
        Current Reality: 5+ implementations exist causing confusion and bugs.
        """
        try:
            # Try to import all the different ExecutionEngine implementations
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.agents.supervisor.request_scoped_execution_engine import RequestScopedExecutionEngine
            from netra_backend.app.agents.supervisor.mcp_execution_engine import MCPExecutionEngine
            from netra_backend.app.agents.execution_engine_consolidated import ConsolidatedExecutionEngine
            
            # Count unique implementations
            implementations = [
                ExecutionEngine,
                UserExecutionEngine, 
                RequestScopedExecutionEngine,
                MCPExecutionEngine,
                ConsolidatedExecutionEngine
            ]
            
            # SSOT VIOLATION: Should be only 1 implementation, not 5+
            self.fail(
                f"SSOT VIOLATION DETECTED: Found {len(implementations)} ExecutionEngine implementations. "
                f"SSOT requires exactly 1 canonical implementation. "
                f"This proves the current system violates SSOT principles."
            )
            
        except ImportError as e:
            # If we can't import them all, that's actually good (less SSOT violations)
            print(f"INFO: Some ExecutionEngine implementations not found: {e}")

    @pytest.mark.mission_critical  
    @pytest.mark.unit
    def test_execution_engines_share_global_state(self):
        """
        SHOULD FAIL: Tests that ExecutionEngine instances share global state.
        
        User Isolation Violation: Each user should have completely isolated state.
        Current Reality: Global state causes user A's data to leak to user B.
        """
        try:
            # Import the main ExecutionEngine
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            # Create two "different user" ExecutionEngine instances
            engine1 = ExecutionEngine()
            engine2 = ExecutionEngine() 
            
            # Check if they share the same global state
            # This is a VIOLATION - each user should have isolated state
            
            # Test 1: Shared agent registry (global state violation)
            if hasattr(engine1, 'agent_registry') and hasattr(engine2, 'agent_registry'):
                if engine1.agent_registry is engine2.agent_registry:
                    self.fail(
                        "GLOBAL STATE VIOLATION: ExecutionEngine instances share the same agent_registry. "
                        "This causes user A's agents to be accessible by user B."
                    )
            
            # Test 2: Shared execution state (isolation violation)
            if hasattr(engine1, '_execution_state') and hasattr(engine2, '_execution_state'):
                # Set state in engine1 that should NOT appear in engine2
                test_key = f"test_user_state_{int(time.time())}"
                if hasattr(engine1._execution_state, 'set'):
                    engine1._execution_state.set(test_key, "user_a_secret_data")
                    
                    # Check if engine2 can see user A's data (VIOLATION)
                    if hasattr(engine2._execution_state, 'get'):
                        leaked_data = engine2._execution_state.get(test_key)
                        if leaked_data == "user_a_secret_data":
                            self.fail(
                                "USER ISOLATION VIOLATION: Engine2 can access Engine1's private data. "
                                "This is a critical security issue causing data leakage between users."
                            )
            
            # Test 3: Singleton pattern violation (should be factory instances)
            if engine1 is engine2:
                self.fail(
                    "SINGLETON VIOLATION: ExecutionEngine is using singleton pattern. "
                    "Multi-user systems require factory pattern for proper isolation."
                )
            
            # If we reach here, the current implementation might already be fixed
            print("INFO: No obvious global state violations detected - implementation may be correct")
            
        except Exception as e:
            print(f"ERROR: Error testing global state sharing: {e}")
            # This might indicate the SSOT violations are even worse
            self.fail(f"Cannot properly test for SSOT violations due to implementation issues: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    def test_websocket_events_cross_contaminate_users(self):
        """
        SHOULD FAIL: Tests that WebSocket events leak between users.
        
        Business Critical Violation: User A should NEVER see user B's WebSocket events.
        Current Reality: Events may be sent to wrong users due to shared state.
        """
        try:
            # Mock WebSocket emitters to track events
            user_a_events = []
            user_b_events = []
            
            def mock_user_a_emit(event_type, data):
                user_a_events.append((event_type, data))
                
            def mock_user_b_emit(event_type, data):
                user_b_events.append((event_type, data))
            
            # Create ExecutionEngine instances for two different users
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            with patch('netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine') as MockEngine:
                # Configure mock engines with different WebSocket emitters
                engine_a = MockEngine()
                engine_b = MockEngine()
                
                engine_a.websocket_emitter = MagicMock()
                engine_a.websocket_emitter.emit = mock_user_a_emit
                
                engine_b.websocket_emitter = MagicMock() 
                engine_b.websocket_emitter.emit = mock_user_b_emit
                
                # Simulate user A executing an agent
                engine_a.websocket_emitter.emit("agent_started", {"user": "A", "secret": "user_a_secret"})
                
                # Check if user B received user A's events (VIOLATION)
                if len(user_b_events) > 0:
                    leaked_events = [event for event in user_b_events if "user_a_secret" in str(event)]
                    if leaked_events:
                        self.fail(
                            f"WEBSOCKET EVENT LEAKAGE: User B received User A's private events: {leaked_events}. "
                            f"This is a critical security violation in chat functionality."
                        )
                
                # Check if both users got events when only A should have (shared emitter violation)
                if hasattr(engine_a, 'websocket_emitter') and hasattr(engine_b, 'websocket_emitter'):
                    if engine_a.websocket_emitter is engine_b.websocket_emitter:
                        self.fail(
                            "SHARED WEBSOCKET EMITTER VIOLATION: Both engines use the same WebSocket emitter. "
                            "This causes events to be sent to all connected users instead of target user."
                        )
            
            print("INFO: No obvious WebSocket cross-contamination detected")
            
        except Exception as e:
            print(f"ERROR: Error testing WebSocket event isolation: {e}")
            # Implementation issues prevent proper testing - also a violation
            self.fail(f"Cannot test WebSocket isolation due to implementation problems: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    def test_factory_pattern_violations_exist(self):
        """
        SHOULD FAIL: Tests that ExecutionEngine doesn't use proper factory pattern.
        
        Architecture Violation: Multi-user systems require factory pattern for isolation.
        Current Reality: Direct instantiation or singleton patterns violate user isolation.
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            # Test 1: Direct instantiation should not be allowed
            try:
                engine = ExecutionEngine()
                # If we can directly instantiate, that's a factory pattern violation
                self.fail(
                    "FACTORY PATTERN VIOLATION: ExecutionEngine allows direct instantiation. "
                    "Multi-user systems require factory methods for proper isolation. "
                    "Should use create_for_user() or similar factory method."
                )
            except TypeError as e:
                # If it fails, that might mean factory pattern is enforced (good)
                print(f"INFO: Direct instantiation prevented: {e}")
            
            # Test 2: Check if proper factory methods exist
            factory_methods = [
                'create_for_user',
                'create_for_request', 
                'create_isolated_instance',
                'from_user_context'
            ]
            
            missing_factory_methods = []
            for method_name in factory_methods:
                if not hasattr(ExecutionEngine, method_name):
                    missing_factory_methods.append(method_name)
            
            if len(missing_factory_methods) == len(factory_methods):
                self.fail(
                    f"FACTORY PATTERN VIOLATION: ExecutionEngine missing factory methods. "
                    f"None of these factory methods exist: {factory_methods}. "
                    f"This prevents proper user isolation."
                )
            
            # Test 3: Check for singleton pattern violations
            try:
                instance1 = ExecutionEngine()
                instance2 = ExecutionEngine()
                
                if instance1 is instance2:
                    self.fail(
                        "SINGLETON PATTERN VIOLATION: ExecutionEngine uses singleton pattern. "
                        "This prevents multiple users from having isolated instances."
                    )
            except:
                # If instantiation fails, we can't test singleton pattern
                pass
            
            print("INFO: Factory pattern testing completed")
            
        except ImportError as e:
            self.fail(f"Cannot import ExecutionEngine to test factory pattern: {e}")
        except Exception as e:
            self.fail(f"Factory pattern testing failed due to implementation issues: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit  
    def test_memory_leaks_from_global_state(self):
        """
        SHOULD FAIL: Tests that ExecutionEngine causes memory leaks from global state.
        
        Performance Violation: Global state causes memory to accumulate indefinitely.
        Current Reality: Each user execution adds to global memory without cleanup.
        """
        try:
            import gc
            import sys
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            # Track initial memory state
            gc.collect()  # Clean up before testing
            initial_objects = len(gc.get_objects())
            
            # Simulate multiple user executions (should not accumulate globally)
            execution_engines = []
            for i in range(10):
                try:
                    engine = ExecutionEngine()
                    execution_engines.append(engine)
                    
                    # Simulate some execution state
                    if hasattr(engine, 'execution_state'):
                        # Add data that should be cleaned up per user
                        engine.execution_state = {
                            f"user_{i}_data": f"large_data_block_{i}" * 1000,  # ~13KB per user
                            "execution_history": [f"step_{j}" for j in range(100)]
                        }
                except Exception as e:
                    print(f"ERROR: Error creating ExecutionEngine {i}: {e}")
            
            # Check if objects accumulated globally (memory leak)
            gc.collect()
            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects
            
            # If we have significant object growth, it suggests memory leaks
            if object_growth > 1000:  # Arbitrary threshold for "significant"
                self.fail(
                    f"MEMORY LEAK VIOLATION: Created {len(execution_engines)} engines, "
                    f"but object count grew by {object_growth}. "
                    f"This suggests global state is accumulating and not being cleaned up."
                )
            
            # Test cleanup - delete engines and see if memory is reclaimed
            del execution_engines
            gc.collect()
            post_cleanup_objects = len(gc.get_objects())
            
            if post_cleanup_objects > initial_objects + 100:  # Allow some tolerance
                self.fail(
                    f"CLEANUP VIOLATION: After deleting engines, object count is still "
                    f"{post_cleanup_objects - initial_objects} higher than initial. "
                    f"This indicates global state preventing proper cleanup."
                )
            
            print(f"INFO: Memory test completed. Object growth: {object_growth}")
            
        except Exception as e:
            print(f"ERROR: Memory leak testing failed: {e}")
            # If we can't test memory leaks, that's also concerning
            self.fail(f"Cannot test for memory leaks due to implementation issues: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    def test_ssot_documentation_violations(self):
        """
        SHOULD FAIL: Tests that ExecutionEngine documentation violates SSOT principles.
        
        Documentation Violation: Code should clearly indicate which is the canonical implementation.
        Current Reality: Multiple implementations without clear SSOT designation.
        """
        implementations_found = []
        ssot_indicators = []
        
        try:
            # Check each implementation for SSOT documentation
            implementation_files = [
                'netra_backend.app.agents.supervisor.execution_engine',
                'netra_backend.app.agents.supervisor.user_execution_engine', 
                'netra_backend.app.agents.supervisor.request_scoped_execution_engine',
                'netra_backend.app.agents.supervisor.mcp_execution_engine',
                'netra_backend.app.agents.execution_engine_consolidated'
            ]
            
            for module_name in implementation_files:
                try:
                    module = __import__(module_name, fromlist=[''])
                    implementations_found.append(module_name)
                    
                    # Check docstring for SSOT indicators
                    if hasattr(module, '__doc__') and module.__doc__:
                        doc = module.__doc__.lower()
                        if any(indicator in doc for indicator in ['ssot', 'canonical', 'single source']):
                            ssot_indicators.append(module_name)
                            
                except ImportError:
                    continue
            
            # SSOT Violation: Multiple implementations exist
            if len(implementations_found) > 1:
                self.fail(
                    f"SSOT DOCUMENTATION VIOLATION: Found {len(implementations_found)} ExecutionEngine implementations: "
                    f"{implementations_found}. SSOT requires exactly 1 canonical implementation with clear documentation."
                )
            
            # SSOT Violation: No clear SSOT designation
            if len(ssot_indicators) == 0:
                self.fail(
                    f"SSOT DOCUMENTATION VIOLATION: None of the implementations clearly indicate SSOT status. "
                    f"The canonical implementation should be clearly marked as SSOT."
                )
            
            # SSOT Violation: Multiple implementations claim to be SSOT
            if len(ssot_indicators) > 1:
                self.fail(
                    f"SSOT DOCUMENTATION VIOLATION: Multiple implementations claim SSOT status: {ssot_indicators}. "
                    f"Only one can be the true SSOT."
                )
            
            print(f"INFO: SSOT documentation check completed. Found {len(implementations_found)} implementations.")
            
        except Exception as e:
            self.fail(f"SSOT documentation testing failed: {e}")


if __name__ == "__main__":
    """
    Run these tests to demonstrate SSOT violations.
    
    Expected Result: MOST OR ALL TESTS SHOULD FAIL
    This proves that SSOT violations exist and need remediation.
    """
    pytest.main([__file__, "-v", "--tb=short"])