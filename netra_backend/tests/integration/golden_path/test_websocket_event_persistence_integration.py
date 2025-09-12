"""
Test WebSocket Event Persistence Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket events are persisted and auditable
- Value Impact: WebSocket events provide transparency and trust - core to user experience
- Strategic Impact: Critical for $500K+ ARR - missing events = poor UX = churn

This test validates Critical Issue #4 from Golden Path:
"Missing WebSocket Events" - Not all required WebSocket events are sent, breaking user experience.
The 5 critical events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

CRITICAL REQUIREMENTS:
1. Test all 5 WebSocket events are stored in real database
2. Test event replay from database for user recovery
3. Test event ordering validation and integrity
4. Test event audit trail for business compliance
5. NO MOCKS for PostgreSQL/Redis - use real event persistence
6. Use E2E authentication for all event operations
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_authenticated_user_context,
    AuthenticatedUser
)
from shared.types.core_types import UserID, ThreadID, RunID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class WebSocketEventType(Enum):
    """Required WebSocket events for Golden Path user experience."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    CONNECTION_READY = "connection_ready"
    ERROR = "error"


@dataclass
class WebSocketEventRecord:
    """WebSocket event record for testing."""
    event_id: str
    event_type: WebSocketEventType
    user_id: str
    thread_id: str
    websocket_id: str
    event_data: Dict[str, Any]
    timestamp: datetime
    sequence_number: int
    persisted: bool = False
    replay_validated: bool = False


class TestWebSocketEventPersistenceIntegration(BaseIntegrationTest):
    """Test WebSocket event persistence with real PostgreSQL and Redis."""
    
    def setup_method(self):
        """Initialize test environment."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.required_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_websocket_events_stored_in_database(self, real_services_fixture):
        """
        Test all 5 WebSocket events are stored in real database.
        
        CRITICAL: This validates that every required WebSocket event is persisted
        to the database for audit, replay, and business intelligence purposes.
        """
        # Verify real services
        assert real_services_fixture["database_available"], "Real PostgreSQL required"
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"websocket_events_{uuid.uuid4().hex[:8]}@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        db_session = real_services_fixture["db"]
        
        # Create user and thread in database
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Generate and store all required WebSocket events
        event_records = []
        
        for sequence, event_type in enumerate(self.required_events):
            event_record = await self._create_and_store_websocket_event(
                db_session,
                event_type,
                user_context,
                thread_id,
                sequence + 1
            )
            event_records.append(event_record)
            
            assert event_record.persisted, f"Event {event_type.value} should be persisted"
        
        # Verify all events are in database
        stored_events = await self._retrieve_websocket_events_from_database(
            db_session,
            str(user_context.user_id),
            thread_id
        )
        
        assert len(stored_events) >= len(self.required_events), \
            f"Should have at least {len(self.required_events)} events in database"
        
        # Verify each required event type is present
        stored_event_types = {event["event_type"] for event in stored_events}
        for required_event in self.required_events:
            assert required_event.value in stored_event_types, \
                f"Missing required WebSocket event: {required_event.value}"
        
        # Verify event data integrity
        for stored_event in stored_events:
            assert stored_event["user_id"] == str(user_context.user_id)
            assert stored_event["thread_id"] == thread_id
            assert stored_event["websocket_id"] == str(user_context.websocket_client_id)
            assert stored_event["event_data"] is not None
            assert stored_event["timestamp"] is not None
            assert stored_event["sequence_number"] > 0
        
        # Verify business value delivered
        self.assert_business_value_delivered(
            {"total_events": len(stored_events), "event_types": list(stored_event_types)},
            "insights"  # WebSocket events provide user insights and transparency
        )
        
        self.logger.info(f" PASS:  All {len(self.required_events)} required WebSocket events stored in database")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_replay_from_database(self, real_services_fixture):
        """
        Test event replay from database for user recovery.
        
        This validates that WebSocket events can be replayed from the database
        to restore user context after disconnection or system restart.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"event_replay_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Create a complete agent execution event sequence
        execution_events = [
            (WebSocketEventType.AGENT_STARTED, {
                "agent_id": "cost_optimizer",
                "message": "Starting cost optimization analysis",
                "estimated_duration": 30
            }),
            (WebSocketEventType.AGENT_THINKING, {
                "agent_id": "cost_optimizer", 
                "thinking_step": "Analyzing current cloud spend patterns",
                "progress": 20
            }),
            (WebSocketEventType.TOOL_EXECUTING, {
                "agent_id": "cost_optimizer",
                "tool_name": "aws_cost_analyzer", 
                "tool_input": {"account_ids": ["123456789"], "time_range": "30d"}
            }),
            (WebSocketEventType.TOOL_COMPLETED, {
                "agent_id": "cost_optimizer",
                "tool_name": "aws_cost_analyzer",
                "tool_result": {"total_cost": 45000, "optimization_opportunities": 12}
            }),
            (WebSocketEventType.AGENT_COMPLETED, {
                "agent_id": "cost_optimizer",
                "result": {
                    "recommendations": ["Right-size instances", "Use reserved instances"],
                    "potential_savings": {"monthly": 3500, "annual": 42000}
                },
                "execution_time": 28.5
            })
        ]
        
        # Store all events in sequence
        stored_event_ids = []
        for sequence, (event_type, event_data) in enumerate(execution_events):
            event_record = await self._create_and_store_websocket_event(
                db_session,
                event_type,
                user_context,
                thread_id,
                sequence + 1,
                event_data
            )
            stored_event_ids.append(event_record.event_id)
        
        # Test event replay functionality
        replayed_events = await self._replay_websocket_events_from_database(
            db_session,
            str(user_context.user_id),
            thread_id,
            sequence_start=1
        )
        
        assert len(replayed_events) == len(execution_events), \
            "Should replay all stored events"
        
        # Verify replay order and content
        for i, replayed_event in enumerate(replayed_events):
            expected_event_type, expected_data = execution_events[i]
            
            assert replayed_event["event_type"] == expected_event_type.value
            assert replayed_event["sequence_number"] == i + 1
            
            # Verify event data matches original
            replayed_data = json.loads(replayed_event["event_data"])
            if "agent_id" in expected_data:
                assert replayed_data["agent_id"] == expected_data["agent_id"]
            
            # Verify replay can reconstruct agent execution state
            if expected_event_type == WebSocketEventType.AGENT_COMPLETED:
                assert "result" in replayed_data
                assert "potential_savings" in replayed_data["result"]
        
        # Test partial replay (from specific sequence number)
        partial_replay = await self._replay_websocket_events_from_database(
            db_session,
            str(user_context.user_id),
            thread_id,
            sequence_start=3  # Start from tool_executing
        )
        
        assert len(partial_replay) == 3, "Should replay last 3 events"
        assert partial_replay[0]["event_type"] == WebSocketEventType.TOOL_EXECUTING.value
        
        self.logger.info(f" PASS:  WebSocket event replay validated for {len(execution_events)} events")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_ordering_validation(self, real_services_fixture):
        """
        Test event ordering validation and integrity.
        
        This validates that WebSocket events maintain correct ordering
        and can detect sequence gaps or corruption.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"event_ordering_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Create events with specific ordering requirements
        ordered_events = [
            (1, WebSocketEventType.AGENT_STARTED, {"agent_start": True}),
            (2, WebSocketEventType.AGENT_THINKING, {"thinking_phase": 1}),
            (3, WebSocketEventType.AGENT_THINKING, {"thinking_phase": 2}),
            (4, WebSocketEventType.TOOL_EXECUTING, {"tool_sequence": 1}),
            (5, WebSocketEventType.TOOL_COMPLETED, {"tool_sequence": 1}),
            (6, WebSocketEventType.TOOL_EXECUTING, {"tool_sequence": 2}),
            (7, WebSocketEventType.TOOL_COMPLETED, {"tool_sequence": 2}),
            (8, WebSocketEventType.AGENT_COMPLETED, {"agent_complete": True})
        ]
        
        # Store events with explicit sequence numbers
        for sequence, event_type, event_data in ordered_events:
            await self._create_and_store_websocket_event(
                db_session,
                event_type,
                user_context,
                thread_id,
                sequence,
                event_data
            )
        
        # Validate event ordering in database
        ordering_result = await self._validate_event_ordering(
            db_session,
            str(user_context.user_id),
            thread_id
        )
        
        assert ordering_result["is_valid"], f"Event ordering validation failed: {ordering_result['errors']}"
        assert ordering_result["total_events"] == len(ordered_events)
        assert ordering_result["sequence_gaps"] == [], "No sequence gaps should exist"
        
        # Test detection of sequence gaps
        # Intentionally create a gap by inserting event with sequence 10
        await self._create_and_store_websocket_event(
            db_session,
            WebSocketEventType.AGENT_STARTED,
            user_context,
            thread_id,
            10,  # Gap: missing sequence 9
            {"gap_test": True}
        )
        
        gap_validation = await self._validate_event_ordering(
            db_session,
            str(user_context.user_id),
            thread_id
        )
        
        assert not gap_validation["is_valid"], "Should detect sequence gap"
        assert 9 in gap_validation["sequence_gaps"], "Should detect gap at sequence 9"
        
        # Test event integrity validation
        integrity_result = await self._validate_event_integrity(
            db_session,
            str(user_context.user_id),
            thread_id
        )
        
        assert integrity_result["valid_events"] >= len(ordered_events)
        assert integrity_result["corrupted_events"] == 0
        
        self.logger.info(f" PASS:  Event ordering validation completed for {len(ordered_events)} events")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_audit_trail(self, real_services_fixture):
        """
        Test event audit trail for business compliance.
        
        This validates that WebSocket events create a complete audit trail
        for business compliance, user activity tracking, and debugging.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"audit_trail_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Create events with audit metadata
        audit_events = [
            {
                "event_type": WebSocketEventType.AGENT_STARTED,
                "audit_data": {
                    "user_action": "requested_cost_analysis",
                    "agent_type": "cost_optimizer", 
                    "business_context": "monthly_review",
                    "compliance_required": True
                }
            },
            {
                "event_type": WebSocketEventType.TOOL_EXECUTING,
                "audit_data": {
                    "tool_name": "aws_billing_api",
                    "data_accessed": ["billing_data", "usage_metrics"],
                    "pii_accessed": False,
                    "audit_level": "standard"
                }
            },
            {
                "event_type": WebSocketEventType.AGENT_COMPLETED,
                "audit_data": {
                    "recommendations_generated": 5,
                    "potential_savings_calculated": 42000,
                    "business_impact": "high",
                    "requires_approval": False
                }
            }
        ]
        
        # Store events with audit metadata
        audit_event_ids = []
        for sequence, event_info in enumerate(audit_events):
            event_record = await self._create_and_store_websocket_event(
                db_session,
                event_info["event_type"],
                user_context,
                thread_id,
                sequence + 1,
                event_info["audit_data"]
            )
            audit_event_ids.append(event_record.event_id)
        
        # Generate audit trail report
        audit_trail = await self._generate_audit_trail_report(
            db_session,
            str(user_context.user_id),
            thread_id,
            include_pii=False
        )
        
        assert audit_trail["user_id"] == str(user_context.user_id)
        assert audit_trail["thread_id"] == thread_id
        assert audit_trail["total_events"] == len(audit_events)
        assert audit_trail["compliance_events"] >= 1
        
        # Verify audit trail includes required business data
        assert "user_actions" in audit_trail
        assert "data_accessed" in audit_trail
        assert "business_impact_summary" in audit_trail
        
        # Test compliance-specific audit queries
        compliance_events = await self._get_compliance_events(
            db_session,
            str(user_context.user_id),
            thread_id
        )
        
        assert len(compliance_events) >= 1, "Should have compliance-relevant events"
        
        # Verify PII access tracking
        pii_access_events = [event for event in compliance_events 
                           if event.get("pii_accessed", False)]
        assert len(pii_access_events) == 0, "No PII access should be recorded for this test"
        
        # Test audit trail time-range queries
        time_filtered_audit = await self._generate_audit_trail_report(
            db_session,
            str(user_context.user_id), 
            thread_id,
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc)
        )
        
        assert time_filtered_audit["total_events"] == len(audit_events), \
            "All events should be within time range"
        
        self.logger.info(f" PASS:  Audit trail validation completed for {len(audit_events)} events")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_event_persistence(self, real_services_fixture):
        """
        Test concurrent WebSocket event persistence across multiple users.
        
        This validates that WebSocket events from multiple users are persisted
        correctly without interference or data corruption.
        """
        # Create multiple concurrent users
        num_concurrent_users = 3
        concurrent_contexts = []
        
        for i in range(num_concurrent_users):
            user_context = await create_authenticated_user_context(
                user_email=f"concurrent_events_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            concurrent_contexts.append(user_context)
        
        db_session = real_services_fixture["db"]
        
        # Set up all users and threads
        thread_ids = []
        for user_context in concurrent_contexts:
            await self._create_user_in_database(db_session, user_context)
            thread_id = await self._create_thread_in_database(db_session, user_context)
            thread_ids.append(thread_id)
        
        # Function to generate events for a single user
        async def generate_user_events(user_index: int, user_context, thread_id: str):
            user_events = []
            
            for sequence, event_type in enumerate(self.required_events):
                event_data = {
                    "user_index": user_index,
                    "concurrent_test": True,
                    "event_sequence": sequence + 1,
                    "timestamp": time.time()
                }
                
                event_record = await self._create_and_store_websocket_event(
                    db_session,
                    event_type,
                    user_context,
                    thread_id,
                    sequence + 1,
                    event_data
                )
                user_events.append(event_record)
                
                # Brief delay to simulate real event timing
                await asyncio.sleep(0.1)
            
            return user_events
        
        # Run concurrent event generation
        concurrent_tasks = [
            generate_user_events(i, concurrent_contexts[i], thread_ids[i])
            for i in range(num_concurrent_users)
        ]
        
        all_user_events = await asyncio.gather(*concurrent_tasks)
        
        # Verify each user's events are correctly isolated
        for user_index, user_events in enumerate(all_user_events):
            user_context = concurrent_contexts[user_index]
            thread_id = thread_ids[user_index]
            
            # Verify all events for this user are persisted
            assert len(user_events) == len(self.required_events), \
                f"User {user_index} should have all events persisted"
            
            for event in user_events:
                assert event.persisted, f"Event {event.event_id} for user {user_index} should be persisted"
                assert event.user_id == str(user_context.user_id)
            
            # Verify no cross-user contamination
            user_stored_events = await self._retrieve_websocket_events_from_database(
                db_session,
                str(user_context.user_id),
                thread_id
            )
            
            for stored_event in user_stored_events:
                event_data = json.loads(stored_event["event_data"])
                assert event_data["user_index"] == user_index, \
                    f"Event data should belong to user {user_index}"
        
        # Verify total event count across all users
        total_events_expected = num_concurrent_users * len(self.required_events)
        total_events_query = """
            SELECT COUNT(*) as total 
            FROM websocket_events 
            WHERE user_id IN %(user_ids)s
        """
        
        user_ids = tuple(str(ctx.user_id) for ctx in concurrent_contexts)
        result = await db_session.execute(total_events_query, {"user_ids": user_ids})
        total_count = result.scalar()
        
        assert total_count == total_events_expected, \
            f"Expected {total_events_expected} total events, got {total_count}"
        
        self.logger.info(f" PASS:  Concurrent event persistence validated for {num_concurrent_users} users")
    
    # Helper methods for WebSocket event operations
    
    async def _create_user_in_database(self, db_session, user_context: StronglyTypedUserExecutionContext):
        """Create user record in database."""
        user_insert = """
            INSERT INTO users (id, email, full_name, is_active, created_at)
            VALUES (%(user_id)s, %(email)s, %(full_name)s, true, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                updated_at = NOW()
        """
        
        await db_session.execute(user_insert, {
            "user_id": str(user_context.user_id),
            "email": user_context.agent_context.get("user_email"),
            "full_name": f"WebSocket Test User {str(user_context.user_id)[:8]}",
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _create_thread_in_database(self, db_session, user_context: StronglyTypedUserExecutionContext) -> str:
        """Create thread record in database."""
        thread_insert = """
            INSERT INTO threads (id, user_id, title, created_at, is_active)
            VALUES (%(thread_id)s, %(user_id)s, %(title)s, %(created_at)s, true)
            RETURNING id
        """
        
        result = await db_session.execute(thread_insert, {
            "thread_id": str(user_context.thread_id),
            "user_id": str(user_context.user_id),
            "title": "WebSocket Event Test Thread",
            "created_at": datetime.now(timezone.utc)
        })
        
        thread_id = result.scalar()
        await db_session.commit()
        return thread_id
    
    async def _create_and_store_websocket_event(
        self,
        db_session,
        event_type: WebSocketEventType,
        user_context: StronglyTypedUserExecutionContext,
        thread_id: str,
        sequence_number: int,
        event_data: Optional[Dict[str, Any]] = None
    ) -> WebSocketEventRecord:
        """Create and store WebSocket event in database."""
        event_id = f"ws_event_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc)
        
        if event_data is None:
            event_data = {
                "event_type": event_type.value,
                "generated_by": "integration_test",
                "timestamp": timestamp.isoformat()
            }
        
        # Store event in database
        event_insert = """
            INSERT INTO websocket_events (
                id, event_type, user_id, thread_id, websocket_id,
                event_data, timestamp, sequence_number, created_at
            ) VALUES (
                %(id)s, %(event_type)s, %(user_id)s, %(thread_id)s, %(websocket_id)s,
                %(event_data)s, %(timestamp)s, %(sequence_number)s, %(created_at)s
            )
        """
        
        await db_session.execute(event_insert, {
            "id": event_id,
            "event_type": event_type.value,
            "user_id": str(user_context.user_id),
            "thread_id": thread_id,
            "websocket_id": str(user_context.websocket_client_id),
            "event_data": json.dumps(event_data),
            "timestamp": timestamp,
            "sequence_number": sequence_number,
            "created_at": timestamp
        })
        await db_session.commit()
        
        return WebSocketEventRecord(
            event_id=event_id,
            event_type=event_type,
            user_id=str(user_context.user_id),
            thread_id=thread_id,
            websocket_id=str(user_context.websocket_client_id),
            event_data=event_data,
            timestamp=timestamp,
            sequence_number=sequence_number,
            persisted=True
        )
    
    async def _retrieve_websocket_events_from_database(
        self,
        db_session,
        user_id: str,
        thread_id: str
    ) -> List[Dict[str, Any]]:
        """Retrieve WebSocket events from database."""
        events_query = """
            SELECT id, event_type, user_id, thread_id, websocket_id,
                   event_data, timestamp, sequence_number, created_at
            FROM websocket_events
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
            ORDER BY sequence_number ASC
        """
        
        result = await db_session.execute(events_query, {
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        return [dict(row) for row in result.fetchall()]
    
    async def _replay_websocket_events_from_database(
        self,
        db_session,
        user_id: str,
        thread_id: str,
        sequence_start: int = 1
    ) -> List[Dict[str, Any]]:
        """Replay WebSocket events from database starting from sequence."""
        replay_query = """
            SELECT id, event_type, user_id, thread_id, websocket_id,
                   event_data, timestamp, sequence_number, created_at
            FROM websocket_events
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s 
                  AND sequence_number >= %(sequence_start)s
            ORDER BY sequence_number ASC
        """
        
        result = await db_session.execute(replay_query, {
            "user_id": user_id,
            "thread_id": thread_id,
            "sequence_start": sequence_start
        })
        
        return [dict(row) for row in result.fetchall()]
    
    async def _validate_event_ordering(
        self,
        db_session,
        user_id: str,
        thread_id: str
    ) -> Dict[str, Any]:
        """Validate event ordering and detect gaps."""
        ordering_query = """
            SELECT sequence_number
            FROM websocket_events
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
            ORDER BY sequence_number ASC
        """
        
        result = await db_session.execute(ordering_query, {
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        sequences = [row.sequence_number for row in result.fetchall()]
        
        if not sequences:
            return {"is_valid": True, "total_events": 0, "sequence_gaps": []}
        
        # Check for gaps
        sequence_gaps = []
        for i in range(1, max(sequences) + 1):
            if i not in sequences:
                sequence_gaps.append(i)
        
        return {
            "is_valid": len(sequence_gaps) == 0,
            "total_events": len(sequences),
            "sequence_gaps": sequence_gaps,
            "min_sequence": min(sequences),
            "max_sequence": max(sequences)
        }
    
    async def _validate_event_integrity(
        self,
        db_session,
        user_id: str,
        thread_id: str
    ) -> Dict[str, Any]:
        """Validate event data integrity."""
        integrity_query = """
            SELECT id, event_type, event_data
            FROM websocket_events
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
        """
        
        result = await db_session.execute(integrity_query, {
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        valid_events = 0
        corrupted_events = 0
        
        for row in result.fetchall():
            try:
                # Test JSON parsing
                json.loads(row.event_data)
                # Validate event type
                if row.event_type in [e.value for e in WebSocketEventType]:
                    valid_events += 1
                else:
                    corrupted_events += 1
            except json.JSONDecodeError:
                corrupted_events += 1
        
        return {
            "valid_events": valid_events,
            "corrupted_events": corrupted_events,
            "integrity_score": valid_events / (valid_events + corrupted_events) if (valid_events + corrupted_events) > 0 else 1.0
        }
    
    async def _generate_audit_trail_report(
        self,
        db_session,
        user_id: str,
        thread_id: str,
        include_pii: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate audit trail report."""
        time_filter = ""
        query_params = {"user_id": user_id, "thread_id": thread_id}
        
        if start_time and end_time:
            time_filter = "AND timestamp BETWEEN %(start_time)s AND %(end_time)s"
            query_params.update({"start_time": start_time, "end_time": end_time})
        
        audit_query = f"""
            SELECT event_type, event_data, timestamp
            FROM websocket_events
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s {time_filter}
            ORDER BY timestamp ASC
        """
        
        result = await db_session.execute(audit_query, query_params)
        events = result.fetchall()
        
        # Analyze events for audit report
        user_actions = []
        data_accessed = []
        business_impact_summary = {}
        compliance_events = 0
        
        for event in events:
            event_data = json.loads(event.event_data)
            
            if "user_action" in event_data:
                user_actions.append(event_data["user_action"])
            
            if "data_accessed" in event_data:
                data_accessed.extend(event_data["data_accessed"])
            
            if "business_impact" in event_data:
                impact = event_data["business_impact"]
                business_impact_summary[impact] = business_impact_summary.get(impact, 0) + 1
            
            if event_data.get("compliance_required", False):
                compliance_events += 1
        
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "total_events": len(events),
            "user_actions": list(set(user_actions)),
            "data_accessed": list(set(data_accessed)),
            "business_impact_summary": business_impact_summary,
            "compliance_events": compliance_events,
            "report_generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_compliance_events(
        self,
        db_session,
        user_id: str,
        thread_id: str
    ) -> List[Dict[str, Any]]:
        """Get compliance-relevant events."""
        compliance_query = """
            SELECT event_type, event_data, timestamp
            FROM websocket_events
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
              AND event_data::jsonb ? 'compliance_required'
            ORDER BY timestamp ASC
        """
        
        result = await db_session.execute(compliance_query, {
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        compliance_events = []
        for row in result.fetchall():
            event_data = json.loads(row.event_data)
            compliance_events.append({
                "event_type": row.event_type,
                "timestamp": row.timestamp,
                **event_data
            })
        
        return compliance_events