"""
Mission critical test for WebSocket startup dependencies.
Tests that agent_supervisor and thread_service are properly initialized
before WebSocket endpoints are accessed.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.websockets import WebSocketDisconnect

from netra_backend.app.startup_module import (
    _run_startup_phase_two,
    _run_startup_phase_three,
    _create_agent_supervisor,
    setup_security_services,
)


class TestWebSocketStartupDependencies:
    """Test WebSocket dependencies are properly initialized during startup."""
    
    @pytest.mark.asyncio
    async def test_phase_two_initializes_llm_manager(self):
        """Test that Phase 2 properly initializes llm_manager."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock logger
        logger = Mock()
        
        # Mock database setup
        with patch('netra_backend.app.startup_module.setup_database_connections', new_callable=AsyncMock):
            # Mock core services
            with patch('netra_backend.app.startup_module.initialize_core_services') as mock_init_core:
                mock_key_manager = Mock()
                mock_init_core.return_value = mock_key_manager
                
                # Mock ClickHouse
                with patch('netra_backend.app.startup_module.initialize_clickhouse', new_callable=AsyncMock):
                    # Mock background task manager
                    with patch('netra_backend.app.startup_module.background_task_manager'):
                        # Mock startup fixes
                        with patch('netra_backend.app.startup_module.startup_fixes') as mock_fixes:
                            mock_fixes.run_comprehensive_verification = AsyncMock(return_value={'total_fixes': 5})
                            
                            # Run Phase 2
                            await _run_startup_phase_two(app, logger)
                            
                            # Verify llm_manager is set
                            assert hasattr(app.state, 'llm_manager')
                            assert app.state.llm_manager is not None
                            
                            # Verify logging
                            logger.info.assert_any_call("Phase 2 completed successfully - core services initialized")
    
    @pytest.mark.asyncio
    async def test_phase_three_requires_dependencies(self):
        """Test that Phase 3 fails properly when dependencies are missing."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock logger
        logger = Mock()
        
        # Don't set required dependencies
        delattr(app.state, 'llm_manager')
        delattr(app.state, 'db_session_factory')
        
        # Mock other Phase 3 functions
        with patch('netra_backend.app.startup_module.startup_health_checks', new_callable=AsyncMock):
            with patch('netra_backend.app.startup_module.validate_schema', new_callable=AsyncMock):
                with patch('netra_backend.app.startup_module.register_websocket_handlers'):
                    with patch('netra_backend.app.startup_module.initialize_websocket_components', new_callable=AsyncMock):
                        with patch('netra_backend.app.startup_module.start_monitoring', new_callable=AsyncMock):
                            # Mock environment to staging
                            with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
                                mock_env.return_value.get.return_value = 'staging'
                                
                                # Phase 3 should fail
                                with pytest.raises(RuntimeError) as exc_info:
                                    await _run_startup_phase_three(app, logger)
                                
                                assert "missing dependencies" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_supervisor_logs_missing_dependencies(self):
        """Test that supervisor creation logs detailed missing dependencies."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Set some but not all dependencies
        app.state.db_session_factory = Mock()
        # Don't set llm_manager
        delattr(app.state, 'llm_manager')
        app.state.tool_dispatcher = Mock()
        
        # Mock environment
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = 'staging'
            
            # Try to create supervisor
            with pytest.raises(RuntimeError) as exc_info:
                _create_agent_supervisor(app)
            
            assert "llm_manager" in str(exc_info.value)
            assert "missing dependencies" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_websocket_fails_gracefully_without_supervisor(self):
        """Test that WebSocket endpoint fails gracefully when supervisor is missing."""
        from netra_backend.app.routes.websocket import websocket_endpoint
        
        # Create mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.app.state = MagicMock()
        mock_websocket.headers = {"sec-websocket-protocol": ""}
        
        # Don't set supervisor
        mock_websocket.app.state.agent_supervisor = None
        mock_websocket.app.state.thread_service = None
        
        # Mock environment as staging
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = 'staging'
            
            # WebSocket should raise error in staging
            with pytest.raises(RuntimeError) as exc_info:
                await websocket_endpoint(mock_websocket)
            
            assert "Critical WebSocket dependencies missing" in str(exc_info.value)
            assert "agent_supervisor" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_full_startup_sequence_success(self):
        """Test successful full startup sequence with all dependencies."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock logger
        logger = Mock()
        
        # Mock all Phase 2 dependencies
        with patch('netra_backend.app.startup_module.setup_database_connections', new_callable=AsyncMock):
            with patch('netra_backend.app.startup_module.initialize_core_services') as mock_init_core:
                mock_key_manager = Mock()
                mock_init_core.return_value = mock_key_manager
                
                with patch('netra_backend.app.startup_module.initialize_clickhouse', new_callable=AsyncMock):
                    with patch('netra_backend.app.startup_module.background_task_manager'):
                        with patch('netra_backend.app.startup_module.startup_fixes') as mock_fixes:
                            mock_fixes.run_comprehensive_verification = AsyncMock(return_value={'total_fixes': 5})
                            
                            # Run Phase 2
                            await _run_startup_phase_two(app, logger)
                            
                            # Set tool_dispatcher for Phase 3
                            app.state.tool_dispatcher = Mock()
                            
                            # Mock Phase 3 dependencies
                            with patch('netra_backend.app.startup_module.startup_health_checks', new_callable=AsyncMock):
                                with patch('netra_backend.app.startup_module.validate_schema', new_callable=AsyncMock):
                                    with patch('netra_backend.app.startup_module.register_websocket_handlers'):
                                        with patch('netra_backend.app.startup_module.initialize_websocket_components', new_callable=AsyncMock):
                                            with patch('netra_backend.app.startup_module.start_monitoring', new_callable=AsyncMock):
                                                # Mock supervisor creation
                                                with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent') as mock_supervisor_class:
                                                    mock_supervisor = Mock()
                                                    mock_supervisor_class.return_value = mock_supervisor
                                                    mock_supervisor.registry = Mock()
                                                    
                                                    # Run Phase 3
                                                    await _run_startup_phase_three(app, logger)
                                                    
                                                    # Verify supervisor and thread_service are set
                                                    assert hasattr(app.state, 'agent_supervisor')
                                                    assert app.state.agent_supervisor is not None
                                                    assert hasattr(app.state, 'thread_service')
                                                    assert app.state.thread_service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])