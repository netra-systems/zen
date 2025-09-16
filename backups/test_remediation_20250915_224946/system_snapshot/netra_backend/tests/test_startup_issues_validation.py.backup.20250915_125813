from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
'\nTest file to expose and validate startup issues\n\nThis test file exposes critical startup issues that were not caught by existing tests:\n1. Wrong StartupCheckResult import in startup_checks/__init__.py\n2. Missing ExecutionMonitor.start_monitoring method\n3. Schema validation service errors\n\nBusiness Value Justification (BVJ):\n- Segment: All (Free to Enterprise) \n- Business Goal: Stability\n- Value Impact: Prevents 100% of startup failures\n- Revenue Impact: Prevents complete service outages\n'
import asyncio
import sys
from pathlib import Path
import pytest

class TestStartupCheckResultImport:
    """Test that StartupCheckResult is properly imported"""

    def test_startup_check_result_has_correct_signature(self):
        """Test that StartupCheckResult from startup_checks has the expected signature"""
        from netra_backend.app.startup_checks.models import StartupCheckResult
        result = StartupCheckResult(name='test_check', success=True, message='Test message', critical=True, duration_ms=100.0)
        assert result.name == 'test_check'
        assert result.success == True
        assert result.message == 'Test message'
        assert result.critical == True
        assert result.duration_ms == 100.0

    def test_startup_checks_imports_correct_model(self):
        """Test that startup_checks module imports the correct StartupCheckResult"""
        from netra_backend.app.startup_checks import StartupCheckResult
        result = StartupCheckResult(name='environment_check', success=True, message='Environment OK', critical=False)
        assert hasattr(result, 'name'), "StartupCheckResult should have 'name' attribute"
        assert result.name == 'environment_check'

    @pytest.mark.asyncio
    async def test_environment_checker_uses_correct_model(self):
        """Test that EnvironmentChecker can create results with name parameter"""
        from netra_backend.app.startup_checks.environment_checks import EnvironmentChecker
        checker = EnvironmentChecker()
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test', 'NETRA_API_KEY': 'test-key', 'JWT_SECRET_KEY': 'secret'}):
            result = await checker.check_environment_variables()
            assert hasattr(result, 'name'), "Result should have 'name' attribute"
            assert result.name == 'environment_variables'

class TestExecutionMonitor:
    """Test that ExecutionMonitor has required methods"""

    def test_execution_monitor_has_start_monitoring(self):
        """Test that ExecutionMonitor has start_monitoring method"""
        from netra_backend.app.agents.base.monitoring import ExecutionMonitor
        monitor = ExecutionMonitor()
        assert hasattr(monitor, 'start_monitoring'), "ExecutionMonitor should have 'start_monitoring' method"

    def test_performance_monitor_can_start(self):
        """Test that the global performance_monitor can start monitoring"""
        from netra_backend.app.agents.base.monitoring import performance_monitor
        assert hasattr(performance_monitor, 'start_monitoring'), "performance_monitor should have 'start_monitoring' method"

    @pytest.mark.asyncio
    async def test_startup_module_can_start_monitoring(self):
        """Test that startup module can successfully start monitoring"""
        from netra_backend.app.agents.base.monitoring import ExecutionMonitor
        monitor = ExecutionMonitor()
        if hasattr(monitor, 'start_monitoring'):
            await monitor.start_monitoring()
        else:
            pytest.fail('ExecutionMonitor missing start_monitoring method')

class TestSchemaValidationService:
    """Test schema validation service errors"""

    @pytest.mark.asyncio
    async def test_schema_validation_imports(self):
        """Test that schema validation service has all required imports"""
        from netra_backend.app.services.schema_validation_service import SchemaValidationService
        assert SchemaValidationService is not None

    @pytest.mark.asyncio
    async def test_database_connectivity_check(self):
        """Test that check_database_connectivity doesn't reference undefined 'settings'"""
        from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
        from netra_backend.app.services.schema_validation_service import SchemaValidationService
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_conn = AsyncNone
        mock_result = AsyncNone
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_engine.connect.return_value.__aexit__.return_value = None
        result = await SchemaValidationService.check_database_connectivity(mock_engine)
        assert result == True

    @pytest.mark.asyncio
    async def test_run_comprehensive_validation(self):
        """Test that run_comprehensive_validation handles errors properly"""
        from sqlalchemy.ext.asyncio import AsyncEngine
        from netra_backend.app.services.schema_validation_service import run_comprehensive_validation
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_conn = AsyncNone
        mock_result = AsyncNone
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_engine.connect.return_value.__aexit__.return_value = None
        result = await run_comprehensive_validation(mock_engine)
        assert isinstance(result, bool)

class TestStartupIntegration:
    """Test the full startup process with all components"""

    @pytest.mark.asyncio
    async def test_startup_module_imports(self):
        """Test that startup module can import without errors"""
        try:
            from netra_backend.app import startup_module
            assert startup_module is not None
        except ImportError as e:
            pytest.fail(f'Failed to import startup_module: {e}')

    @pytest.mark.asyncio
    async def test_startup_checks_can_run(self):
        """Test that startup checks can run without critical errors"""
        from fastapi import FastAPI
        from netra_backend.app.startup_checks import run_startup_checks
        app = FastAPI()
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test', 'NETRA_API_KEY': 'test-key', 'JWT_SECRET_KEY': 'secret', 'REDIS_URL': 'redis://localhost', 'CLICKHOUSE_HOST': 'localhost'}):
            with patch('netra_backend.app.startup_checks.database_checks.AsyncEngine') as mock_engine:
                mock_conn = AsyncNone
                mock_result = AsyncNone
                mock_result.scalar.return_value = 1
                mock_conn.execute.return_value = mock_result
                mock_engine.connect.return_value.__aenter__.return_value = mock_conn
                results = await run_startup_checks(app)
                assert 'total_checks' in results
                assert 'passed' in results
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')