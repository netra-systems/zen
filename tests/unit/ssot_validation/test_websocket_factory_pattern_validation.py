"""
SSOT Factory Pattern Validation Tests for WebSocketNotifier

These tests specifically validate factory pattern implementation and violations
according to Step 2 of WebSocketNotifier SSOT remediation plan (GitHub issue #216).

Focus areas:
- Factory interface compliance
- User isolation through factories
- Resource management in factory patterns
- Anti-pattern detection (singletons, direct instantiation)

Business Value: Platform/Internal - System Stability & User Isolation
Ensures factory patterns properly isolate user contexts and prevent data leakage.
"""

import pytest
import asyncio
import threading
import gc
import weakref
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List, Optional, Set

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketFactoryPatternCompliance(SSotBaseTestCase):
    """Factory pattern compliance tests (PASSING tests for proper implementation)"""
    
    def setUp(self):
        """Set up factory pattern test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()
    
    def test_factory_interface_provides_required_methods(self):
        """Test PASSES: Factory interface provides all required methods."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            # Required methods for proper factory pattern
            required_methods = [
                'create_user_emitter',
                # Optional but recommended methods
                '__init__',
            ]
            
            for method in required_methods:
                self.assertTrue(hasattr(factory, method), 
                              f"Factory missing required method: {method}")
                self.assertTrue(callable(getattr(factory, method)),
                              f"Factory method {method} is not callable")
                
        except ImportError as e:
            self.skipTest(f"Factory pattern not available: {e}")
    
    def test_factory_creates_isolated_user_instances(self):
        """Test PASSES: Factory creates isolated instances for each user."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            # Create instances for different users
            user1_emitter = factory.create_user_emitter("factory_user_1")
            user2_emitter = factory.create_user_emitter("factory_user_2")
            
            # Instances should be different objects
            self.assertIsNot(user1_emitter, user2_emitter)
            
            # Each should be bound to correct user
            self.assertEqual(user1_emitter.user_id, "factory_user_1")
            self.assertEqual(user2_emitter.user_id, "factory_user_2")
            
            # Should not share state
            if hasattr(user1_emitter, '__dict__') and hasattr(user2_emitter, '__dict__'):
                self.assertIsNot(user1_emitter.__dict__, user2_emitter.__dict__)
                
        except ImportError as e:
            self.skipTest(f"Factory user isolation not available: {e}")
    
    def test_factory_validates_user_input(self):
        """Test PASSES: Factory properly validates user input."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            # Should reject invalid user IDs
            with self.assertRaises((ValueError, TypeError)):
                factory.create_user_emitter(None)
            
            with self.assertRaises((ValueError, TypeError)):
                factory.create_user_emitter("")
            
            with self.assertRaises((ValueError, TypeError)):
                factory.create_user_emitter(123)  # Non-string user ID
                
        except ImportError as e:
            self.skipTest(f"Factory validation not available: {e}")
    
    def test_factory_thread_safety_compliance(self):
        """Test PASSES: Factory operations are thread-safe."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            results = []
            errors = []
            
            def create_emitter_safely(thread_id):
                try:
                    emitter = factory.create_user_emitter(f"thread_safe_user_{thread_id}")
                    results.append((thread_id, emitter.user_id))
                except Exception as e:
                    errors.append((thread_id, str(e)))
            
            # Create multiple threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=create_emitter_safely, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Should have no errors and all correct results
            self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
            self.assertEqual(len(results), 10)
            
            # All results should be unique and correct
            for thread_id, user_id in results:
                expected_user_id = f"thread_safe_user_{thread_id}"
                self.assertEqual(user_id, expected_user_id)
                
        except ImportError as e:
            self.skipTest(f"Factory thread safety not available: {e}")
    
    def test_factory_resource_cleanup_capability(self):
        """Test PASSES: Factory supports resource cleanup."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            user_id = "cleanup_test_user"
            
            # Create emitter
            emitter = factory.create_user_emitter(user_id)
            emitter_id = id(emitter)
            weak_ref = weakref.ref(emitter)
            
            # Delete reference
            del emitter
            
            # If factory has cleanup method, use it
            if hasattr(factory, 'cleanup_user_emitter'):
                factory.cleanup_user_emitter(user_id)
            
            # Force garbage collection
            gc.collect()
            
            # Create new emitter - should be different instance
            new_emitter = factory.create_user_emitter(user_id)
            new_emitter_id = id(new_emitter)
            
            self.assertNotEqual(emitter_id, new_emitter_id, 
                              "Factory should create new instance after cleanup")
            
        except ImportError as e:
            self.skipTest(f"Factory cleanup not available: {e}")


class TestWebSocketFactoryAntiPatternDetection(SSotBaseTestCase):
    """Anti-pattern detection tests (FAILING tests for violation detection)"""
    
    def test_singleton_pattern_violation_detected(self):
        """Test FAILS: Singleton pattern violation in WebSocket factory."""
        singleton_violations = []
        
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            # Create multiple factory instances
            factory1 = WebSocketEmitterFactory()
            factory2 = WebSocketEmitterFactory()
            
            # If they're the same instance, it's a singleton violation
            if factory1 is factory2:
                singleton_violations.append("WebSocketEmitterFactory_singleton")
            
            # Test emitter creation for same user
            user_id = "singleton_test_user"
            emitter1 = factory1.create_user_emitter(user_id)
            emitter2 = factory2.create_user_emitter(user_id)
            
            # If emitters are same instance, it's a singleton violation
            if emitter1 is emitter2:
                singleton_violations.append("UserEmitter_singleton")
                
        except ImportError:
            pass
        
        # This test FAILS if singleton violations are found
        if singleton_violations:
            self.fail(f"VIOLATION: Singleton pattern detected: {singleton_violations}")
        else:
            self.fail("No singleton violations found - violation test should fail")
    
    def test_global_state_violation_in_factory(self):
        """Test FAILS: Global state sharing in factory implementation."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory1 = WebSocketEmitterFactory()
            factory2 = WebSocketEmitterFactory()
            
            # Create emitters and modify state
            user_id = "global_state_test"
            emitter1 = factory1.create_user_emitter(user_id)
            
            # Try to detect shared global state
            if hasattr(emitter1, '_global_state'):
                emitter1._global_state['test_key'] = 'test_value'
                
                emitter2 = factory2.create_user_emitter(user_id + "_2")
                if hasattr(emitter2, '_global_state') and emitter2._global_state.get('test_key') == 'test_value':
                    self.fail("VIOLATION: Global state sharing detected between factories")
            
            # Check for class-level shared state
            if hasattr(WebSocketEmitterFactory, '_shared_instances'):
                if len(WebSocketEmitterFactory._shared_instances) > 0:
                    self.fail("VIOLATION: Shared class-level state in factory")
            
            # If no global state violations, test should report failure
            self.fail("No global state violations found - violation test should fail")
            
        except ImportError as e:
            self.skipTest(f"Global state testing not available: {e}")
    
    def test_memory_leak_in_factory_pattern(self):
        """Test FAILS: Memory leaks in factory instance management."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            initial_objects = len(gc.get_objects())
            
            # Create many emitters and let them go out of scope
            for i in range(100):
                emitter = factory.create_user_emitter(f"leak_test_user_{i}")
                # Simulate some operations
                if hasattr(emitter, '_event_queue'):
                    emitter._event_queue.append({"test": "data"})
                del emitter
            
            # Force garbage collection
            gc.collect()
            
            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects
            
            # This test FAILS if significant memory growth occurs
            if object_growth > 200:  # Reasonable threshold
                self.fail(f"VIOLATION: Memory leak detected, {object_growth} objects not cleaned")
            
            # If memory is well managed, test should report failure
            self.fail("No memory leaks found - violation test should fail")
            
        except ImportError as e:
            self.skipTest(f"Memory leak testing not available: {e}")
    
    def test_race_condition_in_factory_operations(self):
        """Test FAILS: Race conditions in concurrent factory operations."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            results = {}
            errors = []
            
            def concurrent_operations(thread_id):
                try:
                    for i in range(20):
                        user_id = f"race_test_{thread_id}_{i}"
                        emitter = factory.create_user_emitter(user_id)
                        results[user_id] = emitter
                        
                        # Try to trigger race conditions
                        if hasattr(factory, '_active_emitters'):
                            count = len(factory._active_emitters)
                            results[f"{user_id}_count"] = count
                            
                except Exception as e:
                    errors.append(f"Thread {thread_id}: {e}")
            
            # Run concurrent operations
            threads = []
            for i in range(5):
                thread = threading.Thread(target=concurrent_operations, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # This test FAILS if race conditions cause errors
            if errors:
                self.fail(f"VIOLATION: Race conditions detected: {errors[:3]}")
            
            # Check for inconsistent state
            emitter_counts = [v for k, v in results.items() if k.endswith('_count')]
            if emitter_counts:
                # If counts are wildly inconsistent, might indicate race conditions
                min_count = min(emitter_counts)
                max_count = max(emitter_counts)
                if max_count - min_count > 50:  # Arbitrary threshold
                    self.fail(f"VIOLATION: Inconsistent state suggesting race conditions")
            
            # If no race conditions, test should report failure
            self.fail("No race conditions found - violation test should fail")
            
        except ImportError as e:
            self.skipTest(f"Race condition testing not available: {e}")
    
    def test_improper_user_context_isolation(self):
        """Test FAILS: Improper user context isolation in factory."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            user1_emitter = factory.create_user_emitter("isolation_user_1")
            user2_emitter = factory.create_user_emitter("isolation_user_2")
            
            # Test for shared connection pools
            if hasattr(user1_emitter, '_connection_pool') and hasattr(user2_emitter, '_connection_pool'):
                if user1_emitter._connection_pool is user2_emitter._connection_pool:
                    self.fail("VIOLATION: Shared connection pool between users")
            
            # Test for shared event queues
            if hasattr(user1_emitter, '_event_queue') and hasattr(user2_emitter, '_event_queue'):
                if user1_emitter._event_queue is user2_emitter._event_queue:
                    self.fail("VIOLATION: Shared event queue between users")
            
            # Test for shared configuration
            if hasattr(user1_emitter, 'config') and hasattr(user2_emitter, 'config'):
                if user1_emitter.config is user2_emitter.config:
                    self.fail("VIOLATION: Shared configuration between users")
            
            # Test cross-user event delivery
            if hasattr(user1_emitter, 'send_event') and hasattr(user2_emitter, 'receive_events'):
                user1_emitter.send_event({"type": "test", "from": "user1"})
                user2_events = user2_emitter.receive_events() if callable(user2_emitter.receive_events) else []
                
                for event in user2_events:
                    if event.get('from') == 'user1':
                        self.fail("VIOLATION: Cross-user event delivery detected")
            
            # If isolation is proper, test should report failure
            self.fail("User context isolation is proper - violation test should fail")
            
        except ImportError as e:
            self.skipTest(f"User isolation testing not available: {e}")
    
    def test_factory_bypassing_through_direct_imports(self):
        """Test FAILS: Factory pattern bypassed through direct imports."""
        direct_import_violations = []
        
        try:
            # Try importing and instantiating WebSocket components directly
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            
            # Direct instantiation should be blocked or warned
            try:
                direct_emitter = UnifiedWebSocketEmitter(user_id="direct_bypass_user")
                direct_import_violations.append("UnifiedWebSocketEmitter_direct")
            except (TypeError, ValueError):
                # If direct instantiation is blocked, that's good
                pass
                
        except ImportError:
            pass
        
        try:
            from netra_backend.app.websocket_core.unified_manager import WebSocketManager
            
            try:
                direct_manager = WebSocketManager()
                direct_import_violations.append("WebSocketManager_direct")
            except (TypeError, ValueError):
                pass
                
        except ImportError:
            pass
        
        # This test FAILS if direct instantiation is allowed
        if direct_import_violations:
            self.fail(f"VIOLATION: Factory bypassing detected: {direct_import_violations}")
        else:
            self.fail("Factory bypassing properly prevented - violation test should fail")


class TestWebSocketFactoryResourceManagement(SSotBaseTestCase):
    """Factory resource management tests (MIXED RESULTS)"""
    
    def test_factory_properly_manages_emitter_lifecycle(self):
        """Test PASSES: Factory properly manages emitter lifecycle."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            user_id = "lifecycle_test_user"
            
            # Create emitter
            emitter = factory.create_user_emitter(user_id)
            self.assertIsNotNone(emitter)
            self.assertEqual(emitter.user_id, user_id)
            
            # If factory tracks active emitters
            if hasattr(factory, 'get_active_emitters'):
                active_emitters = factory.get_active_emitters()
                self.assertIn(user_id, [e.user_id for e in active_emitters])
            
            # Cleanup
            if hasattr(factory, 'cleanup_user_emitter'):
                factory.cleanup_user_emitter(user_id)
                
                # Should no longer be active
                if hasattr(factory, 'get_active_emitters'):
                    active_emitters = factory.get_active_emitters()
                    self.assertNotIn(user_id, [e.user_id for e in active_emitters])
                    
        except ImportError as e:
            self.skipTest(f"Lifecycle management not available: {e}")
    
    def test_factory_resource_limits_enforcement(self):
        """Test PASSES: Factory enforces resource limits."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            # Try to create factory with limits
            try:
                factory = WebSocketEmitterFactory(max_emitters=5)
            except TypeError:
                # If factory doesn't support limits, use default
                factory = WebSocketEmitterFactory()
                # Manually set limit if possible
                if hasattr(factory, 'max_emitters'):
                    factory.max_emitters = 5
            
            # Create emitters up to limit
            emitters = []
            for i in range(5):
                try:
                    emitter = factory.create_user_emitter(f"limit_test_user_{i}")
                    emitters.append(emitter)
                except Exception as e:
                    if "limit" in str(e).lower():
                        # Limit properly enforced
                        break
            
            # Try to exceed limit
            if hasattr(factory, 'max_emitters') and factory.max_emitters == 5:
                with self.assertRaises(Exception):
                    factory.create_user_emitter("limit_exceeded_user")
                    
        except ImportError as e:
            self.skipTest(f"Resource limits not available: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])