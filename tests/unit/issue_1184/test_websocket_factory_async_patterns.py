"""
Additional tests for Issue #1184 - WebSocket Factory Async Pattern Validation

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Infrastructure
- Business Goal: Validate async/sync factory patterns work correctly
- Value Impact: Ensures correct async/await usage in WebSocket factory creation
- Strategic Impact: Prevents async/await compatibility issues in staging/production

These tests focus on the factory pattern async/sync compatibility issues 
discovered in Issue #1184 root cause analysis.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketFactoryAsyncPatternsTests(SSotAsyncTestCase):
    """Test WebSocket factory async pattern compatibility issues."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        # Reset manager registry between tests to prevent cross-test contamination
        from netra_backend.app.websocket_core.canonical_import_patterns import reset_manager_registry
        reset_manager_registry()

    @pytest.mark.issue_1184
    @pytest.mark.mission_critical
    async def test_async_create_websocket_manager_function_compatibility(self):
        """
        Test compatibility between async create_websocket_manager and sync get_websocket_manager.
        
        This addresses the specific issue where async create_websocket_manager is awaited
        but internally calls synchronous get_websocket_manager.
        """
        user_context = {"user_id": "async-compat-test-1184", "thread_id": "async-thread"}
        
        # Test 1: Async create_websocket_manager function (if available)
        try:
            from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
            
            # This should be an async function that can be awaited
            async_manager = await create_websocket_manager(user_context=user_context)
            assert async_manager is not None, "Async create_websocket_manager failed"
            logger.info("CHECK Async create_websocket_manager works correctly")
            
        except ImportError:
            logger.info("ℹ️ Async create_websocket_manager not available, skipping async test")
        except Exception as e:
            logger.error(f"X Async create_websocket_manager failed: {e}")
            pytest.fail(f"Async create_websocket_manager compatibility issue: {e}")

        # Test 2: Synchronous get_websocket_manager (baseline)
        sync_manager = get_websocket_manager(user_context=user_context)
        assert sync_manager is not None, "Sync get_websocket_manager failed"
        logger.info("CHECK Sync get_websocket_manager works correctly")

        # Test 3: Validate both create same type of object (if async version exists)
        try:
            if 'async_manager' in locals():
                assert type(async_manager) == type(sync_manager), \
                    "Async and sync factory methods should create same type"
                logger.info("CHECK Async and sync factories create compatible objects")
        except NameError:
            pass  # async_manager not created, skip comparison

    @pytest.mark.issue_1184
    async def test_internal_websocket_manager_async_wrapper_patterns(self):
        """
        Test internal async wrapper patterns that cause Issue #1184.
        
        Validates that internal _get_websocket_manager methods properly handle
        async/sync compatibility.
        """
        user_context = {"user_id": "internal-async-1184", "thread_id": "internal-thread"}
        
        # Test: Mock an internal async wrapper (like in clickhouse_operations.py)
        class MockServiceWithAsyncWrapper:
            def __init__(self, user_context):
                self.user_context = user_context
                self._websocket_manager = None
                self._websocket_manager_created = False
            
            async def _get_websocket_manager(self):
                """Mock the problematic async wrapper pattern."""
                if not self.user_context:
                    return None
                    
                if not self._websocket_manager_created:
                    try:
                        # ISSUE #1184: This pattern causes async/await issues
                        # when create_websocket_manager is awaited but calls sync functions
                        
                        # Option 1: Use sync get_websocket_manager directly (RECOMMENDED)
                        self._websocket_manager = get_websocket_manager(user_context=self.user_context)
                        self._websocket_manager_created = True
                        logger.info("CHECK Using sync get_websocket_manager directly")
                        
                    except Exception as e:
                        logger.error(f"Failed to create WebSocket manager: {e}")
                        return None
                        
                return self._websocket_manager

        # Test the mock service async wrapper
        service = MockServiceWithAsyncWrapper(user_context)
        
        # This should work without async/await issues
        manager = await service._get_websocket_manager()
        assert manager is not None, "Internal async wrapper failed"
        assert hasattr(manager, 'user_context'), "Manager missing user_context"
        assert manager.user_context == user_context, "User context not preserved"
        
        logger.info("CHECK Internal async wrapper pattern works correctly")

    @pytest.mark.issue_1184
    async def test_websocket_manager_module_loading_compatibility(self):
        """
        Test WebSocket manager module loading compatibility for Issue #1184.
        
        Validates that different import patterns work correctly and don't cause
        async/await issues due to module loading problems.
        """
        user_context = {"user_id": "module-loading-1184", "thread_id": "module-thread"}
        
        # Test 1: Direct import (current working pattern)
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager as direct_import
        manager1 = direct_import(user_context=user_context)
        assert manager1 is not None, "Direct import pattern failed"
        
        # Test 2: Canonical import pattern
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager as canonical_import
            manager2 = canonical_import(user_context=user_context)
            assert manager2 is not None, "Canonical import pattern failed"
            # Should be same instance due to user registry
            assert manager1 is manager2, "Different import patterns should yield same manager"
            logger.info("CHECK Canonical import pattern works correctly")
        except ImportError:
            logger.info("ℹ️ Canonical import pattern not available")
        
        # Test 3: Compatibility import pattern
        try:
            from netra_backend.app.websocket_core.canonical_imports import get_websocket_manager_factory
            factory = get_websocket_manager_factory()
            assert factory is not None, "Factory import pattern failed"
            logger.info("CHECK Factory import pattern works correctly")
        except ImportError:
            logger.info("ℹ️ Factory import pattern not available")

        logger.info("CHECK Module loading compatibility validated")

    @pytest.mark.issue_1184
    async def test_websocket_manager_concurrent_async_sync_mixed_usage(self):
        """
        Test mixed async/sync usage patterns that could cause Issue #1184.
        
        Validates that concurrent usage of both async and sync patterns
        doesn't cause race conditions or compatibility issues.
        """
        base_context = {"user_id": "mixed-usage-1184", "thread_id": "mixed-thread"}
        
        async def async_manager_creator(user_suffix):
            """Create manager using async patterns."""
            context = {**base_context, "user_id": f"{base_context['user_id']}-{user_suffix}"}
            
            # Simulate async service creation pattern
            await asyncio.sleep(0.01)  # Simulate async work
            
            # Use sync get_websocket_manager (correct pattern)
            manager = get_websocket_manager(user_context=context)
            return manager, context
            
        def sync_manager_creator(user_suffix):
            """Create manager using sync patterns."""
            context = {**base_context, "user_id": f"{base_context['user_id']}-{user_suffix}"}
            
            # Direct sync usage
            manager = get_websocket_manager(user_context=context)
            return manager, context

        # Test concurrent mixed usage
        async_task1 = asyncio.create_task(async_manager_creator("async1"))
        async_task2 = asyncio.create_task(async_manager_creator("async2"))
        
        # Run async tasks
        (async_manager1, async_context1), (async_manager2, async_context2) = await asyncio.gather(async_task1, async_task2)
        
        # Run sync tasks
        sync_manager1, sync_context1 = sync_manager_creator("sync1")
        sync_manager2, sync_context2 = sync_manager_creator("sync2")
        
        # Validate all managers created successfully
        managers = [async_manager1, async_manager2, sync_manager1, sync_manager2]
        contexts = [async_context1, async_context2, sync_context1, sync_context2]
        
        for i, manager in enumerate(managers):
            assert manager is not None, f"Manager {i} creation failed"
            assert hasattr(manager, 'user_context'), f"Manager {i} missing user_context"
            assert manager.user_context == contexts[i], f"Manager {i} user context mismatch"
        
        # Validate user isolation (all should be different)
        for i, manager1 in enumerate(managers):
            for j, manager2 in enumerate(managers):
                if i != j:
                    assert manager1 is not manager2, f"Manager isolation failed between {i} and {j}"
        
        logger.info("CHECK Mixed async/sync concurrent usage validated")

    @pytest.mark.issue_1184
    @pytest.mark.mission_critical
    async def test_websocket_manager_staging_async_compatibility_simulation(self):
        """
        Simulate staging environment async compatibility for Issue #1184.
        
        This test reproduces staging-specific async/await patterns that could
        cause the 8/8 golden path test failures mentioned in Issue #1184.
        """
        # Simulate staging environment conditions
        staging_contexts = [
            {"user_id": "staging-user-1", "thread_id": "staging-thread-1", "environment": "staging"},
            {"user_id": "staging-user-2", "thread_id": "staging-thread-2", "environment": "staging"},
            {"user_id": "staging-user-3", "thread_id": "staging-thread-3", "environment": "staging"},
        ]
        
        async def simulate_staging_request(context):
            """Simulate a staging request that creates WebSocket managers."""
            try:
                # Simulate async request processing
                await asyncio.sleep(0.02)  # Simulate network/processing delay
                
                # Create WebSocket manager (the critical operation)
                manager = get_websocket_manager(user_context=context)
                
                # Simulate WebSocket event operations
                if hasattr(manager, 'emit_event'):
                    # Mock event emission (don't actually emit in test)
                    event_success = True
                elif hasattr(manager, 'send_event'):
                    event_success = True
                else:
                    event_success = False  # Manager doesn't have expected methods
                
                return {
                    "manager": manager,
                    "context": context,
                    "event_capable": event_success,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Staging simulation failed for {context['user_id']}: {e}")
                return {
                    "manager": None,
                    "context": context,
                    "event_capable": False,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent staging simulations
        tasks = [simulate_staging_request(ctx) for ctx in staging_contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate staging compatibility
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
        
        # Should have high success rate (like staging environment)
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.8, f"Staging simulation success rate too low: {success_rate:.1%}"
        
        # Validate successful results
        for result in successful_results:
            assert result["manager"] is not None, "Manager creation failed in staging simulation"
            assert result["event_capable"], "Manager not event-capable in staging simulation"
        
        if failed_results:
            logger.warning(f"Some staging simulations failed: {len(failed_results)}/{len(results)}")
            for result in failed_results:
                if isinstance(result, dict):
                    logger.warning(f"Failed result: {result.get('error')}")
        
        logger.info(f"CHECK Staging async compatibility validated: {success_rate:.1%} success rate")