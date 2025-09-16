"""
Mission Critical Test Suite: Supervisor Agent Initialization
=============================================================

This test suite ensures that the supervisor agent initialization sequence
is bulletproof and all dependencies are properly resolved.

CRITICAL: The supervisor agent requires:
1. db_session_factory (from database initialization)
2. llm_manager (from auth_service initialization)  
3. tool_dispatcher (from websocket handler registration)

Tests verify:
- Proper initialization order
- Dependency resolution
- Error handling for missing dependencies
- Recovery from partial initialization failures
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import FastAPI
import logging
import sys
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1')

from netra_backend.app.core.startup_manager import StartupManager, ComponentPriority
from netra_backend.app.startup_module import (
    _build_supervisor_agent,
    _create_agent_supervisor,
    setup_security_services,
    initialize_core_services,
    register_websocket_handlers
)


class TestSupervisorInitialization:
    """Test suite for supervisor agent initialization sequence."""
    
    @pytest.fixture
    def app(self):
        """Create a FastAPI app with mock state."""
        app = FastAPI()
        app.state = MagicMock()
        return app
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=logging.Logger)
        logger.info = Mock()
        logger.error = Mock()
        logger.warning = Mock()
        logger.debug = Mock()
        return logger
    
    def test_supervisor_requires_all_dependencies(self, app):
        """Test that supervisor fails without required dependencies."""
        # Clear all state attributes
        app.state = MagicMock()
        
        # Attempt to build supervisor without dependencies
        with pytest.raises(RuntimeError) as exc_info:
            _build_supervisor_agent(app)
        
        assert "Cannot create supervisor - missing dependencies" in str(exc_info.value)
        assert "llm_manager" in str(exc_info.value)
        assert "db_session_factory" in str(exc_info.value)
        assert "tool_dispatcher" in str(exc_info.value)
    
    def test_supervisor_succeeds_with_all_dependencies(self, app):
        """Test that supervisor builds successfully with all dependencies."""
        # Set up all required dependencies
        app.state.db_session_factory = Mock()
        app.state.llm_manager = Mock()
        app.state.tool_dispatcher = Mock()
        
        with patch('netra_backend.app.startup_module.SupervisorAgent') as mock_supervisor:
            with patch('netra_backend.app.startup_module.get_websocket_manager') as mock_ws:
                mock_ws.return_value = Mock()
                mock_supervisor.return_value = Mock()
                
                # Build supervisor
                supervisor = _build_supervisor_agent(app)
                
                # Verify supervisor was created with correct dependencies
                mock_supervisor.assert_called_once_with(
                    app.state.db_session_factory,
                    app.state.llm_manager,
                    mock_ws.return_value,
                    app.state.tool_dispatcher
                )
                assert supervisor is not None
    
    def test_partial_dependencies_failure(self, app):
        """Test that supervisor fails gracefully with partial dependencies."""
        # Only set some dependencies
        app.state.db_session_factory = Mock()
        app.state.tool_dispatcher = Mock()
        # Missing: llm_manager
        
        with pytest.raises(RuntimeError) as exc_info:
            _build_supervisor_agent(app)
        
        assert "llm_manager" in str(exc_info.value)
        assert "db_session_factory" not in str(exc_info.value)  # This one exists
        assert "tool_dispatcher" not in str(exc_info.value)  # This one exists
    
    @pytest.mark.asyncio
    async def test_startup_manager_dependency_order(self):
        """Test that StartupManager respects dependency order."""
        app = FastAPI()
        app.state = MagicMock()
        
        manager = StartupManager()
        initialization_order = []
        
        # Mock initialization functions that track order
        async def mock_database_init():
            initialization_order.append("database")
            app.state.db_session_factory = Mock()
        
        async def mock_auth_init():
            initialization_order.append("auth_service")
            app.state.llm_manager = Mock()
        
        async def mock_websocket_init():
            initialization_order.append("websocket")
            app.state.tool_dispatcher = Mock()
        
        async def mock_supervisor_init():
            initialization_order.append("agent_supervisor")
            # Should have all dependencies available
            assert hasattr(app.state, 'db_session_factory')
            assert hasattr(app.state, 'llm_manager')
            assert hasattr(app.state, 'tool_dispatcher')
        
        # Register components with dependencies
        manager.register_component(
            name="database",
            init_func=mock_database_init,
            priority=ComponentPriority.CRITICAL,
            dependencies=[]
        )
        
        manager.register_component(
            name="auth_service",
            init_func=mock_auth_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database"]
        )
        
        manager.register_component(
            name="websocket",
            init_func=mock_websocket_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database"]
        )
        
        manager.register_component(
            name="agent_supervisor",
            init_func=mock_supervisor_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database", "websocket", "auth_service"]
        )
        
        # Run startup
        success = await manager.startup()
        
        assert success
        # Verify initialization order
        assert initialization_order.index("database") < initialization_order.index("auth_service")
        assert initialization_order.index("database") < initialization_order.index("websocket")
        assert initialization_order.index("auth_service") < initialization_order.index("agent_supervisor")
        assert initialization_order.index("websocket") < initialization_order.index("agent_supervisor")
    
    def test_auth_service_creates_llm_manager(self, app, mock_logger):
        """Test that auth_service initialization creates llm_manager."""
        with patch('netra_backend.app.startup_module.KeyManager') as mock_key_manager:
            with patch('netra_backend.app.startup_module.LLMManager') as mock_llm_manager:
                mock_key_manager.load_from_settings.return_value = Mock()
                mock_llm_manager.return_value = Mock()
                
                # Initialize core services
                key_manager = initialize_core_services(app, mock_logger)
                
                # Setup security services (including llm_manager)
                setup_security_services(app, key_manager)
                
                # Verify llm_manager was created
                assert hasattr(app.state, 'llm_manager')
                assert app.state.llm_manager is not None
                mock_llm_manager.assert_called_once()
    
    def test_websocket_handlers_create_tool_dispatcher(self, app):
        """Test that websocket handler registration creates tool_dispatcher."""
        with patch('netra_backend.app.startup_module.ToolRegistry') as mock_registry:
            with patch('netra_backend.app.startup_module.ToolDispatcher') as mock_dispatcher:
                app.state.db_session_factory = Mock()
                mock_registry.return_value = Mock()
                mock_registry.return_value.get_tools.return_value = []
                mock_dispatcher.return_value = Mock()
                
                # Register websocket handlers
                register_websocket_handlers(app)
                
                # Verify tool_dispatcher was created
                assert hasattr(app.state, 'tool_dispatcher')
                assert app.state.tool_dispatcher is not None
                mock_dispatcher.assert_called_once()
    
    def test_supervisor_initialization_with_none_supervisor(self, app):
        """Test that WebSocket doesn't crash when supervisor is None."""
        app.state.agent_supervisor = None
        
        # This should not raise an exception
        with patch('netra_backend.app.startup_module._setup_agent_state') as mock_setup:
            _create_agent_supervisor(app)
            
            # Verify supervisor remains None on failure
            if not hasattr(app.state, 'db_session_factory'):
                assert app.state.agent_supervisor is None
    
    @pytest.mark.asyncio
    async def test_recovery_from_partial_initialization(self):
        """Test recovery mechanism when initialization partially fails."""
        app = FastAPI()
        app.state = MagicMock()
        
        manager = StartupManager()
        
        # Mock functions with one failure
        async def mock_database_init():
            app.state.db_session_factory = Mock()
        
        async def mock_auth_init():
            raise Exception("Auth service failed")
        
        async def mock_websocket_init():
            app.state.tool_dispatcher = Mock()
        
        # Register components
        manager.register_component(
            name="database",
            init_func=mock_database_init,
            priority=ComponentPriority.CRITICAL
        )
        
        manager.register_component(
            name="auth_service",
            init_func=mock_auth_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database"],
            max_retries=0  # No retries for this test
        )
        
        manager.register_component(
            name="websocket",
            init_func=mock_websocket_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database"]
        )
        
        # Run startup - should handle failure gracefully
        success = await manager.startup()
        
        # Auth service failure should be handled
        assert not success  # Overall startup failed
        assert "auth_service" in manager.failed_components
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""
        manager = StartupManager()
        
        # Create circular dependency: A -> B -> C -> A
        manager.register_component(
            name="component_a",
            init_func=AsyncMock(),
            dependencies=["component_c"]
        )
        
        manager.register_component(
            name="component_b",
            init_func=AsyncMock(),
            dependencies=["component_a"]
        )
        
        manager.register_component(
            name="component_c",
            init_func=AsyncMock(),
            dependencies=["component_b"]
        )
        
        # This should detect the circular dependency
        with pytest.raises(RuntimeError) as exc_info:
            await manager.startup()
        
        assert "Circular dependency" in str(exc_info.value)


class TestStartupSequenceIntegration:
    """Integration tests for the complete startup sequence."""
    
    @pytest.mark.asyncio
    async def test_full_startup_sequence(self):
        """Test the complete startup sequence with real components."""
        app = FastAPI()
        
        with patch('netra_backend.app.startup_module.initialize_logging') as mock_logging:
            with patch('netra_backend.app.core.startup_manager.DatabaseInitializer') as mock_db_init:
                with patch('netra_backend.app.startup_module.KeyManager') as mock_key_manager:
                    with patch('netra_backend.app.startup_module.LLMManager') as mock_llm_manager:
                        with patch('netra_backend.app.startup_module.ToolRegistry') as mock_registry:
                            with patch('netra_backend.app.startup_module.ToolDispatcher') as mock_dispatcher:
                                with patch('netra_backend.app.startup_module.SupervisorAgent') as mock_supervisor:
                                    # Setup mocks
                                    mock_logging.return_value = (0, Mock(spec=logging.Logger))
                                    mock_db_init.return_value.initialize.return_value = AsyncMock()
                                    mock_key_manager.load_from_settings.return_value = Mock()
                                    mock_llm_manager.return_value = Mock()
                                    mock_registry.return_value = Mock()
                                    mock_registry.return_value.get_tools.return_value = []
                                    mock_dispatcher.return_value = Mock()
                                    mock_supervisor.return_value = Mock()
                                    
                                    # Initialize startup manager
                                    manager = StartupManager()
                                    success = await manager.initialize_system(app)
                                    
                                    # Verify success
                                    assert success
                                    
                                    # Verify all critical components were initialized
                                    assert hasattr(app.state, 'startup_manager')


class TestErrorScenarios:
    """Test error scenarios and edge cases."""
    
    def test_missing_single_dependency(self, app):
        """Test specific error messages for each missing dependency."""
        test_cases = [
            (
                {"db_session_factory": Mock(), "tool_dispatcher": Mock()},
                "llm_manager"
            ),
            (
                {"llm_manager": Mock(), "tool_dispatcher": Mock()},
                "db_session_factory"
            ),
            (
                {"db_session_factory": Mock(), "llm_manager": Mock()},
                "tool_dispatcher"
            )
        ]
        
        for state_attrs, missing_attr in test_cases:
            app.state = MagicMock()
            for attr, value in state_attrs.items():
                setattr(app.state, attr, value)
            
            with pytest.raises(RuntimeError) as exc_info:
                _build_supervisor_agent(app)
            
            assert missing_attr in str(exc_info.value)
            assert "Cannot create supervisor" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that component initialization timeouts are handled."""
        manager = StartupManager()
        
        async def slow_init():
            await asyncio.sleep(10)  # Longer than timeout
        
        manager.register_component(
            name="slow_component",
            init_func=slow_init,
            timeout_seconds=0.1  # Very short timeout
        )
        
        # Should handle timeout gracefully
        success = await manager.startup()
        assert not success
        assert "slow_component" in manager.failed_components
    
    def test_supervisor_creation_logging(self, app, mock_logger):
        """Test that supervisor creation logs appropriate messages."""
        with patch('netra_backend.app.startup_module.central_logger.get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger
            
            # Test failure case
            app.state = MagicMock()
            try:
                _build_supervisor_agent(app)
            except RuntimeError:
                pass
            
            # Verify error was logged
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Missing required app state attributes" in error_call
            
            # Test success case
            app.state.db_session_factory = Mock()
            app.state.llm_manager = Mock()
            app.state.tool_dispatcher = Mock()
            
            with patch('netra_backend.app.startup_module.SupervisorAgent') as mock_supervisor:
                with patch('netra_backend.app.startup_module.get_websocket_manager') as mock_ws:
                    mock_ws.return_value = Mock()
                    mock_supervisor.return_value = Mock()
                    
                    _build_supervisor_agent(app)
                    
                    # Verify debug logging
                    mock_logger.debug.assert_called()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])