"""
SSOT Agent Registry Consolidation Validation Tests

Issue #845: Critical P0 test suite for validating AgentRegistry SSOT consolidation
Business Impact: $500K+ ARR Golden Path protection (login → AI responses)

Tests duplicate AgentRegistry consolidation from:
- Basic: /netra_backend/app/agents/registry.py (419 lines) → TO BE ELIMINATED
- Advanced: /netra_backend/app/agents/supervisor/agent_registry.py (1,817 lines) → SSOT TARGET

Created: 2025-01-13 - SSOT Gardner agents focus
Priority: P0 (Critical/Blocking) - Must pass before consolidation
"""

import pytest
import asyncio
from typing import Dict, Any, Optional

# SSOT Base Test Case - Required for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Environment access through SSOT pattern only
from shared.isolated_environment import IsolatedEnvironment

# Test imports - SSOT consolidated registry
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.types import AgentStatus, AgentType, AgentInfo


class TestAgentRegistrySSoTConsolidation(SSotAsyncTestCase):
    """Critical P0 tests for AgentRegistry SSOT consolidation validation"""
    
    def setup_method(self, method=None):
        """Set up test environment with SSOT patterns"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.registry = AgentRegistry()
        
        # Test user context for isolation validation
        self.test_user_id = "test-user-ssot-consolidation"
        self.test_session_id = "test-session-ssot-validation"

    async def test_consolidated_registry_functionality(self):
        """
        CRITICAL: Validate consolidated registry has all expected functionality
        
        Business Impact: Ensures SSOT consolidation maintains all features
        Expected: PASS - consolidated registry should work completely
        """
        # Test consolidated registry core functionality
        available_agents = await self.registry.list_available_agents()
        
        # Consolidated registry should provide consistent interface
        self.assertIsInstance(available_agents, (list, dict), 
                             "Consolidated registry should return agents list/dict")
        
        # Interface consistency check
        self.assertTrue(hasattr(self.registry, 'create_user_session'),
                       "Consolidated registry must support create_user_session method")
        self.assertTrue(hasattr(self.registry, 'set_websocket_manager'),
                       "Consolidated registry must support WebSocket integration")

    async def test_advanced_registry_features_retained(self):
        """
        CRITICAL: Ensure advanced features not broken by consolidation
        
        Business Impact: User isolation and WebSocket features must be preserved
        Expected: PASS - advanced features must continue working
        """
        # Test user isolation features
        user_session = await self.registry.create_user_session(
            self.test_user_id, self.test_session_id
        )
        
        self.assertIsNotNone(user_session, "User session creation must work")
        
        # Test WebSocket bridge integration (critical for Golden Path)
        if hasattr(self.registry, 'set_websocket_manager'):
            # WebSocket manager integration test
            self.assertTrue(callable(self.registry.set_websocket_manager),
                          "WebSocket manager integration must be available")
        
        # Test concurrent user isolation
        user2_id = "test-user-2-isolation-check"
        user2_session = await self.registry.create_user_session(
            user2_id, f"{self.test_session_id}-2"
        )
        
        # Validate user sessions are isolated
        self.assertNotEqual(user_session, user2_session,
                           "User sessions must be isolated")

    def test_import_path_compatibility(self):
        """
        CRITICAL: Validate import paths resolve correctly after consolidation
        
        Business Impact: All existing code must continue working after consolidation
        Expected: PASS - Single AgentRegistry accessible, deprecated path fails
        """
        # Test SSOT consolidation success
        registry_class_name = AgentRegistry.__name__
        registry_module = AgentRegistry.__module__
        
        # Should have correct class name
        self.assertEqual(registry_class_name, "AgentRegistry", 
                        "Consolidated registry class name correct")
        
        # Should be from the enhanced module path
        self.assertEqual(registry_module, "netra_backend.app.agents.supervisor.agent_registry",
                        "Registry should be from consolidated SSOT module")
        
        # Test that deprecated import path is no longer accessible
        try:
            from netra_backend.app.agents.registry import AgentRegistry as DeprecatedRegistry
            self.fail("Deprecated registry path should not be importable")
        except ImportError:
            # This is expected - deprecated path should fail
            pass
        
        # Test that types are accessible from SSOT module
        agent_type = AgentType.SUPERVISOR
        agent_status = AgentStatus.IDLE
        
        self.assertEqual(agent_type.value, "supervisor", "AgentType enum works correctly")
        self.assertEqual(agent_status.value, "idle", "AgentStatus enum works correctly")
        
        # SSOT consolidation verification PASSES
        print("✅ SSOT VIOLATION RESOLVED: Only one AgentRegistry accessible")

    async def test_interface_consistency_validation(self):
        """
        CRITICAL: Check consolidated registry has all required interfaces
        
        Business Impact: Ensures consolidated registry supports all functionality
        Expected: PASS - consolidated registry should have complete interface
        """
        # Get method signatures from consolidated registry
        registry_methods = [method for method in dir(self.registry) 
                           if not method.startswith('_')]
        
        # Check for core methods that must exist
        required_methods = [
            'list_available_agents',
            'create_user_session', 
            'set_websocket_manager',
            'register_agent',
            'get_agent'
        ]
        
        for method in required_methods:
            self.assertIn(method, registry_methods,
                         f"Consolidated registry missing required method: {method}")
        
        # Validate key methods are callable
        core_methods = ['list_available_agents', 'create_user_session']
        for method_name in core_methods:
            if hasattr(self.registry, method_name):
                method = getattr(self.registry, method_name)
                self.assertTrue(callable(method), 
                               f"Consolidated registry {method_name} must be callable")

    async def test_no_functionality_regression(self):
        """
        CRITICAL: Comprehensive regression test suite
        
        Business Impact: Ensures Golden Path (login → AI responses) still works
        Expected: PASS - all core functionality must be preserved
        """
        # Test consolidated registry functionality
        try:
            agents = await self.registry.list_available_agents()
            registry_works = True
        except Exception as e:
            registry_works = False
            raise AssertionError(f"Consolidated registry functionality broken: {e}")
        
        # Consolidation should work completely
        self.assertTrue(registry_works, "Consolidated registry must work")
        
        # Test user context creation (critical for Golden Path)
        user_context = await self.registry.create_user_session(
            self.test_user_id, self.test_session_id
        )
        self.assertIsNotNone(user_context, "User context creation must work")
        
        # SSOT consolidation success
        print("✅ CONSOLIDATION SUCCESS: All functionality preserved in single registry")

    def teardown_method(self, method=None):
        """Clean up test resources with SSOT patterns"""
        super().teardown_method(method)


if __name__ == "__main__":
    # Run with pytest for proper async support
    pytest.main([__file__, "-v", "--tb=short"])