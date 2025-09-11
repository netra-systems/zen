"""
Factory Consolidation SSOT Validation Tests - Issue #186 WebSocket Manager Fragmentation

Tests that FAIL initially to prove factory pattern fragmentation exists in WebSocket managers.
After SSOT consolidation, these tests should PASS, proving the violations were fixed.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Eliminate fragmented factory patterns causing golden path failures
- Value Impact: Ensure consistent WebSocket manager creation across all user interactions
- Revenue Impact: Prevent $500K+ ARR chat functionality disruptions from manager inconsistency

SSOT Violations This Module Proves:
1. Multiple factory implementations creating different manager types
2. Factory pattern fragmentation causing interface inconsistency
3. Legacy factory methods still being used instead of unified approach
4. Factory state not properly isolated between users
"""

import asyncio
import inspect
import unittest
from typing import Any, Dict, Set, Type
from unittest.mock import Mock, patch

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerFactoryConsolidation(unittest.TestCase):
    """
    Tests to prove WebSocket manager factory fragmentation violations exist.
    
    These tests are designed to FAIL initially, proving SSOT violations.
    After proper SSOT consolidation, they should PASS.
    """

    def test_only_one_websocket_factory_exists(self):
        """
        FAILING test that proves factory fragmentation exists.
        
        EXPECTED INITIAL STATE: FAIL - Multiple factory classes exist
        EXPECTED POST-SSOT STATE: PASS - Only one canonical factory exists
        
        VIOLATION BEING PROVED: Multiple factory implementations creating different managers
        """
        # Search for all WebSocket factory-related classes
        factory_classes = []
        
        try:
            # Check for WebSocketManagerFactory (main factory)
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory_classes.append(('WebSocketManagerFactory', WebSocketManagerFactory))
        except ImportError:
            pass
        
        try:
            # Check for legacy factory patterns
            from netra_backend.app.websocket_core.migration_adapter import WebSocketManagerAdapter
            factory_classes.append(('WebSocketManagerAdapter', WebSocketManagerAdapter))
        except ImportError:
            pass
            
        try:
            # Check for other factory patterns
            from netra_backend.app.websocket_core.unified_manager import WebSocketManager
            if hasattr(WebSocketManager, 'create') or hasattr(WebSocketManager, 'factory'):
                factory_classes.append(('WebSocketManager.factory_methods', WebSocketManager))
        except ImportError:
            pass

        try:
            # Check for protocol-based factories
            from netra_backend.app.core.interfaces_websocket import WebSocketManagerProtocol
            # Look for any factory methods on the protocol
            if hasattr(WebSocketManagerProtocol, 'create_manager'):
                factory_classes.append(('WebSocketManagerProtocol.factory', WebSocketManagerProtocol))
        except ImportError:
            pass

        # ASSERTION THAT SHOULD FAIL INITIALLY: Only one factory should exist
        self.assertEqual(
            len(factory_classes), 1,
            f"SSOT VIOLATION: Multiple WebSocket factory implementations found: {[name for name, _ in factory_classes]}. "
            f"Expected exactly 1 canonical factory. This proves factory fragmentation exists."
        )
        
        # Additional validation - ensure the single factory is the canonical one
        if factory_classes:
            canonical_factory_name = 'WebSocketManagerFactory'
            actual_factory_name = factory_classes[0][0]
            self.assertEqual(
                actual_factory_name, canonical_factory_name,
                f"SSOT VIOLATION: Factory is not canonical. Expected '{canonical_factory_name}', got '{actual_factory_name}'"
            )

    def test_factory_creates_consistent_managers(self):
        """
        Test unified factory produces consistent manager instances.
        
        EXPECTED INITIAL STATE: FAIL - Different factory methods create different manager types
        EXPECTED POST-SSOT STATE: PASS - All factory methods create same manager type
        
        VIOLATION BEING PROVED: Factory pattern fragmentation causing different manager types
        """
        manager_types = set()
        
        try:
            # Test main factory
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            manager1 = factory.create_isolated_manager(
                user_id="test_user_1",
                connection_id="test_conn_1"
            )
            manager_types.add(type(manager1).__name__)
            
        except Exception as e:
            self.fail(f"Main factory failed: {e}")

        try:
            # Test adapter factory (if exists)
            from netra_backend.app.websocket_core.migration_adapter import WebSocketManagerAdapter
            adapter = WebSocketManagerAdapter()
            if hasattr(adapter, 'get_manager'):
                manager2 = adapter.get_manager()
                manager_types.add(type(manager2).__name__)
                
        except ImportError:
            # Expected if adapter doesn't exist
            pass
        except Exception as e:
            logger.warning(f"Adapter factory failed: {e}")

        try:
            # Test unified manager direct creation
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager3 = UnifiedWebSocketManager()
            manager_types.add(type(manager3).__name__)
            
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Unified manager direct creation failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: All factories should create same manager type
        self.assertEqual(
            len(manager_types), 1,
            f"SSOT VIOLATION: Factories create different manager types: {manager_types}. "
            f"Expected all factories to create same manager type. This proves factory fragmentation."
        )

    def test_legacy_factory_methods_deprecated(self):
        """
        Test that old factory patterns show deprecation warnings.
        
        EXPECTED INITIAL STATE: FAIL - Legacy methods exist without deprecation warnings
        EXPECTED POST-SSOT STATE: PASS - Legacy methods properly deprecated or removed
        
        VIOLATION BEING PROVED: Legacy factory methods still active without proper migration path
        """
        legacy_patterns_found = []
        
        # Check for legacy adapter usage
        try:
            from netra_backend.app.websocket_core.migration_adapter import WebSocketManagerAdapter
            legacy_patterns_found.append('WebSocketManagerAdapter')
        except ImportError:
            # Good - adapter removed
            pass

        # Check for direct manager instantiation patterns (anti-pattern)
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            # Direct instantiation should be deprecated in favor of factory
            manager = UnifiedWebSocketManager()
            legacy_patterns_found.append('Direct UnifiedWebSocketManager instantiation')
        except Exception:
            # Could be good or bad - depends on context
            pass

        # Check for any get_websocket_manager global functions (legacy pattern)
        try:
            from netra_backend.app.websocket_core import get_websocket_manager
            legacy_patterns_found.append('Global get_websocket_manager function')
        except ImportError:
            # Good - global function removed
            pass

        # ASSERTION THAT SHOULD FAIL INITIALLY: No legacy patterns should exist
        self.assertEqual(
            len(legacy_patterns_found), 0,
            f"SSOT VIOLATION: Legacy factory patterns still exist: {legacy_patterns_found}. "
            f"Expected all legacy patterns to be deprecated or removed. This proves incomplete SSOT migration."
        )

    def test_factory_instance_isolation(self):
        """
        Test that factory creates properly isolated manager instances.
        
        EXPECTED INITIAL STATE: FAIL - Factory creates shared instances or singletons
        EXPECTED POST-SSOT STATE: PASS - Factory creates unique isolated instances
        
        VIOLATION BEING PROVED: Factory creates shared state instead of isolated instances
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        except ImportError:
            self.fail("CRITICAL: WebSocketManagerFactory not found - factory pattern completely missing")

        factory = WebSocketManagerFactory()
        
        # Create multiple manager instances
        manager1 = factory.create_isolated_manager(
            user_id="user_1",
            connection_id="conn_1"
        )
        
        manager2 = factory.create_isolated_manager(
            user_id="user_2", 
            connection_id="conn_2"
        )

        # ASSERTION: Managers should be different instances (not shared/singleton)
        self.assertIsNot(
            manager1, manager2,
            "SSOT VIOLATION: Factory creates shared/singleton instances instead of isolated instances. "
            "This proves factory doesn't properly isolate user state."
        )

        # ASSERTION: Managers should have different internal state
        self.assertNotEqual(
            getattr(manager1, '_user_id', None),
            getattr(manager2, '_user_id', None),
            "SSOT VIOLATION: Factory creates managers with shared user state. "
            "This proves factory state isolation is broken."
        )

    def test_factory_interface_consistency(self):
        """
        Test that factory consistently implements required interface methods.
        
        EXPECTED INITIAL STATE: FAIL - Factory methods inconsistent across implementations
        EXPECTED POST-SSOT STATE: PASS - Factory has consistent, complete interface
        
        VIOLATION BEING PROVED: Factory interface divergence and incomplete implementations
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        except ImportError:
            self.fail("CRITICAL: WebSocketManagerFactory not found")

        factory = WebSocketManagerFactory()
        
        # Required factory methods for SSOT compliance
        required_methods = [
            'create_isolated_manager',
            'cleanup_manager',
            'get_manager_by_user',
            'get_active_connections_count'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(factory, method_name):
                missing_methods.append(method_name)
            elif not callable(getattr(factory, method_name)):
                missing_methods.append(f"{method_name} (not callable)")

        # ASSERTION THAT SHOULD FAIL INITIALLY: All required methods should exist
        self.assertEqual(
            len(missing_methods), 0,
            f"SSOT VIOLATION: Factory missing required methods: {missing_methods}. "
            f"This proves factory interface is incomplete and inconsistent."
        )

    def test_factory_error_handling_consistency(self):
        """
        Test that factory has consistent error handling across all methods.
        
        EXPECTED INITIAL STATE: FAIL - Inconsistent error handling between factory methods
        EXPECTED POST-SSOT STATE: PASS - Consistent error handling across all factory methods
        
        VIOLATION BEING PROVED: Factory error handling inconsistency causing system instability
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        except ImportError:
            self.fail("CRITICAL: WebSocketManagerFactory not found")

        factory = WebSocketManagerFactory()
        
        # Test error handling consistency
        error_handling_consistent = True
        error_details = []
        
        # Test invalid user_id handling
        try:
            manager = factory.create_isolated_manager(
                user_id=None,  # Invalid
                connection_id="valid_conn"
            )
            error_details.append("Factory accepts None user_id without error")
            error_handling_consistent = False
        except (ValueError, TypeError) as e:
            # Good - proper error handling
            pass
        except Exception as e:
            error_details.append(f"Factory raises unexpected error for None user_id: {type(e).__name__}")
            error_handling_consistent = False

        # Test invalid connection_id handling  
        try:
            manager = factory.create_isolated_manager(
                user_id="valid_user",
                connection_id=""  # Invalid empty string
            )
            error_details.append("Factory accepts empty connection_id without error")
            error_handling_consistent = False
        except (ValueError, TypeError) as e:
            # Good - proper error handling
            pass
        except Exception as e:
            error_details.append(f"Factory raises unexpected error for empty connection_id: {type(e).__name__}")
            error_handling_consistent = False

        # ASSERTION THAT SHOULD FAIL INITIALLY: Error handling should be consistent
        self.assertTrue(
            error_handling_consistent,
            f"SSOT VIOLATION: Factory error handling inconsistent: {error_details}. "
            f"This proves factory error handling needs standardization."
        )

    def test_factory_performance_requirements(self):
        """
        Test that factory meets performance requirements for manager creation.
        
        EXPECTED INITIAL STATE: FAIL - Factory performance inconsistent or slow
        EXPECTED POST-SSOT STATE: PASS - Factory meets performance requirements consistently
        
        VIOLATION BEING PROVED: Factory performance not optimized for production workloads
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        except ImportError:
            self.fail("CRITICAL: WebSocketManagerFactory not found")

        import time
        
        factory = WebSocketManagerFactory()
        
        # Test manager creation performance
        creation_times = []
        for i in range(10):
            start_time = time.time()
            manager = factory.create_isolated_manager(
                user_id=f"user_{i}",
                connection_id=f"conn_{i}"
            )
            end_time = time.time()
            creation_times.append(end_time - start_time)

        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        # Performance requirements for production
        MAX_AVERAGE_CREATION_TIME = 0.01  # 10ms average
        MAX_SINGLE_CREATION_TIME = 0.05   # 50ms max single creation
        
        performance_issues = []
        
        if avg_creation_time > MAX_AVERAGE_CREATION_TIME:
            performance_issues.append(f"Average creation time {avg_creation_time:.3f}s > {MAX_AVERAGE_CREATION_TIME}s")
            
        if max_creation_time > MAX_SINGLE_CREATION_TIME:
            performance_issues.append(f"Max creation time {max_creation_time:.3f}s > {MAX_SINGLE_CREATION_TIME}s")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Performance should meet requirements
        self.assertEqual(
            len(performance_issues), 0,
            f"SSOT VIOLATION: Factory performance issues: {performance_issues}. "
            f"This proves factory needs performance optimization for production workloads."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()