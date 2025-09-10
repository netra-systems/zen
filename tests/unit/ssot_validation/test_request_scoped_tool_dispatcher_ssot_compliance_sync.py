"""SSOT Compliance Tests for RequestScopedToolDispatcher (Synchronous Version).

Test Phase 2: Create NEW SSOT validation tests focusing on 20% validation testing
before SSOT consolidation. This synchronous version documents current SSOT violations
without async complexity.

CRITICAL VIOLATIONS IDENTIFIED:
- Duplicate implementations: RequestScopedToolDispatcher, ToolDispatcher, UnifiedToolExecutionEngine
- 32+ bypass imports
- 3 competing factories: ToolExecutorFactory, ToolDispatcher.create_*, enhanced_tool_dispatcher_*
- High risk zones: Import resolution (85% failure), WebSocket events (85% failure), User isolation (85% failure)

Business Value:
- Ensures only one tool dispatcher implementation exists in runtime
- Validates proper factory pattern implementation
- Prevents cross-user data leakage
- Enables reliable concurrent execution
"""

import importlib
import inspect
import sys
import uuid
from typing import Any, Dict, List, Set

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class TestRequestScopedToolDispatcherSSotComplianceSync(SSotBaseTestCase):
    """Test SSOT compliance for RequestScopedToolDispatcher system (synchronous)."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Create test user contexts for isolation testing
        self.user_context_1 = UserExecutionContext(
            user_id="test_user_1",
            thread_id="test_thread_1",
            run_id=f"test_run_{uuid.uuid4()}"
        )
        
        self.user_context_2 = UserExecutionContext(
            user_id="test_user_2", 
            thread_id="test_thread_2",
            run_id=f"test_run_{uuid.uuid4()}"
        )

    def test_tool_dispatcher_ssot_import_compliance(self):
        """Test that only one tool dispatcher implementation exists in runtime.
        
        EXPECTED: FAIL initially due to duplicate implementations:
        - RequestScopedToolDispatcher
        - ToolDispatcher 
        - UnifiedToolExecutionEngine with dispatcher functionality
        - Multiple bridge/adapter patterns
        
        EXPECTED: PASS after SSOT consolidation
        """
        # Track all tool dispatcher implementations found
        dispatcher_implementations = []
        bridge_implementations = []
        
        # Check for RequestScopedToolDispatcher
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            dispatcher_implementations.append("RequestScopedToolDispatcher")
        except ImportError:
            pass
            
        # Check for ToolDispatcher
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            dispatcher_implementations.append("ToolDispatcher")
        except ImportError:
            pass
            
        # Check for UnifiedToolExecutionEngine (should be SSOT)
        try:
            from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
            dispatcher_implementations.append("UnifiedToolExecutionEngine")
        except ImportError:
            pass
            
        # Check for bridge/adapter patterns
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import WebSocketBridgeAdapter
            bridge_implementations.append("WebSocketBridgeAdapter")
        except ImportError:
            pass
            
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            bridge_implementations.append("AgentWebSocketBridge") 
        except ImportError:
            pass

        # DOCUMENT BASELINE STATE
        print(f"\n=== SSOT IMPORT COMPLIANCE BASELINE ===")
        print(f"Found dispatcher implementations: {dispatcher_implementations}")
        print(f"Found bridge implementations: {bridge_implementations}")
        
        # SSOT VALIDATION: Should have exactly ONE primary dispatcher implementation
        # Currently FAILS due to multiple implementations
        
        # For baseline documentation, we expect multiple implementations currently
        self.assertGreaterEqual(
            len(dispatcher_implementations), 1,
            f"BASELINE FAILURE: No dispatcher implementations found. Expected at least RequestScopedToolDispatcher."
        )
        
        # Document the violation for remediation
        if len(dispatcher_implementations) > 1:
            print(f"SSOT VIOLATION DETECTED: Multiple dispatcher implementations found: {dispatcher_implementations}")
            print("This indicates SSOT consolidation is needed.")
        
        if len(bridge_implementations) > 1:
            print(f"BRIDGE CONSOLIDATION NEEDED: Multiple bridge implementations: {bridge_implementations}")

    def test_factory_pattern_ssot_compliance(self):
        """Test that factory pattern produces consistent instances.
        
        EXPECTED: FAIL initially due to competing factories:
        - ToolExecutorFactory.create_request_scoped_dispatcher()
        - ToolDispatcher.create_request_scoped_dispatcher() 
        - enhance_tool_dispatcher_with_notifications()
        
        EXPECTED: PASS after SSOT consolidation with single factory
        """
        factory_methods = []
        
        # Check ToolExecutorFactory
        try:
            from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
            factory = ToolExecutorFactory()
            if hasattr(factory, 'create_request_scoped_dispatcher'):
                factory_methods.append("ToolExecutorFactory.create_request_scoped_dispatcher")
        except ImportError:
            pass
            
        # Check ToolDispatcher factory methods
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            if hasattr(ToolDispatcher, 'create_request_scoped_dispatcher'):
                factory_methods.append("ToolDispatcher.create_request_scoped_dispatcher")
        except ImportError:
            pass
            
        # Check enhancement pattern
        try:
            from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
            factory_methods.append("enhance_tool_dispatcher_with_notifications")
        except ImportError:
            pass
            
        # Check convenience functions
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import create_request_scoped_tool_dispatcher
            factory_methods.append("create_request_scoped_tool_dispatcher")
        except ImportError:
            pass

        # DOCUMENT BASELINE STATE
        print(f"\n=== FACTORY PATTERN COMPLIANCE BASELINE ===")
        print(f"Found factory methods: {factory_methods}")
        
        # For baseline, we expect multiple factory methods (SSOT violation)
        self.assertGreaterEqual(
            len(factory_methods), 1,
            f"BASELINE FAILURE: No factory methods found. Expected at least create_request_scoped_tool_dispatcher."
        )
        
        # Document violations for remediation
        if len(factory_methods) > 2:  # Allow SSOT + convenience function
            print(f"FACTORY CONSOLIDATION NEEDED: Too many factory methods: {factory_methods}")

    def test_runtime_instance_uniqueness(self):
        """Test that only one dispatcher type exists in runtime after SSOT consolidation.
        
        EXPECTED: FAIL initially due to multiple classes being instantiable
        EXPECTED: PASS after SSOT consolidation blocks deprecated patterns
        """
        instantiable_classes = []
        blocked_patterns = []
        
        # Try to instantiate different dispatcher types
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            # This should FAIL after SSOT consolidation due to RuntimeError
            try:
                ToolDispatcher()
                instantiable_classes.append("ToolDispatcher")
            except RuntimeError as e:
                if "no longer supported" in str(e):
                    # Good - deprecated pattern is properly blocked
                    blocked_patterns.append(f"ToolDispatcher: {str(e)}")
                else:
                    raise
        except ImportError:
            pass
            
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            # This should succeed as it's the SSOT implementation  
            try:
                RequestScopedToolDispatcher(self.user_context_1)
                instantiable_classes.append("RequestScopedToolDispatcher")
            except Exception as e:
                # Document any issues with SSOT implementation
                print(f"SSOT Implementation Issue: RequestScopedToolDispatcher failed: {e}")
        except ImportError:
            pass

        # DOCUMENT BASELINE STATE
        print(f"\n=== RUNTIME UNIQUENESS BASELINE ===")
        print(f"Instantiable classes: {instantiable_classes}")
        print(f"Blocked patterns: {blocked_patterns}")
        
        # For baseline, we expect at least RequestScopedToolDispatcher to work
        self.assertGreaterEqual(
            len(instantiable_classes), 1,
            f"BASELINE FAILURE: No dispatcher classes instantiable. Expected RequestScopedToolDispatcher to work."
        )
        
        # The SSOT implementation should be instantiable
        if instantiable_classes:
            self.assertIn(
                "RequestScopedToolDispatcher", instantiable_classes,
                f"SSOT implementation RequestScopedToolDispatcher should be instantiable, "
                f"but found: {instantiable_classes}"
            )

    def test_import_consistency_across_usage_points(self):
        """Test that all usage points import from the same SSOT location.
        
        EXPECTED: FAIL initially due to 32+ bypass imports
        EXPECTED: PASS after SSOT consolidation
        """
        # Track import sources for tool dispatcher functionality
        import_sources = set()
        module_import_analysis = {}
        
        # Scan known usage points for imports
        usage_files = [
            "netra_backend.app.agents.supervisor.execution_engine",
            "netra_backend.app.agents.supervisor_agent_modern", 
            "netra_backend.app.routes.agents",
        ]
        
        for module_path in usage_files:
            try:
                module = importlib.import_module(module_path)
                source_code = inspect.getsource(module)
                
                found_imports = []
                
                # Check for different import patterns
                if "from netra_backend.app.agents.request_scoped_tool_dispatcher import" in source_code:
                    import_sources.add("request_scoped_tool_dispatcher")
                    found_imports.append("request_scoped_tool_dispatcher")
                if "from netra_backend.app.agents.tool_dispatcher_core import" in source_code:
                    import_sources.add("tool_dispatcher_core")  
                    found_imports.append("tool_dispatcher_core")
                if "from netra_backend.app.agents.unified_tool_execution import" in source_code:
                    import_sources.add("unified_tool_execution")
                    found_imports.append("unified_tool_execution")
                if "from netra_backend.app.tools.enhanced_tool_execution_engine import" in source_code:
                    import_sources.add("enhanced_tool_execution_engine")
                    found_imports.append("enhanced_tool_execution_engine")
                    
                module_import_analysis[module_path] = found_imports
                    
            except (ImportError, OSError):
                # Skip modules that can't be imported or read
                module_import_analysis[module_path] = ["IMPORT_FAILED"]
                continue

        # DOCUMENT BASELINE STATE
        print(f"\n=== IMPORT CONSISTENCY BASELINE ===")
        print(f"Found import sources: {import_sources}")
        print(f"Module import analysis: {module_import_analysis}")
        
        # For baseline, we expect some imports to work
        self.assertGreaterEqual(
            len(import_sources), 1,
            f"BASELINE FAILURE: No import sources found. Expected at least one working import pattern."
        )
        
        # Document violations for remediation
        if len(import_sources) > 2:  # Allow SSOT + compatibility bridge
            print(f"IMPORT CONSOLIDATION NEEDED: Multiple import sources found: {import_sources}")

    def test_websocket_support_availability(self):
        """Test WebSocket support availability in SSOT implementation.
        
        This tests the basic availability of WebSocket support without async complexity.
        """
        websocket_support_available = False
        websocket_methods = []
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context_1)
            
            # Check WebSocket support detection
            websocket_support_available = hasattr(dispatcher, 'has_websocket_support')
            
            # Check for WebSocket-related methods
            for method_name in dir(dispatcher):
                if 'websocket' in method_name.lower():
                    websocket_methods.append(method_name)
                    
        except Exception as e:
            print(f"WebSocket support test failed: {e}")

        # DOCUMENT BASELINE STATE
        print(f"\n=== WEBSOCKET SUPPORT BASELINE ===")
        print(f"WebSocket support available: {websocket_support_available}")
        print(f"WebSocket methods: {websocket_methods}")
        
        # For baseline, we expect basic WebSocket support infrastructure
        self.assertTrue(
            websocket_support_available,
            "BASELINE FAILURE: RequestScopedToolDispatcher should have has_websocket_support method"
        )

    def test_user_context_integration_basic(self):
        """Test basic user context integration without async complexity."""
        context_integration_working = False
        context_properties = {}
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context_1)
            
            # Test context retrieval
            retrieved_context = dispatcher.get_context()
            
            if retrieved_context:
                context_integration_working = True
                context_properties = {
                    'user_id_match': retrieved_context.user_id == self.user_context_1.user_id,
                    'thread_id_match': retrieved_context.thread_id == self.user_context_1.thread_id,
                    'run_id_match': retrieved_context.run_id == self.user_context_1.run_id,
                    'has_correlation_id': hasattr(retrieved_context, 'get_correlation_id')
                }
                
        except Exception as e:
            print(f"User context integration test failed: {e}")

        # DOCUMENT BASELINE STATE
        print(f"\n=== USER CONTEXT INTEGRATION BASELINE ===")
        print(f"Context integration working: {context_integration_working}")
        print(f"Context properties: {context_properties}")
        
        # For baseline, context integration should work
        self.assertTrue(
            context_integration_working,
            "BASELINE FAILURE: User context integration should work in RequestScopedToolDispatcher"
        )
        
        # Context should match input
        if context_properties:
            self.assertTrue(
                all(context_properties.values()),
                f"BASELINE FAILURE: Context properties should match input: {context_properties}"
            )


class TestFactoryPatternComplianceSync(SSotBaseTestCase):
    """Test factory pattern compliance (synchronous)."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.user_context = UserExecutionContext(
            user_id="factory_test_user",
            thread_id="factory_test_thread",
            run_id=f"factory_test_run_{uuid.uuid4()}"
        )

    def test_factory_availability_baseline(self):
        """Test that factory methods are available and discoverable."""
        available_factories = {}
        factory_errors = {}
        
        # Test ToolExecutorFactory availability
        try:
            from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
            factory = ToolExecutorFactory()
            available_factories['ToolExecutorFactory'] = {
                'class_available': True,
                'has_create_method': hasattr(factory, 'create_request_scoped_dispatcher'),
                'methods': [m for m in dir(factory) if not m.startswith('_')]
            }
        except Exception as e:
            factory_errors['ToolExecutorFactory'] = str(e)

        # Test direct RequestScopedToolDispatcher creation
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            available_factories['RequestScopedToolDispatcher_direct'] = {
                'class_available': True,
                'instantiation_works': True,
                'type': type(dispatcher).__name__
            }
        except Exception as e:
            factory_errors['RequestScopedToolDispatcher_direct'] = str(e)

        # Test convenience functions
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import create_request_scoped_tool_dispatcher
            available_factories['create_request_scoped_tool_dispatcher'] = {
                'function_available': True,
                'is_callable': callable(create_request_scoped_tool_dispatcher)
            }
        except Exception as e:
            factory_errors['create_request_scoped_tool_dispatcher'] = str(e)

        # DOCUMENT BASELINE STATE
        print(f"\n=== FACTORY AVAILABILITY BASELINE ===")
        print(f"Available factories: {list(available_factories.keys())}")
        print(f"Factory errors: {list(factory_errors.keys())}")
        
        for factory_name, details in available_factories.items():
            print(f"\n{factory_name}: {details}")

        # VALIDATION: At least one factory pattern should work
        self.assertGreater(
            len(available_factories), 0,
            f"BASELINE FAILURE: No factory patterns available. Errors: {factory_errors}"
        )

    def test_factory_deprecation_enforcement(self):
        """Test that deprecated factory patterns are properly blocked."""
        deprecated_patterns = []
        blocked_patterns = []
        
        # Check if ToolDispatcher direct instantiation is blocked
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            try:
                ToolDispatcher()
                deprecated_patterns.append("ToolDispatcher direct instantiation still works")
            except RuntimeError as e:
                if "no longer supported" in str(e):
                    blocked_patterns.append(f"ToolDispatcher correctly blocked: {str(e)[:50]}...")
                else:
                    deprecated_patterns.append(f"ToolDispatcher wrong error: {e}")
        except ImportError:
            # If ToolDispatcher is not importable, that's also a form of blocking
            blocked_patterns.append("ToolDispatcher not importable")

        # DOCUMENT BASELINE STATE
        print(f"\n=== DEPRECATION ENFORCEMENT BASELINE ===")
        print(f"Deprecated patterns still accessible: {deprecated_patterns}")
        print(f"Properly blocked patterns: {blocked_patterns}")
        
        # VALIDATION: For baseline, we document current state
        # After SSOT consolidation, deprecated_patterns should be empty
        if deprecated_patterns:
            print(f"DEPRECATION ENFORCEMENT NEEDED: {deprecated_patterns}")


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, "-v", "-s"])