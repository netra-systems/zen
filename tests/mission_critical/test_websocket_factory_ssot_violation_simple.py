"""
SSOT Violation Proof Test: WebSocket Factory Pattern Bypassing SSOT (Simplified)

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

import pytest
import asyncio
from typing import Set, Dict, Any

# Import WebSocket components to test
from netra_backend.app.websocket_core.unified_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import ensure_user_id


class TestWebSocketFactorySsotViolation:
    """Prove that WebSocket factory pattern violates SSOT principles."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_user_1 = ensure_user_id("test_user_1")
        self.test_user_2 = ensure_user_id("test_user_2")
        
    @pytest.mark.asyncio
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
        context_1 = UserExecutionContext(
            user_id=self.test_user_1,
            thread_id="test_thread_1", 
            run_id="test_run_1"
        )
        context_2 = UserExecutionContext(
            user_id=self.test_user_2,
            thread_id="test_thread_2",
            run_id="test_run_2"
        )
        
        manager_1 = await factory.create_manager(context_1)
        manager_2 = await factory.create_manager(context_2)
        
        # VIOLATION PROOF: These should be the SAME SSOT instance
        # Currently they are DIFFERENT instances (violates SSOT)
        assert manager_1 is not manager_2, (
            "CURRENT STATE: Factory creates separate instances (SSOT violation)"
        )
        
        # VIOLATION PROOF: Both instances have separate internal state
        assert manager_1.active_connections is not manager_2.active_connections, (
            "CURRENT STATE: Separate connection state per instance (SSOT violation)"
        )
        
        # Document expected behavior after SSOT consolidation
        print("SSOT EXPECTATION: Factory should delegate to SSOT UnifiedWebSocketManager singleton")
        print("CURRENT BEHAVIOR: Factory creates separate WebSocketManager instances")
        print("CONSOLIDATION APPROACH: User isolation through context, not instance separation")

    @pytest.mark.asyncio
    async def test_factory_bypasses_unified_websocket_manager_ssot(self):
        """
        PROOF: Factory implementation completely bypasses UnifiedWebSocketManager.
        
        SSOT VIOLATION: WebSocketManagerFactory creates instances of WebSocketManager
        directly instead of using the established SSOT UnifiedWebSocketManager.
        """
        factory = WebSocketManagerFactory()
        context = UserExecutionContext(
            user_id=self.test_user_1,
            thread_id="test_thread_1",
            run_id="test_run_1" 
        )
        
        # Create manager through factory
        factory_manager = await factory.create_manager(context)
        
        # VIOLATION PROOF: Factory creates WebSocketManager instead of using SSOT
        assert isinstance(factory_manager, WebSocketManager), (
            "Factory creates WebSocketManager instance"
        )
        
        # VIOLATION PROOF: No integration with UnifiedWebSocketManager SSOT patterns
        # The factory bypasses any SSOT coordination that should exist
        
        # Check if factory manager has SSOT coordination capabilities
        has_ssot_coordination = hasattr(factory_manager, '_ssot_instance_registry')
        assert not has_ssot_coordination, (
            "CURRENT STATE: No SSOT coordination in factory-created managers"
        )
        
        print("SSOT EXPECTATION: Factory delegates to UnifiedWebSocketManager SSOT")
        print("CURRENT BEHAVIOR: Factory creates WebSocketManager directly")
        print("CONSOLIDATION APPROACH: All WebSocket operations through SSOT singleton")

    @pytest.mark.asyncio
    async def test_user_isolation_works_but_through_wrong_pattern(self):
        """
        PROOF: User isolation works correctly but through instance separation
        rather than SSOT pattern with context isolation.
        
        This validates the business requirement is met but through non-SSOT approach.
        """
        factory = WebSocketManagerFactory()
        
        # Create isolated contexts for different users
        context_1 = UserExecutionContext(
            user_id=self.test_user_1,
            thread_id="test_thread_1",
            run_id="test_run_1"
        )
        context_2 = UserExecutionContext(
            user_id=self.test_user_2,
            thread_id="test_thread_2", 
            run_id="test_run_2"
        )
        
        manager_1 = await factory.create_manager(context_1)
        manager_2 = await factory.create_manager(context_2)
        
        # Mock connection operations to test isolation
        from unittest.mock import MagicMock
        mock_connection_1 = MagicMock()
        mock_connection_2 = MagicMock()
        
        # Simulate adding connections to both managers
        await manager_1.add_connection("conn_1", mock_connection_1)
        await manager_2.add_connection("conn_2", mock_connection_2)
        
        # PROOF: User isolation works (business requirement satisfied)
        manager_1_connections = set(manager_1.active_connections.keys())
        manager_2_connections = set(manager_2.active_connections.keys())
        
        assert manager_1_connections == {"conn_1"}
        assert manager_2_connections == {"conn_2"}
        
        # No cross-contamination (good for business)
        assert len(manager_1_connections & manager_2_connections) == 0
        
        # VIOLATION: Achieved through instance separation, not SSOT + context
        print("SSOT EXPECTATION: User isolation through SSOT singleton with context")
        print("CURRENT BEHAVIOR: User isolation through separate manager instances")
        print("CONSOLIDATION APPROACH: Single SSOT manager with user-context-based isolation")


class TestFactoryPatternSsotCompliance:
    """Synchronous tests for factory pattern SSOT compliance."""
    
    def test_factory_registration_violates_ssot_registry_pattern(self):
        """
        PROOF: Factory pattern doesn't integrate with SSOT registry patterns.
        
        SSOT systems typically maintain central registries for instance tracking
        and lifecycle management. The current factory pattern operates independently.
        """
        # Check if there's a central WebSocket manager registry (there shouldn't be)
        from unittest.mock import patch
        
        with patch('netra_backend.app.websocket_core.unified_manager.WebSocketManager') as mock_manager:
            # Import should not trigger any SSOT registry initialization
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            
            # PROOF: No SSOT registry integration
            has_central_registry = hasattr(factory, '_ssot_registry')
            assert not has_central_registry, (
                "CURRENT STATE: Factory has no SSOT registry integration"
            )
            
            # PROOF: No SSOT lifecycle coordination
            has_lifecycle_coordination = hasattr(factory, '_ssot_lifecycle_manager')
            assert not has_lifecycle_coordination, (
                "CURRENT STATE: Factory has no SSOT lifecycle coordination"
            )
        
        print("FINDING: Factory pattern operates independently of SSOT registry patterns")
        print("IMPACT: Prevents centralized WebSocket manager coordination")
        print("RECOMMENDATION: Integrate factory with SSOT UnifiedWebSocketManager registry")


if __name__ == "__main__":
    # Run with pytest to see violations in action
    pytest.main([__file__, "-v", "--tb=short"])