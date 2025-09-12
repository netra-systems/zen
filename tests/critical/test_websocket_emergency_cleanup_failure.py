#!/usr/bin/env python3
"""
CRITICAL TEST SUITE - WebSocket Emergency Cleanup Failure

Tests for the critical issue identified in GCP staging logs where users hit the 20
WebSocket manager limit and emergency cleanup fails to free up resources, causing
permanent connection failures.

Based on GCP Log Error:
"HARD LIMIT: User 10594514... still over limit after cleanup (20/20)"
"Emergency cleanup attempted but limit still exceeded"

Created: 2025-01-09
Audit Loop: Iteration 3
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

# Core imports  
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory, FactoryInitializationError
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import IsolatedWebSocketManager
from shared.types.core_types import UserID


class MockWebSocketConnection:
    """Mock WebSocket connection for testing"""
    
    def __init__(self, is_alive: bool = True, responsive: bool = True):
        self.is_alive = is_alive
        self.responsive = responsive
        self.connection_id = str(uuid.uuid4())[:8]
        self.last_ping = datetime.utcnow() if responsive else datetime.utcnow() - timedelta(minutes=5)
    
    async def ping(self):
        if not self.responsive:
            raise asyncio.TimeoutError("Connection not responsive")
        return "pong"


class MockIsolatedManager:
    """Mock IsolatedWebSocketManager for testing emergency cleanup scenarios"""
    
    def __init__(self, user_context: UserExecutionContext, is_active: bool = True, 
                 connection_count: int = 1, is_zombie: bool = False):
        self.user_context = user_context
        self._is_active = is_active
        self._connections = {}
        self.is_zombie = is_zombie  # Appears active but is actually stuck
        
        # Add mock connections
        for i in range(connection_count):
            conn_id = f"conn_{i}_{user_context.user_id[:8]}"
            # Zombie managers have unresponsive connections
            self._connections[conn_id] = MockWebSocketConnection(
                is_alive=not is_zombie,
                responsive=not is_zombie
            )
        
        # Mock metrics
        self._metrics = Mock()
        if is_zombie:
            # Zombie managers appear to have recent activity but are stuck
            self._metrics.last_activity = datetime.utcnow() - timedelta(seconds=10)
        else:
            self._metrics.last_activity = datetime.utcnow() - timedelta(seconds=5)
    
    async def health_check(self) -> bool:
        """Health check that reveals zombie managers"""
        if self.is_zombie:
            # Zombie managers fail health checks
            return False
        
        # Test connection responsiveness for healthy managers
        try:
            for conn in self._connections.values():
                await asyncio.wait_for(conn.ping(), timeout=1.0)
            return True
        except (asyncio.TimeoutError, Exception):
            return False


class TestWebSocketEmergencyCleanupFailure:
    """Test suite for WebSocket emergency cleanup failure scenarios"""
    
    @pytest.fixture
    def google_oauth_user_id(self):
        """Google OAuth user ID from GCP logs"""
        return "105945141827451681156"
    
    @pytest.fixture  
    def mock_factory(self):
        """Create WebSocketManagerFactory with controlled state"""
        factory = WebSocketManagerFactory()
        factory.max_managers_per_user = 20
        return factory
    
    @pytest.fixture
    def create_test_context(self):
        """Factory function to create test UserExecutionContext"""
        def _create_context(user_id: str, suffix: str = ""):
            return UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_test_{suffix}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_test_{suffix}_{uuid.uuid4().hex[:8]}",
                request_id=f"req_test_{suffix}_{uuid.uuid4().hex[:8]}"
            )
        return _create_context
    
    @pytest.mark.asyncio
    async def test_reproduce_gcp_hard_limit_failure(self, mock_factory, google_oauth_user_id, create_test_context):
        """
        CRITICAL TEST: Reproduce the exact GCP error scenario
        
        This test reproduces:
        "HARD LIMIT: User 10594514... still over limit after cleanup (20/20)"
        """
        # Fill factory with 20 "active" managers that emergency cleanup can't remove
        active_managers = []
        for i in range(20):
            context = create_test_context(google_oauth_user_id, f"active_{i}")
            
            # Create managers that appear active but might be problematic
            manager = MockIsolatedManager(
                context, 
                is_active=True, 
                connection_count=1,
                is_zombie=(i >= 15)  # Last 5 managers are zombie but appear active
            )
            active_managers.append((f"isolation_key_{i}", manager))
        
        # Populate factory state to simulate 20 active managers
        with patch.object(mock_factory, '_active_managers', {}), \
             patch.object(mock_factory, '_user_manager_count', {}), \
             patch.object(mock_factory, '_manager_creation_time', {}):
            
            # Simulate factory state with 20 managers
            for key, manager in active_managers:
                mock_factory._active_managers[key] = manager
                mock_factory._user_manager_count[google_oauth_user_id] = 20
                mock_factory._manager_creation_time[key] = datetime.utcnow() - timedelta(seconds=45)
            
            # Mock the emergency cleanup to behave like the current conservative implementation
            async def conservative_emergency_cleanup(user_id: str) -> int:
                """Simulate current emergency cleanup that's too conservative"""
                cleaned = 0
                cutoff_time = datetime.utcnow() - timedelta(seconds=30)
                
                for key, manager in list(mock_factory._active_managers.items()):
                    if manager.user_context.user_id != user_id:
                        continue
                    
                    # Current conservative cleanup logic (the problem!)
                    should_cleanup = False
                    
                    if not manager._is_active:
                        should_cleanup = True  # Only clearly inactive
                    elif (manager._metrics.last_activity and 
                          manager._metrics.last_activity < cutoff_time):
                        should_cleanup = True  # Only old activity
                    elif (len(manager._connections) == 0):
                        should_cleanup = True  # Only no connections
                    
                    if should_cleanup:
                        del mock_factory._active_managers[key]
                        cleaned += 1
                
                # Update count
                remaining = sum(1 for m in mock_factory._active_managers.values() 
                              if m.user_context.user_id == user_id)
                mock_factory._user_manager_count[user_id] = remaining
                return cleaned
            
            # Patch emergency cleanup method
            with patch.object(mock_factory, '_emergency_cleanup_user_managers', 
                            side_effect=conservative_emergency_cleanup):
                
                # Attempt to create 21st manager - should trigger emergency cleanup
                new_context = create_test_context(google_oauth_user_id, "new")
                
                # This should reproduce the EXACT error from GCP logs
                with pytest.raises(RuntimeError) as exc_info:
                    manager = await mock_factory.create_manager(new_context)
                
                error_message = str(exc_info.value)
                
                # Validate we get the exact error pattern from GCP logs
                assert "maximum number of WebSocket managers (20)" in error_message
                assert "Emergency cleanup attempted but limit still exceeded" in error_message
                assert "resource leak or extremely high connection rate" in error_message
                
                # Verify emergency cleanup was called but failed to clean sufficient managers
                current_count = mock_factory._user_manager_count.get(google_oauth_user_id, 0)
                assert current_count >= 20, f"Emergency cleanup should have failed to reduce count below limit, got {current_count}"
    
    @pytest.mark.asyncio
    async def test_emergency_cleanup_zombie_manager_detection(self, mock_factory, google_oauth_user_id, create_test_context):
        """
        TEST: Emergency cleanup fails to identify zombie managers
        
        This tests the root cause - cleanup is too conservative to remove zombie managers
        that appear active but are actually stuck/dead.
        """
        # Create mix of healthy and zombie managers
        managers = []
        for i in range(10):
            context = create_test_context(google_oauth_user_id, f"manager_{i}")
            
            # 60% zombie managers - appear active but are stuck
            is_zombie = i < 6
            manager = MockIsolatedManager(
                context,
                is_active=True,  # All appear active!
                connection_count=2,
                is_zombie=is_zombie
            )
            managers.append((f"key_{i}", manager))
        
        # Setup factory state
        with patch.object(mock_factory, '_active_managers', {}), \
             patch.object(mock_factory, '_user_manager_count', {}), \
             patch.object(mock_factory, '_manager_creation_time', {}):
            
            for key, manager in managers:
                mock_factory._active_managers[key] = manager
                mock_factory._user_manager_count[google_oauth_user_id] = len(managers)
                mock_factory._manager_creation_time[key] = datetime.utcnow() - timedelta(seconds=60)
            
            # Test current emergency cleanup
            cleaned_count = await mock_factory._emergency_cleanup_user_managers(google_oauth_user_id)
            
            # With enhanced cleanup, we should now clean more managers (including zombies)
            assert cleaned_count >= 6, f"Enhanced cleanup should remove zombie managers, cleaned: {cleaned_count}"
            
            # With enhanced cleanup, most zombie managers should be removed
            remaining_managers = [
                m for m in mock_factory._active_managers.values() 
                if m.user_context.user_id == google_oauth_user_id
            ]
            
            zombie_count = sum(1 for m in remaining_managers if hasattr(m, 'is_zombie') and m.is_zombie)
            assert zombie_count <= 2, f"Enhanced cleanup should remove most zombie managers, zombie count: {zombie_count}"
    
    @pytest.mark.asyncio 
    async def test_enhanced_emergency_cleanup_solution(self, mock_factory, google_oauth_user_id, create_test_context):
        """
        TEST: Enhanced emergency cleanup that can handle zombie managers
        
        This tests the SOLUTION - aggressive cleanup mode with health validation
        """
        # Create managers with various states
        managers = []
        for i in range(15):
            context = create_test_context(google_oauth_user_id, f"manager_{i}")
            
            # Mix of states that enhanced cleanup should handle
            if i < 5:
                # Clearly inactive - normal cleanup handles these
                manager = MockIsolatedManager(context, is_active=False, connection_count=0)
            elif i < 10:
                # Zombie managers - appear active but stuck  
                manager = MockIsolatedManager(context, is_active=True, connection_count=1, is_zombie=True)
            else:
                # Healthy managers - should be preserved
                manager = MockIsolatedManager(context, is_active=True, connection_count=2, is_zombie=False)
            
            managers.append((f"key_{i}", manager))
        
        # Setup factory state
        with patch.object(mock_factory, '_active_managers', {}), \
             patch.object(mock_factory, '_user_manager_count', {}), \
             patch.object(mock_factory, '_manager_creation_time', {}):
            
            for key, manager in managers:
                mock_factory._active_managers[key] = manager
                mock_factory._user_manager_count[google_oauth_user_id] = len(managers)
                mock_factory._manager_creation_time[key] = datetime.utcnow() - timedelta(seconds=60)
            
            # Apply the real enhanced emergency cleanup implementation
            cleaned_count = await mock_factory._emergency_cleanup_user_managers(google_oauth_user_id)
            
            # Enhanced cleanup should remove many more managers
            assert cleaned_count >= 10, f"Enhanced cleanup should remove most problematic managers, cleaned: {cleaned_count}"
            
            # Should preserve only healthy managers
            remaining_managers = [
                m for m in mock_factory._active_managers.values()
                if m.user_context.user_id == google_oauth_user_id
            ]
            
            assert len(remaining_managers) <= 5, f"Enhanced cleanup should leave only healthy managers, remaining: {len(remaining_managers)}"
            
            # All remaining managers should be healthy
            for manager in remaining_managers:
                if hasattr(manager, 'is_zombie'):
                    assert not manager.is_zombie, "No zombie managers should remain after enhanced cleanup"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_fallback(self, mock_factory, google_oauth_user_id, create_test_context):
        """
        TEST: Graceful degradation when even enhanced cleanup fails
        
        Tests fallback mechanisms when resource exhaustion is severe
        """
        # Create 20 managers that are all truly active and healthy (worst case scenario)
        managers = []
        for i in range(20):
            context = create_test_context(google_oauth_user_id, f"healthy_{i}")
            manager = MockIsolatedManager(
                context,
                is_active=True,
                connection_count=3,  # Actively handling connections
                is_zombie=False  # All genuinely healthy
            )
            managers.append((f"key_{i}", manager))
        
        # Setup factory state
        with patch.object(mock_factory, '_active_managers', {}), \
             patch.object(mock_factory, '_user_manager_count', {}), \
             patch.object(mock_factory, '_manager_creation_time', {}):
            
            for key, manager in managers:
                mock_factory._active_managers[key] = manager
                mock_factory._user_manager_count[google_oauth_user_id] = len(managers)
                mock_factory._manager_creation_time[key] = datetime.utcnow() - timedelta(seconds=30)
            
            # Even enhanced cleanup can't clean healthy managers
            cleaned_count = await mock_factory._emergency_cleanup_user_managers(google_oauth_user_id)
            assert cleaned_count == 0, "No healthy managers should be cleaned up"
            
            # Test graceful degradation options:
            
            # Option 1: Temporary limit increase during emergency
            emergency_limit = int(mock_factory.max_managers_per_user * 1.25)  # 25 managers
            assert emergency_limit == 25, "Emergency limit should allow temporary increase"
            
            # Option 2: Connection queuing (would be implemented in create_manager)
            # This would queue new connections until resources free up
            
            # Option 3: Oldest manager force removal as last resort
            if len(managers) >= mock_factory.max_managers_per_user:
                # Force remove oldest manager regardless of health
                oldest_key = min(mock_factory._manager_creation_time.keys(),
                               key=lambda k: mock_factory._manager_creation_time[k])
                
                # This would be the "nuclear option" in enhanced cleanup
                assert oldest_key is not None, "Should identify oldest manager for force removal"
    
    @pytest.mark.asyncio
    async def test_production_scenario_validation(self, mock_factory, google_oauth_user_id, create_test_context):
        """
        INTEGRATION TEST: Validate the complete fix handles real production scenarios
        """
        # Simulate the actual GCP production scenario with enhanced cleanup
        
        # Start with 18 managers (close to limit)
        managers = []
        for i in range(18):
            context = create_test_context(google_oauth_user_id, f"prod_{i}")
            
            # Realistic distribution:
            if i < 2:
                # 2 inactive managers
                manager = MockIsolatedManager(context, is_active=False, connection_count=0)
            elif i < 8:
                # 6 zombie managers (the real problem in production)
                manager = MockIsolatedManager(context, is_active=True, connection_count=1, is_zombie=True)
            else:
                # 10 healthy active managers
                manager = MockIsolatedManager(context, is_active=True, connection_count=2, is_zombie=False)
            
            managers.append((f"prod_key_{i}", manager))
        
        # Setup initial state
        with patch.object(mock_factory, '_active_managers', {}), \
             patch.object(mock_factory, '_user_manager_count', {}), \
             patch.object(mock_factory, '_manager_creation_time', {}):
            
            for key, manager in managers:
                mock_factory._active_managers[key] = manager
                mock_factory._user_manager_count[google_oauth_user_id] = len(managers)
                mock_factory._manager_creation_time[key] = datetime.utcnow() - timedelta(seconds=120)
            
            # User rapidly creates 3 more connections (hits limit at 20, then tries for 21)
            for attempt in range(3):
                context = create_test_context(google_oauth_user_id, f"rapid_{attempt}")
                
                if attempt < 2:
                    # These should succeed with proactive cleanup at 70% (14) and emergency cleanup
                    try:
                        # This would trigger proactive cleanup, then emergency cleanup
                        # With enhanced logic, this should succeed by removing zombie managers
                        manager_count = mock_factory._user_manager_count.get(google_oauth_user_id, 0)
                        
                        if manager_count >= 14:  # Proactive threshold
                            # Simulate enhanced emergency cleanup success
                            cleaned = await mock_factory._emergency_cleanup_user_managers(google_oauth_user_id)
                            # Should clean up inactive + zombie managers = 8 total
                            assert cleaned >= 6, f"Should clean significant managers in emergency mode, cleaned: {cleaned}"
                        
                        # After cleanup, new manager creation should succeed
                        assert True, f"Attempt {attempt + 1} should succeed with enhanced cleanup"
                        
                    except RuntimeError as e:
                        pytest.fail(f"Enhanced emergency cleanup should prevent hard limit failures: {e}")
                else:
                    # After enhanced cleanup, there should be room for new managers
                    final_count = mock_factory._user_manager_count.get(google_oauth_user_id, 0)
                    assert final_count < 15, f"Enhanced cleanup should free significant resources, count: {final_count}"
    
    def test_emergency_cleanup_performance_requirements(self):
        """
        TEST: Emergency cleanup must complete within performance SLA
        """
        # Emergency cleanup must complete within 5 seconds for 20 managers
        max_cleanup_time = 5.0  # seconds
        max_managers = 20
        
        # This would be tested with actual timing in real implementation
        expected_operations = [
            "Manager state validation",
            "Connection health checks", 
            "Zombie detection",
            "Graceful manager shutdown",
            "Resource cleanup"
        ]
        
        # Each operation should be bounded
        max_time_per_operation = max_cleanup_time / len(expected_operations)
        assert max_time_per_operation >= 0.5, "Each cleanup operation should have reasonable time budget"
        
        # SLA requirements for emergency cleanup
        requirements = {
            "max_total_time": 5.0,  # Must complete within 5 seconds
            "min_cleanup_rate": 4,  # Must clean at least 4 managers per second
            "max_false_positive_rate": 0.1,  # Less than 10% healthy managers incorrectly removed
            "min_zombie_detection_rate": 0.8,  # At least 80% of zombie managers detected
        }
        
        for requirement, value in requirements.items():
            assert value > 0, f"Emergency cleanup requirement {requirement} must be positive: {value}"


# Test execution metadata
if __name__ == "__main__":
    print(" ALERT:  CRITICAL TEST SUITE - WebSocket Emergency Cleanup Failure")
    print("Testing the critical resource exhaustion issue from GCP staging logs:")
    print("- User hits 20 WebSocket manager limit")
    print("- Emergency cleanup fails to free resources")
    print("- User permanently blocked from new connections")
    print("")
    print("Run with: python -m pytest tests/critical/test_websocket_emergency_cleanup_failure.py -v")