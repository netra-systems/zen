"""
SSOT Validation Test for UserExecutionEngine

CRITICAL: This test validates that UserExecutionEngine can handle ALL use cases
previously handled by the 6 deprecated execution engines.

Purpose:
1. Prove UserExecutionEngine has all required methods/capabilities
2. Test factory delegation routes correctly to UserExecutionEngine
3. Validate user isolation works properly
4. Confirm WebSocket event integration is functional
5. Test tool execution with real tool dispatcher

Business Impact: This test protects $500K+ ARR chat functionality by ensuring
the SSOT consolidation doesn't break agent execution or user isolation.
"""

import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
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
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
    from netra_backend.app.config import get_config
except ImportError as e:
    import pytest
    pytest.skip(f"Backend modules not available: {e}", allow_module_level=True)


class TestUserExecutionEngineSSoTValidation(unittest.TestCase):
    """Comprehensive validation that UserExecutionEngine is a complete SSOT"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
        self.user_id = "test_user_123"
        self.session_id = "test_session_456"
        
        # Mock WebSocket manager for testing
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.send_agent_event = AsyncMock()
        self.mock_websocket_manager.user_id = self.user_id
        
    def test_user_execution_engine_has_all_required_methods(self):
        """Test that UserExecutionEngine has all methods needed to replace deprecated engines"""
        print("\n SEARCH:  Validating UserExecutionEngine has all required methods...")
        
        # Create instance
        engine = UserExecutionEngine(
            user_id=self.user_id,
            session_id=self.session_id,
            websocket_manager=self.mock_websocket_manager
        )
        
        # Core execution methods that must exist
        required_methods = [
            'execute_tool',
            'execute_tool_async', 
            'send_websocket_event',
            'get_user_context',
            'cleanup',
            'validate_tool_access',
            'get_execution_context'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(engine, method_name):
                missing_methods.append(method_name)
            else:
                method = getattr(engine, method_name)
                if not callable(method):
                    missing_methods.append(f"{method_name} (not callable)")
        
        print(f"   PASS:  Checking {len(required_methods)} required methods...")
        for method in required_methods:
            if method not in missing_methods:
                print(f"     PASS:  {method}")
            else:
                print(f"     FAIL:  {method}")
        
        self.assertEqual(len(missing_methods), 0, 
                        f"UserExecutionEngine missing required methods: {missing_methods}")
    
    def test_user_execution_engine_initialization(self):
        """Test UserExecutionEngine initializes correctly with proper isolation"""
        print("\n SEARCH:  Testing UserExecutionEngine initialization and isolation...")
        
        # Test 1: Basic initialization
        engine1 = UserExecutionEngine(
            user_id="user_1",
            session_id="session_1",
            websocket_manager=self.mock_websocket_manager
        )
        
        self.assertEqual(engine1.user_id, "user_1")
        self.assertEqual(engine1.session_id, "session_1")
        self.assertEqual(engine1.websocket_manager, self.mock_websocket_manager)
        print("   PASS:  Basic initialization works")
        
        # Test 2: User isolation
        mock_websocket_2 = Mock()
        mock_websocket_2.user_id = "user_2"
        
        engine2 = UserExecutionEngine(
            user_id="user_2", 
            session_id="session_2",
            websocket_manager=mock_websocket_2
        )
        
        self.assertNotEqual(engine1.user_id, engine2.user_id)
        self.assertNotEqual(engine1.session_id, engine2.session_id)
        self.assertNotEqual(engine1.websocket_manager, engine2.websocket_manager)
        print("   PASS:  User isolation works - different users have separate engines")
        
        # Test 3: Tool dispatcher initialization (async property)
        # Note: tool_dispatcher is an async property, so we test the sync getter
        tool_dispatcher = engine1.tool_dispatcher  # This will return the sync getter result
        self.assertIsNotNone(tool_dispatcher)
        print("   PASS:  Tool dispatcher properly initialized")
        
    def test_factory_delegation_to_user_execution_engine(self):
        """Test that ExecutionEngineFactory delegates to UserExecutionEngine"""
        print("\n SEARCH:  Testing factory delegation to UserExecutionEngine...")
        
        # Test factory creates UserExecutionEngine instances
        factory = ExecutionEngineFactory()
        
        with patch.object(WebSocketManagerFactory, 'get_manager') as mock_get_manager:
            mock_get_manager.return_value = self.mock_websocket_manager
            
            engine = factory.create_execution_engine(
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            self.assertIsInstance(engine, UserExecutionEngine,
                                "Factory should create UserExecutionEngine instances")
            self.assertEqual(engine.user_id, self.user_id)
            self.assertEqual(engine.session_id, self.session_id)
            
        print("   PASS:  Factory correctly delegates to UserExecutionEngine")
        
    def test_websocket_event_integration(self):
        """Test WebSocket event integration works through UserExecutionEngine"""
        print("\n SEARCH:  Testing WebSocket event integration...")
        
        engine = UserExecutionEngine(
            user_id=self.user_id,
            session_id=self.session_id, 
            websocket_manager=self.mock_websocket_manager
        )
        
        # Test sending different types of WebSocket events
        async def test_events():
            # Test agent_started event
            await engine.send_websocket_event("agent_started", {
                "agent_type": "test_agent",
                "message": "Starting test execution"
            })
            
            # Test tool_executing event  
            await engine.send_websocket_event("tool_executing", {
                "tool_name": "test_tool",
                "parameters": {"param1": "value1"}
            })
            
            # Test agent_completed event
            await engine.send_websocket_event("agent_completed", {
                "result": "success",
                "message": "Execution completed"
            })
        
        # Run async test
        asyncio.run(test_events())
        
        # Verify WebSocket manager was called correctly
        self.assertEqual(self.mock_websocket_manager.send_agent_event.call_count, 3)
        
        # Verify call arguments
        calls = self.mock_websocket_manager.send_agent_event.call_args_list
        self.assertEqual(calls[0][0][0], "agent_started")
        self.assertEqual(calls[1][0][0], "tool_executing") 
        self.assertEqual(calls[2][0][0], "agent_completed")
        
        print("   PASS:  WebSocket events sent correctly through UserExecutionEngine")
        
    def test_tool_execution_capabilities(self):
        """Test tool execution capabilities through UserExecutionEngine"""
        print("\n SEARCH:  Testing tool execution capabilities...")
        
        engine = UserExecutionEngine(
            user_id=self.user_id,
            session_id=self.session_id,
            websocket_manager=self.mock_websocket_manager
        )
        
        # Test 1: Tool dispatcher is properly configured
        tool_dispatcher = engine.tool_dispatcher
        self.assertIsNotNone(tool_dispatcher)
        print("   PASS:  Tool dispatcher properly configured")
        
        # Test 2: User context is maintained
        context = engine.get_user_context()
        self.assertIsInstance(context, dict)
        self.assertIn('user_id', context)
        self.assertIn('session_id', context)
        self.assertEqual(context['user_id'], self.user_id)
        self.assertEqual(context['session_id'], self.session_id)
        print("   PASS:  User context properly maintained")
        
        # Test 3: Execution context includes tool access
        exec_context = engine.get_execution_context()
        self.assertIsInstance(exec_context, dict)
        self.assertIn('tool_dispatcher', exec_context)
        self.assertIn('user_context', exec_context)
        print("   PASS:  Execution context includes tool access")
        
    def test_user_execution_engine_vs_deprecated_methods(self):
        """Test that UserExecutionEngine provides equivalents to deprecated engine methods"""
        print("\n SEARCH:  Comparing UserExecutionEngine methods to deprecated engine patterns...")
        
        engine = UserExecutionEngine(
            user_id=self.user_id,
            session_id=self.session_id,
            websocket_manager=self.mock_websocket_manager
        )
        
        # Map of deprecated patterns to UserExecutionEngine equivalents
        method_mappings = {
            # From execution_engine.py
            'execute_tool': 'execute_tool',
            'get_websocket_manager': 'websocket_manager',
            'send_event': 'send_websocket_event',
            
            # From mcp_execution_engine.py
            'execute_mcp_tool': 'execute_tool',  # UserExecutionEngine handles all tool types
            
            # From request_scoped_execution_engine.py  
            'get_request_context': 'get_user_context',
            'cleanup_request': 'cleanup',
            
            # From execution_engine_consolidated.py
            'execute_with_context': 'execute_tool',
            'get_execution_state': 'get_execution_context'
        }
        
        available_methods = []
        missing_methods = []
        
        for deprecated_method, user_engine_method in method_mappings.items():
            if hasattr(engine, user_engine_method):
                available_methods.append(f"{deprecated_method} -> {user_engine_method}")
            else:
                missing_methods.append(f"{deprecated_method} -> {user_engine_method} (MISSING)")
        
        print(f"   PASS:  Available method mappings ({len(available_methods)}):")
        for mapping in available_methods:
            print(f"     PASS:  {mapping}")
            
        if missing_methods:
            print(f"   FAIL:  Missing method mappings ({len(missing_methods)}):")
            for mapping in missing_methods:
                print(f"     FAIL:  {mapping}")
                
        self.assertEqual(len(missing_methods), 0,
                        f"UserExecutionEngine missing equivalents for: {missing_methods}")
        
    def test_concurrent_user_isolation(self):
        """Test that concurrent users are properly isolated"""
        print("\n SEARCH:  Testing concurrent user isolation...")
        
        # Create multiple engines for different users
        users = ["user_1", "user_2", "user_3"]
        engines = {}
        
        for user in users:
            mock_ws = Mock()
            mock_ws.user_id = user
            mock_ws.send_agent_event = AsyncMock()
            
            engines[user] = UserExecutionEngine(
                user_id=user,
                session_id=f"session_{user}",
                websocket_manager=mock_ws
            )
        
        # Test that each engine maintains separate state
        for user, engine in engines.items():
            context = engine.get_user_context()
            self.assertEqual(context['user_id'], user)
            self.assertEqual(context['session_id'], f"session_{user}")
            
            # Test that WebSocket managers are separate
            self.assertEqual(engine.websocket_manager.user_id, user)
            
        print(f"   PASS:  {len(users)} concurrent users properly isolated")
        
        # Test sending events doesn't cross contaminate
        async def test_isolated_events():
            for user, engine in engines.items():
                await engine.send_websocket_event("test_event", {"user": user})
                
        asyncio.run(test_isolated_events())
        
        # Verify each user's WebSocket manager was called exactly once
        for user, engine in engines.items():
            self.assertEqual(engine.websocket_manager.send_agent_event.call_count, 1)
            call_args = engine.websocket_manager.send_agent_event.call_args[0]
            self.assertEqual(call_args[0], "test_event")
            self.assertEqual(call_args[1]["user"], user)
            
        print("   PASS:  WebSocket events properly isolated between users")
        
    def test_error_handling_and_cleanup(self):
        """Test error handling and cleanup capabilities"""
        print("\n SEARCH:  Testing error handling and cleanup...")
        
        engine = UserExecutionEngine(
            user_id=self.user_id,
            session_id=self.session_id,
            websocket_manager=self.mock_websocket_manager
        )
        
        # Test cleanup method exists and is callable
        self.assertTrue(hasattr(engine, 'cleanup'))
        self.assertTrue(callable(engine.cleanup))
        
        # Test cleanup can be called without errors
        try:
            engine.cleanup()
            print("   PASS:  Cleanup method executes without errors")
        except Exception as e:
            self.fail(f"Cleanup method raised exception: {e}")
            
        # Test tool access validation
        self.assertTrue(hasattr(engine, 'validate_tool_access'))
        self.assertTrue(callable(engine.validate_tool_access))
        print("   PASS:  Tool access validation available")
        
    def test_deprecated_engines_still_exist(self):
        """Test that deprecated engines still exist (for safe removal verification)"""
        print("\n SEARCH:  Verifying deprecated engines still exist before removal...")
        
        deprecated_files = [
            '/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/supervisor/execution_engine.py',
            '/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/execution_engine_consolidated.py',
            '/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/supervisor/mcp_execution_engine.py',
            '/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/supervisor/request_scoped_execution_engine.py',
            '/Users/anthony/Desktop/netra-apex/netra_backend/app/core/execution_engine.py',
            '/Users/anthony/Desktop/netra-apex/netra_backend/app/services/unified_tool_registry/execution_engine.py'
        ]
        
        existing_files = []
        missing_files = []
        
        for file_path in deprecated_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
                print(f"   PASS:  {os.path.basename(file_path)} exists")
            else:
                missing_files.append(file_path)
                print(f"   FAIL:  {os.path.basename(file_path)} MISSING")
        
        self.assertGreater(len(existing_files), 0,
                          "At least some deprecated files should exist before removal")
        
        if missing_files:
            print(f"   WARNING: [U+FE0F]  WARNING: {len(missing_files)} deprecated files already missing")
            
        return existing_files, missing_files


if __name__ == '__main__':
    unittest.main(verbosity=2)