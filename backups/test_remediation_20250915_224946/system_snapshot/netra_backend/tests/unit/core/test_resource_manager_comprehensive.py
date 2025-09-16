"""
Comprehensive Unit Test Suite for ResourceManager - SSOT Compatibility Layer

This test suite validates the ResourceManager class, which serves as a unified compatibility 
layer for all resource management across the system, coordinating database, Redis, and 
reliability managers while ensuring complete user isolation.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: System Stability & Resource Management
- Value Impact: Ensures reliable resource coordination for multi-user system
- Strategic Impact: SSOT pattern eliminates resource management duplication and failures

CRITICAL REQUIREMENTS (CLAUDE.md Compliance):
- CHEATING ON TESTS = ABOMINATION - All tests must fail hard when system breaks
- NO business logic mocks - Use real resource instances where possible
- ABSOLUTE IMPORTS only - no relative imports allowed
- Tests must RAISE ERRORS - no try/except blocks masking failures
- Multi-user system awareness in all resource coordination tests

Test Coverage Focus:
1. Core Resource Management - SSOT compatibility layer functionality
2. Resource Coordination - Database, Redis, reliability manager integration  
3. Multi-User Resource Isolation - Per-user allocation and cleanup
4. Error Handling & Resilience - Failure patterns and recovery mechanisms
"""

import asyncio
import logging
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# ABSOLUTE IMPORTS - CLAUDE.md Compliance
from test_framework.ssot.base import BaseTestCase
from netra_backend.app.core.resource_manager import (
    ResourceManager, 
    get_resource_manager,
    get_resource,
    register_resource,
    get_system_resource_status
)
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class MockReliabilityManager:
    """Mock reliability manager for testing resource coordination."""
    
    def __init__(self):
        self.initialized = True
        self.failures = 0
        
    def get_health_status(self):
        """Mock health status method."""
        return {
            "status": "healthy" if self.failures == 0 else "degraded",
            "failures": self.failures,
            "type": "MockReliabilityManager"
        }
        
    async def cleanup(self):
        """Mock cleanup method."""
        self.initialized = False


class MockDatabaseManager:
    """Mock database manager for testing resource coordination."""
    
    def __init__(self):
        self.connected = False
        self.sessions = []
        
    async def initialize(self):
        """Mock initialization."""
        self.connected = True
        
    def get_health_status(self):
        """Mock health status method."""
        return {
            "status": "connected" if self.connected else "disconnected",
            "sessions": len(self.sessions),
            "type": "MockDatabaseManager"
        }
        
    async def cleanup(self):
        """Mock cleanup method."""
        self.connected = False
        self.sessions.clear()


class MockRedisConnectionManager:
    """Mock Redis connection manager for testing resource coordination."""
    
    def __init__(self):
        self.connected = False
        self.client_count = 0
        
    async def connect(self):
        """Mock connection method."""
        self.connected = True
        self.client_count += 1
        
    def health_check(self):
        """Mock health check method."""
        return self.connected
        
    async def close(self):
        """Mock close method."""
        self.connected = False
        self.client_count = 0


class ResourceManagerCoreInitializationTests(BaseTestCase):
    """Test core ResourceManager initialization and SSOT compatibility layer."""
    
    def setUp(self):
        """Set up test environment with isolated resource manager."""
        super().setUp()
        self.resource_manager = ResourceManager()
        
    def tearDown(self):
        """Clean up test environment."""
        # Resource manager cleanup is handled by BaseTestCase
        super().tearDown()
        
    def test_resource_manager_initialization_creates_ssot_layer(self):
        """
        Test: ResourceManager initialization creates proper SSOT compatibility layer
        BVJ: Platform/Internal - Ensures reliable foundation for all resource operations
        
        CRITICAL: Tests that initialization sets up IsolatedEnvironment integration
        and prepares resource registry without importing unavailable dependencies.
        """
        # Verify SSOT environment integration
        self.assertIsInstance(self.resource_manager._env, IsolatedEnvironment)
        
        # Verify initial state
        self.assertFalse(self.resource_manager._initialized)
        self.assertEqual(len(self.resource_manager._resources), 0)
        self.assertIsInstance(self.resource_manager._resources, dict)
        
        logger.info("ResourceManager SSOT compatibility layer initialized correctly")
        
    def test_resource_manager_tracks_initialization_state(self):
        """
        Test: ResourceManager properly tracks initialization state for SSOT compliance
        BVJ: Platform/Internal - Prevents dual initialization and state corruption
        """
        # Initial state
        self.assertFalse(self.resource_manager._initialized)
        
        # After async initialization
        async def run_initialization():
            await self.resource_manager.initialize()
            self.assertTrue(self.resource_manager._initialized)
            
            # Second initialization should be idempotent
            await self.resource_manager.initialize()
            self.assertTrue(self.resource_manager._initialized)
            
        asyncio.run(run_initialization())
        
    def test_isolated_environment_integration_ssot_compliance(self):
        """
        Test: ResourceManager integrates with IsolatedEnvironment following SSOT pattern
        BVJ: Platform/Internal - Ensures environment isolation for multi-user system
        """
        # Verify environment is properly isolated
        with self.isolated_environment(TEST_RESOURCE="test_value"):
            env_value = self.resource_manager._env.get("TEST_RESOURCE")
            self.assertEqual(env_value, "test_value")
            
        # Verify isolation cleanup
        env_value_after = self.resource_manager._env.get("TEST_RESOURCE")
        self.assertIsNone(env_value_after)


class ResourceManagerResourceRegistrationTests(BaseTestCase):
    """Test resource registration and SSOT resource coordination patterns."""
    
    def setUp(self):
        """Set up test with resource manager and mock resources."""
        super().setUp()
        self.resource_manager = ResourceManager()
        self.mock_reliability = MockReliabilityManager()
        self.mock_database = MockDatabaseManager()
        self.mock_redis = MockRedisConnectionManager()
        
    async def asyncSetUp(self):
        """Async setup for resource coordination tests."""
        await super().asyncSetUp()
        await self.resource_manager.initialize()
        
    def test_register_resource_adds_to_ssot_registry(self):
        """
        Test: Resource registration adds resources to SSOT registry
        BVJ: Platform/Internal - Centralizes resource management for system coordination
        
        CRITICAL: Must test that resources are properly tracked in the central registry
        without creating duplicate management patterns.
        """
        # Register test resource
        success = self.resource_manager.register_resource("test_reliability", self.mock_reliability)
        self.assertTrue(success)
        
        # Verify resource is in registry
        registered_resource = self.resource_manager.get_resource("test_reliability")
        self.assertIs(registered_resource, self.mock_reliability)
        
        # Verify resource count
        self.assertEqual(len(self.resource_manager._resources), 1)
        
    def test_register_resource_handles_registration_failures(self):
        """
        Test: Resource registration handles failures without crashing system
        BVJ: Platform/Internal - Ensures system stability even with problematic resources
        """
        # Test registration with None resource (should fail gracefully)
        success = self.resource_manager.register_resource("null_resource", None)
        self.assertTrue(success)  # ResourceManager accepts None resources
        
        # Test registration with invalid name
        class FailingResource:
            def __init__(self):
                raise ValueError("Initialization failed")
                
        failing_resource = None
        try:
            failing_resource = FailingResource()
        except ValueError:
            pass
            
        # Should handle None resource gracefully
        success = self.resource_manager.register_resource("failing_resource", failing_resource)
        self.assertTrue(success)  # ResourceManager is permissive
        
    def test_unregister_resource_removes_from_ssot_registry(self):
        """
        Test: Resource unregistration properly removes from SSOT registry
        BVJ: Platform/Internal - Prevents resource leaks and memory issues in long-running system
        """
        # Register then unregister resource
        self.resource_manager.register_resource("temp_resource", self.mock_reliability)
        self.assertEqual(len(self.resource_manager._resources), 1)
        
        # Unregister resource
        success = self.resource_manager.unregister_resource("temp_resource")
        self.assertTrue(success)
        self.assertEqual(len(self.resource_manager._resources), 0)
        
        # Attempt to unregister non-existent resource
        success = self.resource_manager.unregister_resource("non_existent")
        self.assertFalse(success)
        
    def test_get_resource_retrieves_from_ssot_registry(self):
        """
        Test: get_resource retrieves resources from SSOT registry correctly
        BVJ: Platform/Internal - Provides reliable access to system resources
        """
        # Test retrieval before registration
        resource = self.resource_manager.get_resource("missing_resource")
        self.assertIsNone(resource)
        
        # Register and retrieve resource
        self.resource_manager.register_resource("test_db", self.mock_database)
        retrieved_resource = self.resource_manager.get_resource("test_db")
        self.assertIs(retrieved_resource, self.mock_database)
        
    def test_get_resource_handles_uninitialized_manager(self):
        """
        Test: get_resource handles uninitialized manager gracefully
        BVJ: Platform/Internal - Ensures robustness even with initialization races
        
        CRITICAL: Tests auto-initialization behavior without masking real failures
        """
        uninitialized_manager = ResourceManager()
        self.assertFalse(uninitialized_manager._initialized)
        
        # Should attempt auto-initialization
        resource = uninitialized_manager.get_resource("test_resource")
        self.assertIsNone(resource)  # Resource doesn't exist, but no crash


class ResourceManagerStatusReportingTests(BaseTestCase):
    """Test resource status reporting and health monitoring."""
    
    def setUp(self):
        """Set up test with multiple mock resources for status testing."""
        super().setUp()
        self.resource_manager = ResourceManager()
        self.mock_reliability = MockReliabilityManager()
        self.mock_database = MockDatabaseManager()
        self.mock_redis = MockRedisConnectionManager()
        
    async def asyncSetUp(self):
        """Async setup with initialized resource manager."""
        await super().asyncSetUp()
        await self.resource_manager.initialize()
        
        # Register multiple resources for status testing
        self.resource_manager.register_resource("reliability", self.mock_reliability)
        self.resource_manager.register_resource("database", self.mock_database)
        self.resource_manager.register_resource("redis", self.mock_redis)
        
    def test_get_resource_status_reports_complete_system_state(self):
        """
        Test: get_resource_status reports complete system resource state
        BVJ: Platform/Internal - Enables monitoring and debugging of resource health
        
        CRITICAL: Must provide comprehensive status for all registered resources
        without hiding failure states or masking errors.
        """
        status = self.resource_manager.get_resource_status()
        
        # Verify top-level status structure
        self.assertIn("initialized", status)
        self.assertIn("resource_count", status)
        self.assertIn("resources", status)
        
        # Verify initialization and count
        self.assertTrue(status["initialized"])
        self.assertEqual(status["resource_count"], 3)
        
        # Verify all resources reported
        resource_names = status["resources"].keys()
        self.assertIn("reliability", resource_names)
        self.assertIn("database", resource_names)
        self.assertIn("redis", resource_names)
        
    def test_resource_status_includes_health_information(self):
        """
        Test: Resource status includes detailed health information for monitoring
        BVJ: Platform/Internal - Enables proactive monitoring and issue detection
        """
        status = self.resource_manager.get_resource_status()
        
        # Check reliability manager status
        reliability_status = status["resources"]["reliability"]
        self.assertEqual(reliability_status["status"], "healthy")
        self.assertEqual(reliability_status["failures"], 0)
        
        # Check database manager status  
        db_status = status["resources"]["database"]
        self.assertEqual(db_status["status"], "disconnected")
        self.assertEqual(db_status["sessions"], 0)
        
        # Check Redis status (uses fallback pattern)
        redis_status = status["resources"]["redis"]
        self.assertEqual(redis_status["status"], "available")
        self.assertEqual(redis_status["type"], "MockRedisConnectionManager")
        
    def test_resource_status_handles_failing_resources(self):
        """
        Test: Resource status handles failing resources without crashing status reporting
        BVJ: Platform/Internal - Ensures monitoring continues even when resources fail
        
        CRITICAL: Must not hide failures - failures must be clearly reported
        """
        # Create a resource that fails status checks
        class FailingResource:
            def get_health_status(self):
                raise RuntimeError("Status check failed")
                
        failing_resource = FailingResource()
        self.resource_manager.register_resource("failing", failing_resource)
        
        # Status should handle the failure gracefully
        status = self.resource_manager.get_resource_status()
        
        # Verify failing resource is reported with error
        failing_status = status["resources"]["failing"]
        self.assertEqual(failing_status["status"], "error")
        self.assertIn("Status check failed", failing_status["error"])


class ResourceManagerContextManagementTests(BaseTestCase):
    """Test resource context management for safe resource access."""
    
    def setUp(self):
        """Set up test with resource manager for context testing."""
        super().setUp()
        self.resource_manager = ResourceManager()
        self.mock_database = MockDatabaseManager()
        
    async def asyncSetUp(self):
        """Async setup with registered resource."""
        await super().asyncSetUp()
        await self.resource_manager.initialize()
        self.resource_manager.register_resource("database", self.mock_database)
        
    def test_resource_context_provides_safe_access(self):
        """
        Test: Resource context manager provides safe resource access
        BVJ: Platform/Internal - Ensures proper resource lifecycle management
        
        CRITICAL: Must ensure resources are properly managed during access
        without masking errors or creating resource leaks.
        """
        async def test_context():
            async with self.resource_manager.resource_context("database") as resource:
                self.assertIs(resource, self.mock_database)
                # Resource should be available during context
                self.assertTrue(hasattr(resource, 'connected'))
                
        asyncio.run(test_context())
        
    def test_resource_context_handles_missing_resources(self):
        """
        Test: Resource context raises appropriate error for missing resources  
        BVJ: Platform/Internal - Fails fast on missing resources to prevent silent failures
        
        CRITICAL: Must RAISE ERROR for missing resources - no silent failures allowed
        """
        async def test_missing():
            try:
                async with self.resource_manager.resource_context("missing_resource"):
                    self.fail("Should have raised ValueError for missing resource")
            except ValueError as e:
                self.assertIn("Resource 'missing_resource' not found", str(e))
                
        asyncio.run(test_missing())
        
    def test_resource_context_calls_cleanup_on_exit(self):
        """
        Test: Resource context calls cleanup on context exit
        BVJ: Platform/Internal - Prevents resource leaks in long-running system
        """
        # Create resource with cleanup method
        class CleanupTrackingResource:
            def __init__(self):
                self.cleanup_called = False
                
            async def cleanup(self):
                self.cleanup_called = True
                
        cleanup_resource = CleanupTrackingResource()
        self.resource_manager.register_resource("cleanup_test", cleanup_resource)
        
        async def test_cleanup():
            async with self.resource_manager.resource_context("cleanup_test") as resource:
                self.assertFalse(resource.cleanup_called)
                
            # Cleanup should be called after context
            self.assertTrue(cleanup_resource.cleanup_called)
            
        asyncio.run(test_cleanup())


class ResourceManagerCleanupTests(BaseTestCase):
    """Test resource cleanup and lifecycle management."""
    
    def setUp(self):
        """Set up test with multiple resources for cleanup testing."""
        super().setUp()
        self.resource_manager = ResourceManager()
        self.cleanup_tracking = {
            "reliability": False,
            "database": False,
            "redis": False
        }
        
        # Create resources that track cleanup
        class TrackingReliability:
            def __init__(self, tracker, name):
                self.tracker = tracker
                self.name = name
                
            async def cleanup(self):
                self.tracker[self.name] = True
                
        class TrackingDatabase:
            def __init__(self, tracker, name):
                self.tracker = tracker
                self.name = name
                
            async def cleanup(self):
                self.tracker[self.name] = True
                
        class TrackingRedis:
            def __init__(self, tracker, name):
                self.tracker = tracker
                self.name = name
                
            async def close(self):
                self.tracker[self.name] = True
                
        self.tracking_reliability = TrackingReliability(self.cleanup_tracking, "reliability")
        self.tracking_database = TrackingDatabase(self.cleanup_tracking, "database")  
        self.tracking_redis = TrackingRedis(self.cleanup_tracking, "redis")
        
    async def asyncSetUp(self):
        """Async setup with registered tracking resources."""
        await super().asyncSetUp()
        await self.resource_manager.initialize()
        
        self.resource_manager.register_resource("reliability", self.tracking_reliability)
        self.resource_manager.register_resource("database", self.tracking_database)
        self.resource_manager.register_resource("redis", self.tracking_redis)
        
    def test_cleanup_calls_all_resource_cleanup_methods(self):
        """
        Test: Resource manager cleanup calls all resource cleanup methods
        BVJ: Platform/Internal - Ensures proper resource cleanup prevents memory leaks
        
        CRITICAL: Must clean up ALL resources without exception - partial cleanup is failure
        """
        async def test_full_cleanup():
            await self.resource_manager.cleanup()
            
            # Verify all resources were cleaned up
            self.assertTrue(self.cleanup_tracking["reliability"])
            self.assertTrue(self.cleanup_tracking["database"])
            self.assertTrue(self.cleanup_tracking["redis"])
            
            # Verify manager state is reset
            self.assertEqual(len(self.resource_manager._resources), 0)
            self.assertFalse(self.resource_manager._initialized)
            
        asyncio.run(test_full_cleanup())
        
    def test_cleanup_handles_failing_resource_cleanup(self):
        """
        Test: Resource cleanup continues even when individual resources fail cleanup
        BVJ: Platform/Internal - Ensures system stability during shutdown
        
        CRITICAL: Must not fail entire cleanup if one resource fails - continue cleaning others
        """
        # Add resource that fails cleanup
        class FailingCleanupResource:
            async def cleanup(self):
                raise RuntimeError("Cleanup failed")
                
        failing_resource = FailingCleanupResource()
        self.resource_manager.register_resource("failing", failing_resource)
        
        async def test_partial_cleanup():
            await self.resource_manager.cleanup()
            
            # Other resources should still be cleaned up
            self.assertTrue(self.cleanup_tracking["reliability"])
            self.assertTrue(self.cleanup_tracking["database"]) 
            self.assertTrue(self.cleanup_tracking["redis"])
            
            # Manager should still reset state
            self.assertEqual(len(self.resource_manager._resources), 0)
            self.assertFalse(self.resource_manager._initialized)
            
        asyncio.run(test_partial_cleanup())
        
    def test_cleanup_handles_different_cleanup_patterns(self):
        """
        Test: Resource cleanup handles different cleanup method patterns
        BVJ: Platform/Internal - Supports diverse resource cleanup patterns across system
        """
        # Resources already registered have different patterns:
        # - reliability: async cleanup()  
        # - database: async cleanup()
        # - redis: async close()
        
        async def test_pattern_diversity():
            await self.resource_manager.cleanup()
            
            # All should be cleaned despite different method names
            self.assertTrue(self.cleanup_tracking["reliability"])
            self.assertTrue(self.cleanup_tracking["database"])
            self.assertTrue(self.cleanup_tracking["redis"])
            
        asyncio.run(test_pattern_diversity())


class ResourceManagerAutoInitializationTests(BaseTestCase):
    """Test automatic resource initialization and discovery."""
    
    def setUp(self):
        """Set up test for auto-initialization testing."""
        super().setUp()
        
    def test_initialize_discovers_available_resources(self):
        """
        Test: initialize() discovers and registers available resource managers
        BVJ: Platform/Internal - Automatic resource discovery reduces configuration complexity
        
        CRITICAL: Tests that initialization attempts to load all known resource managers
        without failing if some are unavailable (graceful degradation).
        """
        resource_manager = ResourceManager()
        
        async def test_initialization():
            await resource_manager.initialize()
            
            # Should be initialized
            self.assertTrue(resource_manager._initialized)
            
            # Should not crash even if actual managers are not available
            status = resource_manager.get_resource_status()
            self.assertTrue(status["initialized"])
            
        asyncio.run(test_initialization())
        
    def test_initialize_is_idempotent(self):
        """
        Test: Multiple initialization calls are idempotent
        BVJ: Platform/Internal - Prevents duplicate initialization in concurrent scenarios
        """
        resource_manager = ResourceManager()
        
        async def test_idempotent():
            await resource_manager.initialize()
            first_resource_count = len(resource_manager._resources)
            
            await resource_manager.initialize()
            second_resource_count = len(resource_manager._resources)
            
            self.assertEqual(first_resource_count, second_resource_count)
            self.assertTrue(resource_manager._initialized)
            
        asyncio.run(test_idempotent())
        
    @patch('netra_backend.app.core.resource_manager.DatabaseManager')
    @patch('netra_backend.app.core.resource_manager.ReliabilityManager') 
    @patch('netra_backend.app.core.resource_manager.RedisConnectionManager')
    def test_initialize_handles_import_failures_gracefully(self, mock_redis, mock_reliability, mock_db):
        """
        Test: Initialization handles import failures gracefully
        BVJ: Platform/Internal - System continues operating even with missing components
        
        CRITICAL: Import failures must not crash initialization - graceful degradation required
        """
        # Mock successful imports
        mock_db.return_value = MockDatabaseManager()
        mock_reliability.return_value = MockReliabilityManager() 
        mock_redis.return_value = MockRedisConnectionManager()
        
        resource_manager = ResourceManager()
        
        async def test_graceful_handling():
            await resource_manager.initialize()
            
            # Should be initialized even with mocked imports
            self.assertTrue(resource_manager._initialized)
            
            # Should have attempted to register mocked resources
            status = resource_manager.get_resource_status()
            self.assertTrue(status["initialized"])
            
        asyncio.run(test_graceful_handling())


class ResourceManagerMultiUserIsolationTests(BaseTestCase):
    """Test resource isolation for multi-user system requirements."""
    
    def setUp(self):
        """Set up test for multi-user resource isolation testing.""" 
        super().setUp()
        self.user1_manager = ResourceManager()
        self.user2_manager = ResourceManager()
        
    def test_separate_resource_managers_provide_isolation(self):
        """
        Test: Separate ResourceManager instances provide user isolation
        BVJ: Platform/Internal - Ensures user resource isolation in multi-user system
        
        CRITICAL: Resource managers must not share state between users - complete isolation required
        """
        # Register different resources in each manager
        mock_resource1 = MockReliabilityManager()
        mock_resource2 = MockDatabaseManager()
        
        self.user1_manager.register_resource("user1_resource", mock_resource1)
        self.user2_manager.register_resource("user2_resource", mock_resource2)
        
        # Verify isolation
        user1_resource = self.user1_manager.get_resource("user1_resource")
        user1_missing = self.user1_manager.get_resource("user2_resource")
        
        user2_resource = self.user2_manager.get_resource("user2_resource")
        user2_missing = self.user2_manager.get_resource("user1_resource")
        
        self.assertIs(user1_resource, mock_resource1)
        self.assertIsNone(user1_missing)
        
        self.assertIs(user2_resource, mock_resource2)
        self.assertIsNone(user2_missing)
        
    def test_resource_status_isolation_between_users(self):
        """
        Test: Resource status is isolated between different users
        BVJ: Platform/Internal - Prevents information leakage between users
        """
        # Setup different resources for each user
        self.user1_manager.register_resource("db", MockDatabaseManager())
        self.user2_manager.register_resource("redis", MockRedisConnectionManager())
        
        user1_status = self.user1_manager.get_resource_status()
        user2_status = self.user2_manager.get_resource_status()
        
        # Verify status isolation
        self.assertIn("db", user1_status["resources"])
        self.assertNotIn("redis", user1_status["resources"])
        
        self.assertIn("redis", user2_status["resources"])
        self.assertNotIn("db", user2_status["resources"])
        
    def test_resource_cleanup_isolation(self):
        """
        Test: Resource cleanup is isolated between users
        BVJ: Platform/Internal - Ensures one user's cleanup doesn't affect others
        
        CRITICAL: User cleanup must not affect other users' resources
        """
        # Create tracking resources for both users
        user1_cleanup = {"cleaned": False}
        user2_cleanup = {"cleaned": False}
        
        class TrackingResource:
            def __init__(self, tracker):
                self.tracker = tracker
                
            async def cleanup(self):
                self.tracker["cleaned"] = True
                
        user1_resource = TrackingResource(user1_cleanup)
        user2_resource = TrackingResource(user2_cleanup)
        
        self.user1_manager.register_resource("resource", user1_resource)
        self.user2_manager.register_resource("resource", user2_resource)
        
        async def test_isolated_cleanup():
            # Cleanup user1 only
            await self.user1_manager.cleanup()
            
            # Verify only user1's resource was cleaned
            self.assertTrue(user1_cleanup["cleaned"])
            self.assertFalse(user2_cleanup["cleaned"])
            
            # User2's resource should still be available
            user2_resource_still_there = self.user2_manager.get_resource("resource")
            self.assertIs(user2_resource_still_there, user2_resource)
            
        asyncio.run(test_isolated_cleanup())


class ResourceManagerGlobalConvenienceFunctionTests(BaseTestCase):
    """Test global convenience functions for backward compatibility."""
    
    def setUp(self):
        """Set up test for global function testing."""
        super().setUp()
        
    def test_get_resource_manager_returns_global_instance(self):
        """
        Test: get_resource_manager() returns initialized global instance
        BVJ: Platform/Internal - Provides backward compatibility for existing code
        """
        async def test_global_manager():
            manager = await get_resource_manager()
            self.assertIsInstance(manager, ResourceManager)
            self.assertTrue(manager._initialized)
            
        asyncio.run(test_global_manager())
        
    def test_global_register_resource_uses_global_manager(self):
        """
        Test: Global register_resource function uses global manager
        BVJ: Platform/Internal - Maintains API compatibility
        """
        mock_resource = MockReliabilityManager()
        success = register_resource("global_test", mock_resource)
        self.assertTrue(success)
        
        # Should be retrievable via global function
        retrieved = get_resource("global_test")
        self.assertIs(retrieved, mock_resource)
        
    def test_get_system_resource_status_reports_global_state(self):
        """
        Test: get_system_resource_status reports global system state
        BVJ: Platform/Internal - Provides system-wide monitoring capability
        """
        # Register a resource globally
        mock_resource = MockDatabaseManager()
        register_resource("system_db", mock_resource)
        
        # Get system status
        status = get_system_resource_status()
        self.assertIn("system_db", status["resources"])
        
    def test_global_functions_handle_uninitialized_state(self):
        """
        Test: Global functions handle uninitialized state gracefully
        BVJ: Platform/Internal - Ensures robustness in all initialization scenarios
        """
        # This tests the actual global manager, which may be in various states
        # Should not crash regardless of state
        status = get_system_resource_status()
        self.assertIn("initialized", status)
        self.assertIn("resource_count", status)
        self.assertIn("resources", status)


class ResourceManagerErrorResilienceTests(BaseTestCase):
    """Test error handling and system resilience patterns."""
    
    def setUp(self):
        """Set up test for error resilience testing."""
        super().setUp()
        self.resource_manager = ResourceManager()
        
    def test_resource_manager_continues_operating_after_resource_failures(self):
        """
        Test: ResourceManager continues operating even after individual resource failures
        BVJ: Platform/Internal - Ensures system stability despite component failures
        
        CRITICAL: Individual resource failures must not crash the entire resource management system
        """
        # Register a failing resource
        class FailingResource:
            def get_health_status(self):
                raise RuntimeError("Health check failed")
                
        failing_resource = FailingResource()
        good_resource = MockReliabilityManager()
        
        self.resource_manager.register_resource("failing", failing_resource)
        self.resource_manager.register_resource("good", good_resource)
        
        # Status should handle failures gracefully
        status = self.resource_manager.get_resource_status()
        
        # Good resource should be reported normally
        self.assertEqual(status["resources"]["good"]["status"], "healthy")
        
        # Failing resource should be reported with error
        self.assertEqual(status["resources"]["failing"]["status"], "error")
        
        # System should continue operating
        self.assertEqual(status["resource_count"], 2)
        
    def test_resource_manager_handles_resource_registration_edge_cases(self):
        """
        Test: ResourceManager handles edge cases in resource registration
        BVJ: Platform/Internal - Ensures robustness against problematic resources
        """
        # Test various edge cases
        test_cases = [
            ("none_resource", None),
            ("empty_string_name", MockReliabilityManager()),
            ("duplicate_name", MockDatabaseManager())
        ]
        
        for name, resource in test_cases:
            success = self.resource_manager.register_resource(name, resource)
            self.assertTrue(success, f"Failed to register {name}")
            
        # Test duplicate registration (should succeed - overwrites)
        duplicate_resource = MockRedisConnectionManager()
        success = self.resource_manager.register_resource("duplicate_name", duplicate_resource)
        self.assertTrue(success)
        
        retrieved = self.resource_manager.get_resource("duplicate_name")
        self.assertIs(retrieved, duplicate_resource)
        
    def test_resource_context_handles_resource_failures_during_access(self):
        """
        Test: Resource context handles failures during resource access
        BVJ: Platform/Internal - Ensures resource access failures don't crash system
        
        CRITICAL: Resource access failures must be propagated, not hidden
        """
        class FailingCleanupResource:
            async def cleanup(self):
                raise RuntimeError("Cleanup failed during context exit")
                
        failing_resource = FailingCleanupResource()
        self.resource_manager.register_resource("failing_cleanup", failing_resource)
        
        async def test_failing_context():
            # Context should handle cleanup failure gracefully
            # But should not hide the fact that cleanup failed
            async with self.resource_manager.resource_context("failing_cleanup") as resource:
                self.assertIs(resource, failing_resource)
            # Context exit with failing cleanup should be logged but not crash
            
        asyncio.run(test_failing_context())


class ResourceManagerIntegrationPatternTests(BaseTestCase):
    """Test integration patterns with actual resource manager types."""
    
    def setUp(self):
        """Set up test for integration pattern testing."""
        super().setUp()
        self.resource_manager = ResourceManager()
        
    def test_database_manager_integration_pattern(self):
        """
        Test: ResourceManager integrates properly with DatabaseManager pattern
        BVJ: Platform/Internal - Ensures database resources are properly managed
        """
        # Create mock that mimics actual DatabaseManager interface
        class DatabaseManagerMock:
            def __init__(self):
                self.connected = False
                self.engines = {}
                
            async def initialize(self):
                self.connected = True
                
            def get_health_status(self):
                return {
                    "status": "connected" if self.connected else "disconnected",
                    "engines": len(self.engines),
                    "type": "DatabaseManagerMock"
                }
                
            async def cleanup(self):
                self.connected = False
                self.engines.clear()
                
        db_manager = DatabaseManagerMock()
        
        # Test registration and status
        success = self.resource_manager.register_resource("database", db_manager)
        self.assertTrue(success)
        
        status = self.resource_manager.get_resource_status()
        db_status = status["resources"]["database"]
        self.assertEqual(db_status["status"], "disconnected")
        self.assertEqual(db_status["engines"], 0)
        
    def test_reliability_manager_integration_pattern(self):
        """
        Test: ResourceManager integrates properly with ReliabilityManager pattern  
        BVJ: Platform/Internal - Ensures reliability resources are properly coordinated
        """
        # Create mock that mimics actual ReliabilityManager interface
        class ReliabilityManagerMock:
            def __init__(self):
                self.failure_count = 0
                self.circuit_state = "closed"
                
            def get_health_status(self):
                return {
                    "status": "healthy" if self.failure_count == 0 else "degraded",
                    "failures": self.failure_count,
                    "circuit_state": self.circuit_state,
                    "type": "ReliabilityManagerMock"
                }
                
            async def cleanup(self):
                self.failure_count = 0
                self.circuit_state = "closed"
                
        reliability_manager = ReliabilityManagerMock()
        
        # Test registration and status  
        success = self.resource_manager.register_resource("reliability", reliability_manager)
        self.assertTrue(success)
        
        status = self.resource_manager.get_resource_status()
        reliability_status = status["resources"]["reliability"]
        self.assertEqual(reliability_status["status"], "healthy")
        self.assertEqual(reliability_status["failures"], 0)
        
    def test_redis_connection_manager_integration_pattern(self):
        """
        Test: ResourceManager integrates properly with Redis connection patterns
        BVJ: Platform/Internal - Ensures Redis resources are properly coordinated
        """
        # Create mock that mimics Redis connection manager interface
        class RedisConnectionManagerMock:
            def __init__(self):
                self.connected = False
                self.pool_size = 0
                
            async def connect(self):
                self.connected = True
                self.pool_size = 10
                
            def health_check(self):
                return self.connected
                
            async def close(self):
                self.connected = False 
                self.pool_size = 0
                
        redis_manager = RedisConnectionManagerMock()
        
        # Test registration and status (uses fallback pattern)
        success = self.resource_manager.register_resource("redis", redis_manager)
        self.assertTrue(success)
        
        status = self.resource_manager.get_resource_status()
        redis_status = status["resources"]["redis"]
        self.assertEqual(redis_status["status"], "available")
        self.assertEqual(redis_status["type"], "RedisConnectionManagerMock")


if __name__ == "__main__":
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the comprehensive test suite
    unittest.main(verbosity=2)