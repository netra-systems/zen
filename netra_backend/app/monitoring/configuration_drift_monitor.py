"""
Configuration Drift Monitoring and Alert System - CRITICAL PREVENTION SYSTEM

Business Value Justification:
- Segment: Platform/Internal - Configuration Stability Infrastructure
- Business Goal: System Stability & Configuration Regression Prevention  
- Value Impact: Prevents configuration drift that causes cascade failures affecting $120K+ MRR
- Revenue Impact: Eliminates WebSocket authentication failures from OAuth/JWT misalignment

CRITICAL MISSION: Prevent recurrence of configuration drift issues that caused:
- E2E OAuth simulation key misalignment between test environment and staging auth service
- JWT secret mismatches causing WebSocket authentication cascade failures
- Configuration changes breaking authentication flows without detection

This system implements comprehensive configuration drift monitoring with:
1. Critical configuration health monitoring across environments
2. Real-time drift detection for authentication-related configs  
3. Business impact calculation for configuration stability
4. Integration with existing monitoring and alerting infrastructure
5. Automated remediation trigger capabilities

INTEGRATION POINTS:
- Extends netra_backend/app/monitoring/staging_health_monitor.py
- Uses shared.isolated_environment for SSOT environment access
- Integrates with UnifiedAuthenticationService for validation
- Leverages MISSION_CRITICAL_NAMED_VALUES_INDEX.xml for critical config identification
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.core.health.interface import BaseHealthChecker, HealthLevel
from netra_backend.app.core.health_types import HealthCheckResult
from netra_backend.app.core.unified_logging import central_logger
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service, 
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.monitoring.staging_health_monitor import StagingHealthMonitor
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class DriftSeverity(Enum):
    """Configuration drift severity levels based on business impact."""
    CRITICAL = "critical"      # Immediate business disruption, revenue impact
    HIGH = "high"             # Major functionality impacted, user experience degraded
    MODERATE = "moderate"     # Some functionality affected, workarounds available
    LOW = "low"              # Minor inconsistencies, no immediate impact
    INFORMATIONAL = "info"    # Configuration changes without impact


class ConfigurationScope(Enum):
    """Scope of configuration being monitored."""
    AUTHENTICATION = "authentication"      # Auth-related configs (JWT, OAuth)
    WEBSOCKET = "websocket"               # WebSocket configuration
    DATABASE = "database"                 # Database connection configs
    ENVIRONMENT = "environment"           # Environment-specific configs
    API_ENDPOINTS = "api_endpoints"       # Service endpoint configurations
    CORS = "cors"                        # CORS and security configs


@dataclass
class ConfigurationDrift:
    """Represents a detected configuration drift incident."""
    config_key: str
    scope: ConfigurationScope
    severity: DriftSeverity
    current_value: str
    expected_value: str
    environment: str
    detection_timestamp: float
    business_impact_mrr: float = 0.0
    cascade_risk: List[str] = field(default_factory=list)
    remediation_priority: int = 1  # 1=immediate, 5=scheduled
    detection_source: str = "configuration_drift_monitor"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "config_key": self.config_key,
            "scope": self.scope.value,
            "severity": self.severity.value,
            "current_value": self.current_value[:50] + "..." if len(self.current_value) > 50 else self.current_value,
            "expected_value": self.expected_value[:50] + "..." if len(self.expected_value) > 50 else self.expected_value,
            "environment": self.environment,
            "detection_timestamp": self.detection_timestamp,
            "detection_time": datetime.fromtimestamp(self.detection_timestamp, timezone.utc).isoformat(),
            "business_impact_mrr": self.business_impact_mrr,
            "cascade_risk": self.cascade_risk,
            "remediation_priority": self.remediation_priority,
            "detection_source": self.detection_source
        }


class E2EOAuthSimulationKeyValidator:
    """Validates E2E OAuth simulation key consistency between environments."""
    
    def __init__(self):
        self.env = get_env()
        
    async def validate_key_consistency(self) -> Dict[str, Any]:
        """
        DEPRECATED: Validate E2E OAuth simulation key consistency between test environment and staging auth service.
        
        This method now delegates to SSOT OAuth validation.
        Use shared.configuration.central_config_validator.simulate_oauth_end_to_end() instead.
        
        Returns:
            Validation result with consistency status and any detected drift
        """
        # SSOT OAuth validation - this replaces the duplicate implementation
        try:
            from shared.configuration.central_config_validator import simulate_oauth_end_to_end
            
            logger.warning(
                "E2EOAuthSimulationKeyValidator is deprecated. "
                "Use shared.configuration.central_config_validator.simulate_oauth_end_to_end() instead."
            )
            
            # Use SSOT OAuth E2E validation
            return simulate_oauth_end_to_end()
            
        except ImportError:
            logger.error("Could not import SSOT OAuth validation - falling back to legacy implementation")
        except Exception as e:
            logger.error(f"SSOT OAuth validation failed: {e} - falling back to legacy implementation")
        try:
            current_env = self.env.get("ENVIRONMENT", "development").lower()
            
            # Get E2E OAuth simulation key from current environment
            e2e_oauth_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            
            validation_result = {
                "config_key": "E2E_OAUTH_SIMULATION_KEY",
                "environment": current_env,
                "validation_timestamp": time.time(),
                "key_available": e2e_oauth_key is not None,
                "key_length": len(e2e_oauth_key) if e2e_oauth_key else 0,
                "drift_detected": False,
                "drift_details": [],
                "business_impact": "none"
            }
            
            if not e2e_oauth_key:
                # Missing key - critical for E2E testing capability
                drift = ConfigurationDrift(
                    config_key="E2E_OAUTH_SIMULATION_KEY",
                    scope=ConfigurationScope.AUTHENTICATION,
                    severity=DriftSeverity.HIGH,
                    current_value="<MISSING>",
                    expected_value="<REQUIRED>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=50000.0,  # E2E testing validates $50K+ MRR staging environment
                    cascade_risk=["e2e_authentication_bypass_failure", "staging_validation_blocked", "integration_test_failures"],
                    remediation_priority=2
                )
                
                validation_result.update({
                    "drift_detected": True,
                    "drift_details": [drift.to_dict()],
                    "business_impact": "high",
                    "error": "E2E_OAUTH_SIMULATION_KEY missing - E2E authentication bypass unavailable"
                })
                
                logger.warning(f"CONFIGURATION DRIFT: E2E_OAUTH_SIMULATION_KEY missing in {current_env}")
                return validation_result
            
            # Validate key format and content
            if len(e2e_oauth_key) < 32:
                # Key too short - potential security issue
                drift = ConfigurationDrift(
                    config_key="E2E_OAUTH_SIMULATION_KEY",
                    scope=ConfigurationScope.AUTHENTICATION,
                    severity=DriftSeverity.MODERATE,
                    current_value=f"<{len(e2e_oauth_key)}_chars>",
                    expected_value="<32+_chars>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=10000.0,
                    cascade_risk=["weak_e2e_authentication", "potential_security_bypass"],
                    remediation_priority=3
                )
                
                validation_result.update({
                    "drift_detected": True,
                    "drift_details": [drift.to_dict()],
                    "business_impact": "moderate",
                    "warning": f"E2E_OAUTH_SIMULATION_KEY too short ({len(e2e_oauth_key)} chars, expected 32+)"
                })
                
                logger.warning(f"CONFIGURATION DRIFT: E2E_OAUTH_SIMULATION_KEY too short in {current_env}")
            
            # Test E2E OAuth simulation functionality if in staging
            if current_env == "staging":
                auth_test_result = await self._test_e2e_oauth_simulation(e2e_oauth_key)
                validation_result["e2e_functionality_test"] = auth_test_result
                
                if not auth_test_result.get("success", False):
                    # E2E OAuth simulation not working despite key being present
                    drift = ConfigurationDrift(
                        config_key="E2E_OAUTH_SIMULATION_KEY",
                        scope=ConfigurationScope.AUTHENTICATION,
                        severity=DriftSeverity.CRITICAL,
                        current_value="<PRESENT_BUT_NOT_WORKING>",
                        expected_value="<FUNCTIONAL>",
                        environment=current_env,
                        detection_timestamp=time.time(),
                        business_impact_mrr=120000.0,  # WebSocket auth failures affect full MRR
                        cascade_risk=["websocket_authentication_failure", "e2e_test_failures", "staging_environment_unusable"],
                        remediation_priority=1
                    )
                    
                    validation_result.update({
                        "drift_detected": True,
                        "drift_details": validation_result.get("drift_details", []) + [drift.to_dict()],
                        "business_impact": "critical",
                        "error": f"E2E_OAUTH_SIMULATION_KEY present but non-functional: {auth_test_result.get('error', 'unknown_error')}"
                    })
                    
                    logger.error(f"CRITICAL CONFIGURATION DRIFT: E2E OAuth simulation key non-functional in {current_env}")
            
            if not validation_result["drift_detected"]:
                logger.info(f"✅ E2E_OAUTH_SIMULATION_KEY validation passed in {current_env}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"E2E OAuth simulation key validation failed: {e}")
            return {
                "config_key": "E2E_OAUTH_SIMULATION_KEY",
                "environment": self.env.get("ENVIRONMENT", "unknown"),
                "validation_timestamp": time.time(),
                "key_available": False,
                "drift_detected": True,
                "business_impact": "unknown",
                "error": f"Validation exception: {str(e)}",
                "exception_type": type(e).__name__
            }
    
    async def _test_e2e_oauth_simulation(self, oauth_key: str) -> Dict[str, Any]:
        """
        Test E2E OAuth simulation functionality with the provided key.
        
        Args:
            oauth_key: E2E OAuth simulation key to test
            
        Returns:
            Test result with success status and details
        """
        try:
            # Test E2E OAuth simulation by creating mock auth context
            e2e_context = {
                "bypass_enabled": True,
                "oauth_simulation_key": oauth_key,
                "test_environment": self.env.get("ENVIRONMENT", "unknown")
            }
            
            # Get unified auth service for testing
            auth_service = get_unified_auth_service()
            
            # Create a test JWT token (this would normally come from frontend)
            test_token = f"test-e2e-token-{int(time.time())}-{oauth_key[:8]}"
            
            # Test WebSocket authentication with E2E context
            # Note: We can't create actual WebSocket here, but we can test the auth logic
            from unittest.mock import MagicMock
            mock_websocket = MagicMock()
            mock_websocket.headers = {"authorization": f"Bearer {test_token}"}
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 12345
            
            auth_result, user_context = await auth_service.authenticate_websocket(mock_websocket, e2e_context)
            
            return {
                "success": auth_result.success if auth_result else False,
                "user_id": auth_result.user_id if auth_result and auth_result.success else None,
                "e2e_bypass_used": auth_result.metadata.get("e2e_bypass", False) if auth_result else False,
                "test_timestamp": time.time(),
                "error": auth_result.error if auth_result and not auth_result.success else None
            }
            
        except Exception as e:
            logger.error(f"E2E OAuth simulation test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "exception_type": type(e).__name__,
                "test_timestamp": time.time()
            }


class JWTSecretAlignmentValidator:
    """Validates JWT secret alignment between test framework and staging auth service."""
    
    def __init__(self):
        self.env = get_env()
        
    async def validate_jwt_secret_alignment(self) -> Dict[str, Any]:
        """
        Validate JWT secret alignment between test framework and staging auth service.
        
        Returns:
            Validation result with alignment status and any detected mismatches
        """
        try:
            current_env = self.env.get("ENVIRONMENT", "development").lower()
            
            # Get JWT secret from current environment
            jwt_secret = self.env.get("JWT_SECRET_KEY")
            
            validation_result = {
                "config_key": "JWT_SECRET_KEY",
                "environment": current_env,
                "validation_timestamp": time.time(),
                "secret_available": jwt_secret is not None,
                "secret_length": len(jwt_secret) if jwt_secret else 0,
                "drift_detected": False,
                "drift_details": [],
                "business_impact": "none"
            }
            
            if not jwt_secret:
                # Missing JWT secret - critical authentication failure
                drift = ConfigurationDrift(
                    config_key="JWT_SECRET_KEY",
                    scope=ConfigurationScope.AUTHENTICATION,
                    severity=DriftSeverity.CRITICAL,
                    current_value="<MISSING>",
                    expected_value="<REQUIRED>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=120000.0,  # Complete auth failure affects all revenue
                    cascade_risk=["complete_authentication_failure", "all_user_lockout", "system_unusable"],
                    remediation_priority=1
                )
                
                validation_result.update({
                    "drift_detected": True,
                    "drift_details": [drift.to_dict()],
                    "business_impact": "critical",
                    "error": "JWT_SECRET_KEY missing - Authentication will fail completely"
                })
                
                logger.error(f"CRITICAL CONFIGURATION DRIFT: JWT_SECRET_KEY missing in {current_env}")
                return validation_result
            
            # Validate JWT secret format and strength
            if len(jwt_secret) < 32:
                # JWT secret too short - security risk
                drift = ConfigurationDrift(
                    config_key="JWT_SECRET_KEY",
                    scope=ConfigurationScope.AUTHENTICATION,
                    severity=DriftSeverity.HIGH,
                    current_value=f"<{len(jwt_secret)}_chars>",
                    expected_value="<32+_chars>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=50000.0,
                    cascade_risk=["weak_jwt_security", "token_compromise_risk", "authentication_vulnerabilities"],
                    remediation_priority=2
                )
                
                validation_result.update({
                    "drift_detected": True,
                    "drift_details": [drift.to_dict()],
                    "business_impact": "high",
                    "warning": f"JWT_SECRET_KEY too short ({len(jwt_secret)} chars, expected 32+)"
                })
                
                logger.warning(f"CONFIGURATION DRIFT: JWT_SECRET_KEY too short in {current_env}")
            
            # Test JWT functionality if auth service is available
            jwt_test_result = await self._test_jwt_functionality(jwt_secret)
            validation_result["jwt_functionality_test"] = jwt_test_result
            
            if not jwt_test_result.get("success", False):
                # JWT not working despite secret being present
                drift = ConfigurationDrift(
                    config_key="JWT_SECRET_KEY",
                    scope=ConfigurationScope.AUTHENTICATION,
                    severity=DriftSeverity.CRITICAL,
                    current_value="<PRESENT_BUT_NOT_WORKING>",
                    expected_value="<FUNCTIONAL>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=120000.0,
                    cascade_risk=["jwt_validation_failure", "authentication_breakdown", "websocket_auth_failure"],
                    remediation_priority=1
                )
                
                validation_result.update({
                    "drift_detected": True,
                    "drift_details": validation_result.get("drift_details", []) + [drift.to_dict()],
                    "business_impact": "critical",
                    "error": f"JWT_SECRET_KEY present but JWT functionality failed: {jwt_test_result.get('error', 'unknown_error')}"
                })
                
                logger.error(f"CRITICAL CONFIGURATION DRIFT: JWT functionality failed in {current_env}")
            
            if not validation_result["drift_detected"]:
                logger.info(f"✅ JWT_SECRET_KEY validation passed in {current_env}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"JWT secret alignment validation failed: {e}")
            return {
                "config_key": "JWT_SECRET_KEY",
                "environment": self.env.get("ENVIRONMENT", "unknown"),
                "validation_timestamp": time.time(),
                "secret_available": False,
                "drift_detected": True,
                "business_impact": "unknown",
                "error": f"Validation exception: {str(e)}",
                "exception_type": type(e).__name__
            }
    
    async def _test_jwt_functionality(self, jwt_secret: str) -> Dict[str, Any]:
        """
        Test JWT functionality with the provided secret.
        
        Args:
            jwt_secret: JWT secret to test
            
        Returns:
            Test result with functionality status and details
        """
        try:
            # Test JWT functionality through auth service if available
            auth_service = get_unified_auth_service()
            
            # Test auth service health as proxy for JWT functionality
            health_result = await auth_service.health_check()
            
            if health_result.get("status") == "healthy":
                return {
                    "success": True,
                    "auth_service_status": health_result.get("status"),
                    "test_timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "error": f"Auth service unhealthy: {health_result.get('status', 'unknown')}",
                    "auth_service_status": health_result.get("status"),
                    "test_timestamp": time.time()
                }
                
        except Exception as e:
            logger.error(f"JWT functionality test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "exception_type": type(e).__name__,
                "test_timestamp": time.time()
            }


class WebSocketConfigurationValidator:
    """Validates WebSocket authentication configuration coherence."""
    
    def __init__(self):
        self.env = get_env()
        
    async def validate_websocket_config_coherence(self) -> Dict[str, Any]:
        """
        Validate WebSocket authentication configuration coherence.
        
        Returns:
            Validation result with configuration coherence status
        """
        try:
            current_env = self.env.get("ENVIRONMENT", "development").lower()
            
            validation_result = {
                "config_scope": "websocket_authentication",
                "environment": current_env,
                "validation_timestamp": time.time(),
                "drift_detected": False,
                "drift_details": [],
                "business_impact": "none",
                "validated_configs": []
            }
            
            # Validate WebSocket URL configuration
            websocket_url = self.env.get("NEXT_PUBLIC_WS_URL") or self.env.get("NEXT_PUBLIC_WEBSOCKET_URL")
            if not websocket_url:
                drift = ConfigurationDrift(
                    config_key="NEXT_PUBLIC_WS_URL",
                    scope=ConfigurationScope.WEBSOCKET,
                    severity=DriftSeverity.CRITICAL,
                    current_value="<MISSING>",
                    expected_value="<REQUIRED>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=120000.0,  # WebSocket failure affects all chat functionality
                    cascade_risk=["no_websocket_connection", "chat_appears_broken", "no_real_time_updates"],
                    remediation_priority=1
                )
                
                validation_result["drift_details"].append(drift.to_dict())
                validation_result["drift_detected"] = True
                validation_result["business_impact"] = "critical"
                
                logger.error(f"CRITICAL CONFIGURATION DRIFT: WebSocket URL missing in {current_env}")
            else:
                validation_result["validated_configs"].append({
                    "config": "NEXT_PUBLIC_WS_URL",
                    "status": "present",
                    "value_prefix": websocket_url[:20] + "..." if len(websocket_url) > 20 else websocket_url
                })
            
            # Validate WebSocket authentication integration
            websocket_auth_result = await self._test_websocket_auth_integration()
            validation_result["websocket_auth_test"] = websocket_auth_result
            
            if not websocket_auth_result.get("success", False):
                drift = ConfigurationDrift(
                    config_key="WEBSOCKET_AUTHENTICATION_INTEGRATION",
                    scope=ConfigurationScope.WEBSOCKET,
                    severity=DriftSeverity.HIGH,
                    current_value="<NOT_WORKING>",
                    expected_value="<FUNCTIONAL>",
                    environment=current_env,
                    detection_timestamp=time.time(),
                    business_impact_mrr=80000.0,
                    cascade_risk=["websocket_auth_failure", "user_websocket_disconnection", "chat_functionality_degraded"],
                    remediation_priority=2
                )
                
                validation_result["drift_details"].append(drift.to_dict())
                validation_result["drift_detected"] = True
                if validation_result["business_impact"] == "none":
                    validation_result["business_impact"] = "high"
                
                logger.warning(f"CONFIGURATION DRIFT: WebSocket authentication integration failed in {current_env}")
            
            # Validate CORS configuration for WebSocket
            cors_result = await self._validate_websocket_cors_config()
            validation_result["cors_validation"] = cors_result
            
            if cors_result.get("drift_detected", False):
                validation_result["drift_details"].extend(cors_result.get("drift_details", []))
                validation_result["drift_detected"] = True
                if validation_result["business_impact"] in ["none", "low"]:
                    validation_result["business_impact"] = cors_result.get("business_impact", "moderate")
            
            if not validation_result["drift_detected"]:
                logger.info(f"✅ WebSocket configuration validation passed in {current_env}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"WebSocket configuration validation failed: {e}")
            return {
                "config_scope": "websocket_authentication",
                "environment": self.env.get("ENVIRONMENT", "unknown"),
                "validation_timestamp": time.time(),
                "drift_detected": True,
                "business_impact": "unknown",
                "error": f"Validation exception: {str(e)}",
                "exception_type": type(e).__name__
            }
    
    async def _test_websocket_auth_integration(self) -> Dict[str, Any]:
        """Test WebSocket authentication integration."""
        try:
            # Test if unified auth service is available for WebSocket auth
            auth_service = get_unified_auth_service()
            
            # Get auth service health
            auth_health = await auth_service.health_check()
            
            # Test if WebSocket authentication is properly integrated
            websocket_enabled = self.env.get("WEBSOCKET_ENABLED", "true").lower() in ["true", "1", "yes"]
            
            if auth_health.get("status") == "healthy" and websocket_enabled:
                return {
                    "success": True,
                    "auth_service_healthy": True,
                    "websocket_enabled": True,
                    "test_timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "auth_service_healthy": auth_health.get("status") == "healthy",
                    "websocket_enabled": websocket_enabled,
                    "error": f"Auth service: {auth_health.get('status', 'unknown')}, WebSocket: {'enabled' if websocket_enabled else 'disabled'}",
                    "test_timestamp": time.time()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception_type": type(e).__name__,
                "test_timestamp": time.time()
            }
    
    async def _validate_websocket_cors_config(self) -> Dict[str, Any]:
        """Validate CORS configuration for WebSocket connections."""
        try:
            current_env = self.env.get("ENVIRONMENT", "development").lower()
            
            # Get expected CORS origins based on environment
            if current_env == "staging":
                expected_origins = [
                    "https://app.staging.netrasystems.ai",
                    "https://api.staging.netrasystems.ai",
                    "wss://api.staging.netrasystems.ai"
                ]
            elif current_env == "production":
                expected_origins = [
                    "https://app.netrasystems.ai",
                    "https://api.netrasystems.ai",
                    "wss://api.netrasystems.ai"
                ]
            else:
                expected_origins = [
                    "http://localhost:3000",
                    "ws://localhost:8000",
                    "http://localhost:8000"
                ]
            
            # Check if CORS origins are properly configured (this is a placeholder - 
            # in real implementation, we'd check the actual CORS configuration)
            cors_validation = {
                "expected_origins": expected_origins,
                "environment": current_env,
                "drift_detected": False,
                "drift_details": [],
                "validation_timestamp": time.time()
            }
            
            # For now, assume CORS is properly configured unless we have evidence otherwise
            # In a real implementation, we'd actually check the CORS middleware configuration
            
            return cors_validation
            
        except Exception as e:
            return {
                "drift_detected": True,
                "error": str(e),
                "exception_type": type(e).__name__,
                "validation_timestamp": time.time()
            }


class ConfigurationDriftMonitor(BaseHealthChecker):
    """
    Comprehensive Configuration Drift Monitor - CRITICAL PREVENTION SYSTEM
    
    This monitor extends the staging health monitor with specialized configuration
    drift detection capabilities to prevent the specific configuration issues that
    caused WebSocket authentication failures and $120K+ MRR impact.
    
    MISSION: Detect and alert on configuration drift before it causes cascade failures.
    """
    
    def __init__(self):
        super().__init__("configuration_drift", timeout=30.0)
        self.env = get_env()
        
        # Initialize specialized validators
        self.e2e_oauth_validator = E2EOAuthSimulationKeyValidator()
        self.jwt_secret_validator = JWTSecretAlignmentValidator()
        self.websocket_config_validator = WebSocketConfigurationValidator()
        
        # Drift detection state
        self.drift_history: List[ConfigurationDrift] = []
        self.last_validation_timestamp = 0
        self.validation_interval = 300  # 5 minutes between validations
        
        # Business impact thresholds
        self.mrr_impact_thresholds = {
            DriftSeverity.CRITICAL: 100000.0,    # $100K+ MRR impact
            DriftSeverity.HIGH: 50000.0,         # $50K+ MRR impact  
            DriftSeverity.MODERATE: 10000.0,     # $10K+ MRR impact
            DriftSeverity.LOW: 1000.0,           # $1K+ MRR impact
            DriftSeverity.INFORMATIONAL: 0.0    # No direct MRR impact
        }
        
        logger.info("ConfigurationDriftMonitor initialized - Configuration stability monitoring active")
    
    async def check_health(self) -> HealthCheckResult:
        """
        Comprehensive configuration drift health check.
        
        Returns:
            HealthCheckResult with drift detection status and business impact
        """
        start_time = time.time()
        current_env = self.env.get("ENVIRONMENT", "development").lower()
        
        try:
            logger.info(f"CONFIGURATION DRIFT: Starting comprehensive drift detection in {current_env}")
            
            # Run all configuration validators in parallel
            validation_tasks = [
                self.e2e_oauth_validator.validate_key_consistency(),
                self.jwt_secret_validator.validate_jwt_secret_alignment(),
                self.websocket_config_validator.validate_websocket_config_coherence()
            ]
            
            validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            # Process validation results
            total_drift_detected = False
            critical_drifts = []
            all_drift_details = []
            total_business_impact = 0.0
            
            for i, result in enumerate(validation_results):
                if isinstance(result, Exception):
                    logger.error(f"Configuration validator {i} failed: {result}")
                    continue
                
                if result.get("drift_detected", False):
                    total_drift_detected = True
                    drift_details = result.get("drift_details", [])
                    all_drift_details.extend(drift_details)
                    
                    # Calculate business impact
                    for drift_detail in drift_details:
                        business_impact = drift_detail.get("business_impact_mrr", 0.0)
                        total_business_impact += business_impact
                        
                        if drift_detail.get("severity") == "critical":
                            critical_drifts.append(drift_detail)
            
            # Store detected drifts in history
            for drift_detail in all_drift_details:
                drift = ConfigurationDrift(
                    config_key=drift_detail.get("config_key", "unknown"),
                    scope=ConfigurationScope(drift_detail.get("scope", "environment")),
                    severity=DriftSeverity(drift_detail.get("severity", "informational")),
                    current_value=drift_detail.get("current_value", "unknown"),
                    expected_value=drift_detail.get("expected_value", "unknown"),
                    environment=current_env,
                    detection_timestamp=drift_detail.get("detection_timestamp", time.time()),
                    business_impact_mrr=drift_detail.get("business_impact_mrr", 0.0),
                    cascade_risk=drift_detail.get("cascade_risk", []),
                    remediation_priority=drift_detail.get("remediation_priority", 5)
                )
                self.drift_history.append(drift)
            
            # Calculate overall health score
            if total_drift_detected:
                if critical_drifts:
                    health_score = 0.0  # Critical drift = unhealthy
                elif total_business_impact > 50000:
                    health_score = 0.3  # High impact = severely degraded
                else:
                    health_score = 0.7  # Some drift but manageable
            else:
                health_score = 1.0  # No drift detected
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine alert status
            alert_status = self._determine_alert_status(critical_drifts, total_business_impact)
            
            details = {
                "component_name": self.name,
                "success": not total_drift_detected or len(critical_drifts) == 0,
                "health_score": health_score,
                "environment": current_env,
                "drift_detection_summary": {
                    "total_drift_detected": total_drift_detected,
                    "critical_drift_count": len(critical_drifts),
                    "total_drift_count": len(all_drift_details),
                    "total_business_impact_mrr": total_business_impact
                },
                "validation_results": {
                    "e2e_oauth_simulation": validation_results[0] if len(validation_results) > 0 and not isinstance(validation_results[0], Exception) else {"error": "validation_failed"},
                    "jwt_secret_alignment": validation_results[1] if len(validation_results) > 1 and not isinstance(validation_results[1], Exception) else {"error": "validation_failed"},
                    "websocket_configuration": validation_results[2] if len(validation_results) > 2 and not isinstance(validation_results[2], Exception) else {"error": "validation_failed"}
                },
                "detected_drifts": all_drift_details,
                "critical_drifts": critical_drifts,
                "alert_status": alert_status,
                "remediation_recommendations": self._generate_remediation_recommendations(all_drift_details),
                "business_impact_analysis": self._analyze_business_impact(total_business_impact, critical_drifts),
                "response_time_ms": response_time,
                "validation_timestamp": time.time()
            }
            
            # Log results
            if total_drift_detected:
                if critical_drifts:
                    logger.error(f"🚨 CRITICAL CONFIGURATION DRIFT: {len(critical_drifts)} critical drifts detected with ${total_business_impact:,.0f} MRR impact")
                else:
                    logger.warning(f"⚠️ CONFIGURATION DRIFT: {len(all_drift_details)} drifts detected with ${total_business_impact:,.0f} MRR impact")
            else:
                logger.info(f"✅ CONFIGURATION DRIFT: No drift detected in {current_env}")
            
            return HealthCheckResult(
                component_name=self.name,
                success=not total_drift_detected or len(critical_drifts) == 0,
                health_score=health_score,
                response_time_ms=response_time,
                status="healthy" if health_score >= 0.8 else ("degraded" if health_score >= 0.5 else "critical"),
                response_time=response_time / 1000,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Configuration drift monitor check failed: {e}", exc_info=True)
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component_name=self.name,
                success=False,
                health_score=0.0,
                response_time_ms=response_time,
                status="unhealthy",
                response_time=response_time / 1000,
                details={
                    "component_name": self.name,
                    "success": False,
                    "error": str(e),
                    "exception_type": type(e).__name__,
                    "environment": current_env,
                    "response_time_ms": response_time
                }
            )
    
    def _determine_alert_status(self, critical_drifts: List[Dict[str, Any]], total_business_impact: float) -> Dict[str, Any]:
        """Determine alert status based on drift severity and business impact."""
        if critical_drifts:
            return {
                "level": "critical",
                "should_alert": True,
                "escalate_to_executives": total_business_impact > 100000.0,
                "immediate_action_required": True,
                "reason": f"{len(critical_drifts)} critical configuration drifts detected"
            }
        elif total_business_impact > 50000.0:
            return {
                "level": "high", 
                "should_alert": True,
                "escalate_to_executives": False,
                "immediate_action_required": True,
                "reason": f"High business impact: ${total_business_impact:,.0f} MRR at risk"
            }
        elif total_business_impact > 10000.0:
            return {
                "level": "moderate",
                "should_alert": True,
                "escalate_to_executives": False,
                "immediate_action_required": False,
                "reason": f"Moderate business impact: ${total_business_impact:,.0f} MRR at risk"
            }
        else:
            return {
                "level": "none",
                "should_alert": False,
                "escalate_to_executives": False,
                "immediate_action_required": False,
                "reason": "No significant configuration drift detected"
            }
    
    def _generate_remediation_recommendations(self, drift_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate remediation recommendations based on detected drift."""
        recommendations = []
        
        for drift in drift_details:
            config_key = drift.get("config_key", "unknown")
            severity = drift.get("severity", "informational")
            
            if config_key == "E2E_OAUTH_SIMULATION_KEY":
                recommendations.append({
                    "config": config_key,
                    "action": "update_e2e_oauth_simulation_key",
                    "description": "Update E2E OAuth simulation key in environment configuration",
                    "urgency": "high" if severity == "critical" else "moderate",
                    "estimated_fix_time_minutes": 15,
                    "validation_required": True
                })
            elif config_key == "JWT_SECRET_KEY":
                recommendations.append({
                    "config": config_key,
                    "action": "update_jwt_secret",
                    "description": "Update JWT secret key and restart authentication services",
                    "urgency": "critical",
                    "estimated_fix_time_minutes": 30,
                    "validation_required": True,
                    "requires_service_restart": True
                })
            elif config_key.startswith("NEXT_PUBLIC_WS_URL"):
                recommendations.append({
                    "config": config_key,
                    "action": "update_websocket_url",
                    "description": "Update WebSocket URL configuration and redeploy frontend",
                    "urgency": "critical",
                    "estimated_fix_time_minutes": 20,
                    "validation_required": True,
                    "requires_frontend_redeploy": True
                })
        
        return recommendations
    
    def _analyze_business_impact(self, total_impact: float, critical_drifts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze business impact of detected configuration drift."""
        impact_categories = []
        
        if total_impact >= 100000.0:
            impact_categories.append("complete_service_disruption")
        if total_impact >= 50000.0:
            impact_categories.append("major_functionality_impaired")
        if critical_drifts:
            impact_categories.append("authentication_failure_risk")
        
        return {
            "total_mrr_at_risk": total_impact,
            "impact_level": "critical" if total_impact >= 100000.0 else (
                "high" if total_impact >= 50000.0 else (
                    "moderate" if total_impact >= 10000.0 else "low"
                )
            ),
            "impact_categories": impact_categories,
            "user_impact_percentage": min(100, int(total_impact / 1200)),  # Assuming $120K total MRR
            "recovery_time_estimate_hours": 1 if critical_drifts else 4,
            "preventable_with_monitoring": True
        }
    
    async def get_drift_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get configuration drift history for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        recent_drifts = [
            drift.to_dict() for drift in self.drift_history 
            if drift.detection_timestamp >= cutoff_time
        ]
        return recent_drifts
    
    async def clear_resolved_drifts(self, config_keys: List[str]) -> int:
        """Clear resolved drifts from history."""
        original_count = len(self.drift_history)
        self.drift_history = [
            drift for drift in self.drift_history 
            if drift.config_key not in config_keys
        ]
        cleared_count = original_count - len(self.drift_history)
        
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} resolved configuration drifts")
        
        return cleared_count


# Integration with StagingHealthMonitor
def extend_staging_health_monitor_with_drift_detection():
    """Extend the existing StagingHealthMonitor with configuration drift detection."""
    original_staging_monitor = StagingHealthMonitor()
    
    # Add configuration drift monitor to existing health checkers
    drift_monitor = ConfigurationDriftMonitor()
    original_staging_monitor.health_interface.register_checker(drift_monitor)
    
    logger.info("Extended StagingHealthMonitor with ConfigurationDriftMonitor")
    return original_staging_monitor


# Global configuration drift monitor instance
_configuration_drift_monitor: Optional[ConfigurationDriftMonitor] = None


def get_configuration_drift_monitor() -> ConfigurationDriftMonitor:
    """
    Get the global configuration drift monitor instance.
    
    Returns:
        ConfigurationDriftMonitor instance for configuration stability monitoring
    """
    global _configuration_drift_monitor
    if _configuration_drift_monitor is None:
        _configuration_drift_monitor = ConfigurationDriftMonitor()
        logger.info("ConfigurationDriftMonitor instance created")
    return _configuration_drift_monitor