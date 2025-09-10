"""
Comprehensive Unit Tests for Configuration Drift Monitor SSOT Classes

Business Value Justification (BVJ):
- Segment: Platform/Internal - Configuration Stability & Risk Prevention Infrastructure
- Business Goal: System Stability & Configuration Regression Prevention  
- Value Impact: Validates monitoring that prevents $120K+ MRR cascade failures from configuration drift
- Revenue Impact: Configuration drift causes authentication failures affecting entire platform revenue

CRITICAL MISSION: Ensure Configuration Drift Monitor SSOT classes function correctly:
- ConfigurationDriftMonitor: Main drift detection and business impact analysis
- E2EOAuthSimulationKeyValidator: Validates E2E OAuth simulation key consistency  
- JWTSecretAlignmentValidator: Validates JWT secret alignment between services
- WebSocketConfigurationValidator: Validates WebSocket configuration coherence
- ConfigurationDrift: Data class for drift incident representation

These tests follow TEST_CREATION_GUIDE.md patterns exactly and validate real business value.
NO MOCKS except for external dependencies (subprocess, network calls, auth services).
Tests MUST RAISE ERRORS - no try/except hiding.
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, Mock, AsyncMock
from dataclasses import asdict

# SSOT imports following absolute import rules
from netra_backend.app.monitoring.configuration_drift_monitor import (
    ConfigurationDriftMonitor,
    E2EOAuthSimulationKeyValidator, 
    JWTSecretAlignmentValidator,
    WebSocketConfigurationValidator,
    ConfigurationDrift,
    DriftSeverity,
    ConfigurationScope,
    extend_staging_health_monitor_with_drift_detection,
    get_configuration_drift_monitor
)
from netra_backend.app.core.health_types import HealthCheckResult
from shared.isolated_environment import get_env


@pytest.mark.unit
class TestConfigurationDriftDataClasses:
    """Test Configuration Drift data classes and enums."""
    
    def test_drift_severity_enum(self):
        """Test DriftSeverity enum values."""
        assert DriftSeverity.CRITICAL.value == "critical"
        assert DriftSeverity.HIGH.value == "high"
        assert DriftSeverity.MODERATE.value == "moderate"
        assert DriftSeverity.LOW.value == "low"
        assert DriftSeverity.INFORMATIONAL.value == "info"
        
        # Test all enum members exist
        expected_severities = {"critical", "high", "moderate", "low", "info"}
        actual_severities = {severity.value for severity in DriftSeverity}
        assert actual_severities == expected_severities, "All severity levels should be defined"
    
    def test_configuration_scope_enum(self):
        """Test ConfigurationScope enum values."""
        assert ConfigurationScope.AUTHENTICATION.value == "authentication"
        assert ConfigurationScope.WEBSOCKET.value == "websocket"
        assert ConfigurationScope.DATABASE.value == "database"
        assert ConfigurationScope.ENVIRONMENT.value == "environment"
        assert ConfigurationScope.API_ENDPOINTS.value == "api_endpoints"
        assert ConfigurationScope.CORS.value == "cors"
        
        # Test all enum members exist
        expected_scopes = {"authentication", "websocket", "database", "environment", "api_endpoints", "cors"}
        actual_scopes = {scope.value for scope in ConfigurationScope}
        assert actual_scopes == expected_scopes, "All configuration scopes should be defined"
    
    def test_configuration_drift_initialization(self):
        """Test ConfigurationDrift data class initialization."""
        drift = ConfigurationDrift(
            config_key="TEST_KEY",
            scope=ConfigurationScope.AUTHENTICATION,
            severity=DriftSeverity.CRITICAL,
            current_value="current",
            expected_value="expected",
            environment="test",
            detection_timestamp=time.time()
        )
        
        assert drift.config_key == "TEST_KEY"
        assert drift.scope == ConfigurationScope.AUTHENTICATION
        assert drift.severity == DriftSeverity.CRITICAL
        assert drift.current_value == "current"
        assert drift.expected_value == "expected"
        assert drift.environment == "test"
        assert isinstance(drift.detection_timestamp, float)
        
        # Test default values
        assert drift.business_impact_mrr == 0.0
        assert drift.cascade_risk == []
        assert drift.remediation_priority == 1
        assert drift.detection_source == "configuration_drift_monitor"
    
    def test_configuration_drift_to_dict(self):
        """Test ConfigurationDrift serialization to dictionary."""
        drift = ConfigurationDrift(
            config_key="SERIALIZATION_TEST",
            scope=ConfigurationScope.WEBSOCKET,
            severity=DriftSeverity.HIGH,
            current_value="current_value",
            expected_value="expected_value",
            environment="staging",
            detection_timestamp=1234567890.0,
            business_impact_mrr=50000.0,
            cascade_risk=["auth_failure", "websocket_disconnect"],
            remediation_priority=2
        )
        
        drift_dict = drift.to_dict()
        
        # Test required fields
        assert drift_dict["config_key"] == "SERIALIZATION_TEST"
        assert drift_dict["scope"] == "websocket"
        assert drift_dict["severity"] == "high"
        assert drift_dict["current_value"] == "current_value"
        assert drift_dict["expected_value"] == "expected_value"
        assert drift_dict["environment"] == "staging"
        assert drift_dict["detection_timestamp"] == 1234567890.0
        assert drift_dict["business_impact_mrr"] == 50000.0
        assert drift_dict["cascade_risk"] == ["auth_failure", "websocket_disconnect"]
        assert drift_dict["remediation_priority"] == 2
        
        # Test computed fields
        assert "detection_time" in drift_dict
        assert isinstance(drift_dict["detection_time"], str)
    
    def test_configuration_drift_value_truncation(self):
        """Test ConfigurationDrift truncates long values in serialization."""
        long_value = "x" * 100
        
        drift = ConfigurationDrift(
            config_key="TRUNCATION_TEST",
            scope=ConfigurationScope.DATABASE,
            severity=DriftSeverity.MODERATE,
            current_value=long_value,
            expected_value=long_value,
            environment="test",
            detection_timestamp=time.time()
        )
        
        drift_dict = drift.to_dict()
        
        # Values longer than 50 chars should be truncated with "..."
        assert len(drift_dict["current_value"]) == 53  # 50 + "..."
        assert drift_dict["current_value"].endswith("...")
        assert len(drift_dict["expected_value"]) == 53  # 50 + "..."
        assert drift_dict["expected_value"].endswith("...")


@pytest.mark.unit
class TestE2EOAuthSimulationKeyValidator:
    """Test E2EOAuthSimulationKeyValidator SSOT functionality."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear()
        self.validator = E2EOAuthSimulationKeyValidator()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.reset()
    
    def test_validator_initialization(self):
        """Test E2EOAuthSimulationKeyValidator initialization."""
        validator = E2EOAuthSimulationKeyValidator()
        assert hasattr(validator, 'env'), "Validator should have env attribute"
        assert validator.env is not None, "Environment should be initialized"
    
    @pytest.mark.asyncio
    async def test_validate_key_consistency_missing_key(self):
        """Test validation when E2E OAuth simulation key is missing."""
        # Don't set E2E_OAUTH_SIMULATION_KEY
        self.env.set("ENVIRONMENT", "staging", "test")
        
        result = await self.validator.validate_key_consistency()
        
        # Should detect drift for missing key
        assert result["drift_detected"] is True, "Should detect drift for missing key"
        assert result["key_available"] is False, "Key should not be available"
        assert result["business_impact"] == "high", "Missing key should have high business impact"
        assert len(result["drift_details"]) > 0, "Should have drift details"
        
        # Check drift details
        drift_detail = result["drift_details"][0]
        assert drift_detail["config_key"] == "E2E_OAUTH_SIMULATION_KEY"
        assert drift_detail["severity"] == "high"
        assert drift_detail["current_value"] == "<MISSING>"
        assert drift_detail["expected_value"] == "<REQUIRED>"
    
    @pytest.mark.asyncio
    async def test_validate_key_consistency_short_key(self):
        """Test validation when E2E OAuth simulation key is too short."""
        # Set short key
        self.env.set("E2E_OAUTH_SIMULATION_KEY", "short_key", "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        result = await self.validator.validate_key_consistency()
        
        # Should detect drift for short key
        assert result["drift_detected"] is True, "Should detect drift for short key"
        assert result["key_available"] is True, "Key should be available"
        assert result["key_length"] == 9, "Should report correct key length"
        assert result["business_impact"] == "moderate", "Short key should have moderate business impact"
        
        # Check drift details
        drift_detail = result["drift_details"][0]
        assert drift_detail["config_key"] == "E2E_OAUTH_SIMULATION_KEY"
        assert drift_detail["severity"] == "moderate"
        assert "<9_chars>" in drift_detail["current_value"]
        assert "<32+_chars>" in drift_detail["expected_value"]
    
    @pytest.mark.asyncio
    async def test_validate_key_consistency_valid_key(self):
        """Test validation when E2E OAuth simulation key is valid."""
        # Set valid long key
        valid_key = "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"
        self.env.set("E2E_OAUTH_SIMULATION_KEY", valid_key, "test")
        self.env.set("ENVIRONMENT", "development", "test")
        
        result = await self.validator.validate_key_consistency()
        
        # Should not detect drift for valid key in development
        assert result["drift_detected"] is False, "Should not detect drift for valid key"
        assert result["key_available"] is True, "Key should be available"
        assert result["key_length"] == len(valid_key), "Should report correct key length"
        assert result["business_impact"] == "none", "Valid key should have no business impact"
    
    @pytest.mark.asyncio
    async def test_validate_key_consistency_staging_with_functional_test(self):
        """Test validation in staging environment with functionality test."""
        # Set valid key for staging
        valid_key = "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"
        self.env.set("E2E_OAUTH_SIMULATION_KEY", valid_key, "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock the E2E OAuth simulation test
        with patch.object(self.validator, '_test_e2e_oauth_simulation') as mock_test:
            mock_test.return_value = {
                "success": True,
                "user_id": "test_user_123",
                "e2e_bypass_used": True,
                "test_timestamp": time.time()
            }
            
            result = await self.validator.validate_key_consistency()
            
            # Should not detect drift for functional key
            assert result["drift_detected"] is False, "Should not detect drift for functional key"
            assert "e2e_functionality_test" in result, "Should include functionality test results"
            assert result["e2e_functionality_test"]["success"] is True, "Functionality test should pass"
    
    @pytest.mark.asyncio
    async def test_validate_key_consistency_staging_with_non_functional_key(self):
        """Test validation in staging when key is present but not functional."""
        # Set key that will fail functionality test
        non_functional_key = "test-e2e-oauth-bypass-key-that-does-not-work"
        self.env.set("E2E_OAUTH_SIMULATION_KEY", non_functional_key, "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock the E2E OAuth simulation test to fail
        with patch.object(self.validator, '_test_e2e_oauth_simulation') as mock_test:
            mock_test.return_value = {
                "success": False,
                "error": "Authentication failed",
                "test_timestamp": time.time()
            }
            
            result = await self.validator.validate_key_consistency()
            
            # Should detect critical drift for non-functional key
            assert result["drift_detected"] is True, "Should detect drift for non-functional key"
            assert result["business_impact"] == "critical", "Non-functional key should have critical impact"
            
            # Should have critical drift details
            critical_drifts = [d for d in result["drift_details"] if d["severity"] == "critical"]
            assert len(critical_drifts) > 0, "Should have critical drift for non-functional key"
            
            critical_drift = critical_drifts[0]
            assert critical_drift["current_value"] == "<PRESENT_BUT_NOT_WORKING>"
            assert critical_drift["expected_value"] == "<FUNCTIONAL>"
    
    @pytest.mark.asyncio
    async def test_test_e2e_oauth_simulation_functionality(self):
        """Test E2E OAuth simulation functionality testing."""
        oauth_key = "test-e2e-oauth-key-for-functionality-testing"
        
        # Mock the auth service
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.get_unified_auth_service') as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.authenticate_websocket.return_value = (
                MagicMock(success=True, user_id="test_user", metadata={"e2e_bypass": True}),
                MagicMock()  # user_context
            )
            mock_auth.return_value = mock_auth_service
            
            result = await self.validator._test_e2e_oauth_simulation(oauth_key)
            
            assert result["success"] is True, "E2E OAuth simulation test should succeed"
            assert result["user_id"] == "test_user", "Should return user ID"
            assert result["e2e_bypass_used"] is True, "Should indicate E2E bypass was used"
            assert "test_timestamp" in result, "Should include test timestamp"
    
    @pytest.mark.asyncio
    async def test_test_e2e_oauth_simulation_failure(self):
        """Test E2E OAuth simulation functionality testing when auth fails."""
        oauth_key = "test-e2e-oauth-key-that-fails"
        
        # Mock the auth service to fail
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.get_unified_auth_service') as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.authenticate_websocket.return_value = (
                MagicMock(success=False, error="Authentication failed"),
                None
            )
            mock_auth.return_value = mock_auth_service
            
            result = await self.validator._test_e2e_oauth_simulation(oauth_key)
            
            assert result["success"] is False, "E2E OAuth simulation test should fail"
            assert result["error"] == "Authentication failed", "Should include error message"
            assert "test_timestamp" in result, "Should include test timestamp"


@pytest.mark.unit
class TestJWTSecretAlignmentValidator:
    """Test JWTSecretAlignmentValidator SSOT functionality."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear()
        self.validator = JWTSecretAlignmentValidator()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.reset()
    
    def test_validator_initialization(self):
        """Test JWTSecretAlignmentValidator initialization."""
        validator = JWTSecretAlignmentValidator()
        assert hasattr(validator, 'env'), "Validator should have env attribute"
        assert validator.env is not None, "Environment should be initialized"
    
    @pytest.mark.asyncio
    async def test_validate_jwt_secret_alignment_missing_secret(self):
        """Test validation when JWT secret is missing."""
        # Don't set JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "staging", "test")
        
        result = await self.validator.validate_jwt_secret_alignment()
        
        # Should detect critical drift for missing JWT secret
        assert result["drift_detected"] is True, "Should detect drift for missing JWT secret"
        assert result["secret_available"] is False, "Secret should not be available"
        assert result["business_impact"] == "critical", "Missing JWT secret should have critical impact"
        
        # Check drift details
        drift_detail = result["drift_details"][0]
        assert drift_detail["config_key"] == "JWT_SECRET_KEY"
        assert drift_detail["severity"] == "critical"
        assert drift_detail["current_value"] == "<MISSING>"
        assert drift_detail["business_impact_mrr"] == 120000.0  # Complete auth failure
    
    @pytest.mark.asyncio
    async def test_validate_jwt_secret_alignment_short_secret(self):
        """Test validation when JWT secret is too short."""
        # Set short JWT secret
        self.env.set("JWT_SECRET_KEY", "short", "test")
        self.env.set("ENVIRONMENT", "production", "test")
        
        result = await self.validator.validate_jwt_secret_alignment()
        
        # Should detect high drift for short JWT secret
        assert result["drift_detected"] is True, "Should detect drift for short JWT secret"
        assert result["secret_available"] is True, "Secret should be available"
        assert result["secret_length"] == 5, "Should report correct secret length"
        assert result["business_impact"] == "high", "Short JWT secret should have high impact"
        
        # Check drift details
        drift_detail = result["drift_details"][0]
        assert drift_detail["config_key"] == "JWT_SECRET_KEY"
        assert drift_detail["severity"] == "high"
        assert "<5_chars>" in drift_detail["current_value"]
        assert "<32+_chars>" in drift_detail["expected_value"]
    
    @pytest.mark.asyncio
    async def test_validate_jwt_secret_alignment_valid_secret(self):
        """Test validation when JWT secret is valid and functional."""
        # Set valid JWT secret
        valid_secret = "test-jwt-secret-key-32-characters-long-for-testing-only"
        self.env.set("JWT_SECRET_KEY", valid_secret, "test")
        self.env.set("ENVIRONMENT", "development", "test")
        
        # Mock JWT functionality test to succeed
        with patch.object(self.validator, '_test_jwt_functionality') as mock_test:
            mock_test.return_value = {
                "success": True,
                "auth_service_status": "healthy",
                "test_timestamp": time.time()
            }
            
            result = await self.validator.validate_jwt_secret_alignment()
            
            # Should not detect drift for valid, functional JWT secret
            assert result["drift_detected"] is False, "Should not detect drift for valid JWT secret"
            assert result["secret_available"] is True, "Secret should be available"
            assert result["secret_length"] == len(valid_secret), "Should report correct secret length"
            assert result["business_impact"] == "none", "Valid JWT secret should have no impact"
    
    @pytest.mark.asyncio
    async def test_validate_jwt_secret_alignment_non_functional_secret(self):
        """Test validation when JWT secret is present but not functional."""
        # Set JWT secret that will fail functionality test
        secret = "test-jwt-secret-key-32-characters-but-not-working-properly"
        self.env.set("JWT_SECRET_KEY", secret, "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock JWT functionality test to fail
        with patch.object(self.validator, '_test_jwt_functionality') as mock_test:
            mock_test.return_value = {
                "success": False,
                "error": "Auth service unhealthy: degraded",
                "auth_service_status": "degraded",
                "test_timestamp": time.time()
            }
            
            result = await self.validator.validate_jwt_secret_alignment()
            
            # Should detect critical drift for non-functional JWT
            assert result["drift_detected"] is True, "Should detect drift for non-functional JWT"
            assert result["business_impact"] == "critical", "Non-functional JWT should have critical impact"
            
            # Should have critical drift details
            critical_drifts = [d for d in result["drift_details"] if d["severity"] == "critical"]
            assert len(critical_drifts) > 0, "Should have critical drift for non-functional JWT"
    
    @pytest.mark.asyncio
    async def test_test_jwt_functionality_healthy_service(self):
        """Test JWT functionality testing with healthy auth service."""
        jwt_secret = "test-jwt-secret-for-functionality-testing"
        
        # Mock healthy auth service
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.get_unified_auth_service') as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.health_check.return_value = {"status": "healthy"}
            mock_auth.return_value = mock_auth_service
            
            result = await self.validator._test_jwt_functionality(jwt_secret)
            
            assert result["success"] is True, "JWT functionality test should succeed"
            assert result["auth_service_status"] == "healthy", "Should report healthy status"
            assert "test_timestamp" in result, "Should include test timestamp"
    
    @pytest.mark.asyncio
    async def test_test_jwt_functionality_unhealthy_service(self):
        """Test JWT functionality testing with unhealthy auth service."""
        jwt_secret = "test-jwt-secret-for-functionality-testing"
        
        # Mock unhealthy auth service
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.get_unified_auth_service') as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.health_check.return_value = {"status": "unhealthy"}
            mock_auth.return_value = mock_auth_service
            
            result = await self.validator._test_jwt_functionality(jwt_secret)
            
            assert result["success"] is False, "JWT functionality test should fail"
            assert result["auth_service_status"] == "unhealthy", "Should report unhealthy status"
            assert "error" in result, "Should include error message"


@pytest.mark.unit
class TestWebSocketConfigurationValidator:
    """Test WebSocketConfigurationValidator SSOT functionality."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear()
        self.validator = WebSocketConfigurationValidator()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.reset()
    
    def test_validator_initialization(self):
        """Test WebSocketConfigurationValidator initialization."""
        validator = WebSocketConfigurationValidator()
        assert hasattr(validator, 'env'), "Validator should have env attribute"
        assert validator.env is not None, "Environment should be initialized"
    
    @pytest.mark.asyncio
    async def test_validate_websocket_config_coherence_missing_url(self):
        """Test validation when WebSocket URL is missing."""
        # Don't set WebSocket URL
        self.env.set("ENVIRONMENT", "staging", "test")
        
        result = await self.validator.validate_websocket_config_coherence()
        
        # Should detect critical drift for missing WebSocket URL
        assert result["drift_detected"] is True, "Should detect drift for missing WebSocket URL"
        assert result["business_impact"] == "critical", "Missing WebSocket URL should have critical impact"
        
        # Check drift details
        drift_details = result["drift_details"]
        assert len(drift_details) > 0, "Should have drift details"
        
        websocket_drift = drift_details[0]
        assert websocket_drift["config_key"] == "NEXT_PUBLIC_WS_URL"
        assert websocket_drift["severity"] == "critical"
        assert websocket_drift["current_value"] == "<MISSING>"
        assert websocket_drift["business_impact_mrr"] == 120000.0  # Full chat failure
    
    @pytest.mark.asyncio
    async def test_validate_websocket_config_coherence_with_url(self):
        """Test validation when WebSocket URL is present."""
        # Set WebSocket URL
        self.env.set("NEXT_PUBLIC_WS_URL", "wss://api.staging.netrasystems.ai/ws", "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock WebSocket auth integration test to succeed
        with patch.object(self.validator, '_test_websocket_auth_integration') as mock_auth_test:
            mock_auth_test.return_value = {
                "success": True,
                "auth_service_healthy": True,
                "websocket_enabled": True,
                "test_timestamp": time.time()
            }
            
            # Mock CORS validation to succeed
            with patch.object(self.validator, '_validate_websocket_cors_config') as mock_cors:
                mock_cors.return_value = {
                    "drift_detected": False,
                    "validation_timestamp": time.time()
                }
                
                result = await self.validator.validate_websocket_config_coherence()
                
                # Should not detect drift when everything is configured properly
                assert result["drift_detected"] is False, "Should not detect drift with proper config"
                assert result["business_impact"] == "none", "Proper config should have no impact"
                assert len(result["validated_configs"]) > 0, "Should have validated configs"
    
    @pytest.mark.asyncio
    async def test_validate_websocket_config_coherence_auth_integration_failure(self):
        """Test validation when WebSocket auth integration fails."""
        # Set WebSocket URL but auth integration fails
        self.env.set("NEXT_PUBLIC_WS_URL", "wss://api.staging.netrasystems.ai/ws", "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock WebSocket auth integration test to fail
        with patch.object(self.validator, '_test_websocket_auth_integration') as mock_auth_test:
            mock_auth_test.return_value = {
                "success": False,
                "auth_service_healthy": False,
                "websocket_enabled": True,
                "error": "Auth service unhealthy: degraded",
                "test_timestamp": time.time()
            }
            
            # Mock CORS validation to succeed
            with patch.object(self.validator, '_validate_websocket_cors_config') as mock_cors:
                mock_cors.return_value = {
                    "drift_detected": False,
                    "validation_timestamp": time.time()
                }
                
                result = await self.validator.validate_websocket_config_coherence()
                
                # Should detect drift for auth integration failure
                assert result["drift_detected"] is True, "Should detect drift for auth integration failure"
                assert result["business_impact"] == "high", "Auth integration failure should have high impact"
                
                # Should have drift details for auth integration
                auth_drifts = [d for d in result["drift_details"] 
                             if d["config_key"] == "WEBSOCKET_AUTHENTICATION_INTEGRATION"]
                assert len(auth_drifts) > 0, "Should have auth integration drift"
    
    @pytest.mark.asyncio
    async def test_test_websocket_auth_integration_success(self):
        """Test WebSocket auth integration testing when healthy."""
        # Mock auth service to be healthy
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.get_unified_auth_service') as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.health_check.return_value = {"status": "healthy"}
            mock_auth.return_value = mock_auth_service
            
            # Enable WebSocket
            self.env.set("WEBSOCKET_ENABLED", "true", "test")
            
            result = await self.validator._test_websocket_auth_integration()
            
            assert result["success"] is True, "WebSocket auth integration should succeed"
            assert result["auth_service_healthy"] is True, "Auth service should be healthy"
            assert result["websocket_enabled"] is True, "WebSocket should be enabled"
    
    @pytest.mark.asyncio
    async def test_test_websocket_auth_integration_failure(self):
        """Test WebSocket auth integration testing when unhealthy."""
        # Mock auth service to be unhealthy
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.get_unified_auth_service') as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth_service.health_check.return_value = {"status": "degraded"}
            mock_auth.return_value = mock_auth_service
            
            # Disable WebSocket
            self.env.set("WEBSOCKET_ENABLED", "false", "test")
            
            result = await self.validator._test_websocket_auth_integration()
            
            assert result["success"] is False, "WebSocket auth integration should fail"
            assert result["auth_service_healthy"] is False, "Auth service should be unhealthy"
            assert result["websocket_enabled"] is False, "WebSocket should be disabled"
            assert "error" in result, "Should include error description"
    
    @pytest.mark.asyncio
    async def test_validate_websocket_cors_config_staging(self):
        """Test WebSocket CORS configuration validation for staging."""
        self.env.set("ENVIRONMENT", "staging", "test")
        
        result = await self.validator._validate_websocket_cors_config()
        
        # Should return CORS validation result
        assert "expected_origins" in result, "Should include expected origins"
        assert "environment" in result, "Should include environment"
        assert result["environment"] == "staging", "Should detect staging environment"
        
        # Check expected origins for staging
        expected_origins = result["expected_origins"]
        assert "https://app.staging.netrasystems.ai" in expected_origins, "Should include staging app URL"
        assert "https://api.staging.netrasystems.ai" in expected_origins, "Should include staging API URL"
        assert "wss://api.staging.netrasystems.ai" in expected_origins, "Should include staging WebSocket URL"
    
    @pytest.mark.asyncio
    async def test_validate_websocket_cors_config_production(self):
        """Test WebSocket CORS configuration validation for production."""
        self.env.set("ENVIRONMENT", "production", "test")
        
        result = await self.validator._validate_websocket_cors_config()
        
        # Check expected origins for production
        expected_origins = result["expected_origins"]
        assert "https://app.netrasystems.ai" in expected_origins, "Should include production app URL"
        assert "https://api.netrasystems.ai" in expected_origins, "Should include production API URL"
        assert "wss://api.netrasystems.ai" in expected_origins, "Should include production WebSocket URL"
    
    @pytest.mark.asyncio
    async def test_validate_websocket_cors_config_development(self):
        """Test WebSocket CORS configuration validation for development."""
        self.env.set("ENVIRONMENT", "development", "test")
        
        result = await self.validator._validate_websocket_cors_config()
        
        # Check expected origins for development
        expected_origins = result["expected_origins"]
        assert "http://localhost:3000" in expected_origins, "Should include localhost frontend"
        assert "ws://localhost:8000" in expected_origins, "Should include localhost WebSocket"
        assert "http://localhost:8000" in expected_origins, "Should include localhost API"


@pytest.mark.unit
class TestConfigurationDriftMonitor:
    """Test ConfigurationDriftMonitor main class functionality."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear()
        self.monitor = ConfigurationDriftMonitor()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.reset()
    
    def test_monitor_initialization(self):
        """Test ConfigurationDriftMonitor initialization."""
        monitor = ConfigurationDriftMonitor()
        
        # Test base class initialization
        assert monitor.name == "configuration_drift", "Should have correct component name"
        assert monitor.timeout == 30.0, "Should have correct timeout"
        
        # Test validator initialization
        assert hasattr(monitor, 'e2e_oauth_validator'), "Should have E2E OAuth validator"
        assert hasattr(monitor, 'jwt_secret_validator'), "Should have JWT secret validator"
        assert hasattr(monitor, 'websocket_config_validator'), "Should have WebSocket config validator"
        
        # Test state initialization
        assert hasattr(monitor, 'drift_history'), "Should have drift history"
        assert isinstance(monitor.drift_history, list), "Drift history should be list"
        assert len(monitor.drift_history) == 0, "Drift history should be empty initially"
        
        # Test business impact thresholds
        assert hasattr(monitor, 'mrr_impact_thresholds'), "Should have MRR impact thresholds"
        thresholds = monitor.mrr_impact_thresholds
        assert thresholds[DriftSeverity.CRITICAL] == 100000.0, "Critical threshold should be $100K"
        assert thresholds[DriftSeverity.HIGH] == 50000.0, "High threshold should be $50K"
    
    @pytest.mark.asyncio
    async def test_check_health_no_drift(self):
        """Test health check when no configuration drift is detected."""
        # Set up valid configuration
        self.env.set("E2E_OAUTH_SIMULATION_KEY", "test-e2e-oauth-bypass-key-for-testing-only-unified-2025", "test")
        self.env.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long-for-testing-only", "test")
        self.env.set("NEXT_PUBLIC_WS_URL", "wss://api.staging.netrasystems.ai/ws", "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock all validators to return no drift
        with patch.object(self.monitor.e2e_oauth_validator, 'validate_key_consistency') as mock_oauth:
            mock_oauth.return_value = {"drift_detected": False, "drift_details": []}
            
            with patch.object(self.monitor.jwt_secret_validator, 'validate_jwt_secret_alignment') as mock_jwt:
                mock_jwt.return_value = {"drift_detected": False, "drift_details": []}
                
                with patch.object(self.monitor.websocket_config_validator, 'validate_websocket_config_coherence') as mock_ws:
                    mock_ws.return_value = {"drift_detected": False, "drift_details": []}
                    
                    result = await self.monitor.check_health()
                    
                    # Should be healthy with no drift
                    assert isinstance(result, HealthCheckResult), "Should return HealthCheckResult"
                    assert result.success is True, "Should be successful with no drift"
                    assert result.health_score == 1.0, "Should have perfect health score"
                    assert result.status == "healthy", "Should have healthy status"
                    
                    # Check details
                    details = result.details
                    assert details["drift_detection_summary"]["total_drift_detected"] is False, "Should report no drift"
                    assert details["drift_detection_summary"]["critical_drift_count"] == 0, "Should have no critical drifts"
                    assert details["alert_status"]["level"] == "none", "Should have no alert"
    
    @pytest.mark.asyncio
    async def test_check_health_critical_drift(self):
        """Test health check when critical configuration drift is detected."""
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock validators to return critical drift
        critical_drift_detail = {
            "config_key": "JWT_SECRET_KEY",
            "scope": "authentication",
            "severity": "critical",
            "current_value": "<MISSING>",
            "expected_value": "<REQUIRED>",
            "detection_timestamp": time.time(),
            "business_impact_mrr": 120000.0,
            "cascade_risk": ["complete_authentication_failure"],
            "remediation_priority": 1
        }
        
        with patch.object(self.monitor.e2e_oauth_validator, 'validate_key_consistency') as mock_oauth:
            mock_oauth.return_value = {"drift_detected": False, "drift_details": []}
            
            with patch.object(self.monitor.jwt_secret_validator, 'validate_jwt_secret_alignment') as mock_jwt:
                mock_jwt.return_value = {
                    "drift_detected": True, 
                    "drift_details": [critical_drift_detail]
                }
                
                with patch.object(self.monitor.websocket_config_validator, 'validate_websocket_config_coherence') as mock_ws:
                    mock_ws.return_value = {"drift_detected": False, "drift_details": []}
                    
                    result = await self.monitor.check_health()
                    
                    # Should be unhealthy with critical drift
                    assert result.success is False, "Should be unsuccessful with critical drift"
                    assert result.health_score == 0.0, "Should have zero health score for critical drift"
                    assert result.status == "critical", "Should have critical status"
                    
                    # Check details
                    details = result.details
                    assert details["drift_detection_summary"]["total_drift_detected"] is True, "Should report drift"
                    assert details["drift_detection_summary"]["critical_drift_count"] == 1, "Should have one critical drift"
                    assert details["drift_detection_summary"]["total_business_impact_mrr"] == 120000.0, "Should report business impact"
                    assert details["alert_status"]["level"] == "critical", "Should have critical alert"
                    assert details["alert_status"]["escalate_to_executives"] is True, "Should escalate for $120K impact"
    
    @pytest.mark.asyncio
    async def test_check_health_high_impact_drift(self):
        """Test health check when high-impact drift is detected."""
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Mock validators to return high-impact drift
        high_impact_drift = {
            "config_key": "E2E_OAUTH_SIMULATION_KEY",
            "scope": "authentication",
            "severity": "high",
            "current_value": "<MISSING>",
            "expected_value": "<REQUIRED>",
            "detection_timestamp": time.time(),
            "business_impact_mrr": 75000.0,
            "cascade_risk": ["e2e_test_failures"],
            "remediation_priority": 2
        }
        
        with patch.object(self.monitor.e2e_oauth_validator, 'validate_key_consistency') as mock_oauth:
            mock_oauth.return_value = {
                "drift_detected": True,
                "drift_details": [high_impact_drift]
            }
            
            with patch.object(self.monitor.jwt_secret_validator, 'validate_jwt_secret_alignment') as mock_jwt:
                mock_jwt.return_value = {"drift_detected": False, "drift_details": []}
                
                with patch.object(self.monitor.websocket_config_validator, 'validate_websocket_config_coherence') as mock_ws:
                    mock_ws.return_value = {"drift_detected": False, "drift_details": []}
                    
                    result = await self.monitor.check_health()
                    
                    # Should be degraded with high-impact drift
                    assert result.success is True, "Should be successful (no critical drift)"
                    assert result.health_score == 0.3, "Should have low health score for high impact"
                    assert result.status == "degraded", "Should have degraded status"
                    
                    # Check alert status
                    details = result.details
                    assert details["alert_status"]["level"] == "high", "Should have high alert level"
                    assert details["alert_status"]["should_alert"] is True, "Should trigger alert"
                    assert details["alert_status"]["immediate_action_required"] is True, "Should require immediate action"
    
    def test_determine_alert_status_critical(self):
        """Test alert status determination for critical drifts."""
        critical_drifts = [{"severity": "critical", "business_impact_mrr": 120000.0}]
        
        alert_status = self.monitor._determine_alert_status(critical_drifts, 120000.0)
        
        assert alert_status["level"] == "critical", "Should be critical alert level"
        assert alert_status["should_alert"] is True, "Should trigger alert"
        assert alert_status["escalate_to_executives"] is True, "Should escalate for high impact"
        assert alert_status["immediate_action_required"] is True, "Should require immediate action"
    
    def test_determine_alert_status_high_impact(self):
        """Test alert status determination for high business impact."""
        alert_status = self.monitor._determine_alert_status([], 75000.0)
        
        assert alert_status["level"] == "high", "Should be high alert level"
        assert alert_status["should_alert"] is True, "Should trigger alert"
        assert alert_status["escalate_to_executives"] is False, "Should not escalate for medium impact"
        assert alert_status["immediate_action_required"] is True, "Should require immediate action"
    
    def test_determine_alert_status_moderate_impact(self):
        """Test alert status determination for moderate business impact."""
        alert_status = self.monitor._determine_alert_status([], 25000.0)
        
        assert alert_status["level"] == "moderate", "Should be moderate alert level"
        assert alert_status["should_alert"] is True, "Should trigger alert"
        assert alert_status["immediate_action_required"] is False, "Should not require immediate action"
    
    def test_determine_alert_status_no_impact(self):
        """Test alert status determination for no significant impact."""
        alert_status = self.monitor._determine_alert_status([], 1000.0)
        
        assert alert_status["level"] == "none", "Should be no alert level"
        assert alert_status["should_alert"] is False, "Should not trigger alert"
        assert alert_status["immediate_action_required"] is False, "Should not require action"
    
    def test_generate_remediation_recommendations(self):
        """Test remediation recommendation generation."""
        drift_details = [
            {
                "config_key": "E2E_OAUTH_SIMULATION_KEY",
                "severity": "critical"
            },
            {
                "config_key": "JWT_SECRET_KEY", 
                "severity": "critical"
            },
            {
                "config_key": "NEXT_PUBLIC_WS_URL",
                "severity": "high"
            }
        ]
        
        recommendations = self.monitor._generate_remediation_recommendations(drift_details)
        
        assert len(recommendations) == 3, "Should generate recommendation for each drift"
        
        # Check E2E OAuth recommendation
        oauth_rec = next(r for r in recommendations if r["config"] == "E2E_OAUTH_SIMULATION_KEY")
        assert oauth_rec["action"] == "update_e2e_oauth_simulation_key"
        assert oauth_rec["urgency"] == "high"
        assert oauth_rec["estimated_fix_time_minutes"] == 15
        
        # Check JWT recommendation
        jwt_rec = next(r for r in recommendations if r["config"] == "JWT_SECRET_KEY")
        assert jwt_rec["action"] == "update_jwt_secret"
        assert jwt_rec["urgency"] == "critical"
        assert jwt_rec["requires_service_restart"] is True
        
        # Check WebSocket recommendation
        ws_rec = next(r for r in recommendations if r["config"] == "NEXT_PUBLIC_WS_URL")
        assert ws_rec["action"] == "update_websocket_url"
        assert ws_rec["requires_frontend_redeploy"] is True
    
    def test_analyze_business_impact(self):
        """Test business impact analysis."""
        critical_drifts = [{"config_key": "JWT_SECRET_KEY", "severity": "critical"}]
        
        analysis = self.monitor._analyze_business_impact(120000.0, critical_drifts)
        
        assert analysis["total_mrr_at_risk"] == 120000.0, "Should report correct MRR at risk"
        assert analysis["impact_level"] == "critical", "Should classify as critical impact"
        assert "authentication_failure_risk" in analysis["impact_categories"], "Should include auth failure risk"
        assert analysis["user_impact_percentage"] == 100, "Should impact 100% of users for $120K"
        assert analysis["recovery_time_estimate_hours"] == 1, "Should estimate quick recovery for critical issues"
        assert analysis["preventable_with_monitoring"] is True, "Should be preventable with monitoring"
    
    @pytest.mark.asyncio
    async def test_get_drift_history(self):
        """Test drift history retrieval."""
        # Add some historical drifts
        old_drift = ConfigurationDrift(
            config_key="OLD_DRIFT",
            scope=ConfigurationScope.ENVIRONMENT,
            severity=DriftSeverity.LOW,
            current_value="old",
            expected_value="new",
            environment="test",
            detection_timestamp=time.time() - 48 * 3600  # 48 hours ago
        )
        
        recent_drift = ConfigurationDrift(
            config_key="RECENT_DRIFT", 
            scope=ConfigurationScope.AUTHENTICATION,
            severity=DriftSeverity.HIGH,
            current_value="recent",
            expected_value="new",
            environment="test",
            detection_timestamp=time.time() - 1 * 3600  # 1 hour ago
        )
        
        self.monitor.drift_history = [old_drift, recent_drift]
        
        # Get recent history (24 hours)
        recent_history = await self.monitor.get_drift_history(hours=24)
        
        # Should only include recent drift
        assert len(recent_history) == 1, "Should only include drifts within time window"
        assert recent_history[0]["config_key"] == "RECENT_DRIFT", "Should be the recent drift"
    
    @pytest.mark.asyncio
    async def test_clear_resolved_drifts(self):
        """Test clearing resolved drifts from history."""
        # Add test drifts
        drift1 = ConfigurationDrift(
            config_key="RESOLVED_DRIFT_1",
            scope=ConfigurationScope.AUTHENTICATION,
            severity=DriftSeverity.HIGH,
            current_value="old",
            expected_value="new",
            environment="test",
            detection_timestamp=time.time()
        )
        
        drift2 = ConfigurationDrift(
            config_key="UNRESOLVED_DRIFT",
            scope=ConfigurationScope.DATABASE,
            severity=DriftSeverity.MODERATE,
            current_value="old",
            expected_value="new", 
            environment="test",
            detection_timestamp=time.time()
        )
        
        self.monitor.drift_history = [drift1, drift2]
        
        # Clear resolved drift
        cleared_count = await self.monitor.clear_resolved_drifts(["RESOLVED_DRIFT_1"])
        
        assert cleared_count == 1, "Should clear one drift"
        assert len(self.monitor.drift_history) == 1, "Should have one drift remaining"
        assert self.monitor.drift_history[0].config_key == "UNRESOLVED_DRIFT", "Should keep unresolved drift"


@pytest.mark.unit
class TestConfigurationDriftMonitorUtilityFunctions:
    """Test utility functions for configuration drift monitoring."""
    
    def test_extend_staging_health_monitor_with_drift_detection(self):
        """Test extending staging health monitor with drift detection."""
        # Mock StagingHealthMonitor
        with patch('netra_backend.app.monitoring.configuration_drift_monitor.StagingHealthMonitor') as mock_staging:
            mock_staging_instance = MagicMock()
            mock_staging_instance.health_interface.register_checker = MagicMock()
            mock_staging.return_value = mock_staging_instance
            
            # Extend with drift detection
            extended_monitor = extend_staging_health_monitor_with_drift_detection()
            
            # Should return staging monitor with drift detection added
            assert extended_monitor is mock_staging_instance, "Should return extended staging monitor"
            mock_staging_instance.health_interface.register_checker.assert_called_once()
            
            # Check that a ConfigurationDriftMonitor was registered
            registered_checker = mock_staging_instance.health_interface.register_checker.call_args[0][0]
            assert isinstance(registered_checker, ConfigurationDriftMonitor), "Should register drift monitor"
    
    def test_get_configuration_drift_monitor_singleton(self):
        """Test global configuration drift monitor singleton."""
        # Clear singleton state
        import netra_backend.app.monitoring.configuration_drift_monitor as drift_module
        drift_module._configuration_drift_monitor = None
        
        # Get monitor instances
        monitor1 = get_configuration_drift_monitor()
        monitor2 = get_configuration_drift_monitor()
        
        # Should be the same instance
        assert monitor1 is monitor2, "Should return same singleton instance"
        assert isinstance(monitor1, ConfigurationDriftMonitor), "Should be ConfigurationDriftMonitor instance"
    
    def test_get_configuration_drift_monitor_initialization(self):
        """Test global configuration drift monitor initialization."""
        # Clear singleton state
        import netra_backend.app.monitoring.configuration_drift_monitor as drift_module
        drift_module._configuration_drift_monitor = None
        
        # Get monitor
        monitor = get_configuration_drift_monitor()
        
        # Should be properly initialized
        assert isinstance(monitor, ConfigurationDriftMonitor), "Should be ConfigurationDriftMonitor"
        assert hasattr(monitor, 'e2e_oauth_validator'), "Should have validators initialized"
        assert hasattr(monitor, 'jwt_secret_validator'), "Should have validators initialized"
        assert hasattr(monitor, 'websocket_config_validator'), "Should have validators initialized"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])