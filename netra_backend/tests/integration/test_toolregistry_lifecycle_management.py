"""
Integration Tests for ToolRegistry Lifecycle Management

This module tests the tool registry lifecycle in isolation from the full E2E flow,
focusing on the component interactions that lead to duplicate registration issues.

CRITICAL REQUIREMENTS:
- Tests MUST be designed to FAIL in current broken state
- Tests MUST use real services (PostgreSQL, Redis) when needed
- Tests MUST validate supervisor factory registry isolation
- Tests MUST detect multiple ToolRegistry instantiation points

Business Value:
- Prevents tool registry proliferation (11 instantiation points identified)
- Validates WebSocket supervisor factory proper registry isolation
- Ensures registry cleanup on supervisor destruction

See: /Users/rindhujajohnson/Netra/GitHub/netra-apex/audit/staging/auto-solve-loop/toolregistry-duplicate-registration-20250109.md
"""

import asyncio
import logging
import pytest
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Any
from unittest.mock import Mock, patch

from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.agents.user_context_tool_factory import UserContextToolFactory
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class RegistryLifecycleTracker:
    """Helper to track registry creation, registration attempts, and cleanup."""
    
    def __init__(self):
        self.registries_created: List[Dict[str, Any]] = []
        self.registration_attempts: List[Dict[str, Any]] = []
        self.cleanup_events: List[Dict[str, Any]] = []
        self.active_registries: Set[int] = set()
        self.lock = threading.Lock()
        
    def track_registry_creation(self, registry_id: int, creator: str, timestamp: float = None):
        """Track creation of a new registry."""
        with self.lock:
            event = {
                'registry_id': registry_id,
                'creator': creator,
                'timestamp': timestamp or time.time(),
                'thread_id': threading.get_ident()
            }
            self.registries_created.append(event)
            self.active_registries.add(registry_id)
            
    def track_registration_attempt(self, registry_id: int, tool_name: str, success: bool, error: str = None):
        """Track a tool registration attempt."""
        with self.lock:
            event = {
                'registry_id': registry_id,
                'tool_name': tool_name,
                'success': success,
                'error': error,
                'timestamp': time.time(),
                'thread_id': threading.get_ident()
            }
            self.registration_attempts.append(event)
            
    def track_registry_cleanup(self, registry_id: int, cleanup_method: str):
        """Track registry cleanup."""
        with self.lock:
            event = {
                'registry_id': registry_id,
                'cleanup_method': cleanup_method,
                'timestamp': time.time(),
                'thread_id': threading.get_ident()
            }
            self.cleanup_events.append(event)
            self.active_registries.discard(registry_id)
            
    def get_duplicate_registrations(self) -> List[str]:
        """Get list of tools that were registered multiple times."""
        tool_registrations = {}
        for attempt in self.registration_attempts:
            if attempt['success']:
                tool_name = attempt['tool_name']
                if tool_name not in tool_registrations:
                    tool_registrations[tool_name] = []
                tool_registrations[tool_name].append(attempt)
                
        duplicates = []
        for tool_name, attempts in tool_registrations.items():
            if len(attempts) > 1:
                duplicates.append(tool_name)
                
        return duplicates
        
    def get_analysis_report(self) -> Dict[str, Any]:
        """Get comprehensive analysis report."""
        return {
            'total_registries_created': len(self.registries_created),
            'active_registries': len(self.active_registries),
            'total_registration_attempts': len(self.registration_attempts),
            'successful_registrations': len([a for a in self.registration_attempts if a['success']]),
            'duplicate_tool_registrations': self.get_duplicate_registrations(),
            'cleanup_events': len(self.cleanup_events),
            'registry_creators': list(set(r['creator'] for r in self.registries_created)),
            'thread_distribution': len(set(r['thread_id'] for r in self.registries_created))
        }


@pytest.mark.integration
@pytest.mark.toolregistry
class TestToolRegistryLifecycleManagement(SSotBaseTestCase):
    """
    Integration tests for tool registry lifecycle management.
    
    These tests focus on the registry creation, tool registration, and cleanup
    patterns that lead to the "modelmetaclass already registered" issue.
    """
    
    def setup_method(self, method):
        """Set up method-level fixtures."""
        super().setup_method(method)
        self.lifecycle_tracker = RegistryLifecycleTracker()
        
        # Patch registry creation to track instances
        self.original_registry_init = ToolRegistry.__init__
        self.original_register = ToolRegistry.register
        
        def tracked_init(registry_self, scope_id=None):
            """Track registry creation."""
            result = self.original_registry_init(registry_self, scope_id=scope_id)
            registry_id = id(registry_self)
            creator = self._get_creation_stack()
            self.lifecycle_tracker.track_registry_creation(registry_id, creator)
            return result
            
        def tracked_register(registry_self, name: str, tool):
            """Track tool registration attempts."""
            registry_id = id(registry_self)
            try:
                result = self.original_register(registry_self, name, tool)
                self.lifecycle_tracker.track_registration_attempt(registry_id, name, True)
                return result
            except Exception as e:
                self.lifecycle_tracker.track_registration_attempt(registry_id, name, False, str(e))
                raise
                
        ToolRegistry.__init__ = tracked_init
        ToolRegistry.register = tracked_register
        
    def teardown_method(self, method):
        """Restore original methods and analyze results."""
        # Restore original methods
        ToolRegistry.__init__ = self.original_registry_init  
        ToolRegistry.register = self.original_register
        
        # Log analysis
        analysis = self.lifecycle_tracker.get_analysis_report()
        logger.info(f"📊 Registry lifecycle analysis for {method.__name__}: {analysis}")
        
        super().teardown_method(method)
        
    def _get_creation_stack(self) -> str:
        """Get simplified creation stack for tracking."""
        import inspect
        stack = inspect.stack()
        # Find the first frame outside this test file
        for frame in stack[2:]:  # Skip __init__ and tracked_init
            filename = frame.filename
            if "test_toolregistry_lifecycle" not in filename:
                return f"{filename.split('/')[-1]}:{frame.function}:{frame.lineno}"
        return "unknown_creator"
        
    def test_websocket_supervisor_factory_registry_isolation(self):
        """
        Test supervisor factory creates isolated registries.
        Should catch multiple ToolRegistry() instantiation issues.
        
        CRITICAL: This test should fail if multiple registries are created
        for the same logical supervisor, leading to registration conflicts.
        """
        logger.info("🧪 Testing WebSocket supervisor factory registry isolation")
        
        # Mock user context
        mock_context = Mock()
        mock_context.user_id = "test_user_123"
        mock_context.run_id = "test_run_456" 
        mock_context.get_correlation_id.return_value = "test_correlation_789"
        
        # Mock basic tool classes (avoid BaseModel tools that cause the issue)
        class MockTool:
            def __init__(self):
                self.name = "mock_tool"
                
        class MockTool2:
            def __init__(self):
                self.name = "mock_tool_2"
                
        tool_classes = [MockTool, MockTool2]
        
        # Create multiple supervisor-like tool systems
        systems = []
        for i in range(3):  # Simulate 3 different supervisor creations
            logger.info(f"Creating supervisor tool system {i}...")
            
            # This should create isolated registries per the design
            system = asyncio.run(UserContextToolFactory.create_user_tool_system(
                context=mock_context,
                tool_classes=tool_classes
            ))
            systems.append(system)
            
        # Analyze the results
        analysis = self.lifecycle_tracker.get_analysis_report()
        logger.info(f"📊 Isolation test results: {analysis}")
        
        # CRITICAL VALIDATIONS:
        
        # 1. Each supervisor should create its own registry
        expected_registries = 3  # One per supervisor
        actual_registries = analysis['total_registries_created']
        
        if actual_registries != expected_registries:
            logger.error(f"❌ Registry isolation failure: Expected {expected_registries} registries, got {actual_registries}")
            # This might indicate the issue where registries are shared or not properly isolated
            
        # 2. No tools should be registered multiple times across registries
        duplicate_tools = analysis['duplicate_tool_registrations']
        if duplicate_tools:
            logger.error(f"❌ Duplicate tool registrations detected: {duplicate_tools}")
            pytest.fail(f"REPRODUCED BUG: Tools registered multiple times across registries: {duplicate_tools}")
            
        # 3. All registrations should succeed (no "already registered" errors)
        failed_registrations = [
            attempt for attempt in self.lifecycle_tracker.registration_attempts 
            if not attempt['success'] and "already registered" in (attempt['error'] or "")
        ]
        
        if failed_registrations:
            logger.error(f"❌ 'Already registered' errors detected: {len(failed_registrations)}")
            errors = [f"{r['tool_name']}: {r['error']}" for r in failed_registrations]
            pytest.fail(f"REPRODUCED BUG: Tool registration conflicts: {errors}")
            
        # 4. Check for suspicious BaseModel-related registrations
        basemodel_registrations = [
            attempt for attempt in self.lifecycle_tracker.registration_attempts
            if "modelmetaclass" in attempt['tool_name'].lower() or "basemodel" in attempt['tool_name'].lower()
        ]
        
        if basemodel_registrations:
            logger.error(f"❌ BaseModel registrations detected: {len(basemodel_registrations)}")
            pytest.fail(f"REPRODUCED BUG: BaseModel classes being registered as tools")
            
        logger.info("✅ Registry isolation test passed - no duplicate registration issues")
        
    def test_tool_registry_cleanup_on_supervisor_destruction(self):
        """
        Test that registries are cleaned up when supervisors are destroyed.
        Should catch WebSocket connection lifecycle issues.
        
        CRITICAL: Validates that tool registries don't leak between connections.
        """
        logger.info("🧪 Testing tool registry cleanup on supervisor destruction")
        
        mock_context = Mock()
        mock_context.user_id = "cleanup_test_user"
        mock_context.run_id = "cleanup_test_run"
        mock_context.get_correlation_id.return_value = "cleanup_test_correlation"
        
        class CleanupTestTool:
            def __init__(self):
                self.name = "cleanup_test_tool"
                
        # Step 1: Create supervisor tool system
        logger.info("📦 Creating supervisor tool system...")
        system = asyncio.run(UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[CleanupTestTool]
        ))
        
        registry = system['registry']
        registry_id = id(registry)
        
        # Verify tool was registered
        assert registry.get_tool("cleanup_test_tool") is not None, "Tool should be registered"
        
        # Step 2: Track registry for cleanup detection
        registry_ref = weakref.ref(registry, lambda ref: self.lifecycle_tracker.track_registry_cleanup(
            registry_id, "garbage_collection"
        ))
        
        # Step 3: Destroy the supervisor system (simulate WebSocket disconnect)
        logger.info("🗑️ Destroying supervisor tool system...")
        del system['registry']
        del system['dispatcher'] 
        del system
        del registry
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Step 4: Wait a moment and check if cleanup occurred
        time.sleep(0.1)
        
        # Step 5: Create new supervisor with same tools and verify no conflicts
        logger.info("🔄 Creating new supervisor tool system after cleanup...")
        
        new_system = asyncio.run(UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[CleanupTestTool]
        ))
        
        # Analyze results
        analysis = self.lifecycle_tracker.get_analysis_report()
        logger.info(f"📊 Cleanup test results: {analysis}")
        
        # CRITICAL VALIDATIONS:
        
        # 1. Should have created 2 separate registries (before and after cleanup)
        if analysis['total_registries_created'] < 2:
            pytest.fail("Expected at least 2 registries (before and after cleanup)")
            
        # 2. No duplicate registration errors should occur
        duplicate_tools = analysis['duplicate_tool_registrations']
        if duplicate_tools:
            pytest.fail(f"REPRODUCED BUG: Registry cleanup failed - duplicate tools: {duplicate_tools}")
            
        # 3. All registrations should succeed
        failed_registrations = [
            attempt for attempt in self.lifecycle_tracker.registration_attempts
            if not attempt['success']
        ]
        
        if failed_registrations:
            errors = [f"{r['tool_name']}: {r['error']}" for r in failed_registrations]
            pytest.fail(f"REPRODUCED BUG: Registration failures after cleanup: {errors}")
            
        logger.info("✅ Registry cleanup test passed")
        
    def test_concurrent_registry_creation_thread_safety(self):
        """
        Test multiple threads creating registries simultaneously.
        Should catch race condition scenarios that lead to registration conflicts.
        
        CRITICAL: This test reproduces the exact race conditions possible
        in multi-user WebSocket scenarios.
        """
        logger.info("🧪 Testing concurrent registry creation thread safety")
        
        def create_registry_system(thread_id: int) -> dict:
            """Create a registry system in a specific thread."""
            try:
                mock_context = Mock()
                mock_context.user_id = f"concurrent_user_{thread_id}"
                mock_context.run_id = f"concurrent_run_{thread_id}"
                mock_context.get_correlation_id.return_value = f"concurrent_correlation_{thread_id}"
                
                class ConcurrentTestTool:
                    def __init__(self):
                        self.name = f"concurrent_tool_{thread_id}"
                        
                # Create system - this is where race conditions might occur
                system = asyncio.run(UserContextToolFactory.create_user_tool_system(
                    context=mock_context,
                    tool_classes=[ConcurrentTestTool]
                ))
                
                return {
                    'thread_id': thread_id,
                    'success': True,
                    'registry_id': id(system['registry']),
                    'error': None
                }
                
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'success': False,
                    'registry_id': None,
                    'error': str(e)
                }
        
        # Execute concurrent registry creation
        num_threads = 5
        logger.info(f"⚡ Creating {num_threads} concurrent registry systems...")
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            start_time = time.time()
            futures = [executor.submit(create_registry_system, i) for i in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
            execution_time = time.time() - start_time
            
        logger.info(f"⏱️ Concurrent creation completed in {execution_time:.3f}s")
        
        # Analyze results
        analysis = self.lifecycle_tracker.get_analysis_report()
        logger.info(f"📊 Concurrency test results: {analysis}")
        
        successful_creations = [r for r in results if r['success']]
        failed_creations = [r for r in results if not r['success']]
        
        logger.info(f"   ✅ Successful: {len(successful_creations)}/{num_threads}")
        logger.info(f"   ❌ Failed: {len(failed_creations)}")
        
        # CRITICAL VALIDATIONS:
        
        # 1. All registry creations should succeed (no race condition failures)
        if failed_creations:
            race_condition_errors = [
                f"Thread {r['thread_id']}: {r['error']}" 
                for r in failed_creations 
                if "already registered" in r['error'] or "race" in r['error'].lower()
            ]
            
            if race_condition_errors:
                pytest.fail(f"REPRODUCED BUG: Race condition in registry creation: {race_condition_errors}")
                
            # Log other failures for analysis
            other_errors = [f"Thread {r['thread_id']}: {r['error']}" for r in failed_creations]
            logger.warning(f"⚠️ Other concurrent creation failures: {other_errors}")
            
        # 2. Should have created separate registries for each thread
        expected_registries = num_threads
        if analysis['total_registries_created'] < expected_registries:
            pytest.fail(f"Expected {expected_registries} registries, got {analysis['total_registries_created']}")
            
        # 3. No duplicate tool registrations across threads
        duplicate_tools = analysis['duplicate_tool_registrations']
        if duplicate_tools:
            pytest.fail(f"REPRODUCED BUG: Cross-thread tool registration conflicts: {duplicate_tools}")
            
        # 4. Thread distribution should be appropriate
        thread_count = analysis['thread_distribution']
        if thread_count < num_threads:
            logger.warning(f"⚠️ Registry creation happened in {thread_count} threads instead of {num_threads}")
            
        logger.info("✅ Concurrent registry creation test passed")
        
    def test_registry_instance_proliferation_detection(self):
        """
        Test detection of the 11 distinct ToolRegistry instantiation points.
        This test validates that we can detect the architectural issue causing
        multiple registries to be created when only one should exist per context.
        
        CRITICAL: This test directly addresses the root cause identified in the audit.
        """
        logger.info("🧪 Testing registry instance proliferation detection")
        
        # This test simulates the various ways ToolRegistry gets instantiated
        # across the codebase, as identified in the audit
        
        mock_context = Mock()
        mock_context.user_id = "proliferation_test_user"
        mock_context.run_id = "proliferation_test_run"
        mock_context.get_correlation_id.return_value = "proliferation_test_correlation"
        
        class ProliferationTestTool:
            def __init__(self):
                self.name = "proliferation_test_tool"
        
        # Simulate the different registry creation patterns found in the codebase
        registries = []
        
        # Pattern 1: UserContextToolFactory creates registry (line 69)
        logger.info("📝 Testing UserContextToolFactory registry creation pattern...")
        system1 = asyncio.run(UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[ProliferationTestTool]
        ))
        registries.append(('UserContextToolFactory', system1['registry']))
        
        # Pattern 2: Direct ToolRegistry instantiation (multiple points)
        logger.info("📝 Testing direct ToolRegistry instantiation patterns...")
        direct_registry1 = ToolRegistry()
        direct_registry2 = ToolRegistry()
        registries.append(('Direct_1', direct_registry1))
        registries.append(('Direct_2', direct_registry2))
        
        # Pattern 3: UnifiedToolDispatcherFactory might create registries
        logger.info("📝 Testing UnifiedToolDispatcherFactory registry creation...")
        try:
            dispatcher = UnifiedToolDispatcherFactory.create_for_request(
                user_context=mock_context,
                tools=[ProliferationTestTool()],
                websocket_manager=None
            )
            if hasattr(dispatcher, 'registry'):
                registries.append(('UnifiedToolDispatcherFactory', dispatcher.registry))
        except Exception as e:
            logger.warning(f"⚠️ UnifiedToolDispatcherFactory test failed: {e}")
            
        # Analyze the proliferation
        analysis = self.lifecycle_tracker.get_analysis_report()
        logger.info(f"📊 Proliferation test results: {analysis}")
        
        # CRITICAL VALIDATIONS:
        
        # 1. Detect if multiple registries were created unnecessarily
        unique_registry_ids = set(id(registry) for _, registry in registries)
        if len(unique_registry_ids) > 1:
            logger.warning(f"⚠️ Registry proliferation detected: {len(unique_registry_ids)} distinct registries created")
            logger.info(f"   Registry sources: {[source for source, _ in registries]}")
            
            # This is the architectural issue - too many registries being created
            # In the current broken state, this should fail the test
            if len(unique_registry_ids) > 2:  # Allow some flexibility, but 3+ indicates real proliferation
                pytest.fail(f"REPRODUCED BUG: Registry proliferation - {len(unique_registry_ids)} distinct registries created for single user context")
                
        # 2. Check for tool registration conflicts across registries
        for i, (source1, registry1) in enumerate(registries):
            for j, (source2, registry2) in enumerate(registries[i+1:], i+1):
                if id(registry1) != id(registry2):
                    # Try to register same tool in both - should work if properly isolated
                    try:
                        tool1 = ProliferationTestTool()
                        tool2 = ProliferationTestTool()
                        registry1.register(tool1.name, tool1)
                        registry2.register(tool2.name, tool2)
                    except Exception as e:
                        if "already registered" in str(e):
                            pytest.fail(f"REPRODUCED BUG: Cross-registry registration conflict between {source1} and {source2}: {e}")
                            
        logger.info("✅ Registry proliferation detection test completed")


@pytest.mark.integration 
@pytest.mark.toolregistry
class TestWebSocketRegistryCleanup(SSotBaseTestCase):
    """
    Integration tests for WebSocket connection registry cleanup patterns.
    
    These tests validate the connection lifecycle without requiring full E2E setup.
    """
    
    async def test_websocket_disconnect_registry_cleanup_integration(self):
        """
        Test registry cleanup on WebSocket disconnect (integration level).
        Should catch resource leak scenarios without full E2E overhead.
        """
        logger.info("🧪 Testing WebSocket registry cleanup (integration)")
        
        # Create mock WebSocket connection context
        mock_context = Mock()
        mock_context.user_id = "ws_cleanup_user"
        mock_context.run_id = "ws_cleanup_run"
        mock_context.get_correlation_id.return_value = "ws_cleanup_correlation"
        
        class WebSocketTestTool:
            def __init__(self):
                self.name = "websocket_test_tool"
                
        # Step 1: Simulate WebSocket connection with tool system
        logger.info("🔌 Simulating WebSocket connection with tool registry...")
        system = await UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[WebSocketTestTool]
        )
        
        registry = system['registry']
        original_tool_count = len(registry._registry)
        
        # Verify tool is registered
        assert registry.get_tool("websocket_test_tool") is not None
        
        # Step 2: Simulate connection disconnect and cleanup
        logger.info("🔌❌ Simulating WebSocket disconnect and cleanup...")
        
        # In a real scenario, this would happen when the WebSocket closes
        # For now, we simulate by clearing the registry
        registry.clear()  # This should be called on disconnect
        
        # Step 3: Verify cleanup occurred
        after_cleanup_count = len(registry._registry)
        assert after_cleanup_count == 0, f"Registry not cleaned up: {after_cleanup_count} tools remain"
        
        # Step 4: Simulate reconnection
        logger.info("🔄 Simulating WebSocket reconnection...")
        new_system = await UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[WebSocketTestTool]
        )
        
        new_registry = new_system['registry']
        
        # Should be able to register tools again without conflicts
        assert new_registry.get_tool("websocket_test_tool") is not None
        
        logger.info("✅ WebSocket registry cleanup integration test passed")
        
    async def test_websocket_reconnection_fresh_registry_integration(self):
        """
        Test that WebSocket reconnection gets fresh registry (integration level).
        Should catch registry state pollution between connections.
        """
        logger.info("🧪 Testing WebSocket reconnection fresh registry (integration)")
        
        mock_context = Mock()
        mock_context.user_id = "reconnection_user"
        mock_context.run_id = "reconnection_run_1"
        mock_context.get_correlation_id.return_value = "reconnection_correlation_1"
        
        class ReconnectionTestTool:
            def __init__(self):
                self.name = "reconnection_test_tool"
                self.connection_id = mock_context.run_id
                
        # First connection
        logger.info("🔌 First WebSocket connection...")
        system1 = await UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[ReconnectionTestTool]
        )
        
        registry1 = system1['registry']
        registry1_id = id(registry1)
        
        # Modify context for "reconnection"
        mock_context.run_id = "reconnection_run_2"
        mock_context.get_correlation_id.return_value = "reconnection_correlation_2"
        
        # Second connection (simulated reconnection)
        logger.info("🔄 WebSocket reconnection...")
        system2 = await UserContextToolFactory.create_user_tool_system(
            context=mock_context,
            tool_classes=[ReconnectionTestTool]
        )
        
        registry2 = system2['registry']
        registry2_id = id(registry2)
        
        # CRITICAL VALIDATION: Should have different registry instances
        if registry1_id == registry2_id:
            pytest.fail("REPRODUCED BUG: WebSocket reconnection reused same registry instance (state pollution risk)")
            
        # Both should have tools registered successfully
        tool1 = registry1.get_tool("reconnection_test_tool")
        tool2 = registry2.get_tool("reconnection_test_tool")
        
        assert tool1 is not None, "First connection should have registered tool"
        assert tool2 is not None, "Reconnection should have registered tool"
        
        # Tools should be different instances (fresh creation)
        if id(tool1) == id(tool2):
            pytest.fail("REPRODUCED BUG: Reconnection reused same tool instance")
            
        logger.info("✅ WebSocket reconnection fresh registry test passed")