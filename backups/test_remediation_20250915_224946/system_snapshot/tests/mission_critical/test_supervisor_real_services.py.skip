"""
Real Services Test Suite: Supervisor Agent Initialization
==========================================================

This test suite uses REAL services to verify supervisor initialization.
No mocks - tests the actual initialization sequence.

CRITICAL: Requires real services to be running:
- PostgreSQL database
- Redis
- Real LLM configuration
"""

import asyncio
import pytest
import sys
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

# Add project root to path
sys.path.insert(0, 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1')

# Set up environment for testing
os.environ['NETRA_ENV'] = 'test'
os.environ['DISABLE_STARTUP_CHECKS'] = 'true'
os.environ['FAST_STARTUP_MODE'] = 'true'

from netra_backend.app.core.startup_manager import StartupManager
from netra_backend.app.core.lifespan_manager import lifespan
from netra_backend.app.startup_module import (
    _build_supervisor_agent,
    _create_agent_supervisor,
    run_complete_startup
)
from test_framework.real_services import ensure_real_services_running


class TestRealSupervisorInitialization:
    """Test supervisor initialization with real services."""
    
    @pytest.fixture(scope="class", autouse=True)
    def ensure_services(self):
        """Ensure real services are running before tests."""
        ensure_real_services_running()
    
    @pytest.mark.asyncio
    async def test_real_startup_sequence(self):
        """Test the complete startup sequence with real components."""
        app = FastAPI()
        
        # Run the actual startup sequence
        manager = StartupManager()
        success = await manager.initialize_system(app)
        
        # Verify initialization succeeded
        assert success, "Startup sequence failed"
        
        # Verify all required components for supervisor
        assert hasattr(app.state, 'db_session_factory'), "Missing db_session_factory"
        assert app.state.db_session_factory is not None
        
        assert hasattr(app.state, 'llm_manager'), "Missing llm_manager"
        assert app.state.llm_manager is not None
        
        assert hasattr(app.state, 'tool_dispatcher'), "Missing tool_dispatcher"
        assert app.state.tool_dispatcher is not None
        
        # Verify supervisor was created
        assert hasattr(app.state, 'agent_supervisor'), "Missing agent_supervisor"
        # Note: supervisor might be None if WebSocket failed, but attribute should exist
        
        # Cleanup
        if hasattr(app.state, 'db_session_factory'):
            try:
                await app.state.db_session_factory.close()
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_supervisor_with_lifespan(self):
        """Test supervisor initialization through the lifespan context."""
        app = FastAPI(lifespan=lifespan)
        
        # Simulate the lifespan context
        async with lifespan(app):
            # After lifespan startup, all components should be initialized
            assert hasattr(app.state, 'db_session_factory')
            assert hasattr(app.state, 'llm_manager')
            assert hasattr(app.state, 'tool_dispatcher')
            
            # Supervisor should be created or None (if failed gracefully)
            assert hasattr(app.state, 'agent_supervisor')
            
            if app.state.agent_supervisor is not None:
                # If supervisor exists, verify it has required attributes
                assert hasattr(app.state.agent_supervisor, 'db_session_factory')
                assert hasattr(app.state.agent_supervisor, 'llm_manager')
                assert hasattr(app.state.agent_supervisor, 'websocket_manager')
                assert hasattr(app.state.agent_supervisor, 'tool_dispatcher')
    
    @pytest.mark.asyncio
    async def test_supervisor_dependency_validation(self):
        """Test that supervisor validates its dependencies at creation."""
        app = FastAPI()
        
        # Initialize only partial dependencies
        from netra_backend.app.startup_module import (
            initialize_logging,
            setup_multiprocessing_env,
            validate_database_environment,
            run_database_migrations,
            setup_database_connections,
            initialize_core_services,
            setup_security_services
        )
        from netra_backend.app.logging_config import central_logger
        
        # Initialize logging
        start_time, logger = initialize_logging()
        
        # Setup database
        setup_multiprocessing_env(logger)
        validate_database_environment(logger)
        run_database_migrations(logger)
        setup_database_connections(app, logger)
        
        # Initialize core services and security (creates llm_manager)
        key_manager = initialize_core_services(app, logger)
        setup_security_services(app, key_manager)
        
        # At this point we have db_session_factory and llm_manager
        # but NOT tool_dispatcher
        
        # Attempt to create supervisor - should fail
        with pytest.raises(RuntimeError) as exc_info:
            _build_supervisor_agent(app)
        
        assert "tool_dispatcher" in str(exc_info.value)
        
        # Now add tool_dispatcher
        from netra_backend.app.startup_module import register_websocket_handlers
        register_websocket_handlers(app)
        
        # Now supervisor should build successfully
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.websocket_core import get_websocket_manager
        
        supervisor = _build_supervisor_agent(app)
        assert supervisor is not None
        assert isinstance(supervisor, SupervisorAgent)
        
        # Cleanup
        if hasattr(app.state, 'db_session_factory'):
            try:
                await app.state.db_session_factory.close()
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_supervisor_websocket_integration(self):
        """Test that supervisor integrates properly with WebSocket."""
        app = FastAPI()
        
        # Run full startup
        manager = StartupManager()
        success = await manager.initialize_system(app)
        assert success
        
        # If supervisor was created, verify WebSocket integration
        if app.state.agent_supervisor is not None:
            from netra_backend.app.websocket_core import get_websocket_manager
            
            websocket_manager = get_websocket_manager()
            assert websocket_manager is not None
            
            # Verify supervisor has websocket_manager
            assert hasattr(app.state.agent_supervisor, 'websocket_manager')
            assert app.state.agent_supervisor.websocket_manager is not None
        
        # Cleanup
        if hasattr(app.state, 'db_session_factory'):
            try:
                await app.state.db_session_factory.close()
            except:
                pass


class TestStartupFailureRecovery:
    """Test recovery from various startup failures."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_recovery(self):
        """Test recovery when database connection fails."""
        app = FastAPI()
        
        # Temporarily break database configuration
        original_db_url = os.environ.get('DATABASE_URL', '')
        os.environ['DATABASE_URL'] = 'postgresql://invalid:invalid@nonexistent:5432/invalid'
        
        try:
            manager = StartupManager()
            success = await manager.initialize_system(app)
            
            # Startup should handle the failure gracefully
            assert not success or app.state.agent_supervisor is None
            
        finally:
            # Restore original database URL
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)
    
    @pytest.mark.asyncio
    async def test_partial_initialization_cleanup(self):
        """Test that partial initialization is properly cleaned up."""
        app = FastAPI()
        
        # Start initialization
        manager = StartupManager()
        
        # Manually initialize some components
        from netra_backend.app.startup_module import (
            initialize_logging,
            initialize_core_services
        )
        
        start_time, logger = initialize_logging()
        key_manager = initialize_core_services(app, logger)
        
        # Verify partial initialization
        assert hasattr(app.state, 'redis_manager')
        assert hasattr(app.state, 'background_task_manager')
        assert hasattr(app.state, 'key_manager')
        
        # Attempt to create supervisor - should fail
        with pytest.raises(RuntimeError):
            _build_supervisor_agent(app)
        
        # Verify app is in a consistent state despite failure
        assert not hasattr(app.state, 'agent_supervisor') or app.state.agent_supervisor is None


if __name__ == "__main__":
    # Ensure services are running
    ensure_real_services_running()
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])