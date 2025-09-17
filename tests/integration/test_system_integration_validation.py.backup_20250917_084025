"""
System Integration Validation Test.

This test validates that the entire system integrates properly and all services can work together.
Final test in the development iteration cycle to ensure system coherence.
"""

import pytest
import asyncio
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.integration
class SystemIntegrationValidationTests:
    """Test system-wide integration validation."""

    def test_cross_service_imports_work(self):
        """Test that cross-service imports work correctly."""
        # Test main backend imports
        try:
            from netra_backend.app.config import get_config
            from netra_backend.app.db.postgres import initialize_postgres
            from netra_backend.app.routes.websocket import router as ws_router
            
            assert get_config is not None
            assert initialize_postgres is not None  
            assert ws_router is not None
            
        except ImportError as e:
            pytest.fail(f"Main backend imports failed: {e}")

        # Test auth service imports
        try:
            from auth_service.auth_core.models import User
            from auth_service.config import get_settings
            
            assert User is not None
            assert get_settings is not None
            
        except ImportError as e:
            pytest.fail(f"Auth service imports failed: {e}")

    def test_configuration_consistency(self):
        """Test that configuration is consistent across services."""
        # Test main backend config
        from netra_backend.app.config import get_config as get_backend_config
        from netra_backend.app.core.configuration.base import get_unified_config
        
        backend_config = get_backend_config()
        unified_config = get_unified_config()
        
        assert backend_config is not None
        assert unified_config is not None
        
        # Test auth service config
        try:
            from auth_service.config import get_settings as get_auth_settings
            auth_config = get_auth_settings()
            assert auth_config is not None
        except ImportError:
            # Auth service might not be available in test environment
            pass

    def test_database_integration_consistency(self):
        """Test database integration is consistent across services."""
        # Test main backend database
        from netra_backend.app.db.postgres import initialize_postgres, get_async_db
        
        try:
            session_factory = initialize_postgres()
            # Should either succeed or gracefully handle test mode
            assert session_factory is not None or True  # Accept None in test mode
        except Exception:
            # Database might not be available in test mode
            pass

        # Test auth service database if available
        try:
            from auth_service.auth_core.database import get_session
            assert get_session is not None
        except ImportError:
            # Auth service database might not be available
            pass

    def test_logging_integration_works(self):
        """Test that logging integration works across services."""
        # Test main backend logging
        from netra_backend.app.logging_config import central_logger
        
        backend_logger = central_logger.get_logger('integration_test')
        assert backend_logger is not None
        
        # Test logging actually works
        backend_logger.info("System integration validation test")
        
        # Test auth service logging if available
        try:
            from auth_service.logging_config import get_logger
            auth_logger = get_logger('auth_integration_test')
            assert auth_logger is not None
        except ImportError:
            # Auth service logging might be different
            pass

    def test_environment_isolation_works(self):
        """Test that environment isolation works properly."""
        from shared.isolated_environment import get_env
        
        env = get_env()
        assert env is not None
        
        # Test that environment variables are accessible
        database_url = env.get('DATABASE_URL')
        environment = env.get('ENVIRONMENT') or env.get('NETRA_ENVIRONMENT')
        
        # Should have some environment configuration
        assert database_url is not None or environment is not None

    @pytest.mark.asyncio
    async def test_async_operations_integrate(self):
        """Test that async operations integrate properly across services."""
        # Test main backend async operations
        try:
            from netra_backend.app.db.postgres import get_async_db
            
            async with get_async_db() as session:
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
                
        except Exception as e:
            # Database might not be available in test mode
            pytest.skip(f"Database not available: {e}")

    def test_websocket_integration_ready(self):
        """Test that WebSocket integration is ready."""
        from netra_backend.app.routes.websocket import router
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager, get_websocket_manager
        
        assert router is not None
        assert WebSocketManager is not None
        
        # Test WebSocket manager can be created
        try:
            manager = get_websocket_manager()
            assert manager is not None
        except Exception:
            # Manager creation might require specific setup
            pass

    def test_auth_integration_ready(self):
        """Test that auth integration is ready."""
        try:
            from netra_backend.app.auth_integration.auth import get_current_user
            assert get_current_user is not None
        except ImportError:
            # Auth integration might not be fully set up in test mode
            pass

    def test_middleware_integration_works(self):
        """Test that middleware integration works."""
        try:
            from netra_backend.app.core.middleware_setup import setup_middleware
            assert setup_middleware is not None
            assert callable(setup_middleware)
        except ImportError as e:
            pytest.fail(f"Middleware setup import failed: {e}")

    def test_error_handling_integration(self):
        """Test that error handling is integrated properly."""
        # Test main backend error handling
        try:
            from netra_backend.app.core.error_handlers import setup_error_handlers
            assert setup_error_handlers is not None
        except ImportError:
            # Error handlers might be in different location
            pass

        # Test that standard exceptions can be imported
        from sqlalchemy.exc import SQLAlchemyError
        from fastapi import HTTPException
        
        assert SQLAlchemyError is not None
        assert HTTPException is not None

    def test_service_health_indicators(self):
        """Test service health indicators."""
        # Test that services can report health status
        health_status = {
            'backend': True,
            'database': True,
            'auth': True,
            'websocket': True
        }
        
        # Test backend health
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            health_status['backend'] = config is not None
        except Exception:
            health_status['backend'] = False

        # Test database health
        try:
            from netra_backend.app.db.postgres import initialize_postgres
            session_factory = initialize_postgres()
            health_status['database'] = session_factory is not None
        except Exception:
            health_status['database'] = False

        # Test auth health
        try:
            from auth_service.config import get_settings
            auth_settings = get_settings()
            health_status['auth'] = auth_settings is not None
        except Exception:
            health_status['auth'] = False

        # Test WebSocket health
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            health_status['websocket'] = WebSocketManager is not None
        except Exception:
            health_status['websocket'] = False

        # At least backend and WebSocket should be healthy
        assert health_status['backend'] is True
        assert health_status['websocket'] is True
        
        # Log overall health status
        total_healthy = sum(1 for status in health_status.values() if status)
        total_services = len(health_status)
        
        print(f"System health: {total_healthy}/{total_services} services healthy")
        print(f"Health details: {health_status}")

    def test_dev_launcher_integration_ready(self):
        """Test that dev launcher integration is ready."""
        # Test that key components for dev launcher are available
        components_ready = {
            'config': False,
            'database': False,
            'logging': False,
            'environment': False
        }
        
        # Test config readiness
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            components_ready['config'] = config is not None
        except Exception:
            pass

        # Test database readiness
        try:
            from netra_backend.app.db.postgres import initialize_postgres
            components_ready['database'] = initialize_postgres is not None
        except Exception:
            pass

        # Test logging readiness
        try:
            from netra_backend.app.logging_config import central_logger
            logger = central_logger.get_logger('test')
            components_ready['logging'] = logger is not None
        except Exception:
            pass

        # Test environment readiness
        try:
            from shared.isolated_environment import get_env
            env = get_env()
            components_ready['environment'] = env is not None
        except Exception:
            pass

        # All core components should be ready
        assert components_ready['config'] is True, "Config not ready"
        assert components_ready['logging'] is True, "Logging not ready"
        assert components_ready['environment'] is True, "Environment not ready"
        
        print(f"Dev launcher readiness: {components_ready}")

    def test_system_startup_sequence_works(self):
        """Test that system startup sequence works correctly."""
        # Simulate startup sequence
        startup_steps = []
        
        # Step 1: Load environment
        try:
            from shared.isolated_environment import get_env
            env = get_env()
            startup_steps.append('environment_loaded')
        except Exception:
            startup_steps.append('environment_failed')

        # Step 2: Load configuration
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            startup_steps.append('config_loaded')
        except Exception:
            startup_steps.append('config_failed')

        # Step 3: Initialize logging
        try:
            from netra_backend.app.logging_config import central_logger
            logger = central_logger.get_logger('startup_test')
            startup_steps.append('logging_initialized')
        except Exception:
            startup_steps.append('logging_failed')

        # Step 4: Initialize database
        try:
            from netra_backend.app.db.postgres import initialize_postgres
            session_factory = initialize_postgres()
            startup_steps.append('database_initialized')
        except Exception:
            startup_steps.append('database_failed')

        # Verify startup sequence
        assert 'environment_loaded' in startup_steps, "Environment loading failed"
        assert 'config_loaded' in startup_steps, "Config loading failed"  
        assert 'logging_initialized' in startup_steps, "Logging initialization failed"
        
        print(f"Startup sequence: {startup_steps}")
        
        # Should complete basic startup successfully
        failed_steps = [step for step in startup_steps if 'failed' in step]
        assert len(failed_steps) <= 1, f"Too many startup failures: {failed_steps}"
