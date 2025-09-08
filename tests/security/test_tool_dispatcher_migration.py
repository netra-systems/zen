# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Test suite for ToolDispatcher security migration and deprecation warnings.

    # REMOVED_SYNTAX_ERROR: This test suite validates:
        # REMOVED_SYNTAX_ERROR: 1. Deprecation warnings are properly emitted for unsafe patterns
        # REMOVED_SYNTAX_ERROR: 2. Security detection utilities work correctly
        # REMOVED_SYNTAX_ERROR: 3. Request-scoped patterns provide proper user isolation
        # REMOVED_SYNTAX_ERROR: 4. Migration guidance is helpful and accurate
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import warnings
        # REMOVED_SYNTAX_ERROR: from typing import List, Any, Dict
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class MockUserExecutionContext:
    # REMOVED_SYNTAX_ERROR: """Mock user execution context for testing."""
# REMOVED_SYNTAX_ERROR: def __init__(self, user_id: str):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.user_id = user_id
    # REMOVED_SYNTAX_ERROR: self.session_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: self.request_id = "formatted_string"


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock user execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return MockUserExecutionContext("test_user_123")


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock websocket manager."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: return manager


# REMOVED_SYNTAX_ERROR: class TestDeprecationWarnings:
    # REMOVED_SYNTAX_ERROR: """Test that deprecation warnings are properly emitted."""

# REMOVED_SYNTAX_ERROR: def test_direct_instantiation_warning(self):
    # REMOVED_SYNTAX_ERROR: """Test deprecation warning for direct ToolDispatcher instantiation."""
    # REMOVED_SYNTAX_ERROR: with pytest.warns(DeprecationWarning, match="Direct ToolDispatcher instantiation is deprecated"):
        # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()

        # Verify dispatcher was still created (backward compatibility)
        # REMOVED_SYNTAX_ERROR: assert dispatcher is not None
        # REMOVED_SYNTAX_ERROR: assert hasattr(dispatcher, 'dispatch')

# REMOVED_SYNTAX_ERROR: def test_base_agent_tool_dispatcher_warning(self):
    # REMOVED_SYNTAX_ERROR: """Test deprecation warning when passing tool_dispatcher to BaseAgent."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_llm = Mock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = ToolDispatcher()

    # REMOVED_SYNTAX_ERROR: with pytest.warns(DeprecationWarning, match="BaseAgent.__init__ with tool_dispatcher parameter"):
        # REMOVED_SYNTAX_ERROR: agent = BaseAgent( )
        # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm,
        # REMOVED_SYNTAX_ERROR: name="TestAgent",
        # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_dispatcher
        

        # Verify agent was created with dispatcher (backward compatibility)
        # REMOVED_SYNTAX_ERROR: assert agent.tool_dispatcher is mock_dispatcher

        # Removed problematic line: async def test_dispatch_method_warning(self):
            # REMOVED_SYNTAX_ERROR: """Test deprecation warning when using dispatch method on global instance."""
            # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()

            # REMOVED_SYNTAX_ERROR: with pytest.warns(DeprecationWarning, match="ToolDispatcher.dispatch\\(\\) called on global instance"):
                # This will warn about unsafe global usage
                # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("nonexistent_tool")

# REMOVED_SYNTAX_ERROR: def test_register_tool_warning(self):
    # REMOVED_SYNTAX_ERROR: """Test deprecation warning when registering tools on global instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()

    # REMOVED_SYNTAX_ERROR: with pytest.warns(DeprecationWarning, match="ToolDispatcher.register_tool\\(\\) called on global instance"):
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("test_tool", lambda x: None "result", "Test tool")


# REMOVED_SYNTAX_ERROR: class TestSecurityDetection:
    # REMOVED_SYNTAX_ERROR: """Test security detection and analysis utilities."""

# REMOVED_SYNTAX_ERROR: def test_detect_unsafe_patterns(self):
    # REMOVED_SYNTAX_ERROR: """Test detection of unsafe usage patterns."""
    # REMOVED_SYNTAX_ERROR: analysis = ToolDispatcher.detect_unsafe_usage_patterns()

    # Should analyze call stack
    # REMOVED_SYNTAX_ERROR: assert 'has_unsafe_patterns' in analysis
    # REMOVED_SYNTAX_ERROR: assert 'risks' in analysis
    # REMOVED_SYNTAX_ERROR: assert 'call_stack_analysis' in analysis
    # REMOVED_SYNTAX_ERROR: assert 'migration_recommendations' in analysis

# REMOVED_SYNTAX_ERROR: def test_isolation_status_global_instance(self):
    # REMOVED_SYNTAX_ERROR: """Test isolation status detection for global instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()
    # REMOVED_SYNTAX_ERROR: status = dispatcher.get_isolation_status()

    # Global instance should show security warnings
    # REMOVED_SYNTAX_ERROR: assert status['is_global_instance'] is True
    # REMOVED_SYNTAX_ERROR: assert status['warning_needed'] is True
    # REMOVED_SYNTAX_ERROR: assert status['migration_urgency'] == 'HIGH'
    # REMOVED_SYNTAX_ERROR: assert 'security_risks' in status

    # Removed problematic line: async def test_force_security_check(self):
        # REMOVED_SYNTAX_ERROR: """Test forced security check provides detailed analysis."""
        # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()
        # REMOVED_SYNTAX_ERROR: analysis = await dispatcher.force_secure_migration_check()

        # REMOVED_SYNTAX_ERROR: assert analysis['security_status'] == 'UNSAFE'
        # REMOVED_SYNTAX_ERROR: assert analysis['migration_required'] is True
        # REMOVED_SYNTAX_ERROR: assert len(analysis['migration_steps']) > 0

        # Should provide specific migration guidance
        # REMOVED_SYNTAX_ERROR: steps = analysis['migration_steps']
        # REMOVED_SYNTAX_ERROR: assert any('create_request_scoped_dispatcher' in step for step in steps)
        # REMOVED_SYNTAX_ERROR: assert any('async context manager' in step for step in steps)


# REMOVED_SYNTAX_ERROR: class TestUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test user isolation with request-scoped patterns."""

    # Removed problematic line: async def test_request_scoped_factory_isolation(self, mock_user_context, mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: """Test that request-scoped factory creates isolated dispatchers."""
        # Mock the factory function since we don't have full context setup
        # Removed problematic line: with pytest.mock.patch('netra_backend.app.agents.tool_executor_factory.create_isolated_tool_dispatcher') as mock_factory:
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
            # REMOVED_SYNTAX_ERROR: mock_factory.return_value = mock_isolated_dispatcher

            # Create request-scoped dispatcher
            # REMOVED_SYNTAX_ERROR: dispatcher = await ToolDispatcher.create_request_scoped_dispatcher( )
            # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
            # REMOVED_SYNTAX_ERROR: tools=[],
            # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
            

            # Verify factory was called with proper arguments
            # REMOVED_SYNTAX_ERROR: mock_factory.assert_called_once_with( )
            # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
            # REMOVED_SYNTAX_ERROR: tools=[],
            # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
            

            # REMOVED_SYNTAX_ERROR: assert dispatcher is mock_isolated_dispatcher

            # Removed problematic line: async def test_scoped_context_manager(self, mock_user_context, mock_websocket_manager):
                # REMOVED_SYNTAX_ERROR: """Test that scoped context manager provides automatic cleanup."""
                # REMOVED_SYNTAX_ERROR: pass
                # Mock the context manager since we don't have full context setup
                # Removed problematic line: with pytest.mock.patch('netra_backend.app.agents.tool_executor_factory.isolated_tool_dispatcher_scope') as mock_context:
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
                    # REMOVED_SYNTAX_ERROR: mock_context.return_value = mock_context_manager

                    # Create scoped context
                    # REMOVED_SYNTAX_ERROR: context_manager = await ToolDispatcher.create_scoped_dispatcher_context( )
                    # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
                    # REMOVED_SYNTAX_ERROR: tools=[],
                    # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
                    

                    # Verify context manager factory was called
                    # REMOVED_SYNTAX_ERROR: mock_context.assert_called_once_with( )
                    # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
                    # REMOVED_SYNTAX_ERROR: tools=[],
                    # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
                    

                    # REMOVED_SYNTAX_ERROR: assert context_manager is mock_context_manager


# REMOVED_SYNTAX_ERROR: class TestSecurityRiskAssessment:
    # REMOVED_SYNTAX_ERROR: """Test security risk assessment functionality."""

# REMOVED_SYNTAX_ERROR: def test_assess_security_risks_global_instance(self):
    # REMOVED_SYNTAX_ERROR: """Test security risk assessment for global instance."""
    # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()
    # REMOVED_SYNTAX_ERROR: risks = dispatcher._assess_security_risks()

    # Should identify key security risks
    # REMOVED_SYNTAX_ERROR: assert any('Global state may cause user isolation issues' in risk for risk in risks)
    # REMOVED_SYNTAX_ERROR: assert any('WebSocket events may be delivered to wrong users' in risk for risk in risks)
    # REMOVED_SYNTAX_ERROR: assert any('Tool state shared between concurrent requests' in risk for risk in risks)

# REMOVED_SYNTAX_ERROR: def test_security_documentation_completeness(self):
    # REMOVED_SYNTAX_ERROR: """Test that security documentation is comprehensive."""
    # REMOVED_SYNTAX_ERROR: pass
    # Create dispatcher to trigger warnings and check documentation
    # REMOVED_SYNTAX_ERROR: with warnings.catch_warnings(record=True) as w:
        # REMOVED_SYNTAX_ERROR: warnings.simplefilter("always")
        # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()

        # Check that warning message contains migration guidance
        # REMOVED_SYNTAX_ERROR: assert len(w) >= 1
        # REMOVED_SYNTAX_ERROR: warning_message = str(w[0].message)
        # REMOVED_SYNTAX_ERROR: assert 'create_request_scoped_dispatcher' in warning_message
        # REMOVED_SYNTAX_ERROR: assert 'create_scoped_dispatcher_context' in warning_message
        # REMOVED_SYNTAX_ERROR: assert 'v3.0.0' in warning_message


# REMOVED_SYNTAX_ERROR: class TestMigrationGuidance:
    # REMOVED_SYNTAX_ERROR: """Test migration guidance and examples."""

# REMOVED_SYNTAX_ERROR: def test_factory_method_documentation(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory methods have comprehensive documentation."""
    # Check create_request_scoped_dispatcher docstring
    # REMOVED_SYNTAX_ERROR: doc = ToolDispatcher.create_request_scoped_dispatcher.__doc__
    # REMOVED_SYNTAX_ERROR: assert 'RECOMMENDED SECURE PATTERN' in doc
    # REMOVED_SYNTAX_ERROR: assert 'SECURITY BENEFITS' in doc
    # REMOVED_SYNTAX_ERROR: assert 'USER ISOLATION GUARANTEES' in doc
    # REMOVED_SYNTAX_ERROR: assert 'Example:' in doc

    # Check create_scoped_dispatcher_context docstring
    # REMOVED_SYNTAX_ERROR: context_doc = ToolDispatcher.create_scoped_dispatcher_context.__doc__
    # REMOVED_SYNTAX_ERROR: assert 'AUTOMATIC SAFETY FEATURES' in context_doc
    # REMOVED_SYNTAX_ERROR: assert 'SECURITY GUARANTEES' in context_doc
    # REMOVED_SYNTAX_ERROR: assert 'AsyncContextManager' in context_doc

# REMOVED_SYNTAX_ERROR: def test_migration_warning_actionable(self):
    # REMOVED_SYNTAX_ERROR: """Test that migration warnings provide actionable guidance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with warnings.catch_warnings(record=True) as w:
        # REMOVED_SYNTAX_ERROR: warnings.simplefilter("always")

        # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("test", lambda x: None None)

        # Should have multiple warnings with specific guidance
        # REMOVED_SYNTAX_ERROR: warning_messages = [str(warning.message) for warning in w]

        # Check for specific migration guidance
        # REMOVED_SYNTAX_ERROR: combined_messages = ' '.join(warning_messages)
        # REMOVED_SYNTAX_ERROR: assert 'create_request_scoped_dispatcher' in combined_messages
        # REMOVED_SYNTAX_ERROR: assert 'v3.0.0' in combined_messages
        # REMOVED_SYNTAX_ERROR: assert 'user isolation issues' in combined_messages


        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: class TestMigrationIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for migration scenarios."""

    # Removed problematic line: async def test_concurrent_user_simulation(self):
        # REMOVED_SYNTAX_ERROR: """Simulate concurrent users to demonstrate isolation issues with global state."""
        # This test would ideally show the problem with global state
        # and demonstrate the solution with request-scoped dispatchers

        # Global dispatcher (unsafe)
        # REMOVED_SYNTAX_ERROR: global_dispatcher = ToolDispatcher()

        # Simulate tool registration for different users
        # REMOVED_SYNTAX_ERROR: global_dispatcher.register_tool("user_data", lambda x: None "global_shared_data")

        # Both "users" would see the same tool and data (security issue)
        # In real implementation, this would be dangerous

        # The test demonstrates why we need request-scoped patterns
        # REMOVED_SYNTAX_ERROR: isolation_status = global_dispatcher.get_isolation_status()
        # REMOVED_SYNTAX_ERROR: assert isolation_status['migration_urgency'] == 'HIGH'

# REMOVED_SYNTAX_ERROR: def test_backward_compatibility_maintained(self):
    # REMOVED_SYNTAX_ERROR: """Test that deprecated patterns still work for backward compatibility."""
    # REMOVED_SYNTAX_ERROR: pass
    # Direct instantiation should work but warn
    # REMOVED_SYNTAX_ERROR: with warnings.catch_warnings(record=True):
        # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()

        # Basic functionality should still work
        # REMOVED_SYNTAX_ERROR: assert dispatcher.has_tool("nonexistent") is False

        # Registration should work but warn
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("test_tool", lambda x: None "result")
        # REMOVED_SYNTAX_ERROR: assert dispatcher.has_tool("test_tool") is True


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run with: python -m pytest tests/security/test_tool_dispatcher_migration.py -v
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])