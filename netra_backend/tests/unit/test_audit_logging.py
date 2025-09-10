"""
Test Audit Logging Business Logic

Business Value Justification (BVJ):
- Segment: Enterprise - Compliance & Security
- Business Goal: Ensure regulatory compliance and security audit trails
- Value Impact: Enterprise customers can meet compliance requirements and track system usage
- Strategic Impact: Essential for enterprise sales and regulatory environments

This test suite validates audit logging functionality including:
- User action logging and correlation
- Security event tracking
- Data access audit trails
- Compliance report generation
- Performance under high-volume logging

Performance Requirements:
- Audit log entries should be created within 50ms
- Log queries should complete within 500ms
- Storage should efficiently handle high-volume logging
- Memory usage should remain bounded during bulk operations
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional, List, Union

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types import UserID


class AuditEventType(Enum):
    """Audit event types for tracking."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    AGENT_EXECUTION = "agent_execution"
    SECURITY_VIOLATION = "security_violation"
    ADMIN_ACTION = "admin_action"
    SYSTEM_ERROR = "system_error"
    API_REQUEST = "api_request"
    FILE_UPLOAD = "file_upload"
    CONFIGURATION_CHANGE = "configuration_change"


class AuditEventSeverity(Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MockAuditEvent:
    """Mock audit event for testing."""
    
    def __init__(self, event_id: str, event_type: AuditEventType, user_id: Optional[str] = None,
                 severity: AuditEventSeverity = AuditEventSeverity.INFO, details: Optional[Dict] = None):
        self.event_id = event_id
        self.event_type = event_type
        self.user_id = user_id
        self.severity = severity
        self.timestamp = datetime.now(timezone.utc)
        self.details = details or {}
        self.ip_address = None
        self.user_agent = None
        self.session_id = None
        self.correlation_id = None
        self.metadata = {}


class MockAuditLogger:
    """Mock audit logger for unit testing."""
    
    def __init__(self):
        self._events: Dict[str, MockAuditEvent] = {}
        self._user_events: Dict[str, List[str]] = {}
        self._event_types: Dict[AuditEventType, List[str]] = {}
        self._severity_events: Dict[AuditEventSeverity, List[str]] = {}
        self._metrics = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_severity": {},
            "events_by_user": {},
            "total_logging_time_ms": 0,
            "queries_performed": 0
        }
    
    async def log_event(self, event_type: AuditEventType, user_id: Optional[str] = None,
                       details: Optional[Dict] = None, severity: AuditEventSeverity = AuditEventSeverity.INFO,
                       correlation_id: Optional[str] = None, ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None, session_id: Optional[str] = None) -> str:
        """Log an audit event."""
        start_time = time.time()
        
        event_id = f"audit_{uuid.uuid4().hex[:12]}"
        event = MockAuditEvent(event_id, event_type, user_id, severity, details)
        
        # Set additional context
        event.correlation_id = correlation_id
        event.ip_address = ip_address
        event.user_agent = user_agent
        event.session_id = session_id
        
        # Store event
        self._events[event_id] = event
        
        # Update indexes
        if user_id:
            if user_id not in self._user_events:
                self._user_events[user_id] = []
            self._user_events[user_id].append(event_id)
        
        if event_type not in self._event_types:
            self._event_types[event_type] = []
        self._event_types[event_type].append(event_id)
        
        if severity not in self._severity_events:
            self._severity_events[severity] = []
        self._severity_events[severity].append(event_id)
        
        # Update metrics
        logging_time = (time.time() - start_time) * 1000
        self._metrics["total_events"] += 1
        self._metrics["total_logging_time_ms"] += logging_time
        
        # Update type metrics
        type_key = event_type.value
        if type_key not in self._metrics["events_by_type"]:
            self._metrics["events_by_type"][type_key] = 0
        self._metrics["events_by_type"][type_key] += 1
        
        # Update severity metrics
        severity_key = severity.value
        if severity_key not in self._metrics["events_by_severity"]:
            self._metrics["events_by_severity"][severity_key] = 0
        self._metrics["events_by_severity"][severity_key] += 1
        
        # Update user metrics
        if user_id:
            if user_id not in self._metrics["events_by_user"]:
                self._metrics["events_by_user"][user_id] = 0
            self._metrics["events_by_user"][user_id] += 1
        
        return event_id
    
    async def get_events(self, user_id: Optional[str] = None, event_type: Optional[AuditEventType] = None,
                        severity: Optional[AuditEventSeverity] = None, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None, limit: int = 100) -> List[MockAuditEvent]:
        """Query audit events with filters."""
        start_query_time = time.time()
        self._metrics["queries_performed"] += 1
        
        # Start with all events
        candidate_event_ids = set(self._events.keys())
        
        # Apply filters
        if user_id and user_id in self._user_events:
            candidate_event_ids &= set(self._user_events[user_id])
        elif user_id:
            candidate_event_ids = set()  # User has no events
        
        if event_type and event_type in self._event_types:
            candidate_event_ids &= set(self._event_types[event_type])
        elif event_type:
            candidate_event_ids = set()  # Event type not found
        
        if severity and severity in self._severity_events:
            candidate_event_ids &= set(self._severity_events[severity])
        elif severity:
            candidate_event_ids = set()  # Severity level not found
        
        # Apply time filters
        filtered_events = []
        for event_id in candidate_event_ids:
            event = self._events[event_id]
            
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
                
            filtered_events.append(event)
        
        # Sort by timestamp (most recent first)
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply limit
        return filtered_events[:limit]
    
    async def get_event_by_id(self, event_id: str) -> Optional[MockAuditEvent]:
        """Get specific event by ID."""
        return self._events.get(event_id)
    
    async def delete_old_events(self, older_than: datetime) -> int:
        """Delete events older than specified date."""
        deleted_count = 0
        events_to_delete = []
        
        for event_id, event in self._events.items():
            if event.timestamp < older_than:
                events_to_delete.append(event_id)
        
        # Remove events and update indexes
        for event_id in events_to_delete:
            event = self._events[event_id]
            
            # Remove from main storage
            del self._events[event_id]
            
            # Remove from indexes
            if event.user_id and event.user_id in self._user_events:
                if event_id in self._user_events[event.user_id]:
                    self._user_events[event.user_id].remove(event_id)
                    
            if event.event_type in self._event_types:
                if event_id in self._event_types[event.event_type]:
                    self._event_types[event.event_type].remove(event_id)
                    
            if event.severity in self._severity_events:
                if event_id in self._severity_events[event.severity]:
                    self._severity_events[event.severity].remove(event_id)
            
            deleted_count += 1
        
        return deleted_count
    
    async def get_audit_metrics(self) -> Dict[str, Any]:
        """Get audit logging metrics."""
        return {
            **self._metrics,
            "active_events": len(self._events),
            "unique_users": len(self._user_events),
            "event_types_tracked": len(self._event_types),
            "severity_levels_used": len(self._severity_events)
        }


class TestAuditLogger(SSotBaseTestCase):
    """Test AuditLogger business logic and compliance features."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.audit_logger = MockAuditLogger()
        
        # Test users
        self.user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        self.user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        self.admin_user_id = f"admin_{uuid.uuid4().hex[:8]}"
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_basic_event_logging(self):
        """Test basic audit event logging functionality."""
        # When: Logging different types of events
        login_event_id = await self.audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            user_id=self.user1_id,
            details={"login_method": "oauth", "success": True},
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            session_id="session_123"
        )
        
        data_access_event_id = await self.audit_logger.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            user_id=self.user1_id,
            details={"resource": "/api/documents", "action": "read", "document_count": 5},
            correlation_id="req_456"
        )
        
        admin_action_event_id = await self.audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=self.admin_user_id,
            details={"action": "user_role_change", "target_user": self.user2_id},
            severity=AuditEventSeverity.WARNING
        )
        
        # Then: All events should be logged successfully
        assert login_event_id is not None
        assert data_access_event_id is not None
        assert admin_action_event_id is not None
        
        # And: Events should be retrievable
        login_event = await self.audit_logger.get_event_by_id(login_event_id)
        assert login_event is not None
        assert login_event.event_type == AuditEventType.USER_LOGIN
        assert login_event.user_id == self.user1_id
        assert login_event.details["login_method"] == "oauth"
        assert login_event.ip_address == "192.168.1.100"
        assert login_event.session_id == "session_123"
        
        data_event = await self.audit_logger.get_event_by_id(data_access_event_id)
        assert data_event.event_type == AuditEventType.DATA_ACCESS
        assert data_event.details["resource"] == "/api/documents"
        assert data_event.correlation_id == "req_456"
        
        admin_event = await self.audit_logger.get_event_by_id(admin_action_event_id)
        assert admin_event.event_type == AuditEventType.ADMIN_ACTION
        assert admin_event.severity == AuditEventSeverity.WARNING
        assert admin_event.details["target_user"] == self.user2_id
        
        # And: Metrics should be updated
        metrics = await self.audit_logger.get_audit_metrics()
        assert metrics["total_events"] == 3
        assert metrics["events_by_type"]["user_login"] == 1
        assert metrics["events_by_type"]["data_access"] == 1
        assert metrics["events_by_type"]["admin_action"] == 1
        
        self.record_metric("events_logged", 3)
        self.record_metric("basic_logging_validated", True)
    
    @pytest.mark.unit
    async def test_security_event_tracking(self):
        """Test security-specific event tracking and correlation."""
        # Given: Security-related events
        security_events = [
            {
                "type": AuditEventType.SECURITY_VIOLATION,
                "user_id": self.user1_id,
                "severity": AuditEventSeverity.ERROR,
                "details": {"violation_type": "failed_authentication", "attempt_count": 3},
                "ip_address": "192.168.1.100"
            },
            {
                "type": AuditEventType.SECURITY_VIOLATION,
                "user_id": self.user1_id,
                "severity": AuditEventSeverity.CRITICAL,
                "details": {"violation_type": "account_lockout", "reason": "too_many_failures"},
                "ip_address": "192.168.1.100"
            },
            {
                "type": AuditEventType.ADMIN_ACTION,
                "user_id": self.admin_user_id,
                "severity": AuditEventSeverity.WARNING,
                "details": {"action": "unlock_account", "target_user": self.user1_id},
                "correlation_id": "security_incident_001"
            }
        ]
        
        # When: Logging security events
        event_ids = []
        for event_data in security_events:
            event_id = await self.audit_logger.log_event(
                event_type=event_data["type"],
                user_id=event_data["user_id"],
                severity=event_data["severity"],
                details=event_data["details"],
                ip_address=event_data.get("ip_address"),
                correlation_id=event_data.get("correlation_id")
            )
            event_ids.append(event_id)
        
        # Then: Security events should be properly tracked
        security_violation_events = await self.audit_logger.get_events(
            event_type=AuditEventType.SECURITY_VIOLATION
        )
        assert len(security_violation_events) == 2
        
        # And: Critical events should be identifiable
        critical_events = await self.audit_logger.get_events(
            severity=AuditEventSeverity.CRITICAL
        )
        assert len(critical_events) == 1
        assert critical_events[0].details["violation_type"] == "account_lockout"
        
        # And: User-specific security events should be queryable
        user1_security_events = await self.audit_logger.get_events(
            user_id=self.user1_id,
            event_type=AuditEventType.SECURITY_VIOLATION
        )
        assert len(user1_security_events) == 2
        
        # And: IP address correlation should work
        ip_events = [e for e in security_violation_events if e.ip_address == "192.168.1.100"]
        assert len(ip_events) == 2
        
        self.record_metric("security_events_logged", len(security_events))
        self.record_metric("security_tracking_validated", True)
    
    @pytest.mark.unit
    async def test_data_access_audit_trail(self):
        """Test comprehensive data access audit trail."""
        # Given: Data access operations
        data_operations = [
            {"action": "create", "resource": "document_123", "details": {"title": "Sensitive Report"}},
            {"action": "read", "resource": "document_123", "details": {"access_method": "api"}},
            {"action": "update", "resource": "document_123", "details": {"fields_changed": ["title", "content"]}},
            {"action": "share", "resource": "document_123", "details": {"shared_with": self.user2_id}},
            {"action": "delete", "resource": "document_123", "details": {"deletion_reason": "retention_policy"}}
        ]
        
        correlation_id = f"data_lifecycle_{uuid.uuid4().hex[:8]}"
        
        # When: Logging data operations
        event_ids = []
        for i, operation in enumerate(data_operations):
            event_id = await self.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION if operation["action"] in ["create", "update", "delete"]
                          else AuditEventType.DATA_ACCESS,
                user_id=self.user1_id,
                details={
                    "action": operation["action"],
                    "resource": operation["resource"],
                    **operation["details"],
                    "sequence": i + 1
                },
                correlation_id=correlation_id,
                severity=AuditEventSeverity.INFO
            )
            event_ids.append(event_id)
        
        # Then: Complete audit trail should be available
        data_events = await self.audit_logger.get_events(
            user_id=self.user1_id,
            limit=10
        )
        
        # Filter events for this test (by correlation_id)
        lifecycle_events = [e for e in data_events if e.correlation_id == correlation_id]
        assert len(lifecycle_events) == len(data_operations)
        
        # And: Events should be in correct chronological order
        lifecycle_events.sort(key=lambda e: e.details.get("sequence", 0))
        
        actions_sequence = [e.details["action"] for e in lifecycle_events]
        expected_sequence = ["create", "read", "update", "share", "delete"]
        assert actions_sequence == expected_sequence
        
        # And: Resource access should be trackable
        document_events = [e for e in lifecycle_events if e.details.get("resource") == "document_123"]
        assert len(document_events) == len(data_operations)
        
        self.record_metric("data_operations_logged", len(data_operations))
        self.record_metric("audit_trail_validated", True)
    
    @pytest.mark.unit
    async def test_compliance_reporting_queries(self):
        """Test compliance reporting with various query filters."""
        # Given: Mixed audit events over time
        base_time = datetime.now(timezone.utc)
        
        # Create events with different timestamps
        events_data = [
            (base_time - timedelta(days=7), AuditEventType.USER_LOGIN, self.user1_id),
            (base_time - timedelta(days=6), AuditEventType.DATA_ACCESS, self.user1_id),
            (base_time - timedelta(days=5), AuditEventType.ADMIN_ACTION, self.admin_user_id),
            (base_time - timedelta(days=4), AuditEventType.DATA_MODIFICATION, self.user2_id),
            (base_time - timedelta(days=3), AuditEventType.SECURITY_VIOLATION, self.user1_id),
            (base_time - timedelta(days=2), AuditEventType.AGENT_EXECUTION, self.user1_id),
            (base_time - timedelta(days=1), AuditEventType.USER_LOGOUT, self.user2_id),
            (base_time, AuditEventType.API_REQUEST, self.user1_id)
        ]
        
        # Log events with specific timestamps
        event_ids = []
        for timestamp, event_type, user_id in events_data:
            event_id = await self.audit_logger.log_event(
                event_type=event_type,
                user_id=user_id,
                details={"timestamp_test": True, "original_time": timestamp.isoformat()}
            )
            # Manually set timestamp for testing
            if event_id in self.audit_logger._events:
                self.audit_logger._events[event_id].timestamp = timestamp
            event_ids.append(event_id)
        
        # When: Performing compliance queries
        # Query 1: All events for user1 in last 7 days
        user1_recent = await self.audit_logger.get_events(
            user_id=self.user1_id,
            start_time=base_time - timedelta(days=7),
            limit=20
        )
        
        # Query 2: Admin actions only
        admin_actions = await self.audit_logger.get_events(
            event_type=AuditEventType.ADMIN_ACTION
        )
        
        # Query 3: Security violations
        security_violations = await self.audit_logger.get_events(
            event_type=AuditEventType.SECURITY_VIOLATION
        )
        
        # Query 4: Events in specific time window
        week_ago = base_time - timedelta(days=7)
        three_days_ago = base_time - timedelta(days=3)
        time_window_events = await self.audit_logger.get_events(
            start_time=week_ago,
            end_time=three_days_ago
        )
        
        # Then: Query results should match expectations
        assert len(user1_recent) >= 5  # user1 has multiple events
        user1_event_types = {e.event_type for e in user1_recent}
        assert AuditEventType.USER_LOGIN in user1_event_types
        assert AuditEventType.DATA_ACCESS in user1_event_types
        
        assert len(admin_actions) >= 1
        assert all(e.event_type == AuditEventType.ADMIN_ACTION for e in admin_actions)
        assert all(e.user_id == self.admin_user_id for e in admin_actions)
        
        assert len(security_violations) >= 1
        assert all(e.event_type == AuditEventType.SECURITY_VIOLATION for e in security_violations)
        
        # Time window should include events from day 7 to day 3
        assert len(time_window_events) >= 4
        for event in time_window_events:
            assert week_ago <= event.timestamp <= three_days_ago
        
        self.record_metric("compliance_queries_performed", 4)
        self.record_metric("compliance_reporting_validated", True)
    
    @pytest.mark.unit
    async def test_audit_log_retention_and_cleanup(self):
        """Test audit log retention policies and cleanup."""
        # Given: Old audit events
        base_time = datetime.now(timezone.utc)
        old_events_data = []
        recent_events_data = []
        
        # Create old events (>90 days)
        for i in range(5):
            old_time = base_time - timedelta(days=100 + i)
            old_events_data.append((old_time, f"old_event_{i}"))
        
        # Create recent events (<90 days)
        for i in range(3):
            recent_time = base_time - timedelta(days=30 + i)
            recent_events_data.append((recent_time, f"recent_event_{i}"))
        
        # Log all events
        old_event_ids = []
        for timestamp, event_key in old_events_data:
            event_id = await self.audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                user_id=self.user1_id,
                details={"event_key": event_key, "test_data": True}
            )
            # Set old timestamp
            if event_id in self.audit_logger._events:
                self.audit_logger._events[event_id].timestamp = timestamp
            old_event_ids.append(event_id)
        
        recent_event_ids = []
        for timestamp, event_key in recent_events_data:
            event_id = await self.audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                user_id=self.user1_id,
                details={"event_key": event_key, "test_data": True}
            )
            # Set recent timestamp
            if event_id in self.audit_logger._events:
                self.audit_logger._events[event_id].timestamp = timestamp
            recent_event_ids.append(event_id)
        
        # When: Cleaning up old events (>90 days)
        cleanup_cutoff = base_time - timedelta(days=90)
        deleted_count = await self.audit_logger.delete_old_events(cleanup_cutoff)
        
        # Then: Old events should be deleted
        assert deleted_count == len(old_events_data)
        
        # And: Old events should no longer exist
        for event_id in old_event_ids:
            deleted_event = await self.audit_logger.get_event_by_id(event_id)
            assert deleted_event is None
        
        # And: Recent events should still exist
        for event_id in recent_event_ids:
            existing_event = await self.audit_logger.get_event_by_id(event_id)
            assert existing_event is not None
        
        # And: Metrics should reflect cleanup
        final_metrics = await self.audit_logger.get_audit_metrics()
        # Note: May have other events from previous tests
        remaining_test_events = len([e for e in self.audit_logger._events.values() 
                                    if e.details.get("test_data")])
        assert remaining_test_events == len(recent_events_data)
        
        self.record_metric("old_events_deleted", deleted_count)
        self.record_metric("retention_cleanup_validated", True)


class TestAuditLoggerPerformance(SSotBaseTestCase):
    """Test audit logger performance characteristics."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.audit_logger = MockAuditLogger()
        self.test_user_id = f"perf_user_{uuid.uuid4().hex[:8]}"
    
    @pytest.mark.unit
    async def test_high_volume_logging_performance(self):
        """Test performance under high-volume logging."""
        # Given: High volume of audit events
        event_count = 100
        max_logging_time_ms = 50  # 50ms max per event
        
        # When: Logging many events rapidly
        logging_times = []
        event_ids = []
        
        for i in range(event_count):
            start_time = time.time()
            
            event_id = await self.audit_logger.log_event(
                event_type=AuditEventType.API_REQUEST,
                user_id=self.test_user_id,
                details={
                    "endpoint": f"/api/test/{i}",
                    "method": "GET",
                    "status_code": 200,
                    "response_time_ms": 50 + (i % 100)
                },
                ip_address=f"192.168.1.{100 + (i % 50)}",
                correlation_id=f"req_{i}"
            )
            
            logging_time = (time.time() - start_time) * 1000  # Convert to ms
            logging_times.append(logging_time)
            event_ids.append(event_id)
        
        # Then: Performance should meet requirements
        avg_logging_time = sum(logging_times) / len(logging_times)
        max_logging_time = max(logging_times)
        
        assert avg_logging_time < max_logging_time_ms
        assert max_logging_time < max_logging_time_ms * 2  # Allow variance
        
        # And: All events should be logged
        assert len(event_ids) == event_count
        
        metrics = await self.audit_logger.get_audit_metrics()
        assert metrics["total_events"] >= event_count
        
        self.record_metric("high_volume_events_logged", event_count)
        self.record_metric("avg_logging_time_ms", avg_logging_time)
        self.record_metric("max_logging_time_ms", max_logging_time)
    
    @pytest.mark.unit
    async def test_query_performance_with_large_dataset(self):
        """Test query performance with large audit dataset."""
        # Given: Large dataset of audit events
        event_count = 200
        user_count = 10
        max_query_time_ms = 500  # 500ms max per query
        
        # Create events for multiple users
        users = [f"perf_user_{i}_{uuid.uuid4().hex[:6]}" for i in range(user_count)]
        event_types = list(AuditEventType)
        
        for i in range(event_count):
            user_id = users[i % user_count]
            event_type = event_types[i % len(event_types)]
            
            await self.audit_logger.log_event(
                event_type=event_type,
                user_id=user_id,
                details={"test_index": i, "performance_test": True}
            )
        
        # When: Performing various queries
        query_tests = [
            ("user_specific", lambda: self.audit_logger.get_events(user_id=users[0])),
            ("event_type", lambda: self.audit_logger.get_events(event_type=AuditEventType.DATA_ACCESS)),
            ("severity", lambda: self.audit_logger.get_events(severity=AuditEventSeverity.INFO)),
            ("time_range", lambda: self.audit_logger.get_events(
                start_time=datetime.now(timezone.utc) - timedelta(hours=1)
            )),
            ("combined_filters", lambda: self.audit_logger.get_events(
                user_id=users[0], 
                event_type=AuditEventType.API_REQUEST
            ))
        ]
        
        query_times = []
        query_results = []
        
        for query_name, query_func in query_tests:
            start_time = time.time()
            
            results = await query_func()
            
            query_time = (time.time() - start_time) * 1000  # Convert to ms
            query_times.append((query_name, query_time))
            query_results.append((query_name, len(results)))
        
        # Then: Query performance should meet requirements
        for query_name, query_time in query_times:
            assert query_time < max_query_time_ms, f"Query '{query_name}' took {query_time}ms"
        
        # And: Queries should return reasonable results
        total_results = sum(count for _, count in query_results)
        assert total_results > 0
        
        avg_query_time = sum(time for _, time in query_times) / len(query_times)
        max_query_time = max(time for _, time in query_times)
        
        self.record_metric("performance_events_created", event_count)
        self.record_metric("performance_queries_executed", len(query_tests))
        self.record_metric("avg_query_time_ms", avg_query_time)
        self.record_metric("max_query_time_ms", max_query_time)
        self.record_metric("query_performance_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Log test execution time
        execution_time = self.get_metrics().execution_time
        if execution_time > 2.0:  # Warn for slow tests
            self.record_metric("slow_audit_test_warning", execution_time)
        
        super().teardown_method(method)