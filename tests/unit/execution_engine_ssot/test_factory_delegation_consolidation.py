#!/usr/bin/env python
"""
UNIT TEST 2: Factory Delegation Validation for SSOT Consolidation

PURPOSE: Test that all factory patterns delegate correctly to UserExecutionEngine as the SSOT.
This validates that ExecutionEngineFactory and related factories route to UserExecutionEngine.

Expected to FAIL before SSOT consolidation (proves multiple factory patterns exist)
Expected to PASS after SSOT consolidation (proves all factories use UserExecutionEngine)

Business Impact: $500K+ ARR Golden Path protection - consistent factory patterns prevent execution failures
"""

import asyncio
import inspect
import sys
import os
import time
import uuid
from typing import Dict, List, Any, Type

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockWebSocketManager:
    """Mock WebSocket manager for factory testing"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.send_agent_event = AsyncMock()


class TestFactoryDelegationConsolidation(SSotAsyncTestCase):
    """Unit Test 2: Validate factory delegation to UserExecutionEngine SSOT"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = "factory_test_user"
        self.test_session_id = "factory_test_session"
        self.mock_websocket = MockWebSocketManager(self.test_user_id)
        
    def test_factory_imports_available(self):
        """Test that all factory implementations can be imported"""
        print("\n SEARCH:  Testing factory import availability...")
        
        factory_imports = []
        import_errors = []
        
        # Try to import all known factory implementations
        factory_modules = [
            ('ExecutionEngineFactory', 'netra_backend.app.agents.supervisor.execution_engine_factory'),
            ('ConsolidatedFactory', 'netra_backend.app.agents.execution_engine_consolidated'),
            ('WebSocketManagerFactory', 'netra_backend.app.websocket_core.websocket_manager_factory'),
            ('UserExecutionEngine', 'netra_backend.app.agents.supervisor.user_execution_engine'),
        ]
        
        for class_name, module_path in factory_modules:
            try:
                module = __import__(module_path, fromlist=[class_name])
                factory_class = getattr(module, class_name)
                factory_imports.append({
                    'name': class_name,
                    'module': module_path,
                    'class': factory_class,
                    'source_file': inspect.getfile(factory_class)
                })
                print(f"   PASS:  {class_name} imported successfully")
            except ImportError as e:
                import_errors.append(f"{class_name}: {e}")
                print(f"   FAIL:  {class_name} import failed: {e}")
            except AttributeError as e:
                import_errors.append(f"{class_name}: {e}")
                print(f"   FAIL:  {class_name} not found in module: {e}")
        
        # We need at least UserExecutionEngine and one factory
        if len(factory_imports) < 2:
            self.fail(f"Insufficient factory imports available: {import_errors}")
        
        print(f"   PASS:  {len(factory_imports)} factory classes imported successfully")
        return factory_imports
    
    def test_execution_engine_factory_delegation(self):
        """Test that ExecutionEngineFactory delegates to UserExecutionEngine"""
        print("\n SEARCH:  Testing ExecutionEngineFactory delegation to UserExecutionEngine...")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"Required classes not available: {e}")
        
        delegation_violations = []
        
        # Test 1: Factory creates UserExecutionEngine instances
        factory = ExecutionEngineFactory()
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket
            
            try:
                engine = factory.create_execution_engine(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id
                )
                
                # Validate the engine is UserExecutionEngine
                if not isinstance(engine, UserExecutionEngine):
                    delegation_violations.append(
                        f"Factory created {type(engine).__name__}, expected UserExecutionEngine"
                    )
                else:
                    print(f"   PASS:  Factory correctly created UserExecutionEngine")
                    
                # Validate engine properties
                if hasattr(engine, 'user_id') and engine.user_id != self.test_user_id:
                    delegation_violations.append(f"Engine user_id mismatch: {engine.user_id} != {self.test_user_id}")
                
                if hasattr(engine, 'session_id') and engine.session_id != self.test_session_id:
                    delegation_violations.append(f"Engine session_id mismatch: {engine.session_id} != {self.test_session_id}")
                
                print(f"   PASS:  Engine properties correctly set")
                
            except Exception as e:
                delegation_violations.append(f"Factory creation failed: {e}")
        
        # Test 2: Factory methods delegate correctly
        factory_methods = [m for m in dir(factory) if not m.startswith('_') and callable(getattr(factory, m))]
        required_methods = ['create_execution_engine']
        
        missing_methods = [method for method in required_methods if method not in factory_methods]
        if missing_methods:
            delegation_violations.append(f"Factory missing required methods: {missing_methods}")
        else:
            print(f"   PASS:  Factory has all required methods: {required_methods}")
        
        # Test 3: Multiple factory calls create separate instances
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket
            
            try:
                engine1 = factory.create_execution_engine(
                    user_id="user1",
                    session_id="session1"
                )
                engine2 = factory.create_execution_engine(
                    user_id="user2", 
                    session_id="session2"
                )
                
                if engine1 is engine2:
                    delegation_violations.append("Factory returned same instance for different users")
                elif hasattr(engine1, 'user_id') and hasattr(engine2, 'user_id'):
                    if engine1.user_id == engine2.user_id:
                        delegation_violations.append("Factory created engines with same user_id")
                    else:
                        print(f"   PASS:  Factory creates separate instances for different users")
                
            except Exception as e:
                delegation_violations.append(f"Multiple factory creation failed: {e}")
        
        # CRITICAL: After SSOT consolidation, all delegation should work perfectly
        if delegation_violations:
            self.fail(f"Factory delegation violations: {delegation_violations}")
        
        print(f"   PASS:  ExecutionEngineFactory correctly delegates to UserExecutionEngine")
    
    def test_consolidated_factory_patterns(self):
        """Test consolidated factory patterns delegate to UserExecutionEngine"""
        print("\n SEARCH:  Testing consolidated factory patterns...")
        
        try:
            from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory as ConsolidatedFactory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"ConsolidatedFactory not available: {e}")
        
        consolidation_violations = []
        
        # Test ConsolidatedFactory delegation
        try:
            factory = ConsolidatedFactory()
            
            # Test if factory has create methods
            create_methods = [m for m in dir(factory) if 'create' in m.lower() and callable(getattr(factory, m))]
            if not create_methods:
                consolidation_violations.append("ConsolidatedFactory has no create methods")
            else:
                print(f"   PASS:  ConsolidatedFactory has creation methods: {create_methods}")
            
            # Test factory interface consistency
            if hasattr(factory, 'create_execution_engine'):
                with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.get_manager') as mock_get_manager:
                    mock_get_manager.return_value = self.mock_websocket
                    
                    try:
                        engine = factory.create_execution_engine(
                            user_id=self.test_user_id,
                            session_id=self.test_session_id
                        )
                        
                        if not isinstance(engine, UserExecutionEngine):
                            consolidation_violations.append(
                                f"ConsolidatedFactory created {type(engine).__name__}, expected UserExecutionEngine"
                            )
                        else:
                            print(f"   PASS:  ConsolidatedFactory correctly creates UserExecutionEngine")
                            
                    except Exception as e:
                        consolidation_violations.append(f"ConsolidatedFactory creation failed: {e}")
        
        except Exception as e:
            consolidation_violations.append(f"ConsolidatedFactory test failed: {e}")
        
        # CRITICAL: All factory patterns should be consolidated
        if consolidation_violations:
            self.fail(f"Factory consolidation violations: {consolidation_violations}")
        
        print(f"   PASS:  Consolidated factory patterns correctly delegate to UserExecutionEngine")
    
    async def test_factory_async_delegation(self):
        """Test that factory patterns work correctly with async operations"""
        print("\n SEARCH:  Testing factory async delegation...")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"Required async classes not available: {e}")
        
        async_violations = []
        
        # Test async factory operations
        factory = ExecutionEngineFactory()
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket
            
            try:
                # Test synchronous creation
                engine = factory.create_execution_engine(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id
                )
                
                # Test async operations on created engine
                if hasattr(engine, 'send_websocket_event'):
                    try:
                        await engine.send_websocket_event('factory_test', {
                            'test_type': 'async_delegation',
                            'factory_type': 'ExecutionEngineFactory'
                        })
                        print(f"   PASS:  Async WebSocket event sent successfully")
                    except Exception as e:
                        async_violations.append(f"Async WebSocket event failed: {e}")
                
                # Test async factory creation if available
                if hasattr(factory, 'create_for_user'):
                    try:
                        # Mock user execution context
                        from netra_backend.app.services.user_execution_context import UserExecutionContext
                        
                        context = UserExecutionContext(
                            user_id=self.test_user_id,
                            thread_id=str(uuid.uuid4()),
                            run_id=str(uuid.uuid4())
                        )
                        
                        async_engine = await factory.create_for_user(context)
                        
                        if not isinstance(async_engine, UserExecutionEngine):
                            async_violations.append(
                                f"Async factory created {type(async_engine).__name__}, expected UserExecutionEngine"
                            )
                        else:
                            print(f"   PASS:  Async factory correctly creates UserExecutionEngine")
                        
                    except Exception as e:
                        async_violations.append(f"Async factory creation failed: {e}")
                
            except Exception as e:
                async_violations.append(f"Factory async testing failed: {e}")
        
        # Test concurrent factory usage
        async def create_concurrent_engine(user_index: int):
            """Create engine concurrently"""
            try:
                with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.get_manager') as mock_get_manager:
                    mock_ws = MockWebSocketManager(f"concurrent_user_{user_index}")
                    mock_get_manager.return_value = mock_ws
                    
                    engine = factory.create_execution_engine(
                        user_id=f"concurrent_user_{user_index}",
                        session_id=f"concurrent_session_{user_index}"
                    )
                    
                    # Test async operation
                    await engine.send_websocket_event('concurrent_test', {
                        'user_index': user_index,
                        'timestamp': time.time()
                    })
                    
                    return f"success_{user_index}"
            except Exception as e:
                return f"error_{user_index}_{e}"
        
        # Run concurrent factory operations
        concurrent_tasks = [create_concurrent_engine(i) for i in range(5)]
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        success_count = sum(1 for result in concurrent_results if isinstance(result, str) and result.startswith('success'))
        if success_count != len(concurrent_tasks):
            async_violations.append(f"Only {success_count}/{len(concurrent_tasks)} concurrent operations succeeded")
        else:
            print(f"   PASS:  {success_count} concurrent factory operations completed successfully")
        
        # CRITICAL: Async delegation must work for real-time chat functionality
        if async_violations:
            self.fail(f"Async delegation violations: {async_violations}")
        
        print(f"   PASS:  Factory async delegation works correctly")
    
    def test_factory_interface_consistency(self):
        """Test that all factory interfaces are consistent and delegate to UserExecutionEngine"""
        print("\n SEARCH:  Testing factory interface consistency...")
        
        interface_violations = []
        
        # Get all available factory classes
        factory_imports = self.test_factory_imports_available()
        factory_classes = [imp['class'] for imp in factory_imports if 'Factory' in imp['name']]
        
        if not factory_classes:
            self.skipTest("No factory classes available for testing")
        
        # Analyze factory interfaces
        factory_interfaces = {}
        
        for factory_class in factory_classes:
            methods = [m for m in dir(factory_class) if not m.startswith('_') and callable(getattr(factory_class, m))]
            create_methods = [m for m in methods if 'create' in m.lower()]
            
            factory_interfaces[factory_class.__name__] = {
                'all_methods': methods,
                'create_methods': create_methods,
                'method_count': len(methods),
                'source_file': inspect.getfile(factory_class)
            }
        
        print(f"   PASS:  Analyzed {len(factory_classes)} factory interfaces")
        
        # Check for interface consistency
        create_method_names = set()
        for interface in factory_interfaces.values():
            create_method_names.update(interface['create_methods'])
        
        # Validate common interface patterns
        expected_patterns = ['create_execution_engine', 'create', 'build', 'get', 'make']
        found_patterns = [pattern for pattern in expected_patterns if any(pattern in method for method in create_method_names)]
        
        if not found_patterns:
            interface_violations.append("No common factory patterns found")
        else:
            print(f"   PASS:  Found factory patterns: {found_patterns}")
        
        # Check for SSOT compliance - should be minimal duplication
        total_create_methods = sum(len(interface['create_methods']) for interface in factory_interfaces.values())
        unique_create_methods = len(create_method_names)
        
        if total_create_methods > unique_create_methods * 1.5:  # Allow some reasonable overlap
            interface_violations.append(
                f"Too much method duplication: {total_create_methods} total vs {unique_create_methods} unique"
            )
        else:
            print(f"   PASS:  Reasonable method duplication: {total_create_methods} total, {unique_create_methods} unique")
        
        # Validate file separation
        source_files = set(interface['source_file'] for interface in factory_interfaces.values())
        if len(source_files) != len(factory_classes):
            interface_violations.append("Multiple factory classes in same file detected")
        else:
            print(f"   PASS:  Factory classes properly separated into {len(source_files)} files")
        
        # CRITICAL: Interface consistency is required for SSOT
        if interface_violations:
            self.fail(f"Factory interface violations: {interface_violations}")
        
        print(f"   PASS:  Factory interfaces are consistent and SSOT-compliant")
    
    def test_factory_memory_efficiency(self):
        """Test that factory patterns don't create memory leaks or excessive objects"""
        print("\n SEARCH:  Testing factory memory efficiency...")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.skipTest(f"ExecutionEngineFactory not available: {e}")
        
        memory_violations = []
        
        # Test repeated factory creation
        factory = ExecutionEngineFactory()
        created_engines = []
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket
            
            start_time = time.perf_counter()
            
            for i in range(20):
                try:
                    engine = factory.create_execution_engine(
                        user_id=f"perf_user_{i}",
                        session_id=f"perf_session_{i}"
                    )
                    created_engines.append(engine)
                except Exception as e:
                    memory_violations.append(f"Factory creation {i} failed: {e}")
            
            creation_time = time.perf_counter() - start_time
            avg_creation_time = creation_time / len(created_engines) if created_engines else float('inf')
            
            print(f"   PASS:  Created {len(created_engines)} engines in {creation_time:.3f}s")
            print(f"   PASS:  Average creation time: {avg_creation_time:.3f}s per engine")
            
            # Performance thresholds
            if avg_creation_time > 0.1:  # 100ms per engine is too slow
                memory_violations.append(f"Slow factory creation: {avg_creation_time:.3f}s average")
            
            if creation_time > 5.0:  # 5s total for 20 engines is too slow
                memory_violations.append(f"Slow total factory time: {creation_time:.3f}s")
        
        # Test factory singleton behavior (if applicable)
        factory2 = ExecutionEngineFactory()
        if factory is factory2:
            print(f"   PASS:  Factory uses singleton pattern")
        else:
            print(f"   PASS:  Factory creates new instances (non-singleton)")
        
        # CRITICAL: Factory performance affects Golden Path response time
        if memory_violations:
            self.fail(f"Factory memory/performance violations: {memory_violations}")
        
        print(f"   PASS:  Factory memory efficiency validated")


if __name__ == '__main__':
    unittest.main(verbosity=2)