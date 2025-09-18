#!/usr/bin/env python3
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

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    ServiceReadinessCheck,
    GCPReadinessResult,
    create_gcp_websocket_validator,
    gcp_websocket_readiness_guard,
    gcp_websocket_readiness_check
)


class TestGCPWebSocketInitializationValidator:
    """Unit tests for GCP WebSocket initialization validator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock environment
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        
        # Mock logger
        self.logger_patcher = patch('netra_backend.app.logging_config.central_logger.get_logger')
        self.mock_logger = self.logger_patcher.start()
        
        # Mock app state
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
        # Configure mock environment for GCP staging
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'K_SERVICE': 'netra-backend',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        assert validator.environment == 'staging'
        assert validator.is_gcp_environment == True
        assert validator.is_cloud_run == True
        assert validator.current_state == GCPReadinessState.UNKNOWN
        
        # Check that readiness checks are registered
        assert 'database' in validator.readiness_checks
        assert 'redis' in validator.readiness_checks
        assert 'agent_supervisor' in validator.readiness_checks
        assert 'websocket_bridge' in validator.readiness_checks
    
    def test_validator_initialization_non_gcp_environment(self):
        """Test validator initialization for non-GCP environment."""
        # Configure mock environment for local development
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
        
        # Staging should have balanced timeouts (0.7x multiplier)
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
        
        # Production should have conservative timeouts (1.0x multiplier)
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
        
        # Development should have fast timeouts (0.3x multiplier)
        assert validator.timeout_multiplier == 0.3
        assert validator.safety_margin == 1.0
        assert validator.max_total_timeout == 3.0
    
    def test_get_optimized_timeout(self):
        """Test environment-optimized timeout calculation."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'K_SERVICE': 'netra-backend'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Base timeout of 10.0s in staging (0.7 * 1.1) = 7.7s, capped at 5.0s
        optimized = validator._get_optimized_timeout(10.0)
        assert optimized == 5.0  # Capped by max_total_timeout
        
        # Smaller timeout should not be capped
        optimized_small = validator._get_optimized_timeout(3.0)
        expected = 3.0 * 0.7 * 1.1  # 2.31s
        assert abs(optimized_small - expected) < 0.01
        
        # Cloud Run minimum should be enforced
        optimized_tiny = validator._get_optimized_timeout(0.1)
        assert optimized_tiny >= validator.min_cloud_run_timeout
    
    def test_update_environment_configuration(self):
        """Test environment configuration update functionality."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'development'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Initially non-GCP
        assert validator.is_gcp_environment == False
        
        # Update to GCP environment
        validator.update_environment_configuration('staging', True)
        
        assert validator.environment == 'staging'
        assert validator.is_gcp_environment == True
        
        # Check that readiness checks were re-registered
        assert len(validator.readiness_checks) > 0
        assert 'database' in validator.readiness_checks
    
    def test_validate_database_readiness_staging_bypass(self):
        """Test ISSUE #919 FIX: database readiness with staging bypass."""
        # Setup staging GCP environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # No app_state available (early initialization)
        validator = GCPWebSocketInitializationValidator(None)
        
        # Should return True due to staging bypass
        ready = validator._validate_database_readiness()
        assert ready == True
    
    def test_validate_database_readiness_production_strict(self):
        """Test database readiness with production strict validation."""
        # Setup production environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'GOOGLE_CLOUD_PROJECT': 'netra-production'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # No app_state available
        validator = GCPWebSocketInitializationValidator(None)
        
        # Should return False due to strict production validation
        ready = validator._validate_database_readiness()
        assert ready == False
    
    def test_validate_database_readiness_with_app_state(self):
        """Test database readiness with valid app_state."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state with database factory
        self.mock_app_state.db_session_factory = Mock()  # Not None
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
        
        # Mock app_state with connected Redis
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = True
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        ready = await validator._validate_redis_readiness()
        assert ready == True
    
    @pytest.mark.asyncio
    async def test_validate_redis_readiness_degraded_mode_staging(self):
        """Test ISSUE #919 FIX: Redis degraded mode in staging."""
        # Setup staging environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state with Redis manager but not connected
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = False
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return True due to staging graceful degradation
        ready = await validator._validate_redis_readiness()
        assert ready == True
    
    @pytest.mark.asyncio
    async def test_validate_redis_readiness_production_failure(self):
        """Test Redis readiness failure in production."""
        # Setup production environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'GOOGLE_CLOUD_PROJECT': 'netra-production'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state with Redis manager but not connected
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = False
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return False due to strict production validation
        ready = await validator._validate_redis_readiness()
        assert ready == False
    
    def test_validate_agent_supervisor_readiness_startup_phase_check(self):
        """Test ISSUE #919 FIX: agent supervisor validation with startup phase check."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state in early startup phase
        self.mock_app_state.startup_phase = 'init'  # Early phase
        self.mock_app_state.agent_supervisor = Mock()  # Available but shouldn't validate yet
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return False because we're in early startup phase
        ready = validator._validate_agent_supervisor_readiness()
        assert ready == False
    
    def test_validate_agent_supervisor_readiness_services_phase(self):
        """Test agent supervisor validation in services phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state in services phase
        self.mock_app_state.startup_phase = 'services'  # Services phase
        self.mock_app_state.agent_supervisor = Mock()  # Available
        self.mock_app_state.thread_service = Mock()  # Available
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return True because we're in services phase with available services
        ready = validator._validate_agent_supervisor_readiness()
        assert ready == True
    
    def test_validate_websocket_bridge_readiness_early_phase(self):
        """Test WebSocket bridge validation in early startup phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'production'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state in early startup phase
        self.mock_app_state.startup_phase = 'database'  # Early phase
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return False because we're in early startup phase
        ready = validator._validate_websocket_bridge_readiness()
        assert ready == False
    
    def test_validate_websocket_bridge_readiness_staging_degradation(self):
        """Test ISSUE #919 FIX: WebSocket bridge graceful degradation in staging."""
        # Setup staging environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state without bridge (or None bridge)
        self.mock_app_state.startup_phase = 'services'
        self.mock_app_state.agent_websocket_bridge = None
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return True due to staging graceful degradation
        ready = validator._validate_websocket_bridge_readiness()
        assert ready == True
    
    def test_validate_websocket_integration_readiness_websocket_phase(self):
        """Test ISSUE #919 FIX: WebSocket integration validation in websocket phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state in websocket phase (should pass)
        self.mock_app_state.startup_phase = 'websocket'
        self.mock_app_state.startup_complete = False  # Not yet complete
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return True because we're in websocket phase
        ready = validator._validate_websocket_integration_readiness()
        assert ready == True
    
    def test_validate_websocket_integration_readiness_early_phase(self):
        """Test WebSocket integration validation in early phase."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state in early phase
        self.mock_app_state.startup_phase = 'init'
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should return False because we're in early phase
        ready = validator._validate_websocket_integration_readiness()
        assert ready == False
    
    @pytest.mark.asyncio
    async def test_wait_for_startup_phase_completion_success(self):
        """Test waiting for startup phase completion - success case."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state that transitions to services phase
        self.mock_app_state.startup_phase = 'services'
        self.mock_app_state.startup_failed = False
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should complete immediately since we're already at services phase
        result = await validator._wait_for_startup_phase_completion('services', timeout_seconds=1.0)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_wait_for_startup_phase_completion_timeout(self):
        """Test waiting for startup phase completion - timeout case."""
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'staging'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state that never reaches services phase
        self.mock_app_state.startup_phase = 'init'
        self.mock_app_state.startup_failed = False
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should timeout since startup phase never progresses
        result = await validator._wait_for_startup_phase_completion('services', timeout_seconds=0.2)
        assert result == False
    
    @pytest.mark.asyncio
    async def test_validate_gcp_readiness_for_websocket_issue_919_fix(self):
        """Test ISSUE #919 FIX: GCP readiness validation with unknown startup_phase."""
        # Setup GCP environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'gcp-active-dev'
        mock_env_manager.get.side_effect = lambda key, default='': {
            'K_SERVICE': 'netra-backend',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock app_state with startup_phase stuck at 'unknown' (Issue #919)
        self.mock_app_state.startup_phase = 'unknown'
        self.mock_app_state.startup_complete = False
        self.mock_app_state.startup_failed = False
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Mock service validations to succeed
        with patch.object(validator, '_validate_service_group') as mock_validate:
            mock_validate.return_value = {
                'success': True,
                'failed': [],
                'success_count': 3,
                'total_count': 3
            }
            
            # Should succeed despite unknown startup phase due to Issue #919 fix
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
            
            assert result.ready == True
            assert result.state == GCPReadinessState.WEBSOCKET_READY
            assert len(result.failed_services) == 0
    
    @pytest.mark.asyncio
    async def test_validate_gcp_readiness_for_websocket_non_gcp_environment(self):
        """Test GCP readiness validation for non-GCP environment."""
        # Setup non-GCP environment
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'development'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        validator = GCPWebSocketInitializationValidator(self.mock_app_state)
        
        # Should skip validation for non-GCP environment
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
        
        # Mock all validators to succeed
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
        
        # Mock database to succeed, redis to fail
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
        
        # Create a check that fails first, then succeeds
        call_count = 0
        def mock_validator():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # Fail first call, succeed on second
        
        check = ServiceReadinessCheck(
            name='test_service',
            validator=mock_validator,
            timeout_seconds=5.0,
            retry_count=3,
            retry_delay=0.1,
            is_critical=True
        )
        
        # Should succeed on second attempt
        result = await validator._validate_single_service(check, timeout_seconds=5.0)
        assert result == True
        assert call_count == 2  # Called twice


class TestGCPValidatorFactory:
    """Test validator factory functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock environment
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        
        mock_env_manager = Mock()
        mock_env_manager.get_environment_name.return_value = 'test'
        mock_env_manager.get.side_effect = lambda key, default='': {}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        
        # Mock logger
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
        
        # Mock successful validation
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
        
        # Mock failed validation
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.create_gcp_websocket_validator') as mock_create:
            mock_validator = Mock()
            mock_result = Mock()
            mock_result.ready = False
            mock_result.failed_services = ['agent_supervisor']
            mock_validator.validate_gcp_readiness_for_websocket = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_validator
            
            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="GCP WebSocket readiness validation failed"):
                async with gcp_websocket_readiness_guard(mock_app_state):
                    pass
    
    @pytest.mark.asyncio
    async def test_gcp_websocket_readiness_check_staging_bypass(self):
        """Test ISSUE #919 FIX: GCP readiness check with staging bypass."""
        mock_app_state = Mock()
        
        # Mock environment with staging bypass
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'BYPASS_WEBSOCKET_READINESS_STAGING': 'true'
            }.get(key, default)
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
        
        # Mock environment without bypass
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'production',
                'BYPASS_WEBSOCKET_READINESS_STAGING': 'false'
            }.get(key, default)
            mock_get_env.return_value = mock_env_manager
            
            # Mock validator
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])