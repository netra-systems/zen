"""
Authentication Audit Integration Tests

BVJ:
    - Segment: Enterprise ($200K+ MRR)
- Business Goal: Compliance reporting protecting $200K+ MRR
- Value Impact: Critical SOC2 compliance - tracks all authentication attempts
- Revenue Impact: Protects and enables $200K+ enterprise revenue stream

REQUIREMENTS:
    - Authentication event capture for all login attempts
- Comprehensive audit logging with metadata
- Tamper-proof storage validation
- Authentication event completeness verification
""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
from datetime import datetime, timezone

import pytest

from netra_backend.tests.integration.security.shared_fixtures import (
    AuthenticationAuditHelper,
    auth_audit_helper,
    enterprise_security_infrastructure,
)

class TestAuthenticationAudit:
    """BVJ: Critical for SOC2 compliance - tracks all authentication attempts."""

    @pytest.mark.asyncio
    async def test_authentication_event_capture(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Critical for SOC2 compliance - tracks all authentication attempts."""
        infrastructure = enterprise_security_infrastructure
        
        auth_events = await auth_audit_helper.create_authentication_test_scenarios()
        captured_events = []
        
        for event in auth_events:
            audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, event)
            captured_events.append(audit_entry)
            await auth_audit_helper.verify_authentication_audit_completeness(audit_entry, event)
        
        await self._validate_authentication_audit_storage(infrastructure, captured_events)

    async def _validate_authentication_audit_storage(self, infrastructure, events):
        """Validate authentication events are properly stored."""
        assert len(events) == 4
        assert infrastructure["audit_repository"].create.call_count >= 4

    @pytest.mark.asyncio
    async def test_login_success_audit_capture(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates successful login events are properly audited."""
        infrastructure = enterprise_security_infrastructure
        
        success_event = {
            "event_type": "login_success",
            "user_id": "user123",
            "provider": None,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 Enterprise Browser"
        }
        
        audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, success_event)
        
        assert audit_entry.success is True
        assert audit_entry.error_message is None
        assert audit_entry.event_type == "login_success"

    @pytest.mark.asyncio
    async def test_login_failure_audit_capture(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates failed login attempts are properly audited."""
        infrastructure = enterprise_security_infrastructure
        
        failure_event = {
            "event_type": "login_failure",
            "user_id": "user456",
            "provider": None,
            "ip_address": "10.0.0.50",
            "user_agent": "Malicious Scanner",
            "failure_reason": "Invalid credentials"
        }
        
        audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, failure_event)
        
        assert audit_entry.success is False
        assert audit_entry.error_message == "Invalid credentials"
        assert audit_entry.event_type == "login_failure"

    @pytest.mark.asyncio
    async def test_token_refresh_audit_capture(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates token refresh events are properly audited."""
        infrastructure = enterprise_security_infrastructure
        
        token_event = {
            "event_type": "token_refresh",
            "user_id": "user789",
            "provider": None,
            "ip_address": "172.16.0.25",
            "user_agent": "API Client v2.0"
        }
        
        audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, token_event)
        
        assert audit_entry.success is True
        assert audit_entry.event_type == "token_refresh"
        assert audit_entry.ip_address == "172.16.0.25"

    @pytest.mark.asyncio
    async def test_logout_event_audit_capture(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates logout events are properly audited."""
        infrastructure = enterprise_security_infrastructure
        
        logout_event = {
            "event_type": "logout",
            "user_id": "user123",
            "provider": None,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 Enterprise Browser"
        }
        
        audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, logout_event)
        
        assert audit_entry.success is True
        assert audit_entry.event_type == "logout"
        assert audit_entry.user_id == "user123"

    @pytest.mark.asyncio
    async def test_audit_metadata_completeness(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates audit metadata includes all required security fields."""
        infrastructure = enterprise_security_infrastructure
        
        test_event = {
            "event_type": "login_success",
            "user_id": "user123",
            "provider": None,
            "ip_address": "192.168.1.100",
            "user_agent": "Test Browser"
        }
        
        audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, test_event)
        
        assert audit_entry.metadata is not None
        assert "timestamp" in audit_entry.metadata
        assert audit_entry.ip_address is not None
        assert audit_entry.user_agent is not None

    @pytest.mark.asyncio
    async def test_multiple_authentication_events_sequence(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates sequential authentication events are properly tracked."""
        infrastructure = enterprise_security_infrastructure
        
        event_sequence = [
            {"event_type": "login_success", "user_id": "user1", "ip_address": "192.168.1.1"},
            {"event_type": "token_refresh", "user_id": "user1", "ip_address": "192.168.1.1"},
            {"event_type": "logout", "user_id": "user1", "ip_address": "192.168.1.1"}
        ]
        
        captured_events = []
        for event in event_sequence:
            event["provider"] = None
            event["user_agent"] = "Test Client"
            audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, event)
            captured_events.append(audit_entry)
        
        assert len(captured_events) == 3
        assert all(event.user_id == "user1" for event in captured_events)

    @pytest.mark.asyncio
    async def test_suspicious_activity_detection(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates suspicious authentication activity is properly flagged."""
        infrastructure = enterprise_security_infrastructure
        
        suspicious_events = [
            {
                "event_type": "login_failure",
                "user_id": "admin",
                "provider": None,
                "ip_address": "10.0.0.1",
                "user_agent": "Automated Scanner",
                "failure_reason": "Brute force attempt"
            },
            {
                "event_type": "login_failure", 
                "user_id": "admin",
                "provider": None,
                "ip_address": "10.0.0.1",
                "user_agent": "Automated Scanner",
                "failure_reason": "Brute force attempt"
            }
        ]
        
        for event in suspicious_events:
            audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, event)
            assert audit_entry.success is False
            assert "brute force" in audit_entry.error_message.lower()

    @pytest.mark.asyncio
    async def test_audit_timestamp_accuracy(self, enterprise_security_infrastructure, auth_audit_helper):
        """BVJ: Validates audit timestamps are accurate for forensic analysis."""
        infrastructure = enterprise_security_infrastructure
        
        before_time = datetime.now(timezone.utc)
        
        test_event = {
            "event_type": "login_success",
            "user_id": "timestamp_test",
            "provider": None,
            "ip_address": "127.0.0.1",
            "user_agent": "Timestamp Test Client"
        }
        
        audit_entry = await auth_audit_helper.capture_authentication_event(infrastructure, test_event)
        
        after_time = datetime.now(timezone.utc)
        
        # Verify timestamp is within reasonable range
        assert audit_entry.metadata["timestamp"] is not None
        audit_timestamp = datetime.fromisoformat(audit_entry.metadata["timestamp"].replace('Z', '+00:00'))
        
        assert before_time <= audit_timestamp <= after_time

if __name__ == "__main__":
    pytest.main([__file__, "-v"])