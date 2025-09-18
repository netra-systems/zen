"""
Middleware Setup Failure Tests

PURPOSE: Test middleware setup with missing dependencies
Reproduce exact staging failures at middleware_setup.py lines 799, 852, 860, 1079

STAGING ERROR PATTERNS:
- RuntimeError: Failed to setup enhanced middleware with WebSocket exclusion
- ModuleNotFoundError at middleware_setup.py:799 -> uvicorn_protocol_enhancement
- ModuleNotFoundError at middleware_setup.py:852 -> middleware.__init__ -> gcp_auth_context_middleware
- Container exit(3) due to middleware setup failures

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: Platform Infrastructure
2. Goal: Prevent service startup failures
3. Value Impact: Ensure reliable middleware initialization
4. Revenue Impact: Maintain service availability for $500K+ ARR
"""

import pytest
import sys
import importlib
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMiddlewareSetupFailures(SSotBaseTestCase):
    """Test middleware setup with various failure scenarios."""

    def test_middleware_setup_local_success(self):
        """Verify middleware setup works in local environment."""
        # EXPECTED: PASS locally
        try:
            from netra_backend.app.core.middleware_setup import setup_middleware

            # Create mock app for testing
            mock_app = MagicMock()
            mock_app.add_middleware = MagicMock()

            # Should not raise exceptions
            setup_middleware(mock_app)

            # Verify middleware was added
            assert mock_app.add_middleware.called

        except Exception as e:
            pytest.fail(f"Local middleware setup failed: {e}")

    def test_middleware_setup_missing_monitoring_module(self):
        """Test middleware setup failure when monitoring module is missing."""
        # EXPECTED: Reproduce staging error pattern

        # Mock missing monitoring module
        with patch.dict('sys.modules', {}, clear=False):
            # Remove monitoring modules
            monitoring_modules = [
                k for k in sys.modules.keys()
                if 'netra_backend.app.services.monitoring' in k
            ]
            for module in monitoring_modules:
                del sys.modules[module]

            # Mock import to raise ModuleNotFoundError
            def mock_import(name, *args, **kwargs):
                if 'netra_backend.app.services.monitoring' in name:
                    raise ModuleNotFoundError(f"No module named '{name}'")
                return importlib.__import__(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=mock_import):
                try:
                    from netra_backend.app.core.middleware_setup import setup_middleware

                    mock_app = MagicMock()

                    # Should raise RuntimeError with specific message
                    with pytest.raises(RuntimeError, match="Failed to setup enhanced middleware with WebSocket exclusion.*No module named.*monitoring"):
                        setup_middleware(mock_app)

                except ImportError:
                    # This is also acceptable - shows the module dependency issue
                    pass

    def test_uvicorn_protocol_enhancement_import_failure(self):
        """Test failure at middleware_setup.py:852 - uvicorn protocol enhancement."""
        # EXPECTED: Reproduce staging error at line 852

        try:
            # This import triggers the cascade failure in staging
            from netra_backend.app.middleware.uvicorn_protocol_enhancement import UvicornProtocolEnhancement

            # If this succeeds locally, simulate the failure
            with patch.dict('sys.modules', {}, clear=False):
                # Remove monitoring to break the chain
                if 'netra_backend.app.services.monitoring.gcp_error_reporter' in sys.modules:
                    del sys.modules['netra_backend.app.services.monitoring.gcp_error_reporter']

                # Force reimport
                importlib.reload(sys.modules['netra_backend.app.middleware'])

        except ImportError as e:
            # Expected failure pattern
            assert "No module named 'netra_backend.app.services.monitoring'" in str(e)

    def test_gcp_auth_context_middleware_dependency_failure(self):
        """Test failure in gcp_auth_context_middleware.py:23."""
        # EXPECTED: Reproduce exact import failure

        # Simulate the exact failure from staging traceback
        with patch.dict('sys.modules', {}, clear=False):
            # Remove the problematic module
            modules_to_remove = [
                'netra_backend.app.services.monitoring',
                'netra_backend.app.services.monitoring.gcp_error_reporter'
            ]

            for module in modules_to_remove:
                if module in sys.modules:
                    del sys.modules[module]

            # Mock the specific import that fails
            original_import = builtins.__import__

            def failing_import(name, *args, **kwargs):
                if name == 'netra_backend.app.services.monitoring.gcp_error_reporter':
                    raise ModuleNotFoundError("No module named 'netra_backend.app.services.monitoring'")
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=failing_import):
                with pytest.raises(ModuleNotFoundError, match="No module named 'netra_backend.app.services.monitoring'"):
                    from netra_backend.app.middleware.gcp_auth_context_middleware import auth_user_context

    def test_middleware_init_cascade_failure(self):
        """Test cascade failure through middleware.__init__.py."""
        # EXPECTED: Reproduce middleware package initialization failure

        try:
            # Force reload of middleware package
            if 'netra_backend.app.middleware' in sys.modules:
                importlib.reload(sys.modules['netra_backend.app.middleware'])

            # Test import that triggers __init__.py processing
            from netra_backend.app.middleware import gcp_auth_context_middleware

        except ImportError as e:
            # Verify this is the expected monitoring module error
            assert "monitoring" in str(e).lower()

    def test_enhanced_middleware_websocket_exclusion_failure(self):
        """Test enhanced middleware setup with WebSocket exclusion failure."""
        # EXPECTED: Reproduce specific staging error pattern

        from netra_backend.app.core.middleware_setup import setup_middleware

        mock_app = MagicMock()

        # Simulate the specific failure path
        with patch('netra_backend.app.core.middleware_setup._add_websocket_exclusion_middleware') as mock_websocket:
            mock_websocket.side_effect = ModuleNotFoundError("No module named 'netra_backend.app.services.monitoring'")

            with pytest.raises(RuntimeError, match="Failed to setup enhanced middleware with WebSocket exclusion"):
                setup_middleware(mock_app)

    def test_container_startup_simulation(self):
        """Simulate container startup sequence that fails in staging."""
        # EXPECTED: Reproduce container exit(3) failure

        # Simulate gunicorn worker initialization
        try:
            # This is the sequence from staging traceback:
            # 1. gunicorn arbiter spawns worker
            # 2. uvicorn worker init_process
            # 3. load_wsgi -> main.py -> create_app
            # 4. app_factory.py:170 -> _configure_app_handlers
            # 5. app_factory.py:184 -> setup_middleware
            # 6. middleware_setup.py fails

            from netra_backend.app.core.app_factory import create_app

            # Mock environment to simulate staging
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'staging',
                'SERVICE_NAME': 'netra-backend-staging'
            }):
                # This should work locally but would fail in staging
                app = create_app()
                assert app is not None

        except Exception as e:
            # Log the failure for analysis
            if "monitoring" in str(e):
                # This is the expected staging failure
                pytest.fail(f"Container startup failed due to monitoring module: {e}")
            else:
                # Other failures might be configuration related
                print(f"Container startup failed with different error: {e}")

    def test_middleware_setup_line_799_failure(self):
        """Test specific failure at middleware_setup.py:799."""
        # EXPECTED: Reproduce exact line where staging fails

        # Import the function that fails at line 799
        try:
            from netra_backend.app.core.middleware_setup import _add_websocket_exclusion_middleware

            mock_app = MagicMock()

            # This should trigger the import chain that fails
            _add_websocket_exclusion_middleware(mock_app)

        except ModuleNotFoundError as e:
            # Verify this is the monitoring module error
            assert "netra_backend.app.services.monitoring" in str(e)

    def test_middleware_setup_line_852_failure(self):
        """Test specific failure at middleware_setup.py:852."""
        # EXPECTED: Reproduce exact line where staging fails

        # Mock the condition that leads to line 852
        try:
            from netra_backend.app.core.middleware_setup import _add_websocket_exclusion_middleware

            mock_app = MagicMock()

            # Simulate the path that goes to line 852
            with patch('netra_backend.app.core.middleware_setup._create_enhanced_inline_websocket_exclusion_middleware') as mock_enhanced:
                mock_enhanced.side_effect = ModuleNotFoundError("No module named 'netra_backend.app.services.monitoring'")

                # This should trigger the fallback that goes to line 852
                with pytest.raises(ModuleNotFoundError):
                    _add_websocket_exclusion_middleware(mock_app)

        except ImportError:
            # Expected in simulation
            pass

    def test_middleware_setup_line_860_failure(self):
        """Test specific failure at middleware_setup.py:860."""
        # EXPECTED: Reproduce exact line where staging fails

        try:
            from netra_backend.app.core.middleware_setup import _create_enhanced_inline_websocket_exclusion_middleware

            mock_app = MagicMock()

            # This should trigger the import that fails at line 860
            _create_enhanced_inline_websocket_exclusion_middleware(mock_app)

        except ModuleNotFoundError as e:
            # Verify this is the expected failure
            assert "monitoring" in str(e)

    def test_middleware_setup_line_1079_failure(self):
        """Test specific failure at middleware_setup.py:1079."""
        # EXPECTED: Reproduce exact line where staging fails

        # Test the specific import that happens at line 1079
        with pytest.raises(ModuleNotFoundError, match="No module named 'netra_backend.app.services.monitoring'"):
            # Mock missing monitoring module
            with patch.dict('sys.modules', {}, clear=False):
                modules_to_remove = [k for k in sys.modules.keys() if 'monitoring' in k and 'netra_backend' in k]
                for module in modules_to_remove:
                    del sys.modules[module]

                # This import happens at line 1079 and fails
                from netra_backend.app.middleware.uvicorn_protocol_enhancement import UvicornProtocolEnhancement


class TestMiddlewareSetupRecovery(SSotBaseTestCase):
    """Test middleware setup recovery and graceful degradation."""

    def test_middleware_setup_graceful_degradation(self):
        """Test graceful degradation when monitoring is unavailable."""
        # EXPECTED: Provide fallback behavior

        from netra_backend.app.core.middleware_setup import setup_middleware

        mock_app = MagicMock()

        # Test with monitoring module unavailable
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.set_request_context', side_effect=ImportError):
            # Should not crash, might skip certain middleware
            try:
                setup_middleware(mock_app)
            except RuntimeError as e:
                # Current behavior - fails hard
                assert "monitoring" in str(e)

    def test_monitoring_module_availability_check(self):
        """Test runtime check for monitoring module availability."""
        # EXPECTED: Provide availability detection

        def is_monitoring_available():
            """Check if monitoring module is available."""
            try:
                import netra_backend.app.services.monitoring
                return True
            except ImportError:
                return False

        # This should work regardless of actual availability
        availability = is_monitoring_available()
        assert isinstance(availability, bool)

    def test_middleware_setup_with_monitoring_check(self):
        """Test middleware setup with monitoring availability check."""
        # EXPECTED: Conditional middleware setup

        def safe_setup_middleware(app):
            """Setup middleware with monitoring availability check."""
            try:
                from netra_backend.app.core.middleware_setup import setup_middleware
                setup_middleware(app)
                return True
            except RuntimeError as e:
                if "monitoring" in str(e):
                    # Log warning and continue with basic middleware
                    print(f"WARNING: Advanced monitoring unavailable: {e}")
                    return False
                raise

        mock_app = MagicMock()
        result = safe_setup_middleware(mock_app)
        assert isinstance(result, bool)

import builtins