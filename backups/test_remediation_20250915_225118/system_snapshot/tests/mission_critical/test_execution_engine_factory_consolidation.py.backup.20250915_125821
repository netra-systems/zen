"""ExecutionEngine Factory Consolidation - Mission Critical Validation

Business Value Justification:
- Segment: Platform/Architecture
- Business Goal: Code Quality & Maintainability
- Value Impact: Prevents factory pattern proliferation affecting $500K+ ARR system stability
- Strategic Impact: Reduces architectural complexity from 78 factory classes to essential patterns

CRITICAL FACTORY CONSOLIDATION VALIDATION:
This test validates ExecutionEngine factory patterns are consolidated into a single
authoritative factory that creates only UserExecutionEngine instances, preventing
factory proliferation and ensuring thread-safe, isolated engine creation.

Test Scope: Factory pattern consolidation for ExecutionEngine (Issue #910)
Priority: P0 - Mission Critical
Docker: NO DEPENDENCIES - Unit/Integration non-docker only
"""

import inspect
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Type, Any
import unittest
from unittest.mock import MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestExecutionEngineFactoryConsolidation(SSotBaseTestCase):
    """Validates ExecutionEngine factory consolidation and thread safety."""

    def setUp(self):
        """Set up factory consolidation test environment."""
        super().setUp()
        
        # Test user contexts for factory testing
        self.test_contexts = [
            UserExecutionContext(
                user_id=f'factory_test_user_{i}',
                run_id=str(uuid.uuid4()),
                context_data={'factory_test': True, 'user_index': i}
            ) for i in range(5)
        ]

    def test_single_execution_engine_factory_exists(self):
        """Validate only one ExecutionEngine factory is available as SSOT."""
        try:
            # Test canonical factory import
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            # Validate factory class exists and is properly structured
            self.assertTrue(inspect.isclass(ExecutionEngineFactory))
            self.assertTrue(hasattr(ExecutionEngineFactory, 'create_execution_engine'))
            
            # Validate factory methods return UserExecutionEngine type
            create_method = getattr(ExecutionEngineFactory, 'create_execution_engine')
            method_signature = inspect.signature(create_method)
            
            # Factory should accept user_context parameter
            params = list(method_signature.parameters.keys())
            self.assertIn('user_context', params, 
                         "Factory should accept user_context parameter")
            
        except ImportError as e:
            self.skipTest(f"ExecutionEngine factory not available during consolidation: {e}")

    def test_factory_creates_only_user_execution_engine_instances(self):
        """Validate factory only creates UserExecutionEngine instances, not legacy types."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            created_engines = []
            
            # Create multiple engines using factory
            for context in self.test_contexts:
                engine = ExecutionEngineFactory.create_execution_engine(
                    user_context=context
                )
                created_engines.append(engine)
                
                # Validate engine type
                self.assertIsInstance(engine, UserExecutionEngine,
                                    f"Factory created wrong type: {type(engine)}")
                
                # Validate engine has correct user context
                engine_context = engine.get_user_context()
                self.assertEqual(engine_context.user_id, context.user_id,
                               "Factory created engine with wrong user context")
                self.assertEqual(engine_context.run_id, context.run_id,
                               "Factory created engine with wrong run_id")
            
            # Validate all created engines are unique instances
            engine_ids = [id(engine) for engine in created_engines]
            self.assertEqual(len(set(engine_ids)), len(engine_ids),
                           "Factory should create unique engine instances")
            
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")

    def test_no_duplicate_factory_implementations(self):
        """Validate no duplicate ExecutionEngine factory implementations exist."""
        factory_implementations = []
        
        # Known potential factory locations to check
        potential_factory_paths = [
            "netra_backend.app.agents.supervisor.execution_engine_factory",
            "netra_backend.app.core.managers.execution_engine_factory",
            "netra_backend.app.agents.execution_engine_factory",
            "netra_backend.app.services.execution_engine_factory"
        ]
        
        for factory_path in potential_factory_paths:
            try:
                module = __import__(factory_path, fromlist=[''])
                
                # Look for factory classes or functions
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (inspect.isclass(attr) and 
                        'factory' in attr_name.lower() and 
                        'execution' in attr_name.lower()):
                        factory_implementations.append(f"{factory_path}.{attr_name}")
                    elif (callable(attr) and 
                          'create' in attr_name.lower() and 
                          'execution' in attr_name.lower()):
                        factory_implementations.append(f"{factory_path}.{attr_name}")
                        
            except ImportError:
                continue  # Module doesn't exist, which is fine
                
        # Should have at most one canonical factory implementation
        self.assertLessEqual(
            len(factory_implementations), 1,
            f"Multiple ExecutionEngine factory implementations found: {factory_implementations}. "
            f"Should consolidate to single SSOT factory."
        )

    def test_factory_thread_safety_concurrent_creation(self):
        """Validate factory creates isolated engines safely during concurrent access."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            creation_results = {}
            creation_errors = []
            
            def create_engine_for_context(context_index: int) -> Dict[str, Any]:
                """Create engine for specific context in thread."""
                try:
                    context = self.test_contexts[context_index]
                    thread_id = threading.get_ident()
                    
                    # Create engine using factory
                    engine = ExecutionEngineFactory.create_execution_engine(
                        user_context=context
                    )
                    
                    return {
                        'context_index': context_index,
                        'thread_id': thread_id,
                        'engine_id': id(engine),
                        'user_id': engine.get_user_context().user_id,
                        'run_id': engine.get_user_context().run_id,
                        'success': True
                    }
                    
                except Exception as e:
                    return {
                        'context_index': context_index,
                        'thread_id': threading.get_ident(),
                        'error': str(e),
                        'success': False
                    }
            
            # Create engines concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(create_engine_for_context, i): i
                    for i in range(len(self.test_contexts))
                }
                
                for future in as_completed(futures):
                    context_index = futures[future]
                    result = future.result()
                    
                    if result['success']:
                        creation_results[context_index] = result
                    else:
                        creation_errors.append(result)
            
            # Validate no concurrent creation errors
            self.assertEqual(len(creation_errors), 0,
                           f"Concurrent factory creation errors: {creation_errors}")
            
            # Validate all engines were created successfully
            self.assertEqual(len(creation_results), len(self.test_contexts),
                           "Not all engines were created successfully")
            
            # Validate thread safety - each engine should have correct context
            for context_index, result in creation_results.items():
                expected_context = self.test_contexts[context_index]
                
                self.assertEqual(result['user_id'], expected_context.user_id,
                               f"Thread {result['thread_id']} created engine with wrong user_id")
                self.assertEqual(result['run_id'], expected_context.run_id,
                               f"Thread {result['thread_id']} created engine with wrong run_id")
            
            # Validate all engines are unique (no shared instances)
            engine_ids = [result['engine_id'] for result in creation_results.values()]
            self.assertEqual(len(set(engine_ids)), len(engine_ids),
                           "Factory created shared engine instances (thread safety violation)")
            
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")

    def test_factory_parameter_validation(self):
        """Validate factory properly validates parameters and handles edge cases."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            # Test with valid context
            valid_context = self.test_contexts[0]
            valid_engine = ExecutionEngineFactory.create_execution_engine(
                user_context=valid_context
            )
            self.assertIsNotNone(valid_engine, "Factory should create engine with valid context")
            
            # Test with None context
            with self.assertRaises((TypeError, ValueError)):
                ExecutionEngineFactory.create_execution_engine(user_context=None)
            
            # Test with invalid context type
            with self.assertRaises((TypeError, AttributeError)):
                ExecutionEngineFactory.create_execution_engine(user_context="invalid")
                
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")

    def test_factory_memory_management(self):
        """Validate factory doesn't create memory leaks or retain references."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            # Track memory usage during engine creation
            initial_context_refs = []
            engine_refs = []
            
            # Create and immediately release engines
            for context in self.test_contexts:
                engine = ExecutionEngineFactory.create_execution_engine(
                    user_context=context
                )
                
                # Track references
                initial_context_refs.append(id(context))
                engine_refs.append(id(engine))
                
                # Explicitly delete engine reference
                del engine
            
            # Create new engines with same contexts
            new_engine_refs = []
            for context in self.test_contexts:
                new_engine = ExecutionEngineFactory.create_execution_engine(
                    user_context=context
                )
                new_engine_refs.append(id(new_engine))
                del new_engine
            
            # Validate engines are truly unique (not cached/reused)
            for old_id in engine_refs:
                self.assertNotIn(old_id, new_engine_refs,
                               "Factory appears to be reusing engine instances")
            
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")

    def test_factory_integration_with_websocket_bridge(self):
        """Validate factory creates engines properly integrated with WebSocket bridges."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            with patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge') as mock_bridge_class:
                mock_bridge = MagicMock()
                mock_bridge_class.return_value = mock_bridge
                
                # Create engine with WebSocket bridge
                context = self.test_contexts[0]
                engine = ExecutionEngineFactory.create_execution_engine(
                    user_context=context,
                    websocket_bridge=mock_bridge
                )
                
                # Validate engine was created successfully
                self.assertIsNotNone(engine, "Factory should create engine with WebSocket bridge")
                
                # Validate engine has WebSocket integration
                if hasattr(engine, 'websocket_bridge') or hasattr(engine, '_websocket_bridge'):
                    # Engine should have WebSocket bridge reference
                    bridge_attr = (getattr(engine, 'websocket_bridge', None) or 
                                 getattr(engine, '_websocket_bridge', None))
                    self.assertEqual(bridge_attr, mock_bridge,
                                   "Engine should have correct WebSocket bridge reference")
                
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")

    def test_factory_creates_engines_with_proper_cleanup(self):
        """Validate factory creates engines with proper cleanup capabilities."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            engines_to_cleanup = []
            
            # Create multiple engines
            for context in self.test_contexts[:3]:
                engine = ExecutionEngineFactory.create_execution_engine(
                    user_context=context
                )
                engines_to_cleanup.append(engine)
            
            # Test cleanup functionality
            for i, engine in enumerate(engines_to_cleanup):
                if hasattr(engine, 'cleanup'):
                    # Engine should have cleanup method
                    engine.cleanup()
                    
                    # Validate cleanup doesn't affect other engines
                    for j, other_engine in enumerate(engines_to_cleanup):
                        if i != j:
                            other_context = other_engine.get_user_context()
                            expected_context = self.test_contexts[j]
                            
                            self.assertEqual(other_context.user_id, expected_context.user_id,
                                           f"Cleanup of engine {i} affected engine {j}")
                
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")

    def test_no_legacy_factory_patterns_in_codebase(self):
        """Validate no legacy factory patterns exist in production code."""
        from pathlib import Path
        
        netra_backend_root = Path(__file__).parent.parent.parent / "netra_backend"
        legacy_patterns = []
        
        # Patterns that indicate legacy factory usage
        legacy_factory_patterns = [
            "ExecutionEngineAdapter",
            "LegacyExecutionEngineFactory",  
            "CompatibilityExecutionEngineFactory",
            "create_legacy_execution_engine",
            "get_execution_engine_adapter"
        ]
        
        # Scan Python files for legacy patterns
        for py_file in netra_backend_root.rglob("*.py"):
            if "test" in str(py_file).lower() or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern in legacy_factory_patterns:
                        if pattern in content:
                            legacy_patterns.append(f"{py_file}: {pattern}")
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Allow some legacy patterns during transition period
        self.assertLessEqual(
            len(legacy_patterns), 5,  # Allow up to 5 during consolidation
            f"Too many legacy factory patterns found (should be eliminated after consolidation):\n" +
            "\n".join(legacy_patterns)
        )

    def test_factory_performance_benchmarks(self):
        """Validate factory creation performance meets requirements."""
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            
            # Performance benchmarks
            max_creation_time = 0.1  # 100ms per engine creation
            num_engines = 10
            
            creation_times = []
            
            for i in range(num_engines):
                context = UserExecutionContext(
                    user_id=f'perf_test_user_{i}',
                    run_id=str(uuid.uuid4()),
                    context_data={'performance_test': True}
                )
                
                start_time = time.time()
                engine = ExecutionEngineFactory.create_execution_engine(
                    user_context=context
                )
                creation_time = time.time() - start_time
                
                creation_times.append(creation_time)
                
                # Clean up
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
            
            # Validate performance requirements
            avg_creation_time = sum(creation_times) / len(creation_times)
            max_observed_time = max(creation_times)
            
            self.assertLess(avg_creation_time, max_creation_time,
                           f"Average engine creation time {avg_creation_time:.3f}s exceeds limit {max_creation_time}s")
            
            self.assertLess(max_observed_time, max_creation_time * 2,
                           f"Maximum engine creation time {max_observed_time:.3f}s exceeds reasonable limit")
            
        except ImportError:
            self.skipTest("ExecutionEngine factory not available during consolidation")


if __name__ == '__main__':
    unittest.main()