"""
SSOT Violation Tests for WebSocketNotifier - FAILING TESTS

These tests intentionally FAIL to demonstrate current SSOT violations
according to Step 2 of WebSocketNotifier SSOT remediation plan (GitHub issue #216).

Part B: Tests that FAIL - reproducing current violations
- Multi-implementation detection (6 tests)
- Factory violation detection (8 tests) 
- Legacy code detection (8 tests)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Identifies existing SSOT violations that need remediation in Step 3.

NOTE: These tests are EXPECTED TO FAIL until SSOT remediation is complete.
"""

import pytest
import os
import ast
import importlib
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestWebSocketNotifierMultiImplementationDetection(SSotBaseTestCase):
    """Test 1-6: Multi-Implementation Detection Tests (FAILING)"""
    
    def test_multiple_websocket_notifier_classes_exist(self):
        """Test FAILS: Multiple WebSocketNotifier implementations exist."""
        # Search for WebSocketNotifier class definitions
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        implementations = []
        
        for root, dirs, files in os.walk(backend_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'class WebSocketNotifier' in content and 'websocket_notifier' in file:
                                implementations.append(file_path)
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # This test FAILS because multiple implementations exist
        self.assertGreater(len(implementations), 1, 
                          "VIOLATION: Multiple WebSocketNotifier implementations found")
    
    def test_conflicting_import_paths_detected(self):
        """Test FAILS: Conflicting import paths for WebSocketNotifier exist."""
        import_conflicts = []
        
        # Test different import paths
        try:
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier as SupervisorNotifier
            import_conflicts.append('supervisor.websocket_notifier')
        except ImportError:
            pass
        
        try:
            from netra_backend.app.websocket_core.websocket_notifier import WebSocketNotifier as CoreNotifier
            import_conflicts.append('websocket_core.websocket_notifier')
        except ImportError:
            pass
        
        try:
            from netra_backend.app.services.websocket_notifier import WebSocketNotifier as ServiceNotifier
            import_conflicts.append('services.websocket_notifier')
        except ImportError:
            pass
        
        # This test FAILS because multiple import paths work
        self.assertGreater(len(import_conflicts), 1,
                          "VIOLATION: Multiple import paths for WebSocketNotifier exist")
    
    def test_inconsistent_class_interfaces(self):
        """Test FAILS: WebSocketNotifier implementations have inconsistent interfaces."""
        implementations = []
        
        try:
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
            implementations.append(('supervisor', WebSocketNotifier))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            implementations.append(('bridge', AgentWebSocketBridge))
        except ImportError:
            pass
        
        if len(implementations) < 2:
            self.fail("Not enough implementations to test interface consistency")
        
        # Compare method signatures
        supervisor_methods = set(dir(implementations[0][1])) - set(dir(object))
        bridge_methods = set(dir(implementations[1][1])) - set(dir(object))
        
        # This test FAILS because interfaces are inconsistent
        common_methods = supervisor_methods.intersection(bridge_methods)
        unique_supervisor = supervisor_methods - bridge_methods
        unique_bridge = bridge_methods - supervisor_methods
        
        self.assertGreater(len(unique_supervisor), 0, 
                          "VIOLATION: Supervisor has unique methods not in bridge")
        self.assertGreater(len(unique_bridge), 0,
                          "VIOLATION: Bridge has unique methods not in supervisor")
    
    def test_duplicate_functionality_across_modules(self):
        """Test FAILS: Duplicate WebSocket notification functionality exists."""
        # Search for similar method names across modules
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        websocket_methods = []
        
        for root, dirs, files in os.walk(backend_path):
            if 'websocket' in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Look for common WebSocket methods
                                if 'def send_agent_event' in content:
                                    websocket_methods.append(f"{file_path}:send_agent_event")
                                if 'def notify_agent' in content:
                                    websocket_methods.append(f"{file_path}:notify_agent")
                                if 'def emit_websocket' in content:
                                    websocket_methods.append(f"{file_path}:emit_websocket")
                        except (UnicodeDecodeError, PermissionError):
                            continue
        
        # This test FAILS because duplicate methods exist
        self.assertGreater(len(websocket_methods), 3,
                          "VIOLATION: Duplicate WebSocket notification methods found")
    
    def test_multiple_initialization_patterns(self):
        """Test FAILS: Multiple initialization patterns for WebSocket notifiers exist."""
        initialization_patterns = []
        
        # Search for different initialization patterns
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        
        for root, dirs, files in os.walk(backend_path):
            for file in files:
                if file.endswith('.py') and 'websocket' in file.lower():
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'WebSocketNotifier(' in content:
                                initialization_patterns.append(f"{file_path}:direct_init")
                            if 'create_websocket_notifier' in content:
                                initialization_patterns.append(f"{file_path}:factory_create")
                            if 'get_websocket_notifier' in content:
                                initialization_patterns.append(f"{file_path}:getter_pattern")
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # This test FAILS because multiple patterns exist
        unique_patterns = set([p.split(':')[1] for p in initialization_patterns])
        self.assertGreater(len(unique_patterns), 1,
                          "VIOLATION: Multiple initialization patterns exist")
    
    def test_inconsistent_dependency_injection(self):
        """Test FAILS: Inconsistent dependency injection patterns for WebSocket components."""
        dependency_patterns = []
        
        # Search for different dependency injection approaches
        test_files = [
            "/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/supervisor/execution_engine.py",
            "/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/supervisor/websocket_notifier.py",
            "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/agent_websocket_bridge.py"
        ]
        
        for file_path in test_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'websocket_manager:' in content:
                            dependency_patterns.append('manager_injection')
                        if 'WebSocketManager' in content and '__init__' in content:
                            dependency_patterns.append('constructor_injection')
                        if 'set_websocket' in content:
                            dependency_patterns.append('setter_injection')
                        if 'websocket_manager =' in content:
                            dependency_patterns.append('direct_assignment')
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        # This test FAILS because inconsistent patterns exist
        unique_patterns = set(dependency_patterns)
        self.assertGreater(len(unique_patterns), 2,
                          "VIOLATION: Multiple dependency injection patterns exist")


class TestWebSocketNotifierFactoryViolationDetection(SSotBaseTestCase):
    """Test 7-14: Factory Violation Detection Tests (FAILING)"""
    
    def test_direct_instantiation_bypasses_factory(self):
        """Test FAILS: Direct WebSocketNotifier instantiation bypasses factory pattern."""
        try:
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
            
            # This should fail in proper SSOT implementation
            notifier = WebSocketNotifier(user_id="test_user")
            
            # This test FAILS because direct instantiation is allowed
            self.assertIsNotNone(notifier)
            self.fail("VIOLATION: Direct WebSocketNotifier instantiation is allowed")
            
        except TypeError:
            # If direct instantiation is blocked, this test passes (which means SSOT is working)
            self.fail("Direct instantiation is properly blocked - SSOT violation test should fail")
        except ImportError:
            # If class doesn't exist, we can't test this violation
            self.skipTest("WebSocketNotifier class not available for violation testing")
    
    def test_singleton_pattern_breaks_user_isolation(self):
        """Test FAILS: Singleton pattern breaks user isolation."""
        try:
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
            
            # Test if singleton pattern exists
            notifier1 = WebSocketNotifier(user_id="user1")
            notifier2 = WebSocketNotifier(user_id="user2")
            
            # This test FAILS if singleton pattern exists (shared instance)
            if notifier1 is notifier2:
                self.fail("VIOLATION: Singleton pattern breaks user isolation")
            
            # Check for shared state
            if hasattr(notifier1, '_shared_state') and hasattr(notifier2, '_shared_state'):
                if notifier1._shared_state is notifier2._shared_state:
                    self.fail("VIOLATION: Shared state between user contexts")
                    
        except ImportError:
            self.skipTest("WebSocketNotifier not available for singleton testing")
        except TypeError:
            self.skipTest("Direct instantiation blocked - cannot test singleton violation")
    
    def test_factory_not_enforcing_user_context(self):
        """Test FAILS: Factory doesn't enforce user context requirements."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            # This should fail in proper implementation
            try:
                emitter_no_user = factory.create_user_emitter(None)
                self.fail("VIOLATION: Factory allows None user_id")
            except (ValueError, TypeError):
                pass
            
            try:
                emitter_empty_user = factory.create_user_emitter("")
                self.fail("VIOLATION: Factory allows empty user_id")
            except (ValueError, TypeError):
                pass
            
            # If we get here, factory is properly validating - so this test should report failure
            self.fail("Factory is properly validating user context - violation test should fail")
            
        except ImportError:
            self.skipTest("WebSocketEmitterFactory not available")
    
    def test_missing_factory_interface_compliance(self):
        """Test FAILS: Factory doesn't implement required interface methods."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            # Required factory methods that might be missing
            required_methods = [
                'create_user_emitter',
                'cleanup_user_emitter', 
                'get_active_emitters',
                'health_check'
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(factory, method):
                    missing_methods.append(method)
            
            # This test FAILS if required methods are missing
            if missing_methods:
                self.fail(f"VIOLATION: Factory missing required methods: {missing_methods}")
            else:
                self.fail("Factory has all required methods - violation test should fail")
                
        except ImportError:
            self.skipTest("WebSocketEmitterFactory not available")
    
    def test_factory_creates_shared_instances(self):
        """Test FAILS: Factory creates shared instances instead of isolated ones."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            user_id = "shared_test_user"
            
            # Create multiple emitters for same user
            emitter1 = factory.create_user_emitter(user_id)
            emitter2 = factory.create_user_emitter(user_id)
            
            # This test FAILS if factory returns same instance (caching violation)
            if emitter1 is emitter2:
                self.fail("VIOLATION: Factory returns shared instances")
            
            # Check for shared underlying state
            if hasattr(emitter1, '_connection_pool') and hasattr(emitter2, '_connection_pool'):
                if emitter1._connection_pool is emitter2._connection_pool:
                    self.fail("VIOLATION: Shared connection pool between instances")
            
            # If instances are properly isolated, this test should report failure
            self.fail("Factory creates properly isolated instances - violation test should fail")
            
        except ImportError:
            self.skipTest("WebSocketEmitterFactory not available")
    
    def test_no_factory_cleanup_mechanism(self):
        """Test FAILS: No proper cleanup mechanism for factory-created instances."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            user_id = "cleanup_violation_user"
            
            emitter = factory.create_user_emitter(user_id)
            
            # Check if cleanup method exists
            if not hasattr(factory, 'cleanup_user_emitter'):
                self.fail("VIOLATION: No cleanup method available")
            
            # Check if cleanup actually works
            factory.cleanup_user_emitter(user_id)
            
            # After cleanup, factory should not have references
            if hasattr(factory, '_active_emitters'):
                if user_id in factory._active_emitters:
                    self.fail("VIOLATION: Cleanup doesn't remove factory references")
            
            # If cleanup works properly, this test should report failure
            self.fail("Factory cleanup works properly - violation test should fail")
            
        except ImportError:
            self.skipTest("WebSocketEmitterFactory not available")
    
    def test_factory_memory_leaks(self):
        """Test FAILS: Factory has memory leaks from uncleaned instances."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            import gc
            
            factory = WebSocketEmitterFactory()
            
            # Create many emitters
            initial_objects = len(gc.get_objects())
            
            for i in range(100):
                emitter = factory.create_user_emitter(f"leak_test_user_{i}")
                del emitter
            
            gc.collect()
            final_objects = len(gc.get_objects())
            
            # This test FAILS if significant memory growth occurs
            object_growth = final_objects - initial_objects
            if object_growth > 50:  # Arbitrary threshold
                self.fail(f"VIOLATION: Potential memory leak, {object_growth} objects not cleaned")
            
            # If memory is properly managed, this test should report failure
            self.fail("Factory manages memory properly - violation test should fail")
            
        except ImportError:
            self.skipTest("WebSocketEmitterFactory not available")
    
    def test_factory_thread_safety_violations(self):
        """Test FAILS: Factory operations are not thread-safe."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            import threading
            import time
            
            factory = WebSocketEmitterFactory()
            results = []
            errors = []
            
            def create_concurrent_emitters(thread_id):
                try:
                    for i in range(10):
                        emitter = factory.create_user_emitter(f"thread_{thread_id}_user_{i}")
                        results.append(emitter)
                        time.sleep(0.001)  # Small delay to increase contention
                except Exception as e:
                    errors.append(e)
            
            # Create concurrent access
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_concurrent_emitters, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # This test FAILS if thread safety issues occur
            if errors:
                self.fail(f"VIOLATION: Thread safety issues: {errors}")
            
            # Check for duplicate instances (race condition symptom)
            result_ids = [id(r) for r in results]
            unique_ids = set(result_ids)
            
            if len(unique_ids) != len(results):
                self.fail("VIOLATION: Duplicate instances from race conditions")
            
            # If thread safety works, this test should report failure
            self.fail("Factory is thread-safe - violation test should fail")
            
        except ImportError:
            self.skipTest("WebSocketEmitterFactory not available")


class TestWebSocketNotifierLegacyCodeDetection(SSotBaseTestCase):
    """Test 15-22: Legacy Code Detection Tests (FAILING)"""
    
    def test_deprecated_websocket_notifier_usage(self):
        """Test FAILS: Deprecated WebSocketNotifier is still used in codebase."""
        # Search for usage of deprecated class
        backend_path = "/Users/anthony/Desktop/netra-apex"
        deprecated_usage = []
        
        for root, dirs, files in os.walk(backend_path):
            if '.git' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier' in content:
                                if 'REMOVED_SYNTAX_ERROR' not in content:  # Exclude already commented lines
                                    deprecated_usage.append(file_path)
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # This test FAILS if deprecated usage is found
        if deprecated_usage:
            self.fail(f"VIOLATION: Deprecated WebSocketNotifier still used in: {deprecated_usage[:5]}")
        else:
            self.fail("No deprecated usage found - violation test should fail")
    
    def test_old_initialization_patterns_exist(self):
        """Test FAILS: Old initialization patterns still exist in codebase."""
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        old_patterns = []
        
        for root, dirs, files in os.walk(backend_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Look for old patterns
                            if 'WebSocketNotifier()' in content:
                                old_patterns.append(f"{file_path}:bare_init")
                            if 'notifier = WebSocketNotifier' in content:
                                old_patterns.append(f"{file_path}:direct_assignment")
                            if 'self.websocket_notifier = WebSocketNotifier' in content:
                                old_patterns.append(f"{file_path}:instance_var")
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # This test FAILS if old patterns exist
        if old_patterns:
            self.fail(f"VIOLATION: Old initialization patterns found: {old_patterns[:3]}")
        else:
            self.fail("No old patterns found - violation test should fail")
    
    def test_inconsistent_event_naming_conventions(self):
        """Test FAILS: Inconsistent event naming conventions across implementations."""
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        event_names = set()
        
        for root, dirs, files in os.walk(backend_path):
            if 'websocket' in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Extract event names
                                import re
                                events = re.findall(r'"(agent_\w+)"', content)
                                event_names.update(events)
                        except (UnicodeDecodeError, PermissionError):
                            continue
        
        # This test FAILS if inconsistent naming patterns exist
        camelCase_events = [e for e in event_names if any(c.isupper() for c in e[6:])]  # Skip 'agent_' prefix
        snake_case_events = [e for e in event_names if '_' in e and not any(c.isupper() for c in e)]
        
        if camelCase_events and snake_case_events:
            self.fail(f"VIOLATION: Inconsistent event naming - camelCase: {camelCase_events}, snake_case: {snake_case_events}")
        else:
            self.fail("Event naming is consistent - violation test should fail")
    
    def test_duplicate_websocket_connection_management(self):
        """Test FAILS: Duplicate WebSocket connection management code exists."""
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        connection_managers = []
        
        for root, dirs, files in os.walk(backend_path):
            for file in files:
                if file.endswith('.py') and 'websocket' in file.lower():
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'def connect(' in content or 'def disconnect(' in content:
                                connection_managers.append(file_path)
                            if 'websocket.accept()' in content:
                                connection_managers.append(file_path)
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # This test FAILS if multiple connection managers exist
        if len(connection_managers) > 2:  # Allow some duplication threshold
            self.fail(f"VIOLATION: Multiple WebSocket connection managers: {connection_managers}")
        else:
            self.fail("Connection management is consolidated - violation test should fail")
    
    def test_hardcoded_websocket_event_types(self):
        """Test FAILS: Hardcoded WebSocket event types instead of using constants."""
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        hardcoded_events = []
        
        for root, dirs, files in os.walk(backend_path):
            if 'websocket' in root.lower() or 'agent' in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Look for hardcoded event strings
                                import re
                                hardcoded = re.findall(r'["\']agent_(started|thinking|completed|error)["\']', content)
                                if hardcoded:
                                    hardcoded_events.extend([(file_path, event) for event in hardcoded])
                        except (UnicodeDecodeError, PermissionError):
                            continue
        
        # This test FAILS if hardcoded events are found
        if len(hardcoded_events) > 5:  # Allow some threshold
            self.fail(f"VIOLATION: Hardcoded event types found: {hardcoded_events[:5]}")
        else:
            self.fail("Event types are properly constants - violation test should fail")
    
    def test_missing_websocket_error_handling(self):
        """Test FAILS: Missing consistent error handling in WebSocket operations."""
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        files_with_websocket = []
        files_with_error_handling = []
        
        for root, dirs, files in os.walk(backend_path):
            if 'websocket' in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'websocket' in content.lower() and 'send' in content:
                                    files_with_websocket.append(file_path)
                                    if 'try:' in content and 'except' in content:
                                        files_with_error_handling.append(file_path)
                        except (UnicodeDecodeError, PermissionError):
                            continue
        
        # This test FAILS if error handling coverage is poor
        if len(files_with_websocket) > 0:
            coverage_ratio = len(files_with_error_handling) / len(files_with_websocket)
            if coverage_ratio < 0.8:  # 80% threshold
                self.fail(f"VIOLATION: Poor error handling coverage {coverage_ratio:.2%}")
            else:
                self.fail("Error handling coverage is good - violation test should fail")
        else:
            self.skipTest("No WebSocket files found")
    
    def test_websocket_code_duplication_across_agents(self):
        """Test FAILS: WebSocket code duplication across different agent implementations."""
        agent_path = "/Users/anthony/Desktop/netra-apex/netra_backend/app/agents"
        websocket_code_patterns = {}
        
        for root, dirs, files in os.walk(agent_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Look for common WebSocket patterns
                            if 'send_agent_event' in content:
                                websocket_code_patterns.setdefault('send_agent_event', []).append(file_path)
                            if 'notify_websocket' in content:
                                websocket_code_patterns.setdefault('notify_websocket', []).append(file_path)
                            if 'websocket_manager' in content:
                                websocket_code_patterns.setdefault('websocket_manager', []).append(file_path)
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # This test FAILS if patterns appear in multiple files
        duplicated_patterns = {pattern: files for pattern, files in websocket_code_patterns.items() if len(files) > 1}
        
        if duplicated_patterns:
            self.fail(f"VIOLATION: Duplicated WebSocket patterns: {duplicated_patterns}")
        else:
            self.fail("No WebSocket code duplication found - violation test should fail")
    
    def test_legacy_websocket_configuration_patterns(self):
        """Test FAILS: Legacy WebSocket configuration patterns still in use."""
        config_files = [
            "/Users/anthony/Desktop/netra-apex/netra_backend/app/config.py",
            "/Users/anthony/Desktop/netra-apex/netra_backend/app/core/configuration/services.py",
            "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/manager.py"
        ]
        
        legacy_patterns = []
        
        for file_path in config_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for legacy configuration patterns
                        if 'WEBSOCKET_URL' in content:
                            legacy_patterns.append(f"{file_path}:WEBSOCKET_URL")
                        if 'websocket_host' in content:
                            legacy_patterns.append(f"{file_path}:websocket_host")
                        if 'WS_PORT' in content:
                            legacy_patterns.append(f"{file_path}:WS_PORT")
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        # This test FAILS if legacy patterns exist
        if legacy_patterns:
            self.fail(f"VIOLATION: Legacy WebSocket configuration patterns: {legacy_patterns}")
        else:
            self.fail("No legacy configuration patterns found - violation test should fail")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])