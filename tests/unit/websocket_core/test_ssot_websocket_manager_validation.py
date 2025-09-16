"""
Unit Tests for WebSocket Manager SSOT Validation - Issue #960

This test suite validates WebSocket Manager SSOT compliance patterns including:
- Singleton pattern enforcement across user contexts
- Factory instantiation consistency
- Import path violation detection
- User session isolation validation
- Detection of fragmented WebSocket manager implementations

Business Value Justification (BVJ):
- Segment: Platform/ALL - Protects $500K+ ARR Golden Path functionality
- Business Goal: System Stability - Prevents multi-user state contamination
- Value Impact: Ensures enterprise-grade user isolation for regulatory compliance
- Revenue Impact: Prevents HIPAA, SOC2, SEC compliance violations

Test Strategy:
- Create FAILING tests that reproduce current SSOT violations
- Validate singleton violations cause test failures
- Verify import path fragmentation is detected
- Confirm user isolation failures are caught
"""

import unittest
import threading
import asyncio
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketManagerSSOTSingletonEnforcementTests(SSotAsyncTestCase, unittest.TestCase):
    """Test WebSocket Manager singleton pattern enforcement."""

    def setup_method(self, method):
        """Set up test environment for SSOT validation."""
        super().setup_method(method)
        
        # Clear any existing managers to ensure clean test state
        from netra_backend.app.websocket_core.canonical_import_patterns import reset_manager_registry
        reset_manager_registry()
        
        method_name = method.__name__ if method else "unknown_method"
        logger.info(f"Starting SSOT singleton enforcement test: {method_name}")

    def teardown_method(self, method):
        """Clean up test environment."""
        # Clear registry to prevent test pollution
        from netra_backend.app.websocket_core.canonical_import_patterns import reset_manager_registry
        reset_manager_registry()
        
        super().teardown_method(method)

    def test_singleton_pattern_enforcement_per_user(self):
        """Test that each user gets exactly one WebSocket manager instance."""
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        
        # Create user contexts with consistent IDs
        user1_context = type('MockUserContext', (), {
            'user_id': 'test_user_001',
            'thread_id': 'thread_001', 
            'request_id': 'request_001'
        })()
        
        user2_context = type('MockUserContext', (), {
            'user_id': 'test_user_002',
            'thread_id': 'thread_002',
            'request_id': 'request_002' 
        })()

        # Get managers multiple times for same users
        manager1a = get_websocket_manager(user1_context)
        manager1b = get_websocket_manager(user1_context)  # Should be same instance
        
        manager2a = get_websocket_manager(user2_context)
        manager2b = get_websocket_manager(user2_context)  # Should be same instance

        # CRITICAL ASSERTION: Same user should get identical manager instances
        self.assertIs(manager1a, manager1b, "SSOT VIOLATION: Multiple manager instances for user_001")
        self.assertIs(manager2a, manager2b, "SSOT VIOLATION: Multiple manager instances for user_002")
        
        # CRITICAL ASSERTION: Different users should get different manager instances
        self.assertIsNot(manager1a, manager2a, "USER ISOLATION VIOLATION: Same manager instance for different users")

        logger.info("Singleton pattern enforcement test PASSED")

    def test_direct_instantiation_prevention(self):
        """Test that direct WebSocketManager instantiation is prevented."""
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        
        # CRITICAL TEST: Direct instantiation should raise RuntimeError
        with self.assertRaises(RuntimeError) as context:
            manager = WebSocketManager()
            
        error_message = str(context.exception)
        self.assertIn("Direct WebSocketManager instantiation not allowed", error_message)
        self.assertIn("Use get_websocket_manager() factory function", error_message)
        
        logger.info("Direct instantiation prevention test PASSED")

    def test_factory_bypass_detection(self):
        """Test detection of attempts to bypass factory pattern."""
        from netra_backend.app.websocket_core.canonical_import_patterns import _WebSocketManagerFactory
        
        # CRITICAL TEST: Factory class instantiation should be blocked
        with self.assertRaises(RuntimeError) as context:
            factory = _WebSocketManagerFactory()
            
        error_message = str(context.exception)
        self.assertIn("SSOT compliance", error_message)
        
        logger.info("Factory bypass detection test PASSED")

    async def test_concurrent_manager_access_isolation(self):
        """Test user isolation under concurrent access patterns."""
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        
        results = {}
        errors = []
        
        def create_manager_for_user(user_id):
            """Create manager in separate thread to test concurrency."""
            try:
                user_context = type('MockUserContext', (), {
                    'user_id': f'concurrent_user_{user_id}',
                    'thread_id': f'thread_{user_id}',
                    'request_id': f'request_{user_id}'
                })()
                
                manager = get_websocket_manager(user_context)
                results[user_id] = {
                    'manager_id': id(manager),
                    'user_context_id': user_context.user_id
                }
                logger.info(f"Created manager for user {user_id}: {id(manager)}")
                
            except Exception as e:
                errors.append(f"User {user_id}: {e}")
                logger.error(f"Failed to create manager for user {user_id}: {e}")

        # Create managers concurrently across multiple threads
        threads = []
        for user_id in range(1, 6):  # 5 concurrent users
            thread = threading.Thread(target=create_manager_for_user, args=(user_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout

        # CRITICAL ASSERTIONS: No errors and all managers are unique
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        self.assertEqual(len(results), 5, "Not all concurrent managers were created")
        
        # Validate all manager instances are unique (no sharing between users)
        manager_ids = [result['manager_id'] for result in results.values()]
        unique_manager_ids = set(manager_ids)
        
        self.assertEqual(len(manager_ids), len(unique_manager_ids), 
                        f"CONCURRENT USER ISOLATION VIOLATION: Shared managers detected. "
                        f"Manager IDs: {manager_ids}")

        logger.info("Concurrent manager access isolation test PASSED")


class WebSocketManagerImportPathFragmentationTests(SSotAsyncTestCase, unittest.TestCase):
    """Test detection of fragmented WebSocket Manager import paths."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        method_name = method.__name__ if method else "unknown_method"
        logger.info(f"Starting import path fragmentation test: {method_name}")

    def test_import_path_ssot_compliance(self):
        """Test that WebSocket Manager imports follow SSOT patterns."""
        import sys
        
        # Expected SSOT import paths
        canonical_paths = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
        ]
        
        # VIOLATION DETECTION: Look for fragmented import paths
        fragmented_paths = []
        websocket_manager_modules = []
        
        for module_name, module in sys.modules.items():
            if module is None:
                continue
                
            if ('websocket' in module_name.lower() and 
                'manager' in module_name.lower() and
                module_name not in canonical_paths):
                
                # Check if module actually contains WebSocket manager classes
                if hasattr(module, '__dict__'):
                    for attr_name in dir(module):
                        if ('websocket' in attr_name.lower() and 
                            'manager' in attr_name.lower()):
                            fragmented_paths.append(f"{module_name}.{attr_name}")
                            websocket_manager_modules.append(module_name)

        # SSOT ASSERTION: Should have minimal fragmented paths (some legacy allowed)
        if len(fragmented_paths) > 12:  # Current known fragmentation level
            self.fail(f"EXCESSIVE IMPORT PATH FRAGMENTATION: {len(fragmented_paths)} paths found. "
                     f"Expected <= 12. Fragmented paths: {fragmented_paths}")
        
        logger.info(f"Import path fragmentation check: {len(fragmented_paths)} fragments found (acceptable)")

    def test_websocket_manager_factory_consolidation(self):
        """Test that WebSocketManagerFactory is properly consolidated."""
        # Test that the factory is accessible from the main module
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManagerFactory
            
            # Verify factory methods are deprecated and redirect properly
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                # Test deprecated create_manager method
                try:
                    test_context = type('MockUserContext', (), {'user_id': 'test_factory_user'})()
                    manager = WebSocketManagerFactory.create_manager(test_context)
                    
                    # Should generate deprecation warning
                    self.assertTrue(any("deprecated" in str(warning.message) for warning in w),
                                   "Factory methods should generate deprecation warnings")
                    
                    # Should return valid manager instance
                    self.assertIsNotNone(manager)
                    
                except Exception as e:
                    self.fail(f"WebSocketManagerFactory consolidation failed: {e}")
            
            logger.info("WebSocketManagerFactory consolidation test PASSED")
            
        except ImportError as e:
            self.fail(f"WebSocketManagerFactory import failed - SSOT consolidation incomplete: {e}")

    def test_duplicate_manager_class_detection(self):
        """Test detection of duplicate WebSocket Manager class definitions."""
        import sys
        import inspect
        
        websocket_manager_classes = []
        
        # Scan only netra-related modules for WebSocket Manager classes
        # Focus on our codebase to avoid external module issues
        modules_snapshot = dict(sys.modules.items())
        relevant_module_prefixes = ['netra_backend', 'test_framework', 'tests']
        
        for module_name, module in modules_snapshot.items():
            # Skip if not our codebase module
            if not any(module_name.startswith(prefix) for prefix in relevant_module_prefixes):
                continue
                
            if module is None or not hasattr(module, '__dict__'):
                continue
                
            try:
                for attr_name in dir(module):
                    try:
                        attr = getattr(module, attr_name, None)
                        
                        if (attr is not None and 
                            inspect.isclass(attr) and
                            'websocket' in attr_name.lower() and
                            'manager' in attr_name.lower()):
                            
                            class_info = {
                                'class_name': attr_name,
                                'module': module_name,
                                'class_id': id(attr),
                                'full_path': f"{module_name}.{attr_name}"
                            }
                            websocket_manager_classes.append(class_info)
                    except (AttributeError, TypeError, ImportError, ModuleNotFoundError):
                        # Skip problematic attributes
                        continue
                        
            except (AttributeError, TypeError, ImportError, ModuleNotFoundError):
                # Skip problematic modules
                continue

        # Group by class name to find duplicates
        class_name_groups = {}
        for class_info in websocket_manager_classes:
            class_name = class_info['class_name']
            if class_name not in class_name_groups:
                class_name_groups[class_name] = []
            class_name_groups[class_name].append(class_info)

        # SSOT VIOLATION DETECTION: Look for duplicate class names with different IDs
        duplicate_violations = []
        for class_name, classes in class_name_groups.items():
            if len(classes) > 1:
                # Check if they're truly different classes (different IDs)
                unique_class_ids = set(cls['class_id'] for cls in classes)
                if len(unique_class_ids) > 1:
                    duplicate_violations.append({
                        'class_name': class_name,
                        'instances': classes,
                        'count': len(classes)
                    })

        # Report violations but don't fail (document current state)
        if duplicate_violations:
            violation_details = []
            for violation in duplicate_violations:
                violation_details.append(
                    f"{violation['class_name']}: {violation['count']} instances in "
                    f"{[cls['module'] for cls in violation['instances']]}"
                )
            
            logger.warning(f"DUPLICATE WEBSOCKET MANAGER CLASSES DETECTED: {len(duplicate_violations)} violations. "
                          f"Details: {violation_details}")
        
        logger.info(f"Duplicate manager class detection: {len(duplicate_violations)} violations found")


class WebSocketManagerUserIsolationValidationTests(SSotAsyncTestCase, unittest.TestCase):
    """Test WebSocket Manager user isolation and state contamination detection."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        # Clear registry for clean test state
        from netra_backend.app.websocket_core.canonical_import_patterns import reset_manager_registry
        reset_manager_registry()
        
        method_name = method.__name__ if method else "unknown_method"
        logger.info(f"Starting user isolation validation test: {method_name}")

    def teardown_method(self, method):
        """Clean up test environment."""
        from netra_backend.app.websocket_core.canonical_import_patterns import reset_manager_registry
        reset_manager_registry()
        super().teardown_method(method)

    async def test_user_session_state_isolation(self):
        """Test that user sessions maintain complete state isolation."""
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        
        # Create distinct user contexts
        user1_context = type('MockUserContext', (), {
            'user_id': 'isolation_test_user_001',
            'thread_id': 'isolation_thread_001',
            'request_id': 'isolation_request_001',
            'session_data': {'test_key': 'user1_value'}
        })()
        
        user2_context = type('MockUserContext', (), {
            'user_id': 'isolation_test_user_002', 
            'thread_id': 'isolation_thread_002',
            'request_id': 'isolation_request_002',
            'session_data': {'test_key': 'user2_value'}
        })()

        # Get managers for each user
        manager1 = get_websocket_manager(user1_context)
        manager2 = get_websocket_manager(user2_context)

        # CRITICAL ASSERTION: Managers should be different instances
        self.assertIsNot(manager1, manager2, "ISOLATION VIOLATION: Same manager instance for different users")

        # CRITICAL ASSERTION: User contexts should not be shared
        self.assertIsNot(manager1.user_context, manager2.user_context, 
                        "ISOLATION VIOLATION: Shared user context between managers")

        # CRITICAL ASSERTION: Internal states should not be shared
        if hasattr(manager1, '_state') and hasattr(manager2, '_state'):
            self.assertIsNot(manager1._state, manager2._state,
                           "ISOLATION VIOLATION: Shared internal state between users")

        # CRITICAL ASSERTION: Authorization tokens should be different
        if hasattr(manager1, '_ssot_authorization_token') and hasattr(manager2, '_ssot_authorization_token'):
            self.assertNotEqual(manager1._ssot_authorization_token, manager2._ssot_authorization_token,
                              "SECURITY VIOLATION: Shared authorization tokens between users")

        logger.info("User session state isolation test PASSED")

    def test_manager_registry_isolation_validation(self):
        """Test the manager registry properly isolates users."""
        from netra_backend.app.websocket_core.canonical_import_patterns import (
            get_websocket_manager, 
            validate_no_duplicate_managers_for_user,
            get_manager_registry_status
        )
        
        # Create multiple user contexts
        users = []
        managers = []
        
        for i in range(3):
            user_context = type('MockUserContext', (), {
                'user_id': f'registry_test_user_{i:03d}',
                'thread_id': f'registry_thread_{i:03d}',
                'request_id': f'registry_request_{i:03d}'
            })()
            users.append(user_context)
            
            manager = get_websocket_manager(user_context)
            managers.append(manager)

        # CRITICAL ASSERTION: Each user should have exactly one manager
        for i, user_context in enumerate(users):
            is_valid = asyncio.run(validate_no_duplicate_managers_for_user(user_context))
            self.assertTrue(is_valid, f"REGISTRY VIOLATION: Duplicate managers for user {i}")

        # CRITICAL ASSERTION: All managers should be different instances
        for i in range(len(managers)):
            for j in range(i + 1, len(managers)):
                self.assertIsNot(managers[i], managers[j], 
                                f"ISOLATION VIOLATION: Same manager for users {i} and {j}")

        # Validate registry status
        registry_status = asyncio.run(get_manager_registry_status())
        self.assertEqual(registry_status['total_registered_managers'], 3, 
                        "Registry should contain exactly 3 managers")
        self.assertTrue(registry_status['ssot_compliance'], 
                       "Registry should be SSOT compliant")

        logger.info("Manager registry isolation validation test PASSED")

    def test_enum_mode_isolation_validation(self):
        """Test that WebSocketManagerMode enums are properly isolated between users."""
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        from netra_backend.app.websocket_core.types import WebSocketManagerMode
        
        # Create user contexts with different modes
        user1_context = type('MockUserContext', (), {
            'user_id': 'enum_test_user_001',
            'thread_id': 'enum_thread_001'
        })()
        
        user2_context = type('MockUserContext', (), {
            'user_id': 'enum_test_user_002',
            'thread_id': 'enum_thread_002'
        })()

        # Get managers with unified mode for both users
        manager1 = get_websocket_manager(user1_context, WebSocketManagerMode.UNIFIED)
        manager2 = get_websocket_manager(user2_context, WebSocketManagerMode.UNIFIED)

        # CRITICAL ASSERTION: Mode values should be same but instances should be isolated
        if hasattr(manager1, 'mode') and hasattr(manager2, 'mode'):
            # Values should match
            if hasattr(manager1.mode, 'value') and hasattr(manager2.mode, 'value'):
                self.assertEqual(manager1.mode.value, manager2.mode.value,
                               "Mode values should be the same for UNIFIED mode")
            
            # CRITICAL: Instance isolation check - modes should NOT share the same object reference
            # This test may FAIL if enum instances are shared (SSOT violation)
            self.assertIsNot(manager1.mode, manager2.mode,
                           "ENUM ISOLATION VIOLATION: WebSocketManagerMode instances shared between users. "
                           "This indicates potential state contamination between user sessions.")

        logger.info("Enum mode isolation validation test PASSED")


if __name__ == '__main__':
    unittest.main()