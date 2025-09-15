"""
Test case for Issue #403: GCP-active-dev-medium-fallback-dependency-checker

This test verifies that the EnvironmentContextService is properly initialized
during startup, preventing the system from falling back to the limited
ServiceDependencyChecker.

Root Cause: The _initialize_environment_context method was not calling
await service.initialize(), leaving the service uninitialized.

Business Impact: MEDIUM - Reduced validation capabilities in Cloud Run environment.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from netra_backend.app.smd import StartupOrchestrator
from netra_backend.app.core.environment_context import EnvironmentContextService, EnvironmentType

@pytest.mark.unit
class TestIssue403EnvironmentContextInitialization:
    """Test suite for Issue #403 - EnvironmentContext initialization fix."""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        app = MagicMock()
        app.state = MagicMock()
        return app

    @pytest.fixture
    def startup_orchestrator(self, mock_app):
        """Create StartupOrchestrator instance."""
        return StartupOrchestrator(mock_app)

    @pytest.mark.asyncio
    async def test_environment_context_initialization_calls_proper_async_method(self, startup_orchestrator):
        """
        Test that _initialize_environment_context calls the proper async initialization.

        CRITICAL: This test ensures the root cause of Issue #403 is fixed.
        """
        with patch('netra_backend.app.core.environment_context.initialize_environment_context') as mock_init:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_type.return_value = EnvironmentType.STAGING
            mock_init.return_value = mock_service
            await startup_orchestrator._initialize_environment_context()
            mock_init.assert_called_once()
            assert startup_orchestrator.app.state.environment_context_service == mock_service

    @pytest.mark.asyncio
    async def test_environment_context_initialization_handles_failure_gracefully(self, startup_orchestrator):
        """
        Test that initialization failure doesn't crash startup but allows fallback.

        BUSINESS IMPACT: Ensures system stability while logging the issue for monitoring.
        """
        with patch('netra_backend.app.core.environment_context.initialize_environment_context') as mock_init:
            mock_init.side_effect = RuntimeError('Environment detection failed')
            await startup_orchestrator._initialize_environment_context()
            assert startup_orchestrator.app.state.environment_context_service is None

    @pytest.mark.asyncio
    async def test_startup_phase1_calls_async_environment_context_initialization(self):
        """
        Test that Phase 1 startup properly calls async environment context initialization.

        INTEGRATION TEST: Ensures the async call chain works in startup sequence.
        """
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        orchestrator = StartupOrchestrator(mock_app)
        with patch.object(orchestrator, '_validate_environment'):
            with patch.object(orchestrator, '_run_migrations') as mock_migrations:
                mock_migrations.return_value = None
                with patch.object(orchestrator, '_initialize_environment_context') as mock_env_init:
                    mock_env_init.return_value = None
                    await orchestrator._phase1_foundation()
                    mock_env_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_properly_initialized_environment_context_service_prevents_fallback(self):
        """
        Test that properly initialized EnvironmentContextService prevents fallback.

        BUSINESS VALUE: Ensures full validation capabilities instead of limited fallback.
        """
        from netra_backend.app.core.startup_validation import StartupValidator
        from netra_backend.app.core.environment_context import EnvironmentContextService
        with patch('netra_backend.app.core.startup_validation.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_get_service.return_value = mock_service
            with patch('netra_backend.app.core.startup_validation.ServiceDependencyChecker') as mock_checker_class:
                mock_checker = MagicMock()
                mock_checker_class.return_value = mock_checker
                validator = StartupValidator()
                checker = validator._get_service_dependency_checker()
                assert checker is not None
                assert checker == mock_checker
                mock_checker_class.assert_called_once_with(environment_context_service=mock_service)

    def test_issue_403_root_cause_validation(self):
        """
        Validate that the root cause identified in Issue #403 is addressed.

        ROOT CAUSE: _initialize_environment_context was sync method that didn't call await initialize()
        FIX: Method is now async and calls await initialize_environment_context()
        """
        from netra_backend.app.smd import StartupOrchestrator
        import inspect
        assert inspect.iscoroutinefunction(StartupOrchestrator._initialize_environment_context), '_initialize_environment_context must be async to properly initialize the service'
        sig = inspect.signature(StartupOrchestrator._initialize_environment_context)
        assert str(sig.return_annotation) == 'None', 'Method should return None but be async'

    def test_startup_orchestrator_imports_correct_initialization_function(self):
        """
        Test that StartupOrchestrator imports the correct async initialization function.

        CRITICAL: Ensures we're using initialize_environment_context() not just EnvironmentContextService()
        """
        try:
            from netra_backend.app.core.environment_context import initialize_environment_context
            assert callable(initialize_environment_context), 'initialize_environment_context should be importable and callable'
            import inspect
            assert inspect.iscoroutinefunction(initialize_environment_context), 'initialize_environment_context should be an async function'
        except ImportError:
            pytest.fail('initialize_environment_context should be importable from environment_context module')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')