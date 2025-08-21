"""Agent Audit Trail L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (compliance and governance)
- Business Goal: Complete audit trail for AI operations
- Value Impact: Protects $9K MRR from compliance violations and investigations
- Strategic Impact: Enables regulatory compliance and forensic analysis

Critical Path: Event capture -> Enrichment -> Storage -> Indexing -> Query
Coverage: Real audit logging, compliance tracking, forensic analysis
"""

import pytest
import asyncio
import time
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Union
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import uuid4

# Real components for L2 testing
from app.services.redis_service import RedisService
from app.core.circuit_breaker import CircuitBreaker
from app.core.database_connection_manager import DatabaseConnectionManager
from app.agents.base import BaseSubAgent
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    AGENT_CREATED = "agent_created"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    SECURITY_EVENT = "security_event"
    PERMISSION_CHANGE = "permission_change"


class AuditLevel(Enum):
    """Audit levels for event severity."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Compliance frameworks."""
    SOX = "sox"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"


@dataclass
class AuditEvent:
    """Represents an audit event."""
    event_id: str
    event_type: AuditEventType
    level: AuditLevel
    timestamp: datetime
    agent_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    compliance_tags: List[ComplianceFramework] = field(default_factory=list)
    sensitive_data_hash: Optional[str] = None
    retention_days: int = 2555  # 7 years default
    encrypted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        data["level"] = self.level.value
        data["compliance_tags"] = [tag.value for tag in self.compliance_tags]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = AuditEventType(data["event_type"])
        data["level"] = AuditLevel(data["level"])
        data["compliance_tags"] = [ComplianceFramework(tag) for tag in data["compliance_tags"]]
        return cls(**data)


@dataclass
class AuditQuery:
    """Query parameters for audit trail search."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    agent_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    event_types: Optional[List[AuditEventType]] = None
    levels: Optional[List[AuditLevel]] = None
    compliance_frameworks: Optional[List[ComplianceFramework]] = None
    message_contains: Optional[str] = None
    source_ips: Optional[List[str]] = None
    limit: int = 1000
    offset: int = 0
    order_by: str = "timestamp"
    order_desc: bool = True


class AuditEventEnricher:
    """Enriches audit events with additional context."""
    
    def __init__(self):
        self.enrichment_rules = {}
        self.pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
        ]
        
    def enrich_event(self, event: AuditEvent, context: Dict[str, Any]) -> AuditEvent:
        """Enrich an audit event with additional context."""
        # Add geolocation if IP is available
        if event.source_ip and "geolocation" not in event.details:
            event.details["geolocation"] = self._get_geolocation(event.source_ip)
        
        # Add user agent information
        if "user_agent" in context:
            event.details["user_agent"] = context["user_agent"]
        
        # Add request context
        if "request_id" in context:
            event.details["request_id"] = context["request_id"]
        
        # Detect and hash sensitive data
        sensitive_hash = self._detect_sensitive_data(event.message, event.details)
        if sensitive_hash:
            event.sensitive_data_hash = sensitive_hash
        
        # Apply compliance tags based on event type
        event.compliance_tags = self._determine_compliance_tags(event)
        
        return event
    
    def _get_geolocation(self, ip: str) -> Dict[str, str]:
        """Get geolocation for IP address."""
        # Mock geolocation service
        return {
            "country": "US",
            "region": "CA",
            "city": "San Francisco",
            "timezone": "America/Los_Angeles"
        }
    
    def _detect_sensitive_data(self, message: str, details: Dict[str, Any]) -> Optional[str]:
        """Detect sensitive data and return hash."""
        import re
        
        all_text = message + " " + json.dumps(details)
        
        for pattern in self.pii_patterns:
            if re.search(pattern, all_text):
                # Hash the content for audit purposes
                return hashlib.sha256(all_text.encode()).hexdigest()[:16]
        
        return None
    
    def _determine_compliance_tags(self, event: AuditEvent) -> List[ComplianceFramework]:
        """Determine applicable compliance frameworks."""
        tags = []
        
        # SOX compliance for financial data
        if event.event_type in [AuditEventType.DATA_ACCESS, AuditEventType.CONFIG_CHANGE]:
            tags.append(ComplianceFramework.SOX)
        
        # GDPR for personal data
        if event.sensitive_data_hash:
            tags.append(ComplianceFramework.GDPR)
        
        # SOC2 for security events
        if event.event_type == AuditEventType.SECURITY_EVENT:
            tags.extend([ComplianceFramework.SOC2, ComplianceFramework.PCI_DSS])
        
        return tags


class AuditStorage:
    """Stores audit events with different storage backends."""
    
    def __init__(self, db_manager: DatabaseConnectionManager, redis_service: RedisService):
        self.db_manager = db_manager
        self.redis_service = redis_service
        self.encryption_key = "test_encryption_key"  # In practice, use proper key management
        
    async def store_event(self, event: AuditEvent) -> bool:
        """Store an audit event."""
        try:
            # Store in primary database
            await self._store_in_database(event)
            
            # Cache recent events in Redis
            await self._cache_recent_event(event)
            
            # Store sensitive events with encryption
            if event.sensitive_data_hash or event.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
                await self._store_encrypted(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store audit event {event.event_id}: {e}")
            return False
    
    async def _store_in_database(self, event: AuditEvent) -> None:
        """Store event in primary database."""
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                INSERT INTO audit_events (
                    event_id, event_type, level, timestamp, agent_id, user_id,
                    session_id, source_ip, message, details, compliance_tags,
                    sensitive_data_hash, retention_days, encrypted
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """, 
                event.event_id, event.event_type.value, event.level.value,
                event.timestamp, event.agent_id, event.user_id, event.session_id,
                event.source_ip, event.message, json.dumps(event.details),
                json.dumps([tag.value for tag in event.compliance_tags]),
                event.sensitive_data_hash, event.retention_days, event.encrypted
            )
        finally:
            await self.db_manager.return_connection(conn)
    
    async def _cache_recent_event(self, event: AuditEvent) -> None:
        """Cache recent event in Redis."""
        # Cache last 1000 events per agent
        cache_key = f"audit_recent:{event.agent_id}"
        event_data = json.dumps(event.to_dict())
        
        pipe = self.redis_service.client.pipeline()
        pipe.lpush(cache_key, event_data)
        pipe.ltrim(cache_key, 0, 999)  # Keep last 1000
        pipe.expire(cache_key, 86400)  # 24 hour TTL
        await pipe.execute()
    
    async def _store_encrypted(self, event: AuditEvent) -> None:
        """Store encrypted copy of sensitive event."""
        # In practice, use proper encryption
        encrypted_data = self._encrypt_data(json.dumps(event.to_dict()))
        
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                INSERT INTO audit_events_encrypted (
                    event_id, encrypted_data, created_at
                ) VALUES ($1, $2, $3)
                ON CONFLICT (event_id) DO NOTHING
            """, event.event_id, encrypted_data, datetime.now())
        finally:
            await self.db_manager.return_connection(conn)
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        # Mock encryption - use proper encryption in production
        import base64
        return base64.b64encode(data.encode()).decode()
    
    async def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        conn = await self.db_manager.get_connection()
        try:
            # Build dynamic query
            where_clauses = []
            params = []
            param_count = 0
            
            if query.start_time:
                param_count += 1
                where_clauses.append(f"timestamp >= ${param_count}")
                params.append(query.start_time)
            
            if query.end_time:
                param_count += 1
                where_clauses.append(f"timestamp <= ${param_count}")
                params.append(query.end_time)
            
            if query.agent_ids:
                param_count += 1
                where_clauses.append(f"agent_id = ANY(${param_count})")
                params.append(query.agent_ids)
            
            if query.event_types:
                param_count += 1
                where_clauses.append(f"event_type = ANY(${param_count})")
                params.append([et.value for et in query.event_types])
            
            if query.levels:
                param_count += 1
                where_clauses.append(f"level = ANY(${param_count})")
                params.append([level.value for level in query.levels])
            
            if query.message_contains:
                param_count += 1
                where_clauses.append(f"message ILIKE ${param_count}")
                params.append(f"%{query.message_contains}%")
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            order_direction = "DESC" if query.order_desc else "ASC"
            
            sql = f"""
                SELECT * FROM audit_events 
                WHERE {where_sql}
                ORDER BY {query.order_by} {order_direction}
                LIMIT {query.limit} OFFSET {query.offset}
            """
            
            rows = await conn.fetch(sql, *params)
            
            events = []
            for row in rows:
                event_data = dict(row)
                event_data["details"] = json.loads(event_data["details"])
                event_data["compliance_tags"] = json.loads(event_data["compliance_tags"])
                events.append(AuditEvent.from_dict(event_data))
            
            return events
            
        finally:
            await self.db_manager.return_connection(conn)


class AuditLogger:
    """Main audit logging service."""
    
    def __init__(self, storage: AuditStorage, enricher: AuditEventEnricher):
        self.storage = storage
        self.enricher = enricher
        self.pending_events = []
        self.batch_size = 100
        self.flush_interval = 10  # seconds
        self._last_flush = time.time()
        
    async def log_event(self, 
                       event_type: AuditEventType,
                       level: AuditLevel,
                       agent_id: str,
                       message: str,
                       details: Optional[Dict[str, Any]] = None,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       source_ip: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None) -> str:
        """Log an audit event."""
        
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            level=level,
            timestamp=datetime.now(),
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            source_ip=source_ip,
            message=message,
            details=details or {}
        )
        
        # Enrich the event
        event = self.enricher.enrich_event(event, context or {})
        
        # Add to batch
        self.pending_events.append(event)
        
        # Flush if batch is full or time threshold reached
        if (len(self.pending_events) >= self.batch_size or 
            time.time() - self._last_flush > self.flush_interval):
            await self.flush_events()
        
        return event.event_id
    
    async def flush_events(self) -> None:
        """Flush pending events to storage."""
        if not self.pending_events:
            return
        
        events_to_store = self.pending_events.copy()
        self.pending_events.clear()
        self._last_flush = time.time()
        
        # Store events concurrently
        store_tasks = [self.storage.store_event(event) for event in events_to_store]
        results = await asyncio.gather(*store_tasks, return_exceptions=True)
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to store audit event {events_to_store[i].event_id}: {result}")
    
    async def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        return await self.storage.query_events(query)
    
    async def get_compliance_report(self, 
                                  framework: ComplianceFramework,
                                  start_time: datetime,
                                  end_time: datetime) -> Dict[str, Any]:
        """Generate compliance report."""
        query = AuditQuery(
            start_time=start_time,
            end_time=end_time,
            compliance_frameworks=[framework],
            limit=10000
        )
        
        events = await self.query_events(query)
        
        # Analyze events for compliance
        report = {
            "framework": framework.value,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_events": len(events),
            "event_breakdown": {},
            "risk_events": [],
            "compliance_score": 0.0
        }
        
        # Count events by type
        for event in events:
            event_type = event.event_type.value
            if event_type not in report["event_breakdown"]:
                report["event_breakdown"][event_type] = 0
            report["event_breakdown"][event_type] += 1
            
            # Identify risk events
            if event.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
                report["risk_events"].append({
                    "event_id": event.event_id,
                    "timestamp": event.timestamp.isoformat(),
                    "level": event.level.value,
                    "message": event.message
                })
        
        # Calculate compliance score (simplified)
        risk_count = len(report["risk_events"])
        total_count = len(events)
        if total_count > 0:
            report["compliance_score"] = max(0.0, 1.0 - (risk_count / total_count))
        
        return report


class AuditTrailManager:
    """Manages audit trail testing."""
    
    def __init__(self):
        self.db_manager = None
        self.redis_service = None
        self.storage = None
        self.enricher = None
        self.audit_logger = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.storage = AuditStorage(self.db_manager, self.redis_service)
        self.enricher = AuditEventEnricher()
        self.audit_logger = AuditLogger(self.storage, self.enricher)
        
        # Create test schema
        await self.create_test_schema()
    
    async def create_test_schema(self):
        """Create test database schema."""
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR PRIMARY KEY,
                    event_type VARCHAR NOT NULL,
                    level VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    agent_id VARCHAR NOT NULL,
                    user_id VARCHAR,
                    session_id VARCHAR,
                    source_ip VARCHAR,
                    message TEXT NOT NULL,
                    details JSONB,
                    compliance_tags JSONB,
                    sensitive_data_hash VARCHAR,
                    retention_days INTEGER DEFAULT 2555,
                    encrypted BOOLEAN DEFAULT FALSE
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events_encrypted (
                    event_id VARCHAR PRIMARY KEY,
                    encrypted_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_agent_id ON audit_events(agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)")
            
        finally:
            await self.db_manager.return_connection(conn)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.audit_logger:
            await self.audit_logger.flush_events()
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()


@pytest.fixture
async def audit_manager():
    """Create audit trail manager for testing."""
    manager = AuditTrailManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_audit_event_logging(audit_manager):
    """Test basic audit event logging."""
    manager = audit_manager
    
    # Log a simple audit event
    event_id = await manager.audit_logger.log_event(
        event_type=AuditEventType.AGENT_STARTED,
        level=AuditLevel.INFO,
        agent_id="test_agent_001",
        message="Agent started successfully",
        details={"startup_time_ms": 150},
        user_id="user_123",
        source_ip="192.168.1.100"
    )
    
    assert event_id is not None
    assert len(event_id) > 0
    
    # Flush events to storage
    await manager.audit_logger.flush_events()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_audit_event_enrichment(audit_manager):
    """Test audit event enrichment."""
    manager = audit_manager
    
    # Log event with context for enrichment
    context = {
        "user_agent": "TestAgent/1.0",
        "request_id": "req_12345"
    }
    
    event_id = await manager.audit_logger.log_event(
        event_type=AuditEventType.MODEL_REQUEST,
        level=AuditLevel.INFO,
        agent_id="test_agent_002",
        message="Model request initiated",
        details={"model": "gpt-4", "tokens": 150},
        source_ip="10.0.0.1",
        context=context
    )
    
    await manager.audit_logger.flush_events()
    
    # Query the event to verify enrichment
    query = AuditQuery(agent_ids=["test_agent_002"])
    events = await manager.audit_logger.query_events(query)
    
    assert len(events) >= 1
    event = next(e for e in events if e.event_id == event_id)
    assert event.details["user_agent"] == "TestAgent/1.0"
    assert event.details["request_id"] == "req_12345"
    assert "geolocation" in event.details


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_sensitive_data_detection(audit_manager):
    """Test sensitive data detection and hashing."""
    manager = audit_manager
    
    # Log event with sensitive data
    event_id = await manager.audit_logger.log_event(
        event_type=AuditEventType.DATA_ACCESS,
        level=AuditLevel.WARNING,
        agent_id="test_agent_003",
        message="Accessed user data for john.doe@example.com",
        details={"record_count": 1},
        user_id="admin_001"
    )
    
    await manager.audit_logger.flush_events()
    
    # Query the event to verify sensitive data hash
    query = AuditQuery(agent_ids=["test_agent_003"])
    events = await manager.audit_logger.query_events(query)
    
    assert len(events) >= 1
    event = next(e for e in events if e.event_id == event_id)
    assert event.sensitive_data_hash is not None
    assert ComplianceFramework.GDPR in event.compliance_tags


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_compliance_tagging(audit_manager):
    """Test automatic compliance framework tagging."""
    manager = audit_manager
    
    # Log a security event
    security_event_id = await manager.audit_logger.log_event(
        event_type=AuditEventType.SECURITY_EVENT,
        level=AuditLevel.ERROR,
        agent_id="test_agent_004",
        message="Authentication failure",
        details={"failed_attempts": 3},
        source_ip="suspicious.ip.address"
    )
    
    # Log a config change event
    config_event_id = await manager.audit_logger.log_event(
        event_type=AuditEventType.CONFIG_CHANGE,
        level=AuditLevel.INFO,
        agent_id="test_agent_004",
        message="Agent configuration updated",
        details={"changed_fields": ["timeout", "retry_count"]},
        user_id="admin_002"
    )
    
    await manager.audit_logger.flush_events()
    
    # Query and verify compliance tags
    query = AuditQuery(agent_ids=["test_agent_004"])
    events = await manager.audit_logger.query_events(query)
    
    security_event = next(e for e in events if e.event_id == security_event_id)
    config_event = next(e for e in events if e.event_id == config_event_id)
    
    # Security events should have SOC2 and PCI_DSS tags
    assert ComplianceFramework.SOC2 in security_event.compliance_tags
    assert ComplianceFramework.PCI_DSS in security_event.compliance_tags
    
    # Config changes should have SOX tag
    assert ComplianceFramework.SOX in config_event.compliance_tags


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_audit_event_querying(audit_manager):
    """Test audit event querying capabilities."""
    manager = audit_manager
    
    # Create test events
    agent_id = "query_test_agent"
    start_time = datetime.now()
    
    event_ids = []
    for i in range(5):
        event_id = await manager.audit_logger.log_event(
            event_type=AuditEventType.AGENT_CREATED if i % 2 == 0 else AuditEventType.AGENT_STARTED,
            level=AuditLevel.INFO if i < 3 else AuditLevel.WARNING,
            agent_id=agent_id,
            message=f"Test event {i}",
            details={"sequence": i},
            user_id=f"user_{i}"
        )
        event_ids.append(event_id)
    
    await manager.audit_logger.flush_events()
    
    # Test basic query
    query = AuditQuery(agent_ids=[agent_id])
    events = await manager.audit_logger.query_events(query)
    assert len(events) == 5
    
    # Test event type filtering
    query = AuditQuery(
        agent_ids=[agent_id],
        event_types=[AuditEventType.AGENT_CREATED]
    )
    events = await manager.audit_logger.query_events(query)
    assert len(events) == 3  # Events 0, 2, 4
    
    # Test level filtering
    query = AuditQuery(
        agent_ids=[agent_id],
        levels=[AuditLevel.WARNING]
    )
    events = await manager.audit_logger.query_events(query)
    assert len(events) == 2  # Events 3, 4
    
    # Test message search
    query = AuditQuery(
        agent_ids=[agent_id],
        message_contains="event 2"
    )
    events = await manager.audit_logger.query_events(query)
    assert len(events) == 1


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_batch_event_processing(audit_manager):
    """Test batch processing of audit events."""
    manager = audit_manager
    
    # Log many events to trigger batching
    agent_id = "batch_test_agent"
    event_ids = []
    
    for i in range(150):  # More than batch size
        event_id = await manager.audit_logger.log_event(
            event_type=AuditEventType.MODEL_REQUEST,
            level=AuditLevel.INFO,
            agent_id=agent_id,
            message=f"Batch event {i}",
            details={"batch_index": i}
        )
        event_ids.append(event_id)
    
    # Events should auto-flush due to batch size
    await asyncio.sleep(0.5)  # Give time for async processing
    
    # Verify all events were stored
    query = AuditQuery(agent_ids=[agent_id], limit=200)
    events = await manager.audit_logger.query_events(query)
    assert len(events) == 150


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_compliance_reporting(audit_manager):
    """Test compliance report generation."""
    manager = audit_manager
    
    # Create events for compliance testing
    agent_id = "compliance_test_agent"
    start_time = datetime.now() - timedelta(hours=1)
    
    # Log various event types
    await manager.audit_logger.log_event(
        event_type=AuditEventType.SECURITY_EVENT,
        level=AuditLevel.ERROR,
        agent_id=agent_id,
        message="Security violation detected",
        details={"violation_type": "unauthorized_access"}
    )
    
    await manager.audit_logger.log_event(
        event_type=AuditEventType.DATA_ACCESS,
        level=AuditLevel.INFO,
        agent_id=agent_id,
        message="Accessed customer records",
        details={"records": 10}
    )
    
    await manager.audit_logger.flush_events()
    
    # Generate SOC2 compliance report
    end_time = datetime.now()
    report = await manager.audit_logger.get_compliance_report(
        ComplianceFramework.SOC2,
        start_time,
        end_time
    )
    
    assert report["framework"] == "soc2"
    assert report["total_events"] >= 2
    assert len(report["risk_events"]) >= 1  # Security event
    assert report["compliance_score"] < 1.0  # Due to security event


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_encrypted_storage(audit_manager):
    """Test encrypted storage for sensitive events."""
    manager = audit_manager
    
    # Log a critical event (should trigger encryption)
    event_id = await manager.audit_logger.log_event(
        event_type=AuditEventType.SECURITY_EVENT,
        level=AuditLevel.CRITICAL,
        agent_id="encryption_test_agent",
        message="Critical security breach",
        details={"severity": "high", "affected_systems": ["auth", "data"]},
        user_id="incident_response"
    )
    
    await manager.audit_logger.flush_events()
    
    # Verify event was encrypted
    conn = await manager.db_manager.get_connection()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM audit_events_encrypted WHERE event_id = $1",
            event_id
        )
        assert row is not None
        assert row["encrypted_data"] is not None
    finally:
        await manager.db_manager.return_connection(conn)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_redis_caching(audit_manager):
    """Test Redis caching of recent events."""
    manager = audit_manager
    
    agent_id = "cache_test_agent"
    
    # Log events
    for i in range(5):
        await manager.audit_logger.log_event(
            event_type=AuditEventType.AGENT_STARTED,
            level=AuditLevel.INFO,
            agent_id=agent_id,
            message=f"Cached event {i}",
            details={"index": i}
        )
    
    await manager.audit_logger.flush_events()
    
    # Check Redis cache
    cache_key = f"audit_recent:{agent_id}"
    cached_events = await manager.redis_service.client.lrange(cache_key, 0, -1)
    
    assert len(cached_events) == 5
    
    # Verify cached data
    first_event_data = json.loads(cached_events[0])  # Most recent
    assert first_event_data["message"] == "Cached event 4"


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_audit_logging(audit_manager):
    """Test concurrent audit logging."""
    manager = audit_manager
    
    # Log events concurrently
    tasks = []
    for i in range(50):
        task = manager.audit_logger.log_event(
            event_type=AuditEventType.MODEL_REQUEST,
            level=AuditLevel.INFO,
            agent_id=f"concurrent_agent_{i % 5}",
            message=f"Concurrent event {i}",
            details={"thread": i}
        )
        tasks.append(task)
    
    event_ids = await asyncio.gather(*tasks)
    await manager.audit_logger.flush_events()
    
    assert len(event_ids) == 50
    assert all(event_id is not None for event_id in event_ids)
    
    # Verify all events were stored
    query = AuditQuery(message_contains="Concurrent event", limit=100)
    events = await manager.audit_logger.query_events(query)
    assert len(events) == 50


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_audit_performance(audit_manager):
    """Benchmark audit logging performance."""
    manager = audit_manager
    
    # Benchmark logging performance
    start_time = time.time()
    
    tasks = []
    for i in range(1000):
        task = manager.audit_logger.log_event(
            event_type=AuditEventType.MODEL_REQUEST,
            level=AuditLevel.INFO,
            agent_id=f"perf_agent_{i % 10}",
            message=f"Performance test event {i}",
            details={"iteration": i, "batch": i // 100}
        )
        tasks.append(task)
    
    event_ids = await asyncio.gather(*tasks)
    await manager.audit_logger.flush_events()
    
    total_time = time.time() - start_time
    
    assert len(event_ids) == 1000
    
    # Performance assertions
    assert total_time < 5.0  # 1000 events in under 5 seconds
    avg_time = total_time / 1000
    assert avg_time < 0.005  # Average under 5ms per event
    
    logger.info(f"Audit Performance: {avg_time*1000:.2f}ms per event, {1000/total_time:.0f} events/sec")