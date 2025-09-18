"""
Shared fixtures and utilities for security audit integration tests.

BVJ:
- Segment: Enterprise ($200K+ MRR)
- Business Goal: Compliance reporting protecting $200K+ MRR
- Value Impact: Critical SOC2/GDPR/HIPAA compliance for Enterprise customers
- Revenue Impact: Protects and enables $200K+ enterprise revenue stream
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.db.models_postgres import CorpusAuditLog

# Security and audit imports
from netra_backend.app.schemas.auth_types import AuditLog, AuthProvider, TokenType
from netra_backend.app.schemas.registry import (
    CorpusAuditAction,
    CorpusAuditMetadata,
    CorpusAuditRecord,
    CorpusAuditReport,
    CorpusAuditSearchFilter,
    CorpusAuditStatus,
)
from netra_backend.app.services.audit.corpus_audit import (
    CorpusAuditLogger,
    create_audit_logger,
)
from netra_backend.app.services.audit_service import (
    get_audit_summary,
    get_recent_logs,
    log_admin_action,
)

class MockSecurityInfrastructure:
    """Mock security infrastructure for testing."""
    
    def __init__(self):
        # Mock database session for audit operations
        self.mock_db = AsyncMock()
        
        # Mock audit repository with real behavior simulation
        self.audit_repository = Mock()
        self.audit_repository.create = AsyncMock()
        self.audit_repository.find_by_user = AsyncMock()
        self.audit_repository.search_records = AsyncMock()
        self.audit_repository.count_by_filters = AsyncMock()
        self.audit_repository.get_action_statistics = AsyncMock()
        
        # Create audit logger with mocked repository
        self.audit_logger = CorpusAuditLogger(self.audit_repository)
        
        # Security components
        self.security_monitor = Mock()
        self.compliance_reporter = Mock()
        self.tamper_detector = Mock()
        
    def to_dict(self):
        """Convert to dictionary format."""
        return {
            "audit_logger": self.audit_logger,
            "audit_repository": self.audit_repository,
            "mock_db": self.mock_db,
            "security_monitor": self.security_monitor,
            "compliance_reporter": self.compliance_reporter,
            "tamper_detector": self.tamper_detector
        }

class AuthenticationAuditHelper:
    """Helper for authentication audit testing."""
    
    @staticmethod
    async def create_authentication_test_scenarios() -> List[Dict[str, Any]]:
        """Create comprehensive authentication scenarios for audit testing."""
        return [
            {
                "event_type": "login_success",
                "user_id": "user123",
                "provider": AuthProvider.GOOGLE,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 Enterprise Browser",
                "session_id": str(uuid.uuid4())
            },
            {
                "event_type": "login_failure",
                "user_id": "user456", 
                "provider": AuthProvider.LOCAL,
                "ip_address": "10.0.0.50",
                "user_agent": "Malicious Scanner",
                "failure_reason": "Invalid credentials",
                "session_id": None
            },
            {
                "event_type": "token_refresh",
                "user_id": "user789",
                "provider": AuthProvider.API_KEY,
                "ip_address": "172.16.0.25",
                "user_agent": "API Client v2.0",
                "session_id": str(uuid.uuid4())
            },
            {
                "event_type": "logout",
                "user_id": "user123",
                "provider": AuthProvider.GOOGLE,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 Enterprise Browser",
                "session_id": str(uuid.uuid4())
            }
        ]

    @staticmethod
    async def capture_authentication_event(
        infrastructure: Dict[str, Any], event: Dict[str, Any]
    ) -> AuditLog:
        """Capture authentication event in audit system."""
        audit_log = AuditLog(
            event_id=str(uuid.uuid4()),
            event_type=event["event_type"],
            user_id=event.get("user_id"),
            ip_address=event["ip_address"],
            user_agent=event.get("user_agent"),
            success=event["event_type"] not in ["login_failure"],
            error_message=event.get("failure_reason"),
            metadata={
                "provider": event["provider"].value if event.get("provider") else None,
                "session_id": event.get("session_id"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Actually call the repository create method to increment call count
        await infrastructure["audit_repository"].create(infrastructure["mock_db"], audit_log)
        
        return audit_log

    @staticmethod
    async def verify_authentication_audit_completeness(
        audit_entry: AuditLog, original_event: Dict[str, Any]
    ):
        """Verify authentication audit captures all required fields."""
        assert audit_entry.event_id is not None
        assert audit_entry.event_type == original_event["event_type"]
        assert audit_entry.user_id == original_event.get("user_id")
        assert audit_entry.ip_address == original_event["ip_address"]
        assert audit_entry.user_agent == original_event.get("user_agent")
        
        # Verify security-critical metadata
        assert "provider" in audit_entry.metadata
        assert "timestamp" in audit_entry.metadata
        
        if original_event["event_type"] == "login_failure":
            assert not audit_entry.success
            assert audit_entry.error_message is not None

class DataAccessAuditHelper:
    """Helper for data access audit testing."""
    
    @staticmethod
    async def create_data_access_scenarios() -> List[Dict[str, Any]]:
        """Create comprehensive data access scenarios."""
        return [
            {
                "action": CorpusAuditAction.SEARCH,
                "resource_type": "corpus",
                "resource_id": "corpus123",
                "user_id": "user123",
                "access_type": "api_read",
                "data_classification": "confidential"
            },
            {
                "action": CorpusAuditAction.UPDATE, 
                "resource_type": "document",
                "resource_id": "doc456",
                "user_id": "user456",
                "access_type": "direct_modification",
                "data_classification": "restricted"
            },
            {
                "action": CorpusAuditAction.DELETE,
                "resource_type": "embedding",
                "resource_id": "embed789",
                "user_id": "admin001",
                "access_type": "admin_deletion",
                "data_classification": "public"
            }
        ]

    @staticmethod
    async def log_data_access_event(
        infrastructure: Dict[str, Any], scenario: Dict[str, Any]
    ) -> CorpusAuditRecord:
        """Log data access event with comprehensive metadata."""
        metadata = CorpusAuditMetadata(
            ip_address="192.168.1.100",
            user_agent="Enterprise Client v1.0",
            request_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            configuration={
                "data_classification": scenario["data_classification"],
                "access_type": scenario["access_type"]
            },
            performance_metrics={
                "operation_duration_ms": 150.5,
                "data_size_bytes": 2048
            },
            compliance_flags=["gdpr_logged", "soc2_tracked"]
        )
        
        # Mock the audit logging operation
        audit_record = CorpusAuditRecord(
            user_id=scenario["user_id"],
            action=scenario["action"],
            status=CorpusAuditStatus.SUCCESS,
            resource_type=scenario["resource_type"],
            resource_id=scenario["resource_id"],
            operation_duration_ms=150.5,
            metadata=metadata
        )
        
        # Simulate repository storage
        infrastructure["audit_repository"].create.return_value = audit_record
        
        return audit_record

class ComplianceReportingHelper:
    """Helper for compliance reporting testing."""
    
    @staticmethod
    async def create_compliance_reporting_scenario():
        """Create compliance reporting scenario."""
        return {
            "reporting_period": {
                "start_date": datetime.now(timezone.utc) - timedelta(days=30),
                "end_date": datetime.now(timezone.utc)
            },
            "compliance_standards": ["SOC2", "GDPR", "HIPAA"],
            "report_types": ["audit_summary", "access_report", "security_incidents"],
            "required_metrics": [
                "authentication_events", "data_access_events", 
                "configuration_changes", "security_violations"
            ]
        }

    @staticmethod
    async def generate_compliance_reports(infrastructure: Dict[str, Any], scenario: Dict[str, Any]):
        """Generate compliance reports for audit data."""
        # Mock compliance report generation
        compliance_reports = {}
        
        for standard in scenario["compliance_standards"]:
            report = {
                "standard": standard,
                "period": scenario["reporting_period"],
                "audit_events_count": 1250,
                "security_incidents": 0,
                "compliance_score": 98.5,
                "recommendations": [
                    "Implement MFA for all admin accounts",
                    "Increase password complexity requirements"
                ]
            }
            compliance_reports[standard] = report
        
        infrastructure["compliance_reporter"].generate_reports.return_value = compliance_reports
        return compliance_reports

@pytest.fixture
async def enterprise_security_infrastructure():
    """Setup comprehensive enterprise security audit infrastructure."""
    mock_infra = MockSecurityInfrastructure()
    yield mock_infra.to_dict()

@pytest.fixture
def auth_audit_helper():
    """Create authentication audit helper."""
    return AuthenticationAuditHelper()

@pytest.fixture
def data_access_helper():
    """Create data access audit helper."""
    return DataAccessAuditHelper()

@pytest.fixture
def compliance_helper():
    """Create compliance reporting helper."""
    return ComplianceReportingHelper()