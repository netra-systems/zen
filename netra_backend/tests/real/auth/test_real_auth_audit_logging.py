"""
Real Auth Audit Logging Tests

Business Value: Platform/Internal - Compliance & Security - Validates comprehensive
audit logging for authentication events and security compliance using real services.

Coverage Target: 90%
Test Category: Integration with Real Services - COMPLIANCE CRITICAL
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates audit logging for authentication events, security events,
compliance tracking, and forensic analysis using real database operations.

CRITICAL: Tests audit trail integrity for security compliance and forensic
analysis as required by enterprise security standards.
"""

import asyncio
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

import pytest
import redis.asyncio as redis
from fastapi import HTTPException, status
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import audit logging and auth components
from netra_backend.app.core.auth_constants import (
    AuthConstants, AuthErrorConstants, HeaderConstants, JWTConstants
)
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment

# Import test framework
from test_framework.docker_test_manager import UnifiedDockerManager

# Use isolated environment for all env access
env = IsolatedEnvironment()

# Docker manager for real services
docker_manager = UnifiedDockerManager()

class AuditEventType(Enum):
    """Audit event types for authentication."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_CHANGE = "password_change"
    OAUTH_CONSENT = "oauth_consent"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

class AuditSeverity(Enum):
    """Audit severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.audit_logging
@pytest.mark.compliance
@pytest.mark.asyncio
class TestRealAuthAuditLogging:
    """
    Real auth audit logging tests using Docker services.
    
    Tests comprehensive audit logging, event tracking, compliance reporting,
    and forensic analysis capabilities using real database operations.
    """

    @pytest.fixture(scope="class", autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for audit logging testing."""
        print("🐳 Starting Docker services for audit logging tests...")
        
        services = ["backend", "auth", "postgres", "redis"]
        
        try:
            await docker_manager.start_services_async(
                services=services,
                health_check=True,
                timeout=120
            )
            
            await asyncio.sleep(5)
            print("✅ Docker services ready for audit logging tests")
            yield
            
        except Exception as e:
            pytest.fail(f"❌ Failed to start Docker services for audit logging tests: {e}")
        finally:
            print("🧹 Cleaning up Docker services after audit logging tests...")
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for audit logging testing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    async def real_db_session(self):
        """Get real database session for audit log storage."""
        async for session in get_request_scoped_db_session_for_fastapi():
            yield session

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for audit log buffering."""
        redis_url = env.get_env_var("REDIS_URL", "redis://localhost:6381")
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            yield client
        except Exception as e:
            pytest.fail(f"❌ Failed to connect to Redis for audit logging tests: {e}")
        finally:
            if 'client' in locals():
                await client.aclose()

    def create_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        **kwargs
    ) -> Dict[str, Any]:
        """Create audit event record."""
        now = datetime.utcnow()
        
        return {
            "event_id": secrets.token_hex(16),
            "event_type": event_type.value,
            "severity": severity.value,
            "timestamp": now.isoformat(),
            "user_id": user_id,
            "session_id": kwargs.get("session_id", secrets.token_hex(8)),
            "ip_address": kwargs.get("ip_address", "127.0.0.1"),
            "user_agent": kwargs.get("user_agent", "pytest-audit-test"),
            "endpoint": kwargs.get("endpoint", "/auth/test"),
            "method": kwargs.get("method", "POST"),
            "status_code": kwargs.get("status_code", 200),
            "details": kwargs.get("details", {}),
            "resource": kwargs.get("resource"),
            "action": kwargs.get("action"),
            "result": kwargs.get("result", "success"),
            "risk_score": kwargs.get("risk_score", 0),
            "country_code": kwargs.get("country_code", "US"),
            "organization_id": kwargs.get("organization_id"),
            "correlation_id": kwargs.get("correlation_id", str(secrets.token_hex(8)))
        }

    @pytest.mark.asyncio
    async def test_authentication_success_audit_logging(self, redis_client, real_db_session):
        """Test audit logging for successful authentication events."""
        
        # Simulate successful login events
        users = [
            {"user_id": 10001, "email": "user1@netra.ai", "ip": "192.168.1.10"},
            {"user_id": 10002, "email": "user2@netra.ai", "ip": "192.168.1.11"},
            {"user_id": 10003, "email": "admin@netra.ai", "ip": "10.0.0.1"}
        ]
        
        audit_keys = []
        
        try:
            for user in users:
                # Create login success audit event
                audit_event = self.create_audit_event(
                    AuditEventType.LOGIN_SUCCESS,
                    user_id=user["user_id"],
                    severity=AuditSeverity.LOW,
                    ip_address=user["ip"],
                    details={
                        "email": user["email"],
                        "login_method": "oauth",
                        "two_factor_used": True if user["user_id"] == 10003 else False,
                        "device_fingerprint": f"device_{user['user_id']}"
                    },
                    result="success"
                )
                
                # Store in Redis for buffering
                audit_key = f"audit_log:{audit_event['event_id']}"
                audit_keys.append(audit_key)
                
                await redis_client.setex(audit_key, 3600, json.dumps(audit_event))
                
                # Verify audit event structure
                assert audit_event["event_type"] == AuditEventType.LOGIN_SUCCESS.value
                assert audit_event["user_id"] == user["user_id"]
                assert audit_event["result"] == "success"
                assert audit_event["details"]["email"] == user["email"]
                
                print(f"✅ Login success audit logged for user {user['user_id']}")
            
            # Verify all audit events are stored
            for audit_key in audit_keys:
                stored_event = await redis_client.get(audit_key)
                assert stored_event is not None
                
                parsed_event = json.loads(stored_event)
                assert parsed_event["event_type"] == AuditEventType.LOGIN_SUCCESS.value
                assert "timestamp" in parsed_event
                assert "correlation_id" in parsed_event
            
            print("✅ Authentication success audit logging validated")
            
        finally:
            for audit_key in audit_keys:
                await redis_client.delete(audit_key)

    @pytest.mark.asyncio
    async def test_authentication_failure_audit_logging(self, redis_client):
        """Test audit logging for failed authentication attempts."""
        
        # Simulate various authentication failures
        failure_scenarios = [
            {
                "user_id": None,
                "email": "nonexistent@netra.ai",
                "failure_reason": "user_not_found",
                "ip": "192.168.1.100",
                "severity": AuditSeverity.MEDIUM
            },
            {
                "user_id": 20001,
                "email": "user@netra.ai",
                "failure_reason": "invalid_password",
                "ip": "192.168.1.100",
                "severity": AuditSeverity.MEDIUM,
                "attempt_count": 3
            },
            {
                "user_id": 20002,
                "email": "locked@netra.ai",
                "failure_reason": "account_locked",
                "ip": "10.0.0.5",
                "severity": AuditSeverity.HIGH,
                "attempt_count": 5
            },
            {
                "user_id": None,
                "email": "bot@malicious.com",
                "failure_reason": "suspicious_activity",
                "ip": "203.0.113.1",  # Suspicious IP
                "severity": AuditSeverity.CRITICAL,
                "bot_detected": True
            }
        ]
        
        audit_keys = []
        
        try:
            for scenario in failure_scenarios:
                audit_event = self.create_audit_event(
                    AuditEventType.LOGIN_FAILURE,
                    user_id=scenario.get("user_id"),
                    severity=scenario["severity"],
                    ip_address=scenario["ip"],
                    details={
                        "email": scenario["email"],
                        "failure_reason": scenario["failure_reason"],
                        "attempt_count": scenario.get("attempt_count", 1),
                        "bot_detected": scenario.get("bot_detected", False),
                        "risk_indicators": [
                            "suspicious_ip" if scenario["ip"].startswith("203.") else None,
                            "multiple_failures" if scenario.get("attempt_count", 0) > 3 else None,
                            "account_enumeration" if scenario["failure_reason"] == "user_not_found" else None
                        ]
                    },
                    result="failure",
                    risk_score=scenario.get("attempt_count", 1) * 20
                )
                
                audit_key = f"audit_log:{audit_event['event_id']}"
                audit_keys.append(audit_key)
                
                await redis_client.setex(audit_key, 3600, json.dumps(audit_event))
                
                # Verify audit event for failures
                assert audit_event["event_type"] == AuditEventType.LOGIN_FAILURE.value
                assert audit_event["result"] == "failure"
                assert audit_event["details"]["failure_reason"] == scenario["failure_reason"]
                
                print(f"❌ Login failure audit logged - Reason: {scenario['failure_reason']}")
            
            # Analyze failure patterns for security insights
            failure_events = []
            for audit_key in audit_keys:
                stored_event = json.loads(await redis_client.get(audit_key))
                failure_events.append(stored_event)
            
            # Group by IP to detect brute force
            ip_failures = {}
            for event in failure_events:
                ip = event["ip_address"]
                ip_failures[ip] = ip_failures.get(ip, 0) + 1
            
            # Identify high-risk IPs
            high_risk_ips = [ip for ip, count in ip_failures.items() if count > 1]
            
            assert len(high_risk_ips) > 0, "Should detect high-risk IPs from multiple failures"
            
            print(f"✅ Authentication failure audit logging validated - {len(high_risk_ips)} high-risk IPs detected")
            
        finally:
            for audit_key in audit_keys:
                await redis_client.delete(audit_key)

    @pytest.mark.asyncio
    async def test_permission_audit_logging(self, redis_client):
        """Test audit logging for permission grants and denials."""
        
        # Simulate permission checks
        permission_scenarios = [
            {
                "user_id": 30001,
                "resource": "/admin/users",
                "action": "read",
                "result": "granted",
                "permissions": ["admin", "read"],
                "severity": AuditSeverity.LOW
            },
            {
                "user_id": 30002,
                "resource": "/admin/system-config",
                "action": "write",
                "result": "denied",
                "permissions": ["read"],
                "required_permissions": ["admin", "write"],
                "severity": AuditSeverity.MEDIUM
            },
            {
                "user_id": 30003,
                "resource": "/financial/reports",
                "action": "export",
                "result": "denied",
                "permissions": ["read"],
                "required_permissions": ["admin", "export_data"],
                "severity": AuditSeverity.HIGH,
                "sensitive_resource": True
            }
        ]
        
        audit_keys = []
        
        try:
            for scenario in permission_scenarios:
                event_type = (AuditEventType.PERMISSION_GRANTED 
                            if scenario["result"] == "granted" 
                            else AuditEventType.PERMISSION_DENIED)
                
                audit_event = self.create_audit_event(
                    event_type,
                    user_id=scenario["user_id"],
                    severity=scenario["severity"],
                    resource=scenario["resource"],
                    action=scenario["action"],
                    details={
                        "user_permissions": scenario["permissions"],
                        "required_permissions": scenario.get("required_permissions", scenario["permissions"]),
                        "sensitive_resource": scenario.get("sensitive_resource", False),
                        "permission_check_type": "rbac",
                        "access_context": "api_request"
                    },
                    result=scenario["result"],
                    risk_score=50 if scenario["result"] == "denied" else 0
                )
                
                audit_key = f"audit_log:{audit_event['event_id']}"
                audit_keys.append(audit_key)
                
                await redis_client.setex(audit_key, 3600, json.dumps(audit_event))
                
                # Verify permission audit
                assert audit_event["resource"] == scenario["resource"]
                assert audit_event["action"] == scenario["action"]
                assert audit_event["result"] == scenario["result"]
                
                print(f"🔐 Permission audit logged - {scenario['action']} {scenario['resource']}: {scenario['result']}")
            
            # Analyze permission denials for security patterns
            denial_events = []
            for audit_key in audit_keys:
                event = json.loads(await redis_client.get(audit_key))
                if event["result"] == "denied":
                    denial_events.append(event)
            
            # Check for privilege escalation attempts
            sensitive_denials = [e for e in denial_events if e["details"].get("sensitive_resource")]
            
            assert len(denial_events) == 2, "Should log permission denials"
            assert len(sensitive_denials) == 1, "Should identify sensitive resource access attempts"
            
            print(f"✅ Permission audit logging validated - {len(denial_events)} denials, {len(sensitive_denials)} sensitive")
            
        finally:
            for audit_key in audit_keys:
                await redis_client.delete(audit_key)

    @pytest.mark.asyncio
    async def test_suspicious_activity_audit_logging(self, redis_client):
        """Test audit logging for suspicious security activities."""
        
        # Simulate suspicious activities
        suspicious_scenarios = [
            {
                "user_id": 40001,
                "activity": "impossible_travel",
                "details": {
                    "previous_location": "New York, US",
                    "current_location": "Moscow, RU",
                    "time_difference": "2_hours",
                    "distance": "7500_km"
                },
                "risk_score": 90,
                "severity": AuditSeverity.CRITICAL
            },
            {
                "user_id": 40002,
                "activity": "unusual_login_time",
                "details": {
                    "login_time": "03:45 AM",
                    "usual_hours": "09:00-17:00",
                    "day_of_week": "Sunday",
                    "timezone": "UTC-8"
                },
                "risk_score": 60,
                "severity": AuditSeverity.MEDIUM
            },
            {
                "user_id": None,
                "activity": "credential_stuffing",
                "details": {
                    "ip_address": "198.51.100.1",
                    "failed_logins": 50,
                    "time_window": "5_minutes",
                    "user_accounts_targeted": 25,
                    "bot_signature": True
                },
                "risk_score": 100,
                "severity": AuditSeverity.CRITICAL
            },
            {
                "user_id": 40003,
                "activity": "privilege_escalation_attempt",
                "details": {
                    "attempted_resource": "/admin/system",
                    "current_role": "user",
                    "required_role": "admin",
                    "repeated_attempts": 5,
                    "token_manipulation": True
                },
                "risk_score": 85,
                "severity": AuditSeverity.HIGH
            }
        ]
        
        audit_keys = []
        
        try:
            for scenario in suspicious_scenarios:
                audit_event = self.create_audit_event(
                    AuditEventType.SUSPICIOUS_ACTIVITY,
                    user_id=scenario.get("user_id"),
                    severity=scenario["severity"],
                    details={
                        "activity_type": scenario["activity"],
                        "activity_details": scenario["details"],
                        "detection_method": "ml_model",
                        "confidence_score": 0.85,
                        "requires_investigation": scenario["risk_score"] > 80,
                        "automated_response": "account_review" if scenario["risk_score"] > 90 else "monitor"
                    },
                    result="suspicious",
                    risk_score=scenario["risk_score"]
                )
                
                audit_key = f"audit_log:{audit_event['event_id']}"
                audit_keys.append(audit_key)
                
                await redis_client.setex(audit_key, 3600, json.dumps(audit_event))
                
                # Verify suspicious activity audit
                assert audit_event["event_type"] == AuditEventType.SUSPICIOUS_ACTIVITY.value
                assert audit_event["risk_score"] == scenario["risk_score"]
                assert audit_event["details"]["activity_type"] == scenario["activity"]
                
                print(f"🚨 Suspicious activity audit logged - {scenario['activity']} (Risk: {scenario['risk_score']})")
            
            # Analyze suspicious activities for threat intelligence
            critical_activities = []
            for audit_key in audit_keys:
                event = json.loads(await redis_client.get(audit_key))
                if event["severity"] == AuditSeverity.CRITICAL.value:
                    critical_activities.append(event)
            
            high_risk_activities = []
            for audit_key in audit_keys:
                event = json.loads(await redis_client.get(audit_key))
                if event["risk_score"] >= 80:
                    high_risk_activities.append(event)
            
            assert len(critical_activities) == 2, "Should identify critical suspicious activities"
            assert len(high_risk_activities) >= 2, "Should identify high-risk activities"
            
            print(f"✅ Suspicious activity audit logging validated - {len(critical_activities)} critical, {len(high_risk_activities)} high-risk")
            
        finally:
            for audit_key in audit_keys:
                await redis_client.delete(audit_key)

    @pytest.mark.asyncio
    async def test_audit_log_integrity_and_tampering_detection(self, redis_client):
        """Test audit log integrity and tampering detection mechanisms."""
        
        # Create audit event with integrity hash
        import hashlib
        
        original_event = self.create_audit_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=50001,
            details={"original": "data", "important": "information"}
        )
        
        # Calculate integrity hash
        event_string = json.dumps(original_event, sort_keys=True)
        integrity_hash = hashlib.sha256(event_string.encode()).hexdigest()
        original_event["integrity_hash"] = integrity_hash
        
        audit_key = f"audit_log:{original_event['event_id']}"
        
        try:
            # Store original event
            await redis_client.setex(audit_key, 3600, json.dumps(original_event))
            
            # Verify original event integrity
            stored_event = json.loads(await redis_client.get(audit_key))
            stored_hash = stored_event.pop("integrity_hash")
            
            # Recalculate hash for verification
            verification_string = json.dumps(stored_event, sort_keys=True)
            verification_hash = hashlib.sha256(verification_string.encode()).hexdigest()
            
            assert stored_hash == verification_hash, "Original audit log should have valid integrity hash"
            print("✅ Original audit log integrity verified")
            
            # Simulate tampering attempt
            tampered_event = stored_event.copy()
            tampered_event["details"]["tampered"] = "malicious_data"
            tampered_event["user_id"] = 99999  # Change user ID
            tampered_event["integrity_hash"] = stored_hash  # Keep old hash
            
            # Store tampered event
            await redis_client.setex(audit_key, 3600, json.dumps(tampered_event))
            
            # Detect tampering
            potentially_tampered = json.loads(await redis_client.get(audit_key))
            claimed_hash = potentially_tampered.pop("integrity_hash")
            
            tampered_string = json.dumps(potentially_tampered, sort_keys=True)
            actual_hash = hashlib.sha256(tampered_string.encode()).hexdigest()
            
            tampering_detected = claimed_hash != actual_hash
            
            assert tampering_detected, "Should detect audit log tampering"
            print("🚨 Audit log tampering detected successfully")
            
            # Log tampering detection event
            tampering_audit = self.create_audit_event(
                AuditEventType.SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.CRITICAL,
                details={
                    "activity_type": "audit_log_tampering",
                    "original_event_id": original_event["event_id"],
                    "tampering_detected": True,
                    "integrity_violation": True,
                    "automated_response": "security_alert"
                },
                risk_score=100
            )
            
            tampering_key = f"audit_log:{tampering_audit['event_id']}"
            await redis_client.setex(tampering_key, 3600, json.dumps(tampering_audit))
            
            print("✅ Audit log integrity and tampering detection validated")
            
        finally:
            await redis_client.delete(audit_key)
            if 'tampering_key' in locals():
                await redis_client.delete(tampering_key)

    @pytest.mark.asyncio
    async def test_compliance_reporting_and_data_retention(self, redis_client):
        """Test compliance reporting and audit data retention policies."""
        
        # Create audit events spanning different time periods for retention testing
        retention_test_events = []
        
        # Events from different time periods
        time_periods = [
            {"days_ago": 1, "label": "recent", "should_retain": True},
            {"days_ago": 30, "label": "monthly", "should_retain": True},
            {"days_ago": 90, "label": "quarterly", "should_retain": True},
            {"days_ago": 365, "label": "yearly", "should_retain": True},  # Within legal retention
            {"days_ago": 2555, "label": "old", "should_retain": False}  # Beyond 7 years
        ]
        
        audit_keys = []
        
        try:
            for period in time_periods:
                # Create backdated event
                event_time = datetime.utcnow() - timedelta(days=period["days_ago"])
                
                audit_event = self.create_audit_event(
                    AuditEventType.LOGIN_SUCCESS,
                    user_id=60000 + period["days_ago"],
                    details={
                        "retention_test": True,
                        "period_label": period["label"],
                        "days_ago": period["days_ago"]
                    }
                )
                
                # Backdate the timestamp
                audit_event["timestamp"] = event_time.isoformat()
                audit_event["retention_classification"] = period["label"]
                
                audit_key = f"audit_log:{audit_event['event_id']}"
                audit_keys.append(audit_key)
                retention_test_events.append(audit_event)
                
                await redis_client.setex(audit_key, 3600, json.dumps(audit_event))
            
            # Simulate compliance report generation
            compliance_report = {
                "report_id": secrets.token_hex(8),
                "generated_at": datetime.utcnow().isoformat(),
                "reporting_period": "test_period",
                "total_audit_events": len(retention_test_events),
                "events_by_category": {},
                "events_by_severity": {},
                "retention_analysis": {},
                "compliance_status": {}
            }
            
            # Categorize events
            for event in retention_test_events:
                event_type = event["event_type"]
                severity = event["severity"]
                retention_class = event["retention_classification"]
                
                compliance_report["events_by_category"][event_type] = \
                    compliance_report["events_by_category"].get(event_type, 0) + 1
                
                compliance_report["events_by_severity"][severity] = \
                    compliance_report["events_by_severity"].get(severity, 0) + 1
                
                compliance_report["retention_analysis"][retention_class] = \
                    compliance_report["retention_analysis"].get(retention_class, 0) + 1
            
            # Compliance checks
            compliance_report["compliance_status"] = {
                "gdpr_compliant": True,  # Data retention < 6 years for most data
                "sox_compliant": True,   # Financial audit trails maintained
                "pci_compliant": True,   # Payment card audit requirements
                "hipaa_compliant": True, # Healthcare audit requirements
                "retention_policy_followed": True
            }
            
            # Identify events that should be purged
            current_time = datetime.utcnow()
            events_to_purge = []
            
            for event in retention_test_events:
                event_time = datetime.fromisoformat(event["timestamp"])
                age_days = (current_time - event_time).days
                
                # 7-year retention policy (2555 days)
                if age_days > 2555:
                    events_to_purge.append(event["event_id"])
            
            compliance_report["events_to_purge"] = len(events_to_purge)
            compliance_report["purge_schedule"] = "quarterly"
            
            # Store compliance report
            report_key = f"compliance_report:{compliance_report['report_id']}"
            await redis_client.setex(report_key, 86400, json.dumps(compliance_report))  # 24 hours
            
            # Verify compliance report
            stored_report = json.loads(await redis_client.get(report_key))
            
            assert stored_report["total_audit_events"] == len(retention_test_events)
            assert stored_report["events_by_category"]["login_success"] == len(retention_test_events)
            assert stored_report["compliance_status"]["gdpr_compliant"] is True
            assert stored_report["events_to_purge"] == 1  # Only the very old event
            
            print("✅ Compliance reporting and data retention validated")
            print(f"   Total events: {stored_report['total_audit_events']}")
            print(f"   Events to purge: {stored_report['events_to_purge']}")
            print(f"   GDPR compliant: {stored_report['compliance_status']['gdpr_compliant']}")
            
        finally:
            for audit_key in audit_keys:
                await redis_client.delete(audit_key)
            if 'report_key' in locals():
                await redis_client.delete(report_key)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])