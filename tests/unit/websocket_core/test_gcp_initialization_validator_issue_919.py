"""
Unit Tests for GCP WebSocket Initialization Validator - Issue #919 Fix

MISSION CRITICAL: Tests the fix for startup_phase stuck at 'unknown' in GCP environments
causing WebSocket connections to be rejected even when services are actually ready.

ISSUE #919 ROOT CAUSE ANALYSIS:
- GCP Cloud Run environments may have startup_phase stuck at 'unknown'
- Previous logic required startup_phase to reach 'services' before proceeding
- Fix: Graceful degradation for GCP environments with unknown startup phase
- Solution: Skip startup phase requirement in GCP environments with unknown phase

Business Value Justification:
- Segment: Platform/Internal ($500K+ ARR protection)
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Prevents WebSocket 1011 errors that block chat functionality
- Strategic Impact: Enables reliable WebSocket connections in GCP Cloud Run
"""
import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
import sys
import os
sys.path.append('/Users/anthony/Desktop/netra-apex')
from netra_backend.app.websocket_core.gcp_initialization_validator import GCPWebSocketInitializationValidator, GCPReadinessState, ServiceReadinessCheck, GCPReadinessResult, create_gcp_websocket_validator, gcp_websocket_readiness_guard, gcp_websocket_readiness_check

@pytest.mark.unit
class TestGCPWebSocketInitializationValidator:
    """Unit tests for GCP WebSocket initialization validator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        self.logger_patcher = patch('netra_backend.app.logging_config.central_logger.get_logger')
        self.mock_logger = self.logger_patcher.start()
        self.mock_app_state = Mock()
        self.mock_app_state.startup_phase = 'unknown'
        self.mock_app_state.startup_complete = False
        self.mock_app_state.startup_failed = False

    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        self.logger_patcher.stop()

    def test_validator_initialization_gcp_environment(self):
        """Test validator initialization for GCP environment."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {'K_SERVICE': 'netra-backend', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        assert validator.environment == 'staging'
        assert validator.is_gcp_environment == True
        assert validator.is_cloud_run == True
        assert validator.current_state == GCPReadinessState.UNKNOWN
        assert 'database' in validator.readiness_checks
        assert 'redis' in validator.readiness_checks
        assert 'agent_supervisor' in validator.readiness_checks
        assert 'websocket_bridge' in validator.readiness_checks

    def test_validator_initialization_non_gcp_environment(self):
        """Test validator initialization for non-GCP environment."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'development'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        assert validator.environment == 'development'
        assert validator.is_gcp_environment == False
        assert validator.is_cloud_run == False

    def test_environment_timeout_configuration_staging(self):
        """Test environment-aware timeout configuration for staging."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        assert validator.timeout_multiplier == 0.7
        assert validator.safety_margin == 1.1
        assert validator.max_total_timeout == 5.0

    def test_environment_timeout_configuration_production(self):
        """Test environment-aware timeout configuration for production."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        assert validator.timeout_multiplier == 1.0
        assert validator.safety_margin == 1.2
        assert validator.max_total_timeout == 8.0

    def test_environment_timeout_configuration_development(self):
        """Test environment-aware timeout configuration for development."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'development'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        assert validator.timeout_multiplier == 0.3
        assert validator.safety_margin == 1.0
        assert validator.max_total_timeout == 3.0

    def test_get_optimized_timeout(self):
        """Test environment-optimized timeout calculation."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {'K_SERVICE': 'netra-backend'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        optimized = validator._get_optimized_timeout(10.0)
        assert optimized == 5.0
        optimized_small = validator._get_optimized_timeout(3.0)
        expected = 3.0 * 0.7 * 1.1
        assert abs(optimized_small - expected) < 0.01
        optimized_tiny = validator._get_optimized_timeout(0.1)
        assert optimized_tiny >= validator.min_cloud_run_timeout

    def test_update_environment_configuration(self):
        """Test environment configuration update functionality."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'development'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        assert validator.is_gcp_environment == False
        validator.update_environment_configuration('staging', True)
        assert validator.environment == 'staging'
        assert validator.is_gcp_environment == True
        assert len(validator.readiness_checks) > 0
        assert 'database' in validator.readiness_checks

    def test_validate_database_readiness_staging_bypass(self):
        """Test ISSUE #919 FIX: database readiness with staging bypass."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(None)
        ready = validator._validate_database_readiness()
        assert ready == True

    def test_validate_database_readiness_production_strict(self):
        """Test database readiness with production strict validation."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {'GOOGLE_CLOUD_PROJECT': 'netra-production'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(None)
        ready = validator._validate_database_readiness()
        assert ready == False

    def test_validate_database_readiness_with_app_state(self):
        """Test database readiness with valid app_state."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.db_session_factory = Mock()
        self.mock_app_state.database_available = True
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_database_readiness()
        assert ready == True

    @pytest.mark.asyncio
    async def test_validate_redis_readiness_ideal_case(self):
        """Test Redis readiness in ideal case (fully connected)."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = True
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = await validator._validate_redis_readiness()
        assert ready == True

    @pytest.mark.asyncio
    async def test_validate_redis_readiness_degraded_mode_staging(self):
        """Test ISSUE #919 FIX: Redis degraded mode in staging."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = False
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = await validator._validate_redis_readiness()
        assert ready == True

    @pytest.mark.asyncio
    async def test_validate_redis_readiness_production_failure(self):
        """Test Redis readiness failure in production."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {'GOOGLE_CLOUD_PROJECT': 'netra-production'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = False
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = await validator._validate_redis_readiness()
        assert ready == False

    def test_validate_agent_supervisor_readiness_startup_phase_check(self):
        """Test ISSUE #919 FIX: agent supervisor validation with startup phase check."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'init'
        self.mock_app_state.agent_supervisor = Mock()
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_agent_supervisor_readiness()
        assert ready == False

    def test_validate_agent_supervisor_readiness_services_phase(self):
        """Test agent supervisor validation in services phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'services'
        self.mock_app_state.agent_supervisor = Mock()
        self.mock_app_state.thread_service = Mock()
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_agent_supervisor_readiness()
        assert ready == True

    def test_validate_websocket_bridge_readiness_early_phase(self):
        """Test WebSocket bridge validation in early startup phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'database'
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_websocket_bridge_readiness()
        assert ready == False

    def test_validate_websocket_bridge_readiness_staging_degradation(self):
        """Test ISSUE #919 FIX: WebSocket bridge graceful degradation in staging."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'services'
        self.mock_app_state.agent_websocket_bridge = None
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_websocket_bridge_readiness()
        assert ready == True

    def test_validate_websocket_integration_readiness_websocket_phase(self):
        """Test ISSUE #919 FIX: WebSocket integration validation in websocket phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'websocket'
        self.mock_app_state.startup_complete = False
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_websocket_integration_readiness()
        assert ready == True

    def test_validate_websocket_integration_readiness_early_phase(self):
        """Test WebSocket integration validation in early phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'init'
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        ready = validator._validate_websocket_integration_readiness()
        assert ready == False

    @pytest.mark.asyncio
    async def test_wait_for_startup_phase_completion_success(self):
        """Test waiting for startup phase completion - success case."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'services'
        self.mock_app_state.startup_failed = False
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        result = await validator._wait_for_startup_phase_completion('services', timeout_seconds=1.0)
        assert result == True

    @pytest.mark.asyncio
    async def test_wait_for_startup_phase_completion_timeout(self):
        """Test waiting for startup phase completion - timeout case."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'init'
        self.mock_app_state.startup_failed = False
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        result = await validator._wait_for_startup_phase_completion('services', timeout_seconds=0.2)
        assert result == False

    @pytest.mark.asyncio
    async def test_validate_gcp_readiness_for_websocket_issue_919_fix(self):
        """Test ISSUE #919 FIX: GCP readiness validation with unknown startup_phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'gcp-active-dev'
        mock_env_manager.get.side_effect = lambda key, default='': {'K_SERVICE': 'netra-backend', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.mock_app_state.startup_phase = 'unknown'
        self.mock_app_state.startup_complete = False
        self.mock_app_state.startup_failed = False
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        with patch.object(validator, '_validate_service_group') as mock_validate:
            mock_validate.return_value = {'success': True, 'failed': [], 'success_count': 3, 'total_count': 3}
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
            assert result.ready == True
            assert result.state == GCPReadinessState.WEBSOCKET_READY
            assert len(result.failed_services) == 0

    @pytest.mark.asyncio
    async def test_validate_gcp_readiness_for_websocket_non_gcp_environment(self):
        """Test GCP readiness validation for non-GCP environment."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'development'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
        assert result.ready == True
        assert result.state == GCPReadinessState.WEBSOCKET_READY
        assert 'Skipped GCP validation for non-GCP environment' in result.warnings
        assert result.details['gcp_detected'] == False

    @pytest.mark.asyncio
    async def test_validate_service_group_success(self):
        """Test service group validation - all services pass."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        with patch.object(validator, '_validate_single_service', return_value=True):
            result = await validator._validate_service_group(['database', 'redis'], timeout_seconds=5.0)
            assert result['success'] == True
            assert len(result['failed']) == 0
            assert result['success_count'] == 2
            assert result['total_count'] == 2

    @pytest.mark.asyncio
    async def test_validate_service_group_partial_failure(self):
        """Test service group validation - some services fail."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)

        async def mock_validate_service(check, timeout):
            if check.name == 'database':
                return True
            elif check.name == 'redis':
                return False
            return True
        with patch.object(validator, '_validate_single_service', side_effect=mock_validate_service):
            result = await validator._validate_service_group(['database', 'redis'], timeout_seconds=5.0)
            assert result['success'] == False
            assert 'redis' in result['failed']
            assert result['success_count'] == 1
            assert result['total_count'] == 2

    @pytest.mark.asyncio
    async def test_validate_single_service_exponential_backoff(self):
        """Test single service validation with exponential backoff."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        call_count = 0

        def mock_validator():
            nonlocal call_count
            call_count += 1
            return call_count > 1
        check = ServiceReadinessCheck(name='test_service', validator=mock_validator, timeout_seconds=5.0, retry_count=3, retry_delay=0.1, is_critical=True)
        result = await validator._validate_single_service(check, timeout_seconds=5.0)
        assert result == True
        assert call_count == 2

@pytest.mark.unit
class TestGCPValidatorFactory:
    """Test validator factory functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'test'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.logger_patcher = patch('netra_backend.app.logging_config.central_logger.get_logger')
        self.mock_logger = self.logger_patcher.start()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        self.logger_patcher.stop()

    def test_create_gcp_websocket_validator(self):
        """Test creating GCP WebSocket validator."""
        mock_app_state = Mock()
        validator = create_gcp_websocket_validator(mock_app_state)
        assert isinstance(validator, GCPWebSocketInitializationValidator)
        assert validator.app_state == mock_app_state

    @pytest.mark.asyncio
    async def test_gcp_websocket_readiness_guard_success(self):
        """Test GCP WebSocket readiness guard - success case."""
        mock_app_state = Mock()
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.create_gcp_websocket_validator') as mock_create:
            mock_validator = Mock()
            mock_result = Mock()
            mock_result.ready = True
            mock_result.failed_services = []
            mock_validator.validate_gcp_readiness_for_websocket = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_validator
            async with gcp_websocket_readiness_guard(mock_app_state) as result:
                assert result.ready == True

    @pytest.mark.asyncio
    async def test_gcp_websocket_readiness_guard_failure(self):
        """Test GCP WebSocket readiness guard - failure case."""
        mock_app_state = Mock()
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.create_gcp_websocket_validator') as mock_create:
            mock_validator = Mock()
            mock_result = Mock()
            mock_result.ready = False
            mock_result.failed_services = ['agent_supervisor']
            mock_validator.validate_gcp_readiness_for_websocket = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_validator
            with pytest.raises(RuntimeError, match='GCP WebSocket readiness validation failed'):
                async with gcp_websocket_readiness_guard(mock_app_state):
                    pass

    @pytest.mark.asyncio
    async def test_gcp_websocket_readiness_check_staging_bypass(self):
        """Test ISSUE #919 FIX: GCP readiness check with staging bypass."""
        mock_app_state = Mock()
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging', 'BYPASS_WEBSOCKET_READINESS_STAGING': 'true'}.get(key, default)
            mock_get_env.return_value = mock_env_manager
            ready, details = await gcp_websocket_readiness_check(mock_app_state)
            assert ready == True
            assert details['bypass_active'] == True
            assert details['bypass_reason'] == 'staging_connectivity_remediation'
            assert details['state'] == 'bypassed_for_staging'

    @pytest.mark.asyncio
    async def test_gcp_websocket_readiness_check_normal_validation(self):
        """Test GCP readiness check with normal validation."""
        mock_app_state = Mock()
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'production', 'BYPASS_WEBSOCKET_READINESS_STAGING': 'false'}.get(key, default)
            mock_get_env.return_value = mock_env_manager
            with patch('netra_backend.app.websocket_core.gcp_initialization_validator.create_gcp_websocket_validator') as mock_create:
                mock_validator = Mock()
                mock_result = Mock()
                mock_result.ready = True
                mock_result.state = Mock()
                mock_result.state.value = 'websocket_ready'
                mock_result.elapsed_time = 1.5
                mock_result.failed_services = []
                mock_result.warnings = []
                mock_validator.validate_gcp_readiness_for_websocket = AsyncMock(return_value=mock_result)
                mock_validator.is_gcp_environment = True
                mock_validator.is_cloud_run = True
                mock_create.return_value = mock_validator
                ready, details = await gcp_websocket_readiness_check(mock_app_state)
                assert ready == True
                assert details['bypass_active'] == False
                assert details['state'] == 'websocket_ready'
                assert details['gcp_environment'] == True
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')