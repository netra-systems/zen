"""
Factory Delegation Validation Test

CRITICAL: This test validates that ExecutionEngineFactory properly delegates
all creation requests to UserExecutionEngine, ensuring Phase 1 SSOT consolidation
is working correctly before Phase 2 deprecated file removal.

Purpose:
1. Verify ExecutionEngineFactory creates UserExecutionEngine instances
2. Test factory handles different creation patterns correctly
3. Validate factory maintains user isolation
4. Ensure factory integrates with WebSocket manager correctly
5. Test factory error handling and edge cases

Business Impact: Protects factory-based user isolation which is critical for
multi-user AI chat functionality ($500K+ ARR dependency).
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
    from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
    from netra_backend.app.core.configuration.base import get_config
except ImportError as e:
    import pytest
    pytest.skip(f"Backend modules not available: {e}", allow_module_level=True)


class TestFactoryDelegationValidation(SSotAsyncTestCase):
    """Comprehensive validation of ExecutionEngineFactory delegation to UserExecutionEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
        self.factory = ExecutionEngineFactory()
        
        # Mock WebSocket manager for testing
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.send_agent_event = AsyncMock()
        self.mock_websocket_manager.user_id = "test_user"
        
    def test_factory_creates_user_execution_engine_instances(self):
        """Test that factory creates UserExecutionEngine instances"""
        print("\n🔍 Testing factory creates UserExecutionEngine instances...")
        
        user_id = "test_user_123"
        session_id = "test_session_456"
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            # Test basic creation
            engine = self.factory.create_execution_engine(
                user_id=user_id,
                session_id=session_id
            )
            
            # Verify it's the correct type
            self.assertIsInstance(engine, UserExecutionEngine,
                                "Factory should create UserExecutionEngine instances")
            
            # Verify properties are set correctly
            self.assertEqual(engine.user_id, user_id)
            self.assertEqual(engine.session_id, session_id)
            self.assertEqual(engine.websocket_manager, self.mock_websocket_manager)
            
            print("  ✅ Factory creates UserExecutionEngine with correct properties")
            
    def test_factory_multiple_users_isolation(self):
        """Test factory creates isolated engines for different users"""
        print("\n🔍 Testing factory creates isolated engines for multiple users...")
        
        users = [
            ("user_1", "session_1"),
            ("user_2", "session_2"), 
            ("user_3", "session_3")
        ]
        
        engines = []
        mock_managers = []
        
        for user_id, session_id in users:
            # Create separate mock managers for each user
            mock_manager = Mock()
            mock_manager.user_id = user_id
            mock_manager.send_agent_event = AsyncMock()
            mock_managers.append(mock_manager)
            
            with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
                mock_get_manager.return_value = mock_manager
                
                engine = self.factory.create_execution_engine(
                    user_id=user_id,
                    session_id=session_id
                )
                
                engines.append(engine)
        
        # Verify all engines are separate instances
        for i, engine1 in enumerate(engines):
            for j, engine2 in enumerate(engines):
                if i != j:
                    self.assertIsNot(engine1, engine2,
                                   f"Engine {i} and {j} should be different instances")
                    self.assertNotEqual(engine1.user_id, engine2.user_id,
                                      f"Engine {i} and {j} should have different user IDs")
                    self.assertNotEqual(engine1.session_id, engine2.session_id,
                                      f"Engine {i} and {j} should have different session IDs")
        
        print(f"  ✅ Factory creates {len(engines)} isolated engines for different users")
        
    def test_factory_websocket_integration(self):
        """Test factory properly integrates with WebSocket manager"""
        print("\n🔍 Testing factory WebSocket manager integration...")
        
        user_id = "test_user_ws"
        session_id = "test_session_ws"
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            engine = self.factory.create_execution_engine(
                user_id=user_id,
                session_id=session_id
            )
            
            # Verify WebSocketManagerFactory was called
            mock_get_manager.assert_called_once_with(user_id)
            
            # Verify engine has correct WebSocket manager
            self.assertEqual(engine.websocket_manager, self.mock_websocket_manager)
            
            print("  ✅ Factory properly integrates with WebSocketManagerFactory")
            
    def test_factory_concurrent_creation(self):
        """Test factory handles concurrent creation requests correctly"""
        print("\n🔍 Testing factory handles concurrent creation...")
        
        async def create_engine_async(user_id: str, session_id: str):
            """Helper to create engine in async context"""
            mock_manager = Mock()
            mock_manager.user_id = user_id
            mock_manager.send_agent_event = AsyncMock()
            
            with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
                mock_get_manager.return_value = mock_manager
                
                engine = self.factory.create_execution_engine(
                    user_id=user_id,
                    session_id=session_id
                )
                
                return engine
        
        async def test_concurrent():
            # Create multiple engines concurrently
            tasks = []
            for i in range(5):
                task = create_engine_async(f"concurrent_user_{i}", f"concurrent_session_{i}")
                tasks.append(task)
            
            engines = await asyncio.gather(*tasks)
            
            # Verify all engines were created successfully
            self.assertEqual(len(engines), 5)
            
            # Verify they're all UserExecutionEngine instances
            for engine in engines:
                self.assertIsInstance(engine, UserExecutionEngine)
            
            # Verify they have unique user IDs
            user_ids = [engine.user_id for engine in engines]
            self.assertEqual(len(user_ids), len(set(user_ids)), 
                           "All engines should have unique user IDs")
            
            return engines
        
        engines = asyncio.run(test_concurrent())
        print(f"  ✅ Factory successfully handles {len(engines)} concurrent creations")
        
    def test_factory_error_handling(self):
        """Test factory error handling for edge cases"""
        print("\n🔍 Testing factory error handling...")
        
        # Test 1: Missing user_id
        with self.assertRaises((ValueError, TypeError)) as context:
            self.factory.create_execution_engine(
                user_id=None,
                session_id="test_session"
            )
        print("  ✅ Factory correctly handles missing user_id")
        
        # Test 2: Missing session_id  
        with self.assertRaises((ValueError, TypeError)) as context:
            self.factory.create_execution_engine(
                user_id="test_user",
                session_id=None
            )
        print("  ✅ Factory correctly handles missing session_id")
        
        # Test 3: Empty string parameters
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            with self.assertRaises((ValueError, TypeError)) as context:
                self.factory.create_execution_engine(
                    user_id="",
                    session_id="test_session"
                )
        print("  ✅ Factory correctly handles empty user_id")
        
    def test_factory_websocket_manager_failure_handling(self):
        """Test factory handles WebSocket manager creation failures"""
        print("\n🔍 Testing factory handles WebSocket manager failures...")
        
        user_id = "test_user_fail"
        session_id = "test_session_fail"
        
        # Test WebSocket manager creation failure
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("WebSocket manager creation failed")
            
            with self.assertRaises(Exception) as context:
                self.factory.create_execution_engine(
                    user_id=user_id,
                    session_id=session_id
                )
            
            self.assertIn("WebSocket manager creation failed", str(context.exception))
        
        print("  ✅ Factory properly propagates WebSocket manager creation failures")
        
    def test_factory_method_compatibility(self):
        """Test factory provides all methods needed to replace deprecated patterns"""
        print("\n🔍 Testing factory method compatibility...")
        
        # Test factory has expected methods
        required_methods = [
            'create_execution_engine'
        ]
        
        for method_name in required_methods:
            self.assertTrue(hasattr(self.factory, method_name),
                          f"Factory should have {method_name} method")
            self.assertTrue(callable(getattr(self.factory, method_name)),
                          f"Factory.{method_name} should be callable")
        
        print("  ✅ Factory has all required methods")
        
        # Test factory creates consistent engines for same user
        user_id = "consistent_user"
        session_id_1 = "session_1"
        session_id_2 = "session_2"
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            engine1 = self.factory.create_execution_engine(user_id, session_id_1)
            engine2 = self.factory.create_execution_engine(user_id, session_id_2)
            
            # Engines should be different instances but same user
            self.assertIsNot(engine1, engine2, "Should create separate instances")
            self.assertEqual(engine1.user_id, engine2.user_id, "Should have same user_id")
            self.assertNotEqual(engine1.session_id, engine2.session_id, "Should have different session_ids")
        
        print("  ✅ Factory creates consistent engines for same user")
        
    def test_factory_replaces_deprecated_patterns(self):
        """Test that factory can replace deprecated creation patterns"""
        print("\n🔍 Testing factory replaces deprecated creation patterns...")
        
        user_id = "pattern_test_user"
        session_id = "pattern_test_session"
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            # Pattern 1: Direct creation (replacing deprecated direct imports)
            engine = self.factory.create_execution_engine(user_id, session_id)
            self.assertIsInstance(engine, UserExecutionEngine)
            
            # Pattern 2: Verify engine has all capabilities deprecated engines had
            self.assertTrue(hasattr(engine, 'execute_tool'))
            self.assertTrue(hasattr(engine, 'send_websocket_event'))
            self.assertTrue(hasattr(engine, 'get_user_context'))
            self.assertTrue(hasattr(engine, 'cleanup'))
            
            # Pattern 3: Verify tool dispatcher integration
            self.assertIsNotNone(engine.tool_dispatcher)
            
        print("  ✅ Factory successfully replaces deprecated creation patterns")
        
    def test_factory_instance_reuse_vs_creation(self):
        """Test factory behavior regarding instance reuse vs new creation"""
        print("\n🔍 Testing factory instance creation vs reuse behavior...")
        
        user_id = "reuse_test_user"
        session_id = "reuse_test_session"
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            # Create two engines with same parameters
            engine1 = self.factory.create_execution_engine(user_id, session_id)
            engine2 = self.factory.create_execution_engine(user_id, session_id)
            
            # Verify they are separate instances (no caching/reuse)
            # This is important for user isolation
            self.assertIsNot(engine1, engine2,
                           "Factory should create new instances, not reuse")
            
            # But they should have same properties
            self.assertEqual(engine1.user_id, engine2.user_id)
            self.assertEqual(engine1.session_id, engine2.session_id)
            
        print("  ✅ Factory creates new instances (no unsafe reuse)")
        
    def test_factory_singleton_pattern_verification(self):
        """Test that factory itself follows proper singleton/instance patterns"""
        print("\n🔍 Testing factory instance patterns...")
        
        # Test factory instance creation
        factory1 = ExecutionEngineFactory()
        factory2 = ExecutionEngineFactory()
        
        # Factories can be separate instances (not singleton)
        # This is fine as they're stateless
        self.assertIsInstance(factory1, ExecutionEngineFactory)
        self.assertIsInstance(factory2, ExecutionEngineFactory)
        
        # Both should work identically
        user_id = "singleton_test_user"
        session_id = "singleton_test_session"
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            engine1 = factory1.create_execution_engine(user_id, session_id)
            engine2 = factory2.create_execution_engine(user_id, session_id)
            
            # Both should create valid engines
            self.assertIsInstance(engine1, UserExecutionEngine)
            self.assertIsInstance(engine2, UserExecutionEngine)
            
            # Engines should be separate instances
            self.assertIsNot(engine1, engine2)
            
        print("  ✅ Factory instances work correctly (stateless pattern)")


if __name__ == '__main__':
    unittest.main(verbosity=2)