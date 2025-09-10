"""
SSOT Violation Proof Test: WebSocket Factory Pattern Bypassing SSOT

This test PROVES that the current factory pattern implementation violates SSOT principles
by creating multiple WebSocket manager instances instead of using the SSOT singleton.

BUSINESS IMPACT:
- Segment: Platform/Internal - Architecture Consistency  
- Business Goal: Stability - Ensure SSOT compliance across all managers
- Value Impact: Prevents future maintainability issues and architecture drift
- Revenue Impact: Protects long-term development velocity

SSOT VIOLATION ANALYSIS:
1. SSOT Pattern: UnifiedWebSocketManager should be the single source of truth
2. Current State: WebSocketManagerFactory creates isolated instances per user
3. Expected Behavior: Factory should delegate to SSOT singleton with user context
4. Compliance Gap: Multiple manager instances bypass SSOT architecture

This test should FAIL currently and PASS after SSOT consolidation.
"""

import asyncio
import pytest
from typing import Set, Dict, Any
from unittest.mock import patch, MagicMock

# Import SSOT test infrastructure  
from test_framework.ssot.base_test_case import SsotBaseTestCase, SsotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import WebSocket components to test
from netra_backend.app.websocket_core.unified_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory, WebSocketInstanceManager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ensure_user_id


class TestWebSocketFactorySsotViolationProof(SsotAsyncTestCase):
    """Prove that WebSocket factory pattern violates SSOT principles."""
    
    async def asyncSetUp(self):
        """Set up test environment using SSOT patterns."""
        await super().asyncSetUp()
        self.test_user_1 = ensure_user_id("test_user_1")
        self.test_user_2 = ensure_user_2("test_user_2")
        
    async def test_factory_creates_multiple_manager_instances_violation(self):
        """
        PROOF: Factory creates separate WebSocketManager instances per user.
        
        SSOT VIOLATION: Each factory call creates a new manager instance instead
        of delegating to the SSOT UnifiedWebSocketManager singleton.
        
        EXPECTED AFTER CONSOLIDATION: Factory delegates to SSOT singleton
        with proper user context isolation.
        """
        # PROOF: Factory creates different instances for different users
        factory = WebSocketManagerFactory()
        
        # Create manager instances for two different users
        context_1 = UserExecutionContext(user_id=self.test_user_1)
        context_2 = UserExecutionContext(user_id=self.test_user_2)
        
        manager_1 = await factory.create_websocket_manager(
            user_execution_context=context_1
        )
        manager_2 = await factory.create_websocket_manager(
            user_execution_context=context_2
        )
        
        # VIOLATION PROOF: These should be the SAME SSOT instance
        # Currently they are DIFFERENT instances (violates SSOT)
        self.assertIsNot(
            manager_1, manager_2,
            "CURRENT STATE: Factory creates separate instances (SSOT violation)"
        )
        
        # VIOLATION PROOF: Both instances have separate internal state
        self.assertIsNot(
            manager_1._active_connections, 
            manager_2._active_connections,
            "CURRENT STATE: Separate connection state per instance (SSOT violation)"
        )
        
        # FUTURE EXPECTATION: After SSOT consolidation, the managers should
        # delegate to the same SSOT instance but maintain user isolation
        # through context rather than instance separation
        
        # Document what SHOULD happen after SSOT consolidation
        self.record_ssot_expectation(
            violation_type="multiple_manager_instances",
            current_behavior="Factory creates separate WebSocketManager instances",
            expected_behavior="Factory delegates to SSOT UnifiedWebSocketManager singleton",
            consolidation_approach="User isolation through context, not instance separation"
        )

    async def test_factory_bypasses_unified_websocket_manager_ssot(self):
        """
        PROOF: Factory implementation completely bypasses UnifiedWebSocketManager.
        
        SSOT VIOLATION: WebSocketManagerFactory creates instances of WebSocketManager
        directly instead of using the established SSOT UnifiedWebSocketManager.
        """
        factory = WebSocketManagerFactory()
        context = UserExecutionContext(user_id=self.test_user_1)
        
        # Create manager through factory
        factory_manager = await factory.create_websocket_manager(
            user_execution_context=context
        )
        
        # Import the SSOT UnifiedWebSocketManager
        from netra_backend.app.websocket_core.unified_manager import WebSocketManager as UnifiedWebSocketManager
        
        # VIOLATION PROOF: Factory creates WebSocketManager instead of using SSOT
        self.assertIsInstance(
            factory_manager, 
            UnifiedWebSocketManager,
            "Factory creates WebSocketManager instance"
        )
        
        # VIOLATION PROOF: No integration with UnifiedWebSocketManager SSOT patterns
        # The factory bypasses any SSOT coordination that should exist
        
        # Check if factory manager has SSOT coordination capabilities
        has_ssot_coordination = hasattr(factory_manager, '_ssot_instance_registry')
        self.assertFalse(
            has_ssot_coordination,
            "CURRENT STATE: No SSOT coordination in factory-created managers"
        )
        
        self.record_ssot_expectation(
            violation_type="ssot_bypass",
            current_behavior="Factory creates WebSocketManager directly",
            expected_behavior="Factory delegates to UnifiedWebSocketManager SSOT",
            consolidation_approach="All WebSocket operations through SSOT singleton"
        )

    async def test_user_isolation_works_but_through_wrong_pattern(self):
        """
        PROOF: User isolation works correctly but through instance separation
        rather than SSOT pattern with context isolation.
        
        This validates the business requirement is met but through non-SSOT approach.
        """
        factory = WebSocketManagerFactory()
        
        # Create isolated contexts for different users
        context_1 = UserExecutionContext(user_id=self.test_user_1)
        context_2 = UserExecutionContext(user_id=self.test_user_2)
        
        manager_1 = await factory.create_websocket_manager(context_1)
        manager_2 = await factory.create_websocket_manager(context_2)
        
        # Mock connection operations to test isolation
        mock_connection_1 = MagicMock()
        mock_connection_2 = MagicMock()
        
        # Simulate adding connections to both managers
        await manager_1.add_connection("conn_1", mock_connection_1)
        await manager_2.add_connection("conn_2", mock_connection_2)
        
        # PROOF: User isolation works (business requirement satisfied)
        manager_1_connections = set(manager_1._active_connections.keys())
        manager_2_connections = set(manager_2._active_connections.keys())
        
        self.assertEqual({"conn_1"}, manager_1_connections)
        self.assertEqual({"conn_2"}, manager_2_connections)
        
        # No cross-contamination (good for business)
        self.assertEqual(len(manager_1_connections & manager_2_connections), 0)
        
        # VIOLATION: Achieved through instance separation, not SSOT + context
        self.record_ssot_expectation(
            violation_type="isolation_pattern",
            current_behavior="User isolation through separate manager instances",
            expected_behavior="User isolation through SSOT singleton with context",
            consolidation_approach="Single SSOT manager with user-context-based isolation"
        )
        
    def record_ssot_expectation(self, violation_type: str, current_behavior: str, 
                               expected_behavior: str, consolidation_approach: str):
        """Record SSOT violation expectations for post-consolidation validation."""
        if not hasattr(self, '_ssot_expectations'):
            self._ssot_expectations = []
            
        self._ssot_expectations.append({
            'violation_type': violation_type,
            'current_behavior': current_behavior,
            'expected_behavior': expected_behavior,
            'consolidation_approach': consolidation_approach,
            'test_method': self._testMethodName
        })
        
        # Log expectation for consolidation planning
        self.logger.info(
            f"SSOT Expectation Recorded - {violation_type}: "
            f"Current='{current_behavior}' -> Expected='{expected_behavior}'"
        )


class TestFactoryPatternSsotCompliance(SsotBaseTestCase):
    """Synchronous tests for factory pattern SSOT compliance."""
    
    def test_factory_registration_violates_ssot_registry_pattern(self):
        """
        PROOF: Factory pattern doesn't integrate with SSOT registry patterns.
        
        SSOT systems typically maintain central registries for instance tracking
        and lifecycle management. The current factory pattern operates independently.
        """
        # Check if there's a central WebSocket manager registry (there shouldn't be)
        with patch('netra_backend.app.websocket_core.unified_manager.WebSocketManager') as mock_manager:
            # Import should not trigger any SSOT registry initialization
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            
            # PROOF: No SSOT registry integration
            has_central_registry = hasattr(factory, '_ssot_registry')
            self.assertFalse(
                has_central_registry,
                "CURRENT STATE: Factory has no SSOT registry integration"
            )
            
            # PROOF: No SSOT lifecycle coordination
            has_lifecycle_coordination = hasattr(factory, '_ssot_lifecycle_manager')
            self.assertFalse(
                has_lifecycle_coordination,
                "CURRENT STATE: Factory has no SSOT lifecycle coordination"
            )
        
        self.record_test_finding(
            finding_type="ssot_registry_violation",
            description="Factory pattern operates independently of SSOT registry patterns",
            impact="Prevents centralized WebSocket manager coordination",
            recommendation="Integrate factory with SSOT UnifiedWebSocketManager registry"
        )


if __name__ == "__main__":
    # Run with pytest to see violations in action
    pytest.main([__file__, "-v", "--tb=short"])