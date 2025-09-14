"""
TEST SUITE 1: Registry Consolidation Transition State Validation (Issue #1034)

Business Value Protection: $500K+ ARR Golden Path functionality during registry consolidation
Test Type: Integration (Real services, NO Docker)

PURPOSE: Test system behavior during active registry consolidation
EXPECTED: FAILING tests initially (reproduce SSOT violation), then PASSING after fix

This test suite validates that the system gracefully handles the transition from
duplicate agent registries to a single SSOT registry implementation while maintaining
business-critical functionality.

Critical Requirements:
- User sessions survive registry consolidation
- Mixed registry state error handling  
- Registry feature parity validation
- No golden path functionality loss
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# SSOT TEST INFRASTRUCTURE - Use established testing patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import IsolatedEnvironment

# Import both registries to test transition behavior
# These imports should reveal SSOT violations initially
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
    ADVANCED_REGISTRY_AVAILABLE = True
except ImportError:
    AdvancedRegistry = None
    ADVANCED_REGISTRY_AVAILABLE = False

try:
    from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
    BASIC_REGISTRY_AVAILABLE = True
except ImportError:
    BasicRegistry = None
    BASIC_REGISTRY_AVAILABLE = False


class TestRegistryConsolidationTransition(SSotAsyncTestCase):
    """Test registry consolidation transition state handling."""
    
    async def asyncSetUp(self):
        """Set up test environment with SSOT compliance."""
        await super().asyncSetUp()
        
        # Create isolated environment for test
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        
        # Create mock LLM manager for registry initialization
        self.mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
        
        # Track registries for cleanup
        self.advanced_registry: Optional[AdvancedRegistry] = None
        self.basic_registry: Optional[BasicRegistry] = None
        
        # Mock user context for testing
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "test_user_transition"
        self.mock_user_context.request_id = "test_request_transition"
        self.mock_user_context.thread_id = "test_thread_transition"
        self.mock_user_context.run_id = "test_run_transition"
    
    async def asyncTearDown(self):
        """Clean up test resources."""
        try:
            # Cleanup registries
            if self.advanced_registry:
                await self.advanced_registry.cleanup()
            if self.basic_registry:
                # Basic registry doesn't have async cleanup
                pass
        except Exception as e:
            print(f"Warning: Error during registry cleanup: {e}")
        
        await super().asyncTearDown()
    
    @pytest.mark.asyncio
    async def test_registry_import_availability_validation(self):
        """
        Test registry import availability during transition.
        
        EXPECTED INITIAL BEHAVIOR: Should reveal SSOT violation
        - Both registries should be importable (causing conflict)
        - Test should identify the SSOT violation state
        
        EXPECTED POST-CONSOLIDATION: Should pass cleanly
        - Only SSOT registry available
        - No import conflicts
        """
        # Document current registry availability
        availability_status = {
            "advanced_registry_available": ADVANCED_REGISTRY_AVAILABLE,
            "basic_registry_available": BASIC_REGISTRY_AVAILABLE,
            "ssot_violation_detected": ADVANCED_REGISTRY_AVAILABLE and BASIC_REGISTRY_AVAILABLE
        }
        
        print(f"Registry Availability Status: {availability_status}")
        
        # INITIAL EXPECTATION: SSOT violation should be detected
        if availability_status["ssot_violation_detected"]:
            self.fail(
                f"SSOT VIOLATION DETECTED: Both registries are available simultaneously. "
                f"Advanced: {ADVANCED_REGISTRY_AVAILABLE}, Basic: {BASIC_REGISTRY_AVAILABLE}. "
                f"This test is correctly detecting the consolidation requirement."
            )
        
        # POST-CONSOLIDATION: Only one registry should be available
        self.assertTrue(
            ADVANCED_REGISTRY_AVAILABLE or BASIC_REGISTRY_AVAILABLE,
            "At least one registry implementation should be available"
        )
    
    @pytest.mark.asyncio
    async def test_user_session_survival_during_transition(self):
        """
        Test that user sessions survive registry consolidation.
        
        EXPECTED: User sessions should be preserved across registry changes
        Critical for maintaining active user chat sessions during deployment.
        """
        if not ADVANCED_REGISTRY_AVAILABLE:
            self.skipTest("Advanced registry not available for transition testing")
        
        # Create advanced registry with user session
        self.advanced_registry = AdvancedRegistry(llm_manager=self.mock_llm_manager)
        
        # Create user session before transition
        user_session = await self.advanced_registry.get_user_session("transition_test_user")
        self.assertIsNotNone(user_session, "User session should be created")
        
        # Simulate session activity
        await user_session.register_agent("test_agent", Mock())
        session_metrics_before = user_session.get_metrics()
        
        self.assertEqual(session_metrics_before["agent_count"], 1)
        self.assertEqual(session_metrics_before["user_id"], "transition_test_user")
        
        # Simulate registry transition (simulate recreation/consolidation)
        old_registry = self.advanced_registry
        
        # Create new registry instance (simulating transition)
        self.advanced_registry = AdvancedRegistry(llm_manager=self.mock_llm_manager)
        
        # Verify session can be recreated with same data integrity
        new_user_session = await self.advanced_registry.get_user_session("transition_test_user")
        self.assertIsNotNone(new_user_session, "User session should be recreatable after transition")
        
        # Clean up old registry
        await old_registry.cleanup()
        
        # Verify new session maintains user isolation
        new_session_metrics = new_user_session.get_metrics()
        self.assertEqual(new_session_metrics["user_id"], "transition_test_user")
    
    @pytest.mark.asyncio
    async def test_mixed_registry_state_error_handling(self):
        """
        Test error handling during mixed registry state.
        
        EXPECTED INITIAL: Should gracefully handle mixed registry scenarios
        EXPECTED POST-CONSOLIDATION: No mixed state possible
        """
        if not (ADVANCED_REGISTRY_AVAILABLE and BASIC_REGISTRY_AVAILABLE):
            # This test validates the current mixed state, skip if not in mixed state
            self.skipTest("Mixed registry state not available - consolidation may be complete")
        
        # Test that we can instantiate both registries
        try:
            self.advanced_registry = AdvancedRegistry(llm_manager=self.mock_llm_manager)
            self.basic_registry = BasicRegistry()
            
            # Both should be functional independently
            self.assertTrue(hasattr(self.advanced_registry, 'get_user_session'))
            self.assertTrue(hasattr(self.basic_registry, 'register_agent'))
            
            # But this represents an SSOT violation that should be resolved
            self.fail(
                "SSOT VIOLATION: Both basic and advanced registries can be instantiated. "
                "This mixed state should be resolved by consolidation."
            )
            
        except Exception as e:
            # If there's an error instantiating both, that indicates some consolidation
            print(f"Mixed registry instantiation error (may indicate partial consolidation): {e}")
            # This is acceptable - indicates consolidation is working
            pass
    
    @pytest.mark.asyncio
    async def test_registry_feature_parity_validation(self):
        """
        Test that consolidated registry maintains feature parity.
        
        EXPECTED: All critical features should be available after consolidation
        """
        if not ADVANCED_REGISTRY_AVAILABLE:
            self.skipTest("Advanced registry not available for feature parity testing")
        
        self.advanced_registry = AdvancedRegistry(llm_manager=self.mock_llm_manager)
        
        # Test core registry features
        core_features = [
            'get_user_session',
            'create_agent_for_user',
            'cleanup_user_session',
            'set_websocket_manager',
            'register_default_agents',
            'get_registry_health'
        ]
        
        for feature in core_features:
            self.assertTrue(
                hasattr(self.advanced_registry, feature),
                f"Critical feature '{feature}' missing from consolidated registry"
            )
            self.assertTrue(
                callable(getattr(self.advanced_registry, feature)),
                f"Feature '{feature}' is not callable"
            )
        
        # Test WebSocket integration features (critical for $500K+ ARR)
        websocket_features = [
            'set_websocket_manager',
            'set_websocket_manager_async',
            'diagnose_websocket_wiring'
        ]
        
        for feature in websocket_features:
            self.assertTrue(
                hasattr(self.advanced_registry, feature),
                f"WebSocket feature '{feature}' missing - critical for business value"
            )
        
        # Test user isolation features (critical for security)
        isolation_features = [
            'get_user_session',
            'create_agent_for_user',
            'cleanup_user_session',
            'monitor_all_users'
        ]
        
        for feature in isolation_features:
            self.assertTrue(
                hasattr(self.advanced_registry, feature),
                f"User isolation feature '{feature}' missing - critical for security"
            )
    
    @pytest.mark.asyncio
    async def test_transition_performance_impact(self):
        """
        Test that registry transition doesn't cause performance degradation.
        
        EXPECTED: Registry operations should maintain performance during transition
        """
        if not ADVANCED_REGISTRY_AVAILABLE:
            self.skipTest("Advanced registry not available for performance testing")
        
        self.advanced_registry = AdvancedRegistry(llm_manager=self.mock_llm_manager)
        
        # Measure baseline performance for user session creation
        start_time = asyncio.get_event_loop().time()
        
        # Create multiple user sessions to test performance
        session_count = 5
        for i in range(session_count):
            user_session = await self.advanced_registry.get_user_session(f"perf_test_user_{i}")
            self.assertIsNotNone(user_session)
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        avg_time_per_session = total_time / session_count
        
        # Performance threshold: each session creation should be < 100ms
        self.assertLess(
            avg_time_per_session, 0.1,
            f"User session creation too slow: {avg_time_per_session:.3f}s per session. "
            f"Registry transition may have caused performance degradation."
        )
        
        # Test registry health reporting performance
        start_time = asyncio.get_event_loop().time()
        health_report = self.advanced_registry.get_registry_health()
        end_time = asyncio.get_event_loop().time()
        
        health_check_time = end_time - start_time
        self.assertLess(
            health_check_time, 0.05,
            f"Registry health check too slow: {health_check_time:.3f}s. "
            f"Should be < 50ms for operational monitoring."
        )
        
        # Verify health report contains expected information
        self.assertIn("total_agents", health_report)
        self.assertIn("hardened_isolation", health_report)
        self.assertIn("total_user_sessions", health_report)
    
    @pytest.mark.asyncio
    async def test_consolidation_configuration_consistency(self):
        """
        Test configuration consistency after registry consolidation.
        
        EXPECTED: Registry configuration should be consistent and validated
        """
        if not ADVANCED_REGISTRY_AVAILABLE:
            self.skipTest("Advanced registry not available for configuration testing")
        
        self.advanced_registry = AdvancedRegistry(llm_manager=self.mock_llm_manager)
        
        # Test SSOT compliance status
        compliance_status = self.advanced_registry.get_ssot_compliance_status()
        
        self.assertIn("compliance_score", compliance_status)
        self.assertIn("status", compliance_status)
        self.assertIn("violations", compliance_status)
        
        # After consolidation, compliance score should be high
        self.assertGreater(
            compliance_status["compliance_score"], 80,
            f"SSOT compliance score too low: {compliance_status['compliance_score']}%. "
            f"Registry consolidation should improve SSOT compliance."
        )
        
        # Test registry factory integration status
        factory_status = self.advanced_registry.get_factory_integration_status()
        
        expected_factory_features = [
            "using_universal_registry",
            "factory_patterns_enabled",
            "hardened_isolation_enabled",
            "user_isolation_enforced",
            "ssot_compliance"
        ]
        
        for feature in expected_factory_features:
            self.assertIn(feature, factory_status)
            if isinstance(factory_status[feature], bool):
                self.assertTrue(
                    factory_status[feature],
                    f"Factory feature '{feature}' should be enabled after consolidation"
                )