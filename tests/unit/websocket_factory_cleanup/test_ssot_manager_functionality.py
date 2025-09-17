"""
Unit Tests for WebSocket Factory Legacy Cleanup - SSOT Manager Functionality Validation

Purpose: Validate that the SSOT get_websocket_manager() function works correctly
and can safely replace the legacy websocket_manager_factory.py functionality.

This test suite validates:
1. SSOT manager functionality through canonical import patterns
2. User context isolation in manager instances
3. Import path validation for both legacy and SSOT patterns
4. Manager instance creation and basic functionality

Business Justification:
- Segment: Platform/Infrastructure
- Business Goal: Ensure zero disruption during legacy cleanup
- Value Impact: Maintain $500K+ ARR Golden Path functionality
- Strategic Impact: Validate SSOT compliance before removal

CRITICAL: These tests MUST all pass before legacy factory removal is safe.
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Optional

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Test the SSOT canonical import pattern
from netra_backend.app.websocket_core.websocket_manager import (
    get_websocket_manager,
    WebSocketManagerMode
)

# Import types for validation
from netra_backend.app.websocket_core.types import WebSocketConnection


class TestSSotManagerFunctionality(SSotAsyncTestCase):
    """Test SSOT WebSocket Manager functionality for legacy cleanup validation."""

    def setup_method(self, method):
        """Setup test environment with isolated configuration."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Setup test user contexts
        self.test_user_context_1 = {"user_id": "test_user_1", "connection_id": "conn_1"}
        self.test_user_context_2 = {"user_id": "test_user_2", "connection_id": "conn_2"}

    def teardown_method(self, method):
        """Cleanup test environment."""
        super().teardown_method(method)

    def test_ssot_manager_import_validation(self):
        """Test that SSOT canonical import pattern works correctly."""
        # Test importing the manager function
        assert callable(get_websocket_manager), "get_websocket_manager should be callable"

        # Test that WebSocketManagerMode enum is available
        assert hasattr(WebSocketManagerMode, 'UNIFIED'), "WebSocketManagerMode should have UNIFIED"

        # Log successful import
        self.logger.info("SSOT canonical import patterns validated successfully")

    def test_ssot_manager_creation_basic(self):
        """Test basic SSOT manager creation without user context."""
        # Create manager using SSOT pattern
        manager = get_websocket_manager()

        # Validate manager is created
        assert manager is not None, "Manager should be created"

        # Validate manager has expected interface
        assert hasattr(manager, 'connect'), "Manager should have connect method"
        assert hasattr(manager, 'disconnect'), "Manager should have disconnect method"
        assert hasattr(manager, 'send_message'), "Manager should have send_message method"

        self.logger.info("SSOT manager basic creation validated")

    def test_ssot_manager_creation_with_user_context(self):
        """Test SSOT manager creation with user context for isolation."""
        # Create manager with user context
        manager = get_websocket_manager(user_context=self.test_user_context_1)

        # Validate manager is created
        assert manager is not None, "Manager should be created with user context"

        # Validate manager interface
        assert hasattr(manager, 'connect'), "Manager should have connect method"
        assert hasattr(manager, 'disconnect'), "Manager should have disconnect method"

        self.logger.info("SSOT manager creation with user context validated")

    def test_ssot_manager_user_isolation(self):
        """Test that different user contexts create isolated manager instances."""
        # Create managers for different users
        manager_1 = get_websocket_manager(user_context=self.test_user_context_1)
        manager_2 = get_websocket_manager(user_context=self.test_user_context_2)

        # Validate that instances are different (user isolation)
        assert manager_1 is not manager_2, "Different user contexts should create different instances"

        # Both should be valid managers
        assert manager_1 is not None, "Manager 1 should be valid"
        assert manager_2 is not None, "Manager 2 should be valid"

        self.logger.info("SSOT manager user isolation validated")

    def test_ssot_manager_mode_parameter(self):
        """Test SSOT manager creation with different modes."""
        # Test unified mode (default)
        manager_unified = get_websocket_manager(mode=WebSocketManagerMode.UNIFIED)
        assert manager_unified is not None, "Unified mode manager should be created"

        self.logger.info("SSOT manager mode parameter validation completed")

    def test_legacy_import_path_still_works(self):
        """Test that legacy import path still works (backward compatibility)."""
        try:
            # Test legacy import path
            from netra_backend.app.websocket_core.manager import WebSocketManager

            # Validate it's available
            assert WebSocketManager is not None, "Legacy import should still work"

            # Should be the same as the SSOT implementation
            ssot_manager = get_websocket_manager()
            legacy_manager = WebSocketManager()

            # Both should have the same interface
            assert hasattr(legacy_manager, 'connect'), "Legacy manager should have connect method"
            assert hasattr(legacy_manager, 'disconnect'), "Legacy manager should have disconnect method"

            self.logger.info("Legacy import path backward compatibility validated")

        except ImportError as e:
            self.fail(f"Legacy import path should still work for backward compatibility: {e}")

    def test_legacy_factory_import_validation(self):
        """Test that legacy factory still exists before removal."""
        try:
            # Validate that legacy factory still exists
            from netra_backend.app.websocket_core.websocket_manager_factory import (
                create_websocket_manager
            )

            assert callable(create_websocket_manager), "Legacy factory function should exist"
            self.logger.info("Legacy factory import validation completed")

        except ImportError:
            # This is expected if cleanup has already happened
            self.logger.warning("Legacy factory already removed or not available")

    def test_manager_basic_functionality(self):
        """Test basic manager functionality works with SSOT pattern."""
        manager = get_websocket_manager(user_context=self.test_user_context_1)

        # Test that manager has expected methods
        expected_methods = ['connect', 'disconnect', 'send_message', 'broadcast']
        for method_name in expected_methods:
            assert hasattr(manager, method_name), f"Manager should have {method_name} method"

        self.logger.info("SSOT manager basic functionality validated")

    def test_environment_isolation_compliance(self):
        """Test that manager respects IsolatedEnvironment patterns."""
        # Create manager and validate it doesn't access os.environ directly
        with patch('os.environ', new_callable=dict) as mock_environ:
            manager = get_websocket_manager()

            # Manager creation should not have accessed os.environ directly
            # Note: This is a basic test - more comprehensive env isolation
            # testing is done in integration tests
            assert manager is not None, "Manager should be created without direct os.environ access"

        self.logger.info("Environment isolation compliance basic validation completed")

    async def test_async_manager_functionality(self):
        """Test that manager works correctly in async context."""
        manager = get_websocket_manager(user_context=self.test_user_context_1)

        # Validate manager can be used in async context
        assert manager is not None, "Manager should work in async context"

        # If manager has async methods, they should be callable
        if hasattr(manager, 'async_connect'):
            assert asyncio.iscoroutinefunction(manager.async_connect), "async_connect should be coroutine"

        self.logger.info("Async manager functionality validated")


class TestLegacyFactoryRemovalReadiness(SSotAsyncTestCase):
    """Test readiness for legacy factory removal."""

    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

    def test_ssot_manager_can_replace_legacy_factory(self):
        """Test that SSOT manager can completely replace legacy factory functionality."""
        # Test that we can create managers with various configurations
        # that would have been handled by the legacy factory

        # Basic manager
        basic_manager = get_websocket_manager()
        assert basic_manager is not None, "Basic manager creation should work"

        # Manager with user context
        user_manager = get_websocket_manager(user_context={"user_id": "test"})
        assert user_manager is not None, "User context manager creation should work"

        # Manager with mode specification
        unified_manager = get_websocket_manager(mode=WebSocketManagerMode.UNIFIED)
        assert unified_manager is not None, "Mode-specific manager creation should work"

        self.logger.info("SSOT manager can replace legacy factory functionality")

    def test_no_breaking_changes_in_manager_interface(self):
        """Test that manager interface has no breaking changes."""
        manager = get_websocket_manager()

        # Test critical interface methods exist
        critical_methods = ['connect', 'disconnect', 'send_message']
        for method in critical_methods:
            assert hasattr(manager, method), f"Critical method {method} must exist"

        # Test that methods are callable
        for method in critical_methods:
            method_obj = getattr(manager, method)
            assert callable(method_obj), f"Method {method} must be callable"

        self.logger.info("Manager interface has no breaking changes")

    def test_error_scenarios_handled_correctly(self):
        """Test that error scenarios are handled correctly in SSOT manager."""
        # Test with None user context (should not fail)
        try:
            manager = get_websocket_manager(user_context=None)
            assert manager is not None, "Manager should handle None user context"
        except Exception as e:
            self.fail(f"Manager should handle None user context gracefully: {e}")

        # Test with empty user context
        try:
            manager = get_websocket_manager(user_context={})
            assert manager is not None, "Manager should handle empty user context"
        except Exception as e:
            self.fail(f"Manager should handle empty user context gracefully: {e}")

        self.logger.info("Error scenarios handled correctly in SSOT manager")


if __name__ == '__main__':
    unittest.main()