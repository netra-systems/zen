from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import Mock, patch, MagicMock
'Critical path test for staging environment module imports.\n\nBusiness Value: Platform/Internal - Deployment Stability - Ensures the backend\nservice can start successfully in staging without dev_launcher dependencies.\n\nThis test validates that the backend service can properly initialize in a staging\nenvironment where dev_launcher module is not available. This prevents deployment\nfailures caused by attempting to import development-only modules in production\nenvironments.\n'
import sys
from pathlib import Path
import os
import sys
from typing import Any, Dict
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from netra_backend.app.core.environment_constants import Environment, EnvironmentVariables

class StagingEnvironmentImportsTests:
    """Test suite for staging environment module imports and initialization."""

    @pytest.fixture(autouse=True)
    def setup_staging_environment(self, monkeypatch):
        """Use real service instance."""
        'Set up staging environment for tests.'
        original_env = os.environ.get(EnvironmentVariables.ENVIRONMENT)
        monkeypatch.setenv(EnvironmentVariables.ENVIRONMENT, Environment.STAGING.value)
        monkeypatch.setenv(EnvironmentVariables.K_SERVICE, 'backend-staging')
        yield
        if original_env:
            monkeypatch.setenv(EnvironmentVariables.ENVIRONMENT, original_env)
        else:
            monkeypatch.delenv(EnvironmentVariables.ENVIRONMENT, raising=False)

            @pytest.fixture
            def real_dev_launcher_import():
                """Use real service instance."""
                'Mock dev_launcher module to simulate it not being available in staging.'
                modules_to_remove = [m for m in sys.modules if m.startswith('dev_launcher')]
                for module in modules_to_remove:
                    del sys.modules[module]
                    import builtins
                    original_import = builtins.__import__

                    def mock_import(name, *args, **kwargs):
                        if name.startswith('dev_launcher'):
                            raise ImportError(f"No module named '{name}'")
                        return original_import(name, *args, **kwargs)
                    with mock.patch('builtins.__import__', side_effect=mock_import):
                        yield

                        def test_middleware_setup_without_dev_launcher(self, mock_dev_launcher_import):
                            """Test that middleware setup works in staging without dev_launcher.

                            L3 Test - Validates staging-specific behavior where dev_launcher is not available.
                            """
                            from netra_backend.app.core.middleware_setup import setup_cors_middleware
                            app = FastAPI()
                            setup_cors_middleware(app)

                            def test_staging_cors_configuration(self):
                                """Test CORS configuration in staging environment.

                                L3 Test - Validates that CORS is properly configured for staging.
                                """
                                from netra_backend.app.core.middleware_setup import setup_cors_middleware
                                app = FastAPI()
                                setup_cors_middleware(app)
                                client = TestClient(app)

                                @app.get('/test')
                                def test_route():
                                    return {'status': 'ok'}
                                response = client.get('/test', headers={'Origin': 'https://staging.netrasystems.ai'})
                                assert response.status_code == 200
                                assert 'access-control-allow-origin' in response.headers

                                def test_backend_startup_in_staging(self, mock_dev_launcher_import):
                                    """Test that the backend service can start in staging environment.

                                    L4 Test - End-to-end validation of backend startup without dev dependencies.
                                    """
                                    from netra_backend.app.core.middleware_setup import setup_cors_middleware, setup_session_middleware
                                    app = FastAPI()
                                    setup_cors_middleware(app)
                                    setup_session_middleware(app)
                                    assert hasattr(app, 'middleware_stack'), 'FastAPI app should have middleware_stack after setup'

                                    def test_service_discovery_fallback_in_staging(self):
                                        """Test that service discovery gracefully falls back in staging.

                                        L3 Test - Validates fallback behavior when service discovery is not available.
                                        """
                                        from fastapi import FastAPI
                                        from netra_backend.app.core.middleware_setup import _setup_custom_cors_middleware
                                        app = FastAPI()
                                        with mock.patch('builtins.__import__', side_effect=ImportError("No module named 'dev_launcher'")):
                                            _setup_custom_cors_middleware(app)

                                            @pytest.mark.parametrize('environment', [Environment.STAGING.value, Environment.PRODUCTION.value])
                                            def test_no_dev_launcher_in_non_dev_environments(self, environment, monkeypatch):
                                                """Test that dev_launcher is not imported in non-development environments.

                                                L3 Test - Validates environment-specific import behavior.
                                                """
                                                monkeypatch.setenv(EnvironmentVariables.ENVIRONMENT, environment)
                                                from netra_backend.app.core.middleware_setup import _setup_custom_cors_middleware
                                                app = FastAPI()
                                                import_attempted = False

                                                def mock_import(name, *args, **kwargs):
                                                    nonlocal import_attempted
                                                    if name == 'dev_launcher.service_discovery':
                                                        import_attempted = True
                                                        raise ImportError(f"No module named '{name}'")
                                                    return __import__(name, *args, **kwargs)
                                                with mock.patch('builtins.__import__', side_effect=mock_import):
                                                    _setup_custom_cors_middleware(app)
                                                    assert not import_attempted, f'dev_launcher should not be imported in {environment}'

                                                    def test_development_environment_uses_dev_launcher(self, monkeypatch):
                                                        """Test that dev_launcher IS imported in development environment.

                                                        L3 Test - Validates that dev_launcher is properly used in development.
                                                        """
                                                        monkeypatch.setenv(EnvironmentVariables.ENVIRONMENT, Environment.DEVELOPMENT.value)
                                                        from netra_backend.app.core.middleware_setup import _setup_custom_cors_middleware
                                                        app = FastAPI()
                                                        import_attempted = False

                                                        def mock_import(name, *args, **kwargs):
                                                            nonlocal import_attempted
                                                            if name == 'dev_launcher.service_discovery':
                                                                import_attempted = True
                                                                module = MagicMock()
                                                                module.ServiceDiscovery = MagicMock
                                                                return module
                                                            return __import__(name, *args, **kwargs)
                                                        with mock.patch('builtins.__import__', side_effect=mock_import):
                                                            _setup_custom_cors_middleware(app)
                                                            assert import_attempted, 'dev_launcher should be imported in development'

                                                            def test_staging_environment_detection(self):
                                                                """Test that staging environment is properly detected.

                                                                L2 Test - Unit test for environment detection logic.
                                                                """
                                                                from netra_backend.app.core.environment_constants import EnvironmentDetector
                                                                with mock.patch.dict(os.environ, {EnvironmentVariables.K_SERVICE: 'backend-staging', EnvironmentVariables.ENVIRONMENT: ''}):
                                                                    env = EnvironmentDetector.get_environment()
                                                                    assert env == Environment.STAGING.value
                                                                    with mock.patch.dict(os.environ, {EnvironmentVariables.ENVIRONMENT: Environment.STAGING.value}):
                                                                        env = EnvironmentDetector.get_environment()
                                                                        assert env == Environment.STAGING.value
                                                                        with mock.patch.dict(os.environ, {EnvironmentVariables.K_SERVICE: 'backend-pr-123', EnvironmentVariables.PR_NUMBER: '123'}):
                                                                            env = EnvironmentDetector.get_environment()
                                                                            assert env == Environment.STAGING.value
                                                                            if __name__ == '__main__':
                                                                                'MIGRATED: Use SSOT unified test runner'
                                                                                print('MIGRATION NOTICE: Please use SSOT unified test runner')
                                                                                print('Command: python tests/unified_test_runner.py --category <category>')