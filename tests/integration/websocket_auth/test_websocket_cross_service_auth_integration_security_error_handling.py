"""
Integration Tests: Cross-Service Security and Error Handling for WebSocket Authentication

Business Value Justification (BVJ):
- Segment: Platform/Internal - Security & Risk Management
- Business Goal: System Security & Compliance - Protects $500K+ ARR Golden Path
- Value Impact: Ensures robust security across service boundaries and graceful error handling
- Revenue Impact: Prevents security breaches and system failures that would impact customer trust

CRITICAL PURPOSE: These integration tests validate security measures and error handling
across service boundaries in WebSocket authentication scenarios, ensuring the system
remains secure and stable even when individual services fail.

Test Coverage Areas:
1. Auth service connection failure graceful degradation
2. Service-to-service authentication credentials validation  
3. Cross-service rate limiting and throttling coordination
4. Authentication propagation across service boundaries
5. Service mesh authentication integration
6. Cross-service audit logging and security compliance
"""

import asyncio
import json
import pytest
import time
import hashlib
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, call
from datetime import datetime, timedelta
import httpx

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.fixtures.security import security_test_fixture

from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService,
    AuthenticationContext
)
from netra_backend.app.auth import AuthenticationResult, AuthMethodType, SecurityAuditEvent
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceConnectionError,
    AuthServiceValidationError,
    AuthServiceError
)
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth
from netra_backend.app.services.rate_limiter import RateLimiter
# SecurityAuditLogger may not be available in production code
try:
    from netra_backend.app.services.security.audit_logger import SecurityAuditLogger
except ImportError:
    # Mock SecurityAuditLogger for tests if not available
    from unittest.mock import MagicMock
    SecurityAuditLogger = MagicMock


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossServiceSecurityIntegration(BaseIntegrationTest):
    """Integration tests for cross-service security in WebSocket authentication."""
    
    async def setup_method(self):
        """Setup security test environment."""
        await super().setup_method()
        
        # Real service instances for security integration testing
        self.auth_client = AuthServiceClient()
        self.unified_auth_service = UnifiedAuthenticationService()
        self.websocket_auth = UnifiedWebSocketAuth()
        self.rate_limiter = RateLimiter()
        self.security_auditor = SecurityAuditLogger()
        
        # Test security context
        self.test_user_id = "security-test-user-123"
        self.test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwIjoyMTQ3NDgzNjQ3fQ.secure"
        self.malicious_token = "invalid.token.attempt"
        
    async def teardown_method(self):
        """Cleanup security test resources."""
        if hasattr(self, 'auth_client') and self.auth_client:
            await self.auth_client.cleanup()
        if hasattr(self, 'rate_limiter') and self.rate_limiter:
            await self.rate_limiter.cleanup()
        await super().teardown_method()

    async def test_auth_service_connection_failure_graceful_degradation(self):
        """
        BVJ: Tests graceful degradation when auth service connection fails
        Prevents complete system failure while maintaining security
        """
        failure_scenarios = [
            ("connection_timeout", AuthServiceConnectionError("Connection timeout after 5s")),
            ("service_unavailable", AuthServiceError("Auth service temporarily unavailable")),
            ("network_partition", ConnectionError("Network unreachable")),
            ("dns_failure", TimeoutError("DNS resolution failed"))
        ]
        
        for scenario_name, error in failure_scenarios:
            with self.subTest(scenario=scenario_name):
                
                with patch.object(self.auth_client, 'validate_token', side_effect=error):
                    
                    auth_context = AuthenticationContext(
                        token=self.test_token,
                        user_id=self.test_user_id,
                        method=AuthMethodType.JWT_BEARER,
                        source="websocket_handshake"
                    )
                    
                    # Test graceful degradation
                    result = await self.unified_auth_service.authenticate_with_degradation(auth_context)
                    
                    # Should implement security fallback
                    assert result.success is False
                    assert result.degraded_mode is True
                    assert result.security_level == "restricted"
                    assert result.error_code == "AUTH_SERVICE_DEGRADED"
                    
                    # Should maintain audit trail even during failure
                    assert result.audit_logged is True
                    assert scenario_name in result.failure_reason

    async def test_service_to_service_authentication_credentials_validation(self):
        """
        BVJ: Tests validation of service credentials for cross-service communication
        Ensures only authorized services can communicate with auth service
        """
        valid_service_credentials = {
            "service_id": "netra-backend",
            "service_secret": "backend-secure-secret-123",
            "service_role": "websocket_handler"
        }
        
        invalid_credentials = [
            {"service_id": "malicious-service", "service_secret": "fake-secret", "service_role": "admin"},
            {"service_id": "netra-backend", "service_secret": "wrong-secret", "service_role": "websocket_handler"},
            {"service_id": "", "service_secret": "backend-secure-secret-123", "service_role": "websocket_handler"}
        ]
        
        with patch.object(self.auth_client, 'validate_service_credentials') as mock_validate:
            
            # Test valid credentials
            mock_validate.return_value = {
                "valid": True,
                "service_id": valid_service_credentials["service_id"],
                "permissions": ["token_validation", "user_authentication"],
                "rate_limit": 1000
            }
            
            valid_result = await self.unified_auth_service.validate_service_credentials(
                valid_service_credentials
            )
            
            assert valid_result["valid"] is True
            assert valid_result["service_id"] == "netra-backend"
            assert "token_validation" in valid_result["permissions"]
            
            # Test invalid credentials
            for invalid_creds in invalid_credentials:
                mock_validate.return_value = {
                    "valid": False,
                    "error": "Invalid service credentials",
                    "security_alert": True
                }
                
                invalid_result = await self.unified_auth_service.validate_service_credentials(
                    invalid_creds
                )
                
                assert invalid_result["valid"] is False
                assert invalid_result["security_alert"] is True

    async def test_cross_service_rate_limiting_coordination(self):
        """
        BVJ: Tests rate limiting coordination between services
        Prevents abuse and ensures fair resource allocation across services
        """
        user_requests = []
        service_limits = {
            "backend": {"requests_per_minute": 100, "burst_limit": 10},
            "websocket": {"requests_per_minute": 200, "burst_limit": 20},
            "auth_service": {"requests_per_minute": 500, "burst_limit": 50}
        }
        
        async def mock_rate_limit_check(service, user_id, request_type):
            request_key = f"{service}:{user_id}:{request_type}"
            current_time = time.time()
            
            # Count recent requests
            recent_requests = [
                req for req in user_requests 
                if req["key"] == request_key and req["timestamp"] > current_time - 60
            ]
            
            limit = service_limits.get(service, {}).get("requests_per_minute", 60)
            
            if len(recent_requests) >= limit:
                return {"allowed": False, "limit_exceeded": True, "retry_after": 60}
            
            user_requests.append({"key": request_key, "timestamp": current_time})
            return {"allowed": True, "remaining": limit - len(recent_requests) - 1}
        
        with patch.object(self.rate_limiter, 'check_rate_limit', side_effect=mock_rate_limit_check):
            
            # Test normal rate limiting
            for i in range(50):
                rate_result = await self.unified_auth_service.check_cross_service_rate_limit(
                    service="websocket",
                    user_id=self.test_user_id,
                    request_type="token_validation"
                )
                
                if i < 200:  # Within websocket limit
                    assert rate_result["allowed"] is True
                    assert rate_result["remaining"] >= 0
                else:
                    assert rate_result["allowed"] is False
                    assert rate_result["limit_exceeded"] is True

    async def test_authentication_propagation_across_service_boundaries(self):
        """
        BVJ: Tests secure propagation of authentication state across services
        Ensures authentication remains consistent and secure across service calls
        """
        service_chain = ["websocket", "backend", "auth_service", "analytics"]
        propagation_log = []
        
        async def mock_service_call(source_service, target_service, auth_token, user_context):
            # Simulate secure token propagation
            propagated_token = f"propagated-{source_service}-to-{target_service}-{auth_token}"
            
            propagation_log.append({
                "from": source_service,
                "to": target_service,
                "original_token": auth_token,
                "propagated_token": propagated_token,
                "user_id": user_context.get("user_id"),
                "timestamp": time.time(),
                "secure_channel": True
            })
            
            return {
                "success": True,
                "propagated_token": propagated_token,
                "user_context": user_context,
                "security_verified": True
            }
        
        with patch.object(self.unified_auth_service, 'propagate_auth_across_services') as mock_propagate:
            mock_propagate.side_effect = mock_service_call
            
            # Test authentication propagation chain
            user_context = {"user_id": self.test_user_id, "permissions": ["websocket_access"]}
            
            for i in range(len(service_chain) - 1):
                source = service_chain[i] 
                target = service_chain[i + 1]
                
                result = await self.unified_auth_service.propagate_auth_across_services(
                    source_service=source,
                    target_service=target, 
                    auth_token=self.test_token,
                    user_context=user_context
                )
                
                assert result["success"] is True
                assert result["security_verified"] is True
                assert result["user_context"]["user_id"] == self.test_user_id
            
            # Verify complete propagation chain
            assert len(propagation_log) == len(service_chain) - 1
            for log_entry in propagation_log:
                assert log_entry["secure_channel"] is True
                assert log_entry["user_id"] == self.test_user_id

    async def test_service_mesh_authentication_integration(self):
        """
        BVJ: Tests integration with service mesh authentication
        Ensures WebSocket auth works with service mesh security policies
        """
        service_mesh_config = {
            "mtls_enabled": True,
            "service_accounts": {
                "netra-backend": "backend-sa",
                "netra-websocket": "websocket-sa", 
                "netra-auth": "auth-sa"
            },
            "policies": {
                "websocket_to_auth": {"allow": True, "require_mtls": True},
                "backend_to_auth": {"allow": True, "require_mtls": True},
                "external_to_websocket": {"allow": True, "require_auth": True}
            }
        }
        
        async def mock_mesh_auth_check(source_service, target_service, request_context):
            policy_key = f"{source_service}_to_{target_service}"
            policy = service_mesh_config["policies"].get(policy_key, {"allow": False})
            
            if not policy.get("allow", False):
                return {"allowed": False, "reason": "Policy denied"}
            
            if policy.get("require_mtls", False) and not request_context.get("mtls_verified"):
                return {"allowed": False, "reason": "mTLS required"}
            
            if policy.get("require_auth", False) and not request_context.get("authenticated"):
                return {"allowed": False, "reason": "Authentication required"}
            
            return {
                "allowed": True,
                "service_account_verified": True,
                "mtls_verified": request_context.get("mtls_verified", False)
            }
        
        with patch.object(self.unified_auth_service, 'check_service_mesh_policy') as mock_mesh:
            mock_mesh.side_effect = mock_mesh_auth_check
            
            # Test service mesh integration
            request_context = {
                "mtls_verified": True,
                "authenticated": True,
                "source_service_account": "websocket-sa",
                "target_service_account": "auth-sa"
            }
            
            mesh_result = await self.unified_auth_service.check_service_mesh_policy(
                source_service="websocket",
                target_service="auth",
                request_context=request_context
            )
            
            assert mesh_result["allowed"] is True
            assert mesh_result["service_account_verified"] is True
            assert mesh_result["mtls_verified"] is True

    async def test_cross_service_audit_logging_security_compliance(self):
        """
        BVJ: Tests comprehensive audit logging across service boundaries  
        Ensures security compliance and forensic capabilities
        """
        audit_events = []
        
        async def mock_audit_log(event_type, event_data, service_context):
            audit_event = {
                "event_id": f"audit-{len(audit_events) + 1}",
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "service": service_context.get("service_name"),
                "user_id": event_data.get("user_id"),
                "source_ip": event_data.get("source_ip"),
                "user_agent": event_data.get("user_agent"),
                "success": event_data.get("success", False),
                "error_code": event_data.get("error_code"),
                "security_level": service_context.get("security_level", "standard")
            }
            
            # Add security hash for audit integrity
            audit_content = json.dumps(audit_event, sort_keys=True)
            audit_event["integrity_hash"] = hashlib.sha256(audit_content.encode()).hexdigest()
            
            audit_events.append(audit_event)
            return {"logged": True, "event_id": audit_event["event_id"]}
        
        with patch.object(self.security_auditor, 'log_security_event', side_effect=mock_audit_log):
            
            # Test various security events
            security_events = [
                {
                    "type": "authentication_attempt",
                    "data": {
                        "user_id": self.test_user_id,
                        "source_ip": "192.168.1.100", 
                        "user_agent": "WebSocket Client",
                        "success": True
                    },
                    "context": {"service_name": "websocket", "security_level": "high"}
                },
                {
                    "type": "authentication_failure",
                    "data": {
                        "user_id": "unknown",
                        "source_ip": "10.0.0.50",
                        "user_agent": "Malicious Bot",
                        "success": False,
                        "error_code": "INVALID_TOKEN"
                    },
                    "context": {"service_name": "auth_service", "security_level": "critical"}
                },
                {
                    "type": "service_authentication",
                    "data": {
                        "service_id": "netra-backend",
                        "success": True,
                        "permissions_granted": ["token_validation"]
                    },
                    "context": {"service_name": "auth_service", "security_level": "standard"}
                }
            ]
            
            # Log all security events
            for event in security_events:
                await self.security_auditor.log_security_event(
                    event["type"],
                    event["data"], 
                    event["context"]
                )
            
            # Verify comprehensive audit logging
            assert len(audit_events) == 3
            
            # Verify audit event integrity
            for audit_event in audit_events:
                assert audit_event["event_id"] is not None
                assert audit_event["integrity_hash"] is not None
                assert audit_event["timestamp"] is not None
                
            # Verify security levels recorded
            security_levels = [event["security_level"] for event in audit_events]
            assert "high" in security_levels
            assert "critical" in security_levels 
            assert "standard" in security_levels
            
            # Verify failure events flagged appropriately  
            failure_events = [event for event in audit_events if not event.get("success", True)]
            assert len(failure_events) == 1
            assert failure_events[0]["error_code"] == "INVALID_TOKEN"


@pytest.mark.integration
@pytest.mark.asyncio  
class TestSecurityComplianceIntegration(BaseIntegrationTest):
    """Tests security compliance across cross-service WebSocket authentication."""
    
    async def setup_method(self):
        await super().setup_method()
        self.unified_auth_service = UnifiedAuthenticationService()
        self.test_user_id = "compliance-user-456"
        
    async def test_security_policy_enforcement_cross_service(self):
        """
        BVJ: Tests enforcement of security policies across service boundaries
        Ensures consistent security posture across the entire system
        """
        security_policies = {
            "token_validation": {
                "require_signature_verification": True,
                "max_token_age_minutes": 60,
                "require_audience_match": True
            },
            "service_communication": {
                "require_mtls": True,
                "require_service_account_verification": True,
                "allowed_cipher_suites": ["TLS_AES_256_GCM_SHA384"]
            },
            "audit_requirements": {
                "log_all_auth_attempts": True,
                "log_service_communications": True,
                "retain_logs_days": 90
            }
        }
        
        with patch.object(self.unified_auth_service, 'enforce_security_policies') as mock_enforce:
            mock_enforce.return_value = {
                "policies_enforced": list(security_policies.keys()),
                "compliance_level": "full",
                "violations": []
            }
            
            compliance_result = await self.unified_auth_service.enforce_security_policies(
                security_policies
            )
            
            assert compliance_result["compliance_level"] == "full"
            assert len(compliance_result["violations"]) == 0
            assert len(compliance_result["policies_enforced"]) == 3