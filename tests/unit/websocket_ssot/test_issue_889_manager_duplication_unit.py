"""
Issue #889 WebSocket Manager SSOT Violations - Unit Test Suite
Manager Creation Duplication Detection

MUST FAIL INITIALLY: These tests are designed to reproduce the exact SSOT violations
identified in Issue #889, specifically the "Multiple manager instances for user demo-user-001"
warnings appearing in GCP staging logs.

Business Value: Protects $500K+ ARR chat functionality by ensuring proper WebSocket 
manager factory patterns and user isolation critical for regulatory compliance.

Expected Behavior:
- All tests MUST FAIL initially, proving the violations exist
- Tests validate proper SSOT factory pattern compliance
- Tests ensure user isolation integrity for multi-tenant security

Agent Session: agent-session-2025-09-15-1430
Created: 2025-09-15
Priority: P2 (escalated from P3 due to high frequency)
"""

import pytest
import asyncio
import unittest
from unittest.mock import patch, Mock, MagicMock
from typing import Optional, Any
import secrets

# SSOT Base Test Case - MANDATORY for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT imports for isolated environment
from shared.isolated_environment import IsolatedEnvironment, get_env

# WebSocket manager imports - testing the actual implementation
try:
    from netra_backend.app.websocket_core.websocket_manager import (
        get_websocket_manager,
        _UnifiedWebSocketManagerImplementation,
        WebSocketManagerMode,
        create_test_user_context
    )
    WEBSOCKET_IMPORTS_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_IMPORTS_AVAILABLE = False
    print(f"WebSocket imports not available: {e}")


@pytest.mark.unit
class TestIssue889ManagerDuplicationUnit(SSotAsyncTestCase):
    """
    Unit tests for Issue #889 WebSocket Manager SSOT Violations
    
    Focus: Manager creation duplication detection and SSOT compliance validation
    """
    
    def setup_method(self, method):
        """Standard setup following SSOT patterns"""
        super().setup_method(method)
        self.test_user_id = "demo-user-001"  # Exact pattern from GCP logs
        self.created_managers = []
        
    def teardown_method(self, method=None):
        """Cleanup any managers created during testing"""
        # Clean up any managers to prevent resource leaks
        self.created_managers.clear()
        super().teardown_method(method)
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_direct_instantiation_bypasses_ssot_factory(self):
        """
        MUST FAIL INITIALLY: Detect when code bypasses SSOT factory pattern
        
        Business Value: Protects factory pattern integrity for user isolation
        Expected Failure: Should detect multiple manager instances for same user
        
        This test reproduces the core violation where multiple creation paths
        can lead to duplicate managers for the same user context.
        """
        # Create test user context - using demo-user-001 pattern from logs
        test_context = type('MockUserContext', (), {
            'user_id': self.test_user_id,
            'thread_id': 'test-thread-001',
            'request_id': 'test-request-001',
            'is_test': True
        })()
        
        # PATH 1: Create manager through official factory function
        manager1 = await get_websocket_manager(user_context=test_context)
        self.created_managers.append(manager1)
        
        # PATH 2: Direct instantiation bypassing factory (VIOLATION)
        # This simulates the problematic pattern that causes duplication
        auth_token = secrets.token_urlsafe(32)
        manager2 = _UnifiedWebSocketManagerImplementation(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=test_context,
            _ssot_authorization_token=auth_token
        )
        self.created_managers.append(manager2)
        
        # VALIDATION: This should detect the SSOT violation
        # In the current implementation, this will NOT be detected as a violation
        # causing this test to FAIL initially as expected
        manager1_id = getattr(manager1, 'manager_id', id(manager1))
        manager2_id = getattr(manager2, 'manager_id', id(manager2))
        
        # This assertion WILL FAIL initially - proving the violation exists
        self.assertEqual(
            manager1_id, 
            manager2_id,
            f"SSOT Violation: Multiple manager instances for user {self.test_user_id} - "
            f"Factory created {manager1_id}, Direct created {manager2_id}. "
            f"This violates SSOT principles and can cause user isolation failures."
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_demo_user_001_duplication_pattern(self):
        """
        MUST FAIL INITIALLY: Reproduce exact pattern seen in GCP logs
        
        Business Value: Validates test user patterns don't cause production issues
        Expected Failure: "Multiple manager instances for user demo-user-001"
        
        This test recreates the exact demo-user-001 scenario from staging logs.
        """
        violation_messages = []
        
        # Create multiple managers for demo-user-001 through different scenarios
        demo_context = type('MockUserContext', (), {
            'user_id': self.test_user_id,
            'thread_id': 'demo-thread-001',
            'request_id': 'demo-request-001',
            'is_test': True
        })()
        
        # Scenario 1: Normal creation
        manager1 = await get_websocket_manager(user_context=demo_context)
        self.created_managers.append(manager1)
        
        # Scenario 2: Concurrent creation (simulates race condition)
        manager2 = await get_websocket_manager(user_context=demo_context)
        self.created_managers.append(manager2)
        
        # Check if different manager instances were created (violation)
        if id(manager1) != id(manager2):
            violation_messages.append(f"Multiple manager instances for user {self.test_user_id} - potential duplication")
            
        # This assertion WILL FAIL initially - no violations detected in current implementation
        self.assertGreater(
            len(violation_messages), 
            0,
            f"Expected SSOT violation detection for demo-user-001 pattern, but no violations were captured. "
            f"This indicates the SSOT validation is not properly detecting duplicate manager creation. "
            f"Expected message: 'Multiple manager instances for user demo-user-001 - potential duplication'"
        )
        
        # Verify exact log message pattern
        expected_violation = f"Multiple manager instances for user {self.test_user_id} - potential duplication"
        self.assertIn(
            expected_violation,
            violation_messages,
            f"Expected exact violation message '{expected_violation}' not found in {violation_messages}"
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_null_user_context_creates_duplicate_managers(self):
        """
        MUST FAIL INITIALLY: Detect when null context creates multiple test managers
        
        Business Value: Ensures proper test isolation doesn't affect production
        Expected Failure: Multiple test managers created instead of reusing
        
        This tests the scenario where user_context is None, which triggers
        test manager creation paths that may not follow SSOT patterns.
        """
        created_test_managers = []
        
        # Mock the test manager creation to track instances
        original_create_test_context = create_test_user_context
        
        def track_test_context_creation():
            context = original_create_test_context()
            # Track each test context creation
            created_test_managers.append(context)
            return context
            
        with patch('netra_backend.app.websocket_core.websocket_manager.create_test_user_context', side_effect=track_test_context_creation):
            # Create multiple managers with None user_context
            # This should trigger test manager creation
            manager1 = await get_websocket_manager(user_context=None)
            self.created_managers.append(manager1)
            
            manager2 = await get_websocket_manager(user_context=None)
            self.created_managers.append(manager2)
            
            manager3 = await get_websocket_manager(user_context=None)
            self.created_managers.append(manager3)
            
        # This assertion WILL FAIL initially - multiple test contexts created instead of reusing
        self.assertEqual(
            len(created_test_managers),
            1,
            f"SSOT Violation: Expected single test manager creation, but {len(created_test_managers)} were created. "
            f"Multiple test managers indicate lack of proper SSOT factory pattern for test scenarios. "
            f"This can lead to resource waste and inconsistent test behavior."
        )
        
        # Verify managers use the same test context (should fail initially)
        manager1_context_id = getattr(manager1.user_context, 'user_id', None)
        manager2_context_id = getattr(manager2.user_context, 'user_id', None)
        manager3_context_id = getattr(manager3.user_context, 'user_id', None)
        
        self.assertEqual(
            manager1_context_id,
            manager2_context_id,
            f"Test managers should share same context ID but got {manager1_context_id} vs {manager2_context_id}"
        )
        
        self.assertEqual(
            manager2_context_id,
            manager3_context_id,
            f"Test managers should share same context ID but got {manager2_context_id} vs {manager3_context_id}"
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_ssot_validation_enhancer_bypass(self):
        """
        MUST FAIL INITIALLY: Detect when SSOT validation is bypassed
        
        Business Value: Ensures validation always runs in production
        Expected Failure: Manager created without proper SSOT validation
        
        This tests the ImportError scenario where the SSOT validation enhancer
        is not available, which can lead to managers being created without validation.
        """
        validation_called = []
        
        # Create manager normally to test validation behavior
        test_context = type('MockUserContext', (), {
            'user_id': 'test-validation-user',
            'thread_id': 'test-thread',
            'request_id': 'test-request',
            'is_test': True
        })()
        
        manager = await get_websocket_manager(user_context=test_context)
        self.created_managers.append(manager)
            
        # Now test the bypass scenario
        validation_bypassed = []
        
        with patch('builtins.__import__') as mock_import:
            # Simulate ImportError for the validation enhancer
            def import_side_effect(name, *args, **kwargs):
                if 'ssot_validation_enhancer' in name:
                    raise ImportError("SSOT validation enhancer not available")
                # Call the real import for other modules
                return __import__(name, *args, **kwargs)
                
            mock_import.side_effect = import_side_effect
            
            # This should create a manager without SSOT validation
            bypass_manager = await get_websocket_manager(user_context=test_context)
            self.created_managers.append(bypass_manager)
            validation_bypassed.append(bypass_manager)
            
        # This assertion WILL FAIL initially - validation is not enforced when enhancer unavailable
        self.assertEqual(
            len(validation_bypassed),
            0,
            f"SSOT Violation: Manager was created without SSOT validation when enhancer unavailable. "
            f"This bypasses critical SSOT compliance checking and can lead to undetected violations. "
            f"System should fail securely when validation components are unavailable."
        )
        
        # Verify that when validation is available, it gets called (this should pass)
        self.assertGreater(
            len(validation_called),
            0,
            "SSOT validation should be called when enhancer is available"
        )


@pytest.mark.unit
class TestIssue889SSotFactoryComplianceUnit(SSotAsyncTestCase):
    """
    Additional unit tests focusing on SSOT factory compliance patterns
    
    Focus: Factory pattern enforcement and compliance validation
    """
    
    def setup_method(self, method):
        """Standard setup following SSOT patterns"""
        super().setup_method(method)
        self.created_managers = []
        
    def teardown_method(self, method=None):
        """Cleanup any managers created during testing"""
        self.created_managers.clear()
        super().teardown_method(method)
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_factory_pattern_enforcement(self):
        """
        MUST FAIL INITIALLY: Validate factory pattern is properly enforced
        
        Business Value: Ensures consistent manager creation across all code paths
        Expected Failure: Direct instantiation should be prevented or tracked
        """
        # Test that direct instantiation is tracked/prevented
        factory_violations = []
        
        # Test that direct instantiation creates different instances (violation)
        test_context = type('MockUserContext', (), {
            'user_id': 'factory-test-user',
            'thread_id': 'test-thread',
            'request_id': 'test-request',
            'is_test': True
        })()
        
        # Create manager through factory (should be allowed)
        factory_manager = await get_websocket_manager(user_context=test_context)
        self.created_managers.append(factory_manager)
        
        # Attempt direct instantiation (should be detected as violation)
        auth_token = secrets.token_urlsafe(32)
        direct_manager = _UnifiedWebSocketManagerImplementation(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=test_context,
            _ssot_authorization_token=auth_token
        )
        self.created_managers.append(direct_manager)
        
        # Check if they are different instances (indicating lack of SSOT enforcement)
        if id(factory_manager) != id(direct_manager):
            factory_violations.append({
                'factory_manager_id': id(factory_manager),
                'direct_manager_id': id(direct_manager),
                'violation_type': 'different_instances_for_same_user'
            })
            
        # This assertion WILL FAIL initially - direct instantiation not prevented
        self.assertEqual(
            len(factory_violations),
            0,
            f"SSOT Violation: Direct instantiation should be prevented but {len(factory_violations)} violations detected. "
            f"Direct instantiation bypasses factory pattern controls and can lead to SSOT compliance issues. "
            f"Violations: {factory_violations}"
        )


if __name__ == '__main__':
    # Run tests using standard unittest runner for compatibility
    unittest.main()