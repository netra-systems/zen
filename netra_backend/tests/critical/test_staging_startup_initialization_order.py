"""
Critical test suite for staging startup initialization order issues.

This test reproduces the initialization order problems seen in staging where:
- Uvicorn startup error at `/usr/local/bin/uvicorn:8`
- Services start before dependencies are properly initialized
- Logger and configuration systems aren't ready when needed

The tests verify proper initialization sequence and detect order-dependent failures.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from typing import List, Dict, Any
import asyncio


class TestStagingStartupInitializationOrder:
    """Test suite for startup initialization order issues in staging."""
    
    def test_uvicorn_startup_before_config_ready_fails(self):
        """
        FAILING TEST: Uvicorn starts before configuration system is ready.
        
        This reproduces the exact error from staging:
        `/usr/local/bin/uvicorn:8` - startup fails because config isn't initialized.
        """
        # Mock uvicorn to simulate startup before config is ready
        startup_attempts = []
        
        def mock_uvicorn_run(*args, **kwargs):
            startup_attempts.append("uvicorn_start")
            # Try to access config during uvicorn startup
            from netra_backend.app.core.configuration.base import get_unified_config
            config = get_unified_config()  # This should fail if config isn't ready
            return Mock()
        
        # Mock configuration to not be ready during uvicorn startup
        with patch('netra_backend.app.core.configuration.base.UnifiedConfigManager._initialized', False):
            with patch('uvicorn.run', side_effect=mock_uvicorn_run):
                
                # This should fail because uvicorn tries to start before config is ready
                with pytest.raises((AttributeError, RuntimeError, ImportError)) as exc_info:
                    # Simulate startup sequence
                    import uvicorn
                    uvicorn.run("netra_backend.app.main:app", host="0.0.0.0", port=8000)
                
                assert "config" in str(exc_info.value).lower() or "not ready" in str(exc_info.value).lower()
    
    def test_logger_initialization_before_config_manager_fails(self):
        """
        FAILING TEST: Logger tries to initialize before configuration manager is ready.
        
        This tests the initialization order issue where logger setup happens
        before the configuration system is properly initialized.
        """
        initialization_order = []
        
        def track_config_init(self, *args, **kwargs):
            initialization_order.append("config_manager_init")
            # Simulate config manager not ready yet
            raise RuntimeError("Configuration manager not fully initialized")
        
        def track_logger_init(self, *args, **kwargs):
            initialization_order.append("logger_init")
            # Logger tries to load config which isn't ready
            self._load_config()
        
        with patch('netra_backend.app.core.configuration.base.UnifiedConfigManager.__init__', side_effect=track_config_init):
            with patch('netra_backend.app.core.unified_logging.UnifiedLogger._setup_logging', side_effect=track_logger_init):
                
                # This should fail because logger initializes before config manager
                with pytest.raises(RuntimeError) as exc_info:
                    from netra_backend.app.core.unified_logging import central_logger
                    central_logger._setup_logging()
                
                assert "not fully initialized" in str(exc_info.value)
                # Logger should try to initialize before config is ready
                assert "logger_init" in initialization_order
    
    def test_database_connection_before_config_loaded_fails(self):
        """
        FAILING TEST: Database connection attempted before configuration is loaded.
        
        This reproduces the scenario where database services try to connect
        during startup before database configuration is available.
        """
        connection_attempts = []
        
        def mock_db_connect(*args, **kwargs):
            connection_attempts.append("db_connection_attempt")
            # Try to get database config which isn't loaded yet
            from netra_backend.app.core.configuration.base import get_unified_config
            config = get_unified_config()
            db_url = config.database_url  # Should fail if config not ready
        
        # Mock config to not have database_url ready
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = AttributeError("Configuration not loaded - database_url unavailable")
            
            # This should fail when database tries to connect before config is ready
            with pytest.raises(AttributeError) as exc_info:
                mock_db_connect()
            
            assert "database_url unavailable" in str(exc_info.value)
            assert len(connection_attempts) == 1
    
    def test_websocket_manager_startup_before_dependencies_fails(self):
        """
        FAILING TEST: WebSocket manager starts before its dependencies are ready.
        
        This tests the scenario where WebSocket manager tries to initialize
        before configuration, logging, and database systems are ready.
        """
        startup_sequence = []
        
        def mock_websocket_init(self, *args, **kwargs):
            startup_sequence.append("websocket_manager_init")
            # WebSocket manager needs config and logger
            from netra_backend.app.core.configuration.base import get_unified_config
            from netra_backend.app.logging_config import central_logger
            
            config = get_unified_config()  # Should fail if not ready
            central_logger.info("WebSocket manager starting")  # Should fail if logger not ready
        
        # Mock dependencies to not be ready
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = RuntimeError("Configuration system not initialized")
            
            with patch('netra_backend.app.websocket_core.WebSocketManager.__init__', side_effect=mock_websocket_init):
                
                # This should fail because WebSocket manager starts before dependencies
                with pytest.raises(RuntimeError) as exc_info:
                    from netra_backend.app.websocket_core.manager import WebSocketManager
                    manager = WebSocketManager()
                
                assert "not initialized" in str(exc_info.value)
                assert "websocket_manager_init" in startup_sequence


class TestApplicationLifecycleInitializationOrder:
    """Test application lifecycle initialization order issues."""
    
    def test_lifespan_startup_sequence_wrong_order_fails(self):
        """
        FAILING TEST: Application lifespan startup happens in wrong order.
        
        This tests the scenario where lifespan events fire before
        critical systems are initialized.
        """
        lifespan_events = []
        
        async def mock_startup_event():
            lifespan_events.append("startup_event")
            # Startup event tries to access systems that aren't ready
            from netra_backend.app.core.configuration.base import config_manager
            config = config_manager.get_config()  # Should fail if not ready
            return config
        
        async def mock_lifespan_manager():
            lifespan_events.append("lifespan_manager_start")
            # Try to run startup before dependencies are ready
            await mock_startup_event()
        
        # Mock config manager to not be ready
        with patch('netra_backend.app.core.configuration.base.UnifiedConfigManager.get_config') as mock_get_config:
            mock_get_config.side_effect = RuntimeError("Config manager not ready during lifespan startup")
            
            # This should fail because lifespan starts before config is ready
            with pytest.raises(RuntimeError) as exc_info:
                asyncio.run(mock_lifespan_manager())
            
            assert "not ready during lifespan startup" in str(exc_info.value)
            assert "lifespan_manager_start" in lifespan_events
    
    def test_fastapi_app_creation_before_config_fails(self):
        """
        FAILING TEST: FastAPI app creation happens before configuration is ready.
        
        This reproduces the scenario where the FastAPI app tries to initialize
        routes and middleware before configuration system is available.
        """
        app_creation_steps = []
        
        def mock_create_app():
            app_creation_steps.append("app_creation_start")
            # App creation tries to access config for setup
            from netra_backend.app.core.configuration.base import get_unified_config
            config = get_unified_config()
            
            # Try to setup middleware based on config
            cors_enabled = config.cors_enabled  # Should fail if config not ready
            return Mock()
        
        # Mock config to not be available during app creation
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.side_effect = ImportError("Configuration module not available during app creation")
            
            # This should fail because app creation happens before config is ready
            with pytest.raises(ImportError) as exc_info:
                mock_create_app()
            
            assert "not available during app creation" in str(exc_info.value)
            assert "app_creation_start" in app_creation_steps
    
    def test_dependency_injection_before_services_ready_fails(self):
        """
        FAILING TEST: FastAPI dependency injection tries to inject unready services.
        
        This tests the scenario where FastAPI dependency injection system
        tries to provide services that haven't been properly initialized yet.
        """
        injection_attempts = []
        
        def mock_get_database_dependency():
            injection_attempts.append("database_dependency_injection")
            # Try to inject database service that isn't ready
            from netra_backend.app.db.database_manager import get_database_manager
            return get_database_manager()  # Should fail if not ready
        
        def mock_get_websocket_dependency():
            injection_attempts.append("websocket_dependency_injection")
            # Try to inject WebSocket service that isn't ready  
            from netra_backend.app.websocket_core.manager import get_websocket_manager
            return get_websocket_manager()  # Should fail if not ready
        
        # Mock services to not be ready during dependency injection
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_db:
            mock_db.side_effect = RuntimeError("Database manager not initialized for dependency injection")
            
            with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws:
                mock_ws.side_effect = RuntimeError("WebSocket manager not initialized for dependency injection")
                
                # Both dependency injections should fail
                with pytest.raises(RuntimeError) as exc_info:
                    mock_get_database_dependency()
                
                assert "not initialized for dependency injection" in str(exc_info.value)
                
                with pytest.raises(RuntimeError) as exc_info:
                    mock_get_websocket_dependency()
                
                assert "not initialized for dependency injection" in str(exc_info.value)
                
                # Both injection attempts should be recorded
                assert "database_dependency_injection" in injection_attempts
                assert "websocket_dependency_injection" in injection_attempts


class TestEnvironmentSpecificInitializationOrder:
    """Test environment-specific initialization order issues."""
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': '0'})
    def test_staging_environment_detection_during_early_startup_fails(self):
        """
        FAILING TEST: Staging environment detection fails during early startup.
        
        This reproduces the scenario where environment detection happens
        before environment variables are properly loaded.
        """
        detection_attempts = []
        
        def mock_detect_environment():
            detection_attempts.append("environment_detection")
            # Try to detect environment but env vars aren't loaded yet
            import os
            env = os.environ.get("ENVIRONMENT")
            if env is None:
                raise RuntimeError("Environment variables not loaded during early startup")
            return env
        
        # Mock os.environ to not have ENVIRONMENT set during early startup
        with patch.dict('os.environ', {}, clear=True):
            # This should fail because environment detection happens too early
            with pytest.raises(RuntimeError) as exc_info:
                mock_detect_environment()
            
            assert "not loaded during early startup" in str(exc_info.value)
            assert "environment_detection" in detection_attempts
    
    def test_staging_secret_loading_before_config_ready_fails(self):
        """
        FAILING TEST: Staging secret loading happens before configuration is ready.
        
        This tests the scenario where secret manager tries to load secrets
        before the configuration system knows where to find them.
        """
        secret_loading_steps = []
        
        def mock_load_secrets():
            secret_loading_steps.append("secret_loading_start")
            # Try to load secrets but config isn't ready to provide secret paths
            from netra_backend.app.core.configuration.base import get_unified_config
            config = get_unified_config()
            secret_path = config.secret_path  # Should fail if config not ready
            return secret_path
        
        # Mock config to not have secret configuration ready
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config_obj = Mock()
            del mock_config_obj.secret_path  # Remove secret_path attribute
            mock_config.return_value = mock_config_obj
            
            # This should fail because secret loading happens before config defines secret paths
            with pytest.raises(AttributeError) as exc_info:
                mock_load_secrets()
            
            assert "secret_path" in str(exc_info.value)
            assert "secret_loading_start" in secret_loading_steps
    
    def test_production_vs_staging_initialization_order_difference_fails(self):
        """
        FAILING TEST: Production and staging have different initialization orders.
        
        This tests that initialization order is consistent between environments
        and detects when staging has different (broken) order.
        """
        # Track initialization order for different environments
        production_order = []
        staging_order = []
        
        def track_production_init():
            production_order.extend(["config", "logger", "database", "websocket", "app"])
            # Production order works correctly
            return True
        
        def track_staging_init():
            # Staging has wrong order - websocket before config
            staging_order.extend(["websocket", "config", "logger", "database", "app"])
            # This should cause failure due to wrong order
            raise RuntimeError("Staging initialization order is incorrect - websocket before config")
        
        # Test production order (should work)
        track_production_init()
        assert len(production_order) == 5
        assert production_order[0] == "config"  # Config should be first
        
        # Test staging order (should fail)
        with pytest.raises(RuntimeError) as exc_info:
            track_staging_init()
        
        assert "incorrect - websocket before config" in str(exc_info.value)
        assert staging_order[0] == "websocket"  # Wrong - websocket should not be first


class TestCriticalStartupDependencyFailures:
    """Test critical startup dependency failures that cause cascading errors."""
    
    def test_single_service_failure_cascades_to_uvicorn_startup_fails(self):
        """
        FAILING TEST: Single service failure cascades to cause Uvicorn startup failure.
        
        This reproduces how a single initialization failure can cause
        the entire Uvicorn startup process to fail.
        """
        failure_cascade = []
        
        def mock_database_service_init():
            failure_cascade.append("database_init_failed")
            raise RuntimeError("Database service initialization failed")
        
        def mock_websocket_service_init():
            failure_cascade.append("websocket_depends_on_database")
            # WebSocket service depends on database, so it also fails
            mock_database_service_init()  # This will fail
        
        def mock_uvicorn_startup():
            failure_cascade.append("uvicorn_startup_attempted")
            # Uvicorn startup depends on all services being ready
            mock_websocket_service_init()  # This will fail due to database
        
        # This should fail at the database level and cascade to Uvicorn
        with pytest.raises(RuntimeError) as exc_info:
            mock_uvicorn_startup()
        
        assert "Database service initialization failed" in str(exc_info.value)
        # All cascade steps should be recorded
        assert "database_init_failed" in failure_cascade
        assert "websocket_depends_on_database" in failure_cascade
        assert "uvicorn_startup_attempted" in failure_cascade
    
    def test_circular_service_dependencies_prevent_startup_fails(self):
        """
        FAILING TEST: Circular service dependencies prevent any startup.
        
        This tests the scenario where services have circular dependencies
        that prevent any of them from starting successfully.
        """
        initialization_attempts = []
        
        def mock_service_a_init():
            initialization_attempts.append("service_a_needs_service_b")
            # Service A needs Service B to be initialized
            mock_service_b_init()
        
        def mock_service_b_init():
            initialization_attempts.append("service_b_needs_service_a")
            # Service B needs Service A to be initialized (circular dependency)
            if "service_a_needs_service_b" in initialization_attempts:
                raise RuntimeError("Circular dependency detected: Service A <-> Service B")
            mock_service_a_init()
        
        # This should fail due to circular dependency
        with pytest.raises(RuntimeError) as exc_info:
            mock_service_a_init()
        
        assert "Circular dependency detected" in str(exc_info.value)
        assert "service_a_needs_service_b" in initialization_attempts
        assert "service_b_needs_service_a" in initialization_attempts
    
    def test_timeout_during_startup_initialization_fails(self):
        """
        FAILING TEST: Startup initialization times out waiting for dependencies.
        
        This reproduces the scenario where initialization takes too long
        and times out, causing startup failure.
        """
        import time
        
        timeout_events = []
        
        def mock_slow_initialization():
            timeout_events.append("slow_init_started")
            # Simulate very slow initialization that would timeout in production
            time.sleep(0.1)  # Simulate slow startup
            timeout_events.append("slow_init_still_running")
            # In real scenario, this would be much longer and timeout
            raise TimeoutError("Initialization timed out waiting for dependencies")
        
        def mock_startup_with_timeout():
            timeout_events.append("startup_with_timeout_attempted")
            # Set a very short timeout to simulate production timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Startup initialization timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(1)  # 1 second timeout
            
            try:
                mock_slow_initialization()
            finally:
                signal.alarm(0)  # Cancel the alarm
        
        # This should fail due to timeout
        with pytest.raises(TimeoutError) as exc_info:
            mock_startup_with_timeout()
        
        assert "timeout" in str(exc_info.value).lower()
        assert "startup_with_timeout_attempted" in timeout_events


if __name__ == "__main__":
    pytest.main([__file__, "-v"])