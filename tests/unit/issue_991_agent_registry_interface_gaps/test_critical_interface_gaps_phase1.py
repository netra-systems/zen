"""
Test Critical AgentRegistry Interface Gaps - Issue #991 Phase 1

This test module creates FAILING tests to prove specific interface gaps exist
before implementing fixes. Focus on the most critical missing methods affecting
Golden Path functionality.

Business Value: Protects $500K+ ARR by identifying critical interface gaps
that prevent proper agent registry operations and WebSocket integration.

Test Category: Unit (no Docker required)
Purpose: Failing tests that prove interface gaps exist - DESIGNED TO FAIL initially
"""
import asyncio
import inspect
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class CriticalInterfaceGapsPhase1Tests(SSotAsyncTestCase):
    """
    Test critical interface gaps for Issue #991 Phase 1.
    
    These tests are DESIGNED TO FAIL initially to prove that specific
    critical interface methods are missing from the AgentRegistry implementation.
    
    Focus: Most critical missing methods that block Golden Path functionality.
    """

    def setup_method(self, method):
        """Setup test environment for critical interface gap validation."""
        # Focus on the most critical missing methods identified in Issue #991
        self.critical_missing_methods = {
            'list_available_agents',  # Critical for agent discovery
            'get_websocket_manager',  # Critical for WebSocket integration  
            'create_user_session',    # Critical for user isolation
            'register_agent_async',   # Critical for async operations
            'cleanup_async',          # Critical for proper cleanup
            'get_agent_instance',     # Critical for agent retrieval
            'find_agent_by_name',     # Critical for agent lookup
            'get_agents_by_status',   # Critical for status filtering
            'reset_all_agents',       # Critical for state management
        }
        
        # Golden Path critical methods that MUST work
        self.golden_path_blocking_methods = {
            'list_available_agents',
            'get_websocket_manager', 
            'create_user_session'
        }

    async def test_critical_missing_method_list_available_agents_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove list_available_agents method is missing or broken.
        
        This method is CRITICAL for Golden Path - users must be able to discover
        available agents to start AI interactions.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            # Create registry instance
            registry = AgentRegistry(llm_manager=None)
            
            # This should FAIL - method should be missing or broken
            if not hasattr(registry, 'list_available_agents'):
                self.fail(
                    "CRITICAL FAILURE CONFIRMED: list_available_agents method is completely missing. "
                    "This blocks Golden Path agent discovery functionality."
                )
            
            # Test if method is callable
            method = getattr(registry, 'list_available_agents')
            if not callable(method):
                self.fail(
                    "CRITICAL FAILURE CONFIRMED: list_available_agents exists but is not callable. "
                    "This blocks Golden Path agent discovery functionality."
                )
            
            # Test if method actually works
            try:
                if asyncio.iscoroutinefunction(method):
                    result = await method()
                else:
                    result = method()
                
                # Validate result type
                if not isinstance(result, (list, tuple)):
                    self.fail(
                        f"CRITICAL FAILURE CONFIRMED: list_available_agents returns invalid type {type(result).__name__}. "
                        f"Expected list or tuple for Golden Path compatibility."
                    )
                    
                logger.info(f"list_available_agents returned: {result} (type: {type(result).__name__})")
                
            except Exception as e:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: list_available_agents method exists but fails when called: {e}. "
                    f"This blocks Golden Path agent discovery functionality."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        # If we reach here, the method actually works - test should be updated after fix
        logger.warning("list_available_agents method is working - this test should be updated after Issue #991 Phase 1 fix")

    async def test_websocket_manager_integration_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove WebSocket manager integration is broken.
        
        This is CRITICAL for Golden Path - users must receive real-time agent events.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry = AgentRegistry(llm_manager=None)
            
            # Test get_websocket_manager method
            if not hasattr(registry, 'get_websocket_manager'):
                self.fail(
                    "CRITICAL FAILURE CONFIRMED: get_websocket_manager method is missing. "
                    "This blocks Golden Path WebSocket integration."
                )
            
            method = getattr(registry, 'get_websocket_manager')
            if not callable(method):
                self.fail(
                    "CRITICAL FAILURE CONFIRMED: get_websocket_manager exists but is not callable. "
                    "This blocks Golden Path WebSocket integration."
                )
            
            # Test WebSocket manager setting/getting
            mock_websocket_manager = Mock()
            
            try:
                # Set WebSocket manager
                if hasattr(registry, 'set_websocket_manager'):
                    set_method = getattr(registry, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(set_method):
                        await set_method(mock_websocket_manager)
                    else:
                        set_method(mock_websocket_manager)
                
                # Get WebSocket manager
                if asyncio.iscoroutinefunction(method):
                    result = await method()
                else:
                    result = method()
                
                if result is None:
                    self.fail(
                        "CRITICAL FAILURE CONFIRMED: get_websocket_manager returns None after setting manager. "
                        "This blocks Golden Path WebSocket integration."
                    )
                    
            except Exception as e:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: WebSocket manager integration fails: {e}. "
                    f"This blocks Golden Path real-time agent events."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("WebSocket manager integration is working - this test should be updated after Issue #991 Phase 1 fix")

    async def test_user_session_management_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove user session management is broken.
        
        This is CRITICAL for Golden Path - multi-user agent isolation is required.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry = AgentRegistry(llm_manager=None)
            
            # Test create_user_session method
            if not hasattr(registry, 'create_user_session'):
                self.fail(
                    "CRITICAL FAILURE CONFIRMED: create_user_session method is missing. "
                    "This blocks Golden Path multi-user functionality."
                )
            
            method = getattr(registry, 'create_user_session')
            if not callable(method):
                self.fail(
                    "CRITICAL FAILURE CONFIRMED: create_user_session exists but is not callable. "
                    "This blocks Golden Path multi-user functionality."
                )
            
            # Test user session creation
            test_user_id = "test_user_991"
            
            try:
                if asyncio.iscoroutinefunction(method):
                    result = await method(test_user_id)
                else:
                    result = method(test_user_id)
                
                if result is None:
                    self.fail(
                        "CRITICAL FAILURE CONFIRMED: create_user_session returns None. "
                        "This blocks Golden Path user isolation."
                    )
                
                # Test if user session can be retrieved
                if hasattr(registry, 'get_user_session'):
                    get_method = getattr(registry, 'get_user_session')
                    if asyncio.iscoroutinefunction(get_method):
                        session = await get_method(test_user_id)
                    else:
                        session = get_method(test_user_id)
                    
                    if session is None:
                        self.fail(
                            "CRITICAL FAILURE CONFIRMED: User session created but cannot be retrieved. "
                            "This blocks Golden Path user isolation."
                        )
                        
            except Exception as e:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: User session management fails: {e}. "
                    f"This blocks Golden Path multi-user functionality."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("User session management is working - this test should be updated after Issue #991 Phase 1 fix")

    async def test_async_operations_support_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove async operations are not properly supported.
        
        Modern agent operations require async support for non-blocking execution.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry = AgentRegistry(llm_manager=None)
            
            # Test async registration method
            async_methods_to_test = ['register_agent_async', 'cleanup_async', 'get_async']
            missing_async_methods = []
            broken_async_methods = []
            
            for method_name in async_methods_to_test:
                if not hasattr(registry, method_name):
                    missing_async_methods.append(method_name)
                    continue
                
                method = getattr(registry, method_name)
                if not callable(method):
                    broken_async_methods.append(f"{method_name} (not callable)")
                    continue
                
                if not asyncio.iscoroutinefunction(method):
                    broken_async_methods.append(f"{method_name} (not async)")
                    continue
            
            if missing_async_methods:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: Missing async methods: {missing_async_methods}. "
                    f"This blocks modern async agent operations."
                )
            
            if broken_async_methods:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: Broken async methods: {broken_async_methods}. "
                    f"This blocks modern async agent operations."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("Async operations support is working - this test should be updated after Issue #991 Phase 1 fix")

    async def test_agent_lookup_methods_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove agent lookup methods are missing or broken.
        
        These methods are required for agent discovery and management.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry = AgentRegistry(llm_manager=None)
            
            # Test critical lookup methods
            lookup_methods = [
                'get_agent_instance',
                'find_agent_by_name', 
                'get_agents_by_status',
                'get_agents_by_type'
            ]
            
            missing_methods = []
            broken_methods = []
            
            for method_name in lookup_methods:
                if not hasattr(registry, method_name):
                    missing_methods.append(method_name)
                    continue
                
                method = getattr(registry, method_name)
                if not callable(method):
                    broken_methods.append(f"{method_name} (not callable)")
                    continue
                
                # Test method call with safe parameters
                try:
                    if method_name == 'get_agent_instance':
                        if asyncio.iscoroutinefunction(method):
                            result = await method("test_agent_id")
                        else:
                            result = method("test_agent_id")
                    elif method_name == 'find_agent_by_name':
                        if asyncio.iscoroutinefunction(method):
                            result = await method("test_agent_name")  
                        else:
                            result = method("test_agent_name")
                    elif method_name == 'get_agents_by_status':
                        if asyncio.iscoroutinefunction(method):
                            result = await method("idle")
                        else:
                            result = method("idle")
                    elif method_name == 'get_agents_by_type':
                        if asyncio.iscoroutinefunction(method):
                            result = await method("triage")
                        else:
                            result = method("triage")
                            
                    # Validate result type for list-returning methods
                    if method_name in ['get_agents_by_status', 'get_agents_by_type']:
                        if not isinstance(result, (list, tuple)):
                            broken_methods.append(f"{method_name} (returns {type(result).__name__}, expected list)")
                            
                except Exception as e:
                    broken_methods.append(f"{method_name} (call error: {e})")
            
            if missing_methods:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: Missing agent lookup methods: {missing_methods}. "
                    f"This blocks agent discovery and management functionality."
                )
            
            if broken_methods:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: Broken agent lookup methods: {broken_methods}. "
                    f"This blocks agent discovery and management functionality."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("Agent lookup methods are working - this test should be updated after Issue #991 Phase 1 fix")

    def test_interface_method_count_gap_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove that the total method count is insufficient.
        
        This test validates that we have the expected number of interface methods
        for full SSOT compliance.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry_class = AgentRegistry
            
            # Count actual public methods
            actual_methods = set()
            for attr_name in dir(registry_class):
                if not attr_name.startswith('_'):  # Public methods only
                    attr = getattr(registry_class, attr_name)
                    if callable(attr):
                        actual_methods.add(attr_name)
            
            # Expected minimum method count for full SSOT compliance
            expected_minimum_methods = 40  # Based on interface analysis
            actual_method_count = len(actual_methods)
            
            logger.info(f"Actual public methods count: {actual_method_count}")
            logger.info(f"Expected minimum methods: {expected_minimum_methods}")
            logger.info(f"Actual methods: {sorted(actual_methods)}")
            
            if actual_method_count < expected_minimum_methods:
                missing_method_count = expected_minimum_methods - actual_method_count
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: AgentRegistry has only {actual_method_count} public methods, "
                    f"expected at least {expected_minimum_methods}. Missing approximately {missing_method_count} methods. "
                    f"This indicates significant interface gaps that block SSOT compliance."
                )
            
            # Check for specific critical missing methods
            missing_critical = []
            for method_name in self.critical_missing_methods:
                if method_name not in actual_methods:
                    missing_critical.append(method_name)
            
            if missing_critical:
                self.fail(
                    f"CRITICAL FAILURE CONFIRMED: Missing critical interface methods: {missing_critical}. "
                    f"These methods are required for Golden Path functionality and SSOT compliance."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("Interface method count is sufficient - this test should be updated after Issue #991 Phase 1 fix")

    async def test_golden_path_blocking_methods_FAILS(self):
        """
        TEST DESIGNED TO FAIL: Prove Golden Path is blocked by missing methods.
        
        This test specifically focuses on methods that directly block the Golden Path
        user flow: Users login -> get AI responses.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry = AgentRegistry(llm_manager=None)
            
            golden_path_failures = []
            
            for method_name in self.golden_path_blocking_methods:
                if not hasattr(registry, method_name):
                    golden_path_failures.append(f"Missing: {method_name}")
                    continue
                
                method = getattr(registry, method_name)
                if not callable(method):
                    golden_path_failures.append(f"Not callable: {method_name}")
                    continue
                
                # Test if method can be called safely
                try:
                    if method_name == 'list_available_agents':
                        if asyncio.iscoroutinefunction(method):
                            result = await method()
                        else:
                            result = method()
                        if not isinstance(result, (list, tuple)):
                            golden_path_failures.append(f"Invalid return type: {method_name}")
                    
                    elif method_name == 'get_websocket_manager':
                        if asyncio.iscoroutinefunction(method):
                            result = await method()
                        else:
                            result = method()
                        # Result can be None if not set, that's not a failure
                    
                    elif method_name == 'create_user_session':
                        if asyncio.iscoroutinefunction(method):
                            result = await method("test_user_golden_path")
                        else:
                            result = method("test_user_golden_path")
                        if result is None:
                            golden_path_failures.append(f"Returns None: {method_name}")
                            
                except Exception as e:
                    golden_path_failures.append(f"Call error: {method_name} - {e}")
            
            if golden_path_failures:
                self.fail(
                    f"CRITICAL GOLDEN PATH FAILURE CONFIRMED: Golden Path is blocked by interface failures: "
                    f"{golden_path_failures}. This prevents users from logging in and getting AI responses, "
                    f"blocking the core $500K+ ARR business functionality."
                )
                
        except ImportError as e:
            self.fail(f"CRITICAL FAILURE: Cannot import AgentRegistry: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED CRITICAL FAILURE: {e}")
            
        logger.warning("Golden Path methods are working - this test should be updated after Issue #991 Phase 1 fix")


if __name__ == '__main__':
    # MIGRATED: Use SSOT unified test runner
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --test-file tests/unit/issue_991_agent_registry_interface_gaps/test_critical_interface_gaps_phase1.py')