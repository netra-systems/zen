"""Auth Audit Trail Integrity L4 Integration Tests

Tests comprehensive audit trail integrity for authentication and authorization
events, including tamper detection, compliance reporting, and forensic analysis.

Business Value Justification (BVJ):
- Segment: Enterprise (Compliance requirements)
- Business Goal: Meet SOC2, ISO27001, GDPR compliance for enterprise deals
- Value Impact: Enable $3M+ enterprise contracts requiring audit compliance
- Strategic Impact: Critical for regulated industries and security certifications

Critical Path:
Auth event -> Audit capture -> Integrity signing -> Storage -> 
Replication -> Compliance check -> Retention -> Forensic query

Mock-Real Spectrum: L4 (Production audit infrastructure)
- Real audit database
- Real cryptographic signing
- Real compliance checks
- Real retention policies
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from netra_backend.app.clients.auth_client_core import auth_client

# Removed broken import statement
# # # #     AuditEvent, AuditQuery, ComplianceReport,  # Class may not exist, commented out  # Class may not exist, commented out  # Class may not exist, commented out
# # #     ForensicAnalysis, IntegrityCheck  # Class may not exist, commented out  # Class may not exist, commented out
# )
# Note: These classes don't exist in auth_types, using generic dict structures instead
from netra_backend.app.core.config import get_settings
from netra_backend.app.db.postgres import get_async_db

# from app.core.audit_logger import AuditLogger  # May not exist, commenting out
# from app.core.monitoring import metrics_collector  # May not exist, commenting out

@dataclass
class AuditRecord:
    """Immutable audit record"""
    event_id: str
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    resource: str
    result: str  # "success", "failure", "error"
    ip_address: str
    user_agent: str
    metadata: Dict[str, Any]
    integrity_hash: str
    signature: Optional[bytes] = None
    previous_hash: Optional[str] = None  # For blockchain-style chaining

@dataclass
class AuditMetrics:
    """Metrics for audit trail testing"""
    total_events: int = 0
    events_captured: int = 0
    events_lost: int = 0
    integrity_violations: int = 0
    signature_failures: int = 0
    compliance_violations: int = 0
    query_performance_ms: List[float] = field(default_factory=list)
    storage_size_mb: float = 0
    
    @property
    def capture_rate(self) -> float:
        if self.total_events == 0:
            return 0
        return (self.events_captured / self.total_events) * 100
    
    @property
    def integrity_rate(self) -> float:
        if self.events_captured == 0:
            return 0
        return ((self.events_captured - self.integrity_violations) / self.events_captured) * 100

class TestAuthAuditTrailIntegrity:
    """Test suite for auth audit trail integrity"""
    
    @pytest.fixture
    async def audit_logger(self):
        """Initialize audit logger with integrity features"""
        settings = get_settings()
        
        # Generate signing keys
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        logger = AuditLogger(
            database_url=settings.database_url,
            signing_key=private_key,
            verification_key=public_key,
            enable_blockchain=True,
            retention_days=90
        )
        
        await logger.initialize()
        yield logger
        await logger.close()
    
    @pytest.fixture
    async def compliance_checker(self):
        """Check compliance requirements"""
        requirements = {
            "SOC2": {
                "retention_days": 90,
                "encryption_required": True,
                "signature_required": True,
                "immutable_storage": True
            },
            "ISO27001": {
                "retention_days": 365,
                "access_logging": True,
                "integrity_verification": True,
                "regular_audits": True
            },
            "GDPR": {
                "retention_days": 1095,  # 3 years
                "data_minimization": True,
                "right_to_erasure": True,
                "audit_trail": True
            }
        }
        
        async def check_compliance(audit_record: AuditRecord, standard: str) -> bool:
            req = requirements.get(standard, {})
            
            # Check retention
            age_days = (datetime.now(timezone.utc) - audit_record.timestamp).days
            if age_days > req.get("retention_days", 365):
                yield False
            
            # Check encryption/signature
            if req.get("signature_required") and not audit_record.signature:
                yield False
            
            # Check integrity
            if req.get("integrity_verification"):
                if not audit_record.integrity_hash:
                    yield False
            
            yield True
        
        yield check_compliance
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    @pytest.mark.asyncio
    async def test_complete_audit_trail_capture(
        self, audit_logger
    ):
        """Test complete capture of all auth events"""
        metrics = AuditMetrics()
        
        # Define auth operations to audit
        operations = [
            ("login", {"email": "user@test.com", "password": "pass123"}),
            ("token_validation", {"token": "jwt_token_123"}),
            ("permission_check", {"user": "user123", "resource": "/api/data", "action": "read"}),
            ("token_refresh", {"refresh_token": "refresh_123"}),
            ("logout", {"session_id": "session_123"}),
            ("failed_login", {"email": "attacker@evil.com", "password": "wrong"}),
            ("rate_limit_exceeded", {"ip": "192.168.1.100"}),
            ("permission_denied", {"user": "user456", "resource": "/api/admin", "action": "write"})
        ]
        
        # Execute operations and capture audit events
        for op_type, op_data in operations:
            metrics.total_events += 1
            
            # Create audit event
            event = AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                event_type=op_type,
                user_id=op_data.get("user"),
                session_id=op_data.get("session_id"),
                action=op_type,
                resource=op_data.get("resource", "/auth"),
                result="success" if "failed" not in op_type else "failure",
                ip_address=op_data.get("ip", "127.0.0.1"),
                user_agent="TestClient/1.0",
                metadata=op_data,
                integrity_hash=""
            )
            
            # Calculate integrity hash
            event.integrity_hash = await self.calculate_integrity_hash(event)
            
            # Log event
            logged = await audit_logger.log(event)
            if logged:
                metrics.events_captured += 1
            else:
                metrics.events_lost += 1
        
        # Verify all events captured
        assert metrics.capture_rate >= 99.9, \
            f"Capture rate {metrics.capture_rate}% below 99.9%"
        
        # Query audit trail
        async with get_async_db() as db:
            result = await db.fetch(
                "SELECT COUNT(*) as count FROM audit_log WHERE timestamp > $1",
                datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            assert result[0]["count"] >= metrics.events_captured
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    @pytest.mark.asyncio
    async def test_audit_trail_integrity_verification(
        self, audit_logger
    ):
        """Test integrity verification and tamper detection"""
        metrics = AuditMetrics()
        
        # Create chain of audit events
        events = []
        previous_hash = None
        
        for i in range(10):
            event = AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                event_type="test_event",
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                action="test_action",
                resource="/test",
                result="success",
                ip_address="127.0.0.1",
                user_agent="Test",
                metadata={"index": i},
                integrity_hash="",
                previous_hash=previous_hash
            )
            
            # Calculate hash including previous hash (blockchain style)
            event.integrity_hash = await self.calculate_integrity_hash(event)
            previous_hash = event.integrity_hash
            
            # Sign event
            event.signature = await audit_logger.sign_event(event)
            
            events.append(event)
            await audit_logger.log(event)
        
        # Verify integrity of all events
        for i, event in enumerate(events):
            # Verify hash
            calculated_hash = await self.calculate_integrity_hash(event)
            if calculated_hash != event.integrity_hash:
                metrics.integrity_violations += 1
            
            # Verify signature
            signature_valid = await audit_logger.verify_signature(event)
            if not signature_valid:
                metrics.signature_failures += 1
            
            # Verify chain
            if i > 0 and event.previous_hash != events[i-1].integrity_hash:
                metrics.integrity_violations += 1
        
        assert metrics.integrity_violations == 0, \
            f"Found {metrics.integrity_violations} integrity violations"
        assert metrics.signature_failures == 0, \
            f"Found {metrics.signature_failures} signature failures"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    @pytest.mark.asyncio
    async def test_audit_tampering_detection(
        self, audit_logger
    ):
        """Test detection of tampered audit records"""
        # Create legitimate audit event
        event = AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type="sensitive_action",
            user_id="admin_user",
            session_id="admin_session",
            action="delete_user",
            resource="/api/users/123",
            result="success",
            ip_address="192.168.1.1",
            user_agent="AdminTool",
            metadata={"deleted_user": "user123"},
            integrity_hash=""
        )
        
        # Calculate and sign
        event.integrity_hash = await self.calculate_integrity_hash(event)
        event.signature = await audit_logger.sign_event(event)
        
        # Log event
        await audit_logger.log(event)
        
        # Attempt to tamper with database directly
        async with get_async_db() as db:
            # Try to modify the result
            await db.execute(
                """
                UPDATE audit_log 
                SET result = 'failure', metadata = '{"tampered": true}'
                WHERE event_id = $1
                """,
                event.event_id
            )
            await db.commit()
        
        # Run integrity check
        integrity_report = await audit_logger.verify_integrity(
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc)
        )
        
        # Should detect tampering
        assert integrity_report.tampered_records > 0, \
            "Tampering not detected"
        assert event.event_id in integrity_report.tampered_event_ids, \
            "Tampered event not identified"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    @pytest.mark.asyncio
    async def test_compliance_reporting(
        self, audit_logger, compliance_checker
    ):
        """Test compliance reporting for various standards"""
        metrics = AuditMetrics()
        
        # Generate audit events for different compliance scenarios
        test_events = []
        
        # SOC2 event - financial transaction
        test_events.append(AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type="payment_processed",
            user_id="customer_123",
            session_id="session_456",
            action="charge_card",
            resource="/api/payments",
            result="success",
            ip_address="10.0.0.1",
            user_agent="PaymentGateway",
            metadata={"amount": 99.99, "currency": "USD"},
            integrity_hash="",
            signature=b"signed"
        ))
        
        # ISO27001 event - security incident
        test_events.append(AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type="security_alert",
            user_id=None,
            session_id=None,
            action="brute_force_detected",
            resource="/api/login",
            result="blocked",
            ip_address="192.168.1.100",
            user_agent="Unknown",
            metadata={"attempts": 50, "blocked": True},
            integrity_hash="",
            signature=b"signed"
        ))
        
        # GDPR event - data access
        test_events.append(AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type="personal_data_access",
            user_id="processor_789",
            session_id="session_999",
            action="export_user_data",
            resource="/api/gdpr/export",
            result="success",
            ip_address="10.0.0.2",
            user_agent="GDPRTool",
            metadata={"data_subject": "user_xyz", "purpose": "user_request"},
            integrity_hash="",
            signature=b"signed"
        ))
        
        # Log all events
        for event in test_events:
            event.integrity_hash = await self.calculate_integrity_hash(event)
            await audit_logger.log(event)
        
        # Generate compliance reports
        compliance_standards = ["SOC2", "ISO27001", "GDPR"]
        
        for standard in compliance_standards:
            report = await audit_logger.generate_compliance_report(
                standard=standard,
                start_date=datetime.now(timezone.utc) - timedelta(days=30),
                end_date=datetime.now(timezone.utc)
            )
            
            # Check compliance for each event
            compliant_events = 0
            for event in test_events:
                is_compliant = await compliance_checker(event, standard)
                if is_compliant:
                    compliant_events += 1
                else:
                    metrics.compliance_violations += 1
            
            # Verify report accuracy
            assert report.total_events >= len(test_events)
            assert report.compliant_events >= compliant_events
            assert report.compliance_percentage >= 90, \
                f"{standard} compliance {report.compliance_percentage}% below 90%"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    @pytest.mark.asyncio
    async def test_forensic_analysis_capabilities(
        self, audit_logger
    ):
        """Test forensic analysis and investigation capabilities"""
        # Simulate security incident
        attacker_ip = "192.168.100.50"
        victim_user = "victim_user_123"
        incident_time = datetime.now(timezone.utc)
        
        # Create attack pattern
        attack_events = []
        
        # Reconnaissance
        for i in range(10):
            attack_events.append(AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=incident_time - timedelta(minutes=30-i),
                event_type="failed_login",
                user_id=None,
                session_id=None,
                action="login_attempt",
                resource="/api/login",
                result="failure",
                ip_address=attacker_ip,
                user_agent="Scanner/1.0",
                metadata={"username": f"test{i}", "error": "invalid_credentials"},
                integrity_hash=""
            ))
        
        # Successful breach
        attack_events.append(AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp=incident_time - timedelta(minutes=15),
            event_type="login",
            user_id=victim_user,
            session_id="compromised_session",
            action="login",
            resource="/api/login",
            result="success",
            ip_address=attacker_ip,
            user_agent="Scanner/1.0",
            metadata={"username": victim_user},
            integrity_hash=""
        ))
        
        # Data exfiltration
        for i in range(5):
            attack_events.append(AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=incident_time - timedelta(minutes=10-i),
                event_type="data_access",
                user_id=victim_user,
                session_id="compromised_session",
                action="export_data",
                resource=f"/api/data/{i}",
                result="success",
                ip_address=attacker_ip,
                user_agent="Scanner/1.0",
                metadata={"records_exported": 1000},
                integrity_hash=""
            ))
        
        # Log all events
        for event in attack_events:
            event.integrity_hash = await self.calculate_integrity_hash(event)
            await audit_logger.log(event)
        
        # Perform forensic analysis
        analysis = await audit_logger.forensic_analysis(
            ip_address=attacker_ip,
            time_window=(incident_time - timedelta(hours=1), incident_time),
            event_types=["failed_login", "login", "data_access"]
        )
        
        # Verify attack pattern detected
        assert analysis.suspicious_activity_detected, "Attack not detected"
        assert attacker_ip in analysis.suspicious_ips
        assert len(analysis.timeline) >= len(attack_events)
        
        # Check attack indicators
        assert analysis.failed_login_attempts >= 10
        assert analysis.successful_breach == True
        assert analysis.data_exfiltration_detected == True
        assert victim_user in analysis.compromised_users
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    @pytest.mark.asyncio
    async def test_audit_retention_and_archival(
        self, audit_logger
    ):
        """Test audit retention policies and archival"""
        metrics = AuditMetrics()
        
        # Create events with different ages
        retention_test_events = []
        
        # Recent events (should be retained)
        for i in range(5):
            event = AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                event_type="recent_event",
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                action="test",
                resource="/test",
                result="success",
                ip_address="127.0.0.1",
                user_agent="Test",
                metadata={"age_days": i},
                integrity_hash=""
            )
            retention_test_events.append(event)
        
        # Old events (should be archived)
        for i in range(5):
            event = AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc) - timedelta(days=100+i),
                event_type="old_event",
                user_id=f"old_user_{i}",
                session_id=f"old_session_{i}",
                action="test",
                resource="/test",
                result="success",
                ip_address="127.0.0.1",
                user_agent="Test",
                metadata={"age_days": 100+i},
                integrity_hash=""
            )
            retention_test_events.append(event)
        
        # Log all events
        for event in retention_test_events:
            event.integrity_hash = await self.calculate_integrity_hash(event)
            await audit_logger.log(event)
        
        # Run retention policy (90 day retention)
        archived_count = await audit_logger.archive_old_events(
            retention_days=90,
            archive_location="s3://audit-archive/"
        )
        
        # Verify archival
        assert archived_count >= 5, f"Only {archived_count} events archived"
        
        # Verify recent events still accessible
        async with get_async_db() as db:
            recent = await db.fetch(
                """
                SELECT COUNT(*) as count 
                FROM audit_log 
                WHERE timestamp > $1
                """,
                datetime.now(timezone.utc) - timedelta(days=90)
            )
            assert recent[0]["count"] >= 5, "Recent events missing"
            
            # Verify old events moved to archive
            old = await db.fetch(
                """
                SELECT COUNT(*) as count 
                FROM audit_log 
                WHERE timestamp < $1
                """,
                datetime.now(timezone.utc) - timedelta(days=90)
            )
            assert old[0]["count"] == 0, "Old events not archived"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    @pytest.mark.asyncio
    async def test_audit_query_performance(
        self, audit_logger
    ):
        """Test audit query performance at scale"""
        metrics = AuditMetrics()
        
        # Generate large number of audit events
        bulk_events = []
        for i in range(1000):
            event = AuditRecord(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
                event_type="bulk_event",
                user_id=f"user_{i % 100}",  # 100 unique users
                session_id=f"session_{i % 50}",  # 50 unique sessions
                action=f"action_{i % 10}",  # 10 action types
                resource=f"/api/resource_{i % 20}",  # 20 resources
                result="success" if i % 10 != 0 else "failure",
                ip_address=f"192.168.{i % 256}.{i % 256}",
                user_agent="BulkTest",
                metadata={"index": i},
                integrity_hash=""
            )
            bulk_events.append(event)
        
        # Bulk insert
        for event in bulk_events:
            event.integrity_hash = await self.calculate_integrity_hash(event)
        
        await audit_logger.bulk_log(bulk_events)
        
        # Test various query patterns
        queries = [
            # User activity
            ("user_activity", {"user_id": "user_10", "limit": 100}),
            # Time range
            ("time_range", {
                "start": datetime.now(timezone.utc) - timedelta(hours=1),
                "end": datetime.now(timezone.utc)
            }),
            # Failed operations
            ("failures", {"result": "failure", "limit": 50}),
            # Specific resource
            ("resource", {"resource": "/api/resource_5", "limit": 20}),
            # IP address search
            ("ip_search", {"ip_address": "192.168.10.%", "limit": 10})
        ]
        
        for query_name, query_params in queries:
            start_time = time.time()
            
            results = await audit_logger.query(query_params)
            
            query_time = (time.time() - start_time) * 1000
            metrics.query_performance_ms.append(query_time)
            
            # Performance assertion
            assert query_time < 100, \
                f"Query {query_name} took {query_time}ms (>100ms)"
            
            # Result verification
            assert len(results) > 0, f"No results for {query_name}"
        
        # Check average performance
        avg_query_time = sum(metrics.query_performance_ms) / len(metrics.query_performance_ms)
        assert avg_query_time < 50, \
            f"Average query time {avg_query_time}ms exceeds 50ms"
    
    async def calculate_integrity_hash(self, event: AuditRecord) -> str:
        """Calculate integrity hash for audit event"""
        # Create deterministic string representation
        event_str = json.dumps({
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "user_id": event.user_id,
            "action": event.action,
            "resource": event.resource,
            "result": event.result,
            "metadata": event.metadata,
            "previous_hash": event.previous_hash
        }, sort_keys=True)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(event_str.encode()).hexdigest()