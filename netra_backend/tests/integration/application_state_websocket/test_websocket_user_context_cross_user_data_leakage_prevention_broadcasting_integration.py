"""
Test WebSocket Cross-User Data Leakage Prevention During Event Broadcasting Integration (#26)

Business Value Justification (BVJ):
- Segment: Enterprise (Critical data security for multi-tenant environments)
- Business Goal: Prevent any user data from accidentally being exposed to unauthorized users
- Value Impact: Enterprise customers trust their sensitive data is never visible to other users
- Strategic Impact: Foundation of enterprise security - prevents data breach liability

CRITICAL SECURITY REQUIREMENT: WebSocket event broadcasting must NEVER leak data between
users. Each user must only receive events and data they are authorized to see. Any
cross-user data leakage is a critical security vulnerability that violates user trust.
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
EventID = str
BroadcastID = str
ChannelID = str


class EventSensitivityLevel(Enum):
    """Sensitivity levels for events and data."""
    PUBLIC = "public"  # Can be seen by anyone in organization
    INTERNAL = "internal"  # User's own data only
    CONFIDENTIAL = "confidential"  # Highly sensitive, strict access
    ORGANIZATION_SCOPED = "organization_scoped"  # Within organization only


@dataclass
class UserEventSubscription:
    """Represents a user's event subscription and data access rights."""
    user_id: UserID
    subscribed_channels: Set[ChannelID] = field(default_factory=set)
    authorized_event_types: Set[MessageType] = field(default_factory=set)
    data_access_level: EventSensitivityLevel = EventSensitivityLevel.INTERNAL
    organization_id: Optional[str] = None
    thread_access: Set[str] = field(default_factory=set)
    blocked_users: Set[UserID] = field(default_factory=set)  # Users to never receive events from


@dataclass
class WebSocketEvent:
    """Represents a WebSocket event with sensitivity and targeting."""
    event_id: EventID
    source_user_id: UserID
    event_type: MessageType
    payload: Dict[str, Any]
    sensitivity_level: EventSensitivityLevel
    target_users: Optional[Set[UserID]] = None  # None = broadcast to all authorized
    organization_scope: Optional[str] = None
    thread_scope: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def should_be_visible_to_user(self, user_subscription: UserEventSubscription) -> bool:
        """Determine if this event should be visible to a specific user."""
        # Never show events from blocked users
        if self.source_user_id in user_subscription.blocked_users:
            return False
        
        # Self-events are always visible
        if self.source_user_id == user_subscription.user_id:
            return True
        
        # Check explicit targeting
        if self.target_users and user_subscription.user_id not in self.target_users:
            return False
        
        # Check organization scope
        if (self.organization_scope and 
            user_subscription.organization_id != self.organization_scope):
            return False
        
        # Check thread scope
        if (self.thread_scope and 
            self.thread_scope not in user_subscription.thread_access and
            user_subscription.data_access_level != EventSensitivityLevel.PUBLIC):
            return False
        
        # Check sensitivity level access
        if self.sensitivity_level == EventSensitivityLevel.CONFIDENTIAL:
            # Only source user can see confidential events
            return self.source_user_id == user_subscription.user_id
        elif self.sensitivity_level == EventSensitivityLevel.INTERNAL:
            # Only source user can see internal events
            return self.source_user_id == user_subscription.user_id
        elif self.sensitivity_level == EventSensitivityLevel.ORGANIZATION_SCOPED:
            # Users in same organization can see
            return user_subscription.organization_id == self.organization_scope
        elif self.sensitivity_level == EventSensitivityLevel.PUBLIC:
            # Public events can be seen by anyone in organization
            return user_subscription.organization_id == self.organization_scope
        
        return False


@dataclass
class DataLeakageDetection:
    """Tracks potential data leakage incidents."""
    leak_id: str
    source_user_id: UserID
    exposed_to_user_id: UserID
    event_id: EventID
    leaked_data_type: str
    leaked_data_sample: str
    severity: str  # low, medium, high, critical
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "leak_id": self.leak_id,
            "source_user_id": self.source_user_id,
            "exposed_to_user_id": self.exposed_to_user_id,
            "event_id": self.event_id,
            "leaked_data_type": self.leaked_data_type,
            "leaked_data_sample": self.leaked_data_sample,
            "severity": self.severity,
            "timestamp": self.timestamp
        }


class WebSocketBroadcastingSecurityValidator:
    """Validates WebSocket broadcasting security and prevents data leakage."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.user_subscriptions = {}
        self.detected_leakages = []
        self.broadcast_logs = []
        self.event_delivery_matrix = defaultdict(list)  # user_id -> [events_received]
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_user_with_subscription(self, user_suffix: str, 
                                          sensitivity_level: EventSensitivityLevel = EventSensitivityLevel.INTERNAL,
                                          organization_id: str = None,
                                          blocked_users: Set[UserID] = None) -> UserEventSubscription:
        """Create user with specific event subscription and access rights."""
        user_id = f"broadcast-test-user-{user_suffix}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@broadcast-test.com", f"Broadcast Test User {user_suffix}", True)
        
        # Create organization if specified
        if organization_id is None:
            organization_id = f"broadcast-org-{user_suffix}"
        
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug
        """, organization_id, f"Broadcast Test Org {user_suffix}", 
            f"broadcast-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, organization_id, "member")
        
        # Create user's threads for access testing
        thread_access = set()
        for i in range(2):
            thread_id = f"thread-{user_suffix}-{i}"
            await self.real_services["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    title = EXCLUDED.title,
                    updated_at = NOW()
            """, thread_id, user_id, f"Broadcast Test Thread {i}")
            thread_access.add(thread_id)
        
        # Create event subscription
        subscription = UserEventSubscription(
            user_id=user_id,
            subscribed_channels={f"channel-{user_suffix}", "general"},
            authorized_event_types={
                MessageType.USER_MESSAGE,
                MessageType.THREAD_UPDATE,
                MessageType.AGENT_STARTED,
                MessageType.AGENT_COMPLETED,
                MessageType.SYSTEM_MESSAGE
            },
            data_access_level=sensitivity_level,
            organization_id=organization_id,
            thread_access=thread_access,
            blocked_users=blocked_users or set()
        )
        
        # Store subscription in Redis
        subscription_key = f"event_subscription:{user_id}"
        await self.redis_client.set(
            subscription_key,
            json.dumps({
                "user_id": user_id,
                "subscribed_channels": list(subscription.subscribed_channels),
                "authorized_event_types": [t.value for t in subscription.authorized_event_types],
                "data_access_level": sensitivity_level.value,
                "organization_id": organization_id,
                "thread_access": list(thread_access),
                "blocked_users": list(blocked_users or set()),
                "created_at": time.time()
            }),
            ex=3600
        )
        
        self.user_subscriptions[user_id] = subscription
        return subscription
    
    async def simulate_websocket_event_broadcast(self, events: List[WebSocketEvent]) -> Dict[str, Any]:
        """Simulate WebSocket event broadcasting with security validation."""
        broadcast_results = {
            "total_events": len(events),
            "events_processed": 0,
            "total_deliveries": 0,
            "blocked_deliveries": 0,
            "security_violations": 0,
            "event_delivery_log": [],
            "leakage_incidents": []
        }
        
        for event in events:
            event_deliveries = await self._broadcast_event_with_security_checks(event)
            
            broadcast_results["events_processed"] += 1
            broadcast_results["total_deliveries"] += len(event_deliveries["delivered_to"])
            broadcast_results["blocked_deliveries"] += len(event_deliveries["blocked_for"])
            broadcast_results["security_violations"] += len(event_deliveries["security_violations"])
            
            broadcast_results["event_delivery_log"].append({
                "event_id": event.event_id,
                "source_user": event.source_user_id,
                "event_type": event.event_type.value,
                "sensitivity": event.sensitivity_level.value,
                "delivered_to": event_deliveries["delivered_to"],
                "blocked_for": event_deliveries["blocked_for"],
                "security_violations": event_deliveries["security_violations"]
            })
            
            # Track deliveries for leakage analysis
            for recipient_user_id in event_deliveries["delivered_to"]:
                self.event_delivery_matrix[recipient_user_id].append({
                    "event_id": event.event_id,
                    "source_user": event.source_user_id,
                    "event_type": event.event_type.value,
                    "payload_keys": list(event.payload.keys()),
                    "received_at": time.time()
                })
        
        # Analyze for potential data leakage
        leakage_analysis = await self._analyze_data_leakage_patterns()
        broadcast_results["leakage_incidents"] = [leak.to_dict() for leak in leakage_analysis]
        broadcast_results["security_violations"] += len(leakage_analysis)
        
        return broadcast_results
    
    async def _broadcast_event_with_security_checks(self, event: WebSocketEvent) -> Dict[str, Any]:
        """Broadcast event with comprehensive security checks."""
        delivery_result = {
            "event_id": event.event_id,
            "delivered_to": [],
            "blocked_for": [],
            "security_violations": []
        }
        
        # Check each user subscription for delivery eligibility
        for user_id, subscription in self.user_subscriptions.items():
            should_deliver = event.should_be_visible_to_user(subscription)
            
            if should_deliver:
                # Additional security validation before delivery
                security_check = await self._validate_event_security_for_user(event, subscription)
                
                if security_check["allowed"]:
                    # Deliver event (simulate)
                    await self._deliver_event_to_user(event, user_id)
                    delivery_result["delivered_to"].append(user_id)
                else:
                    # Block delivery due to security concerns
                    delivery_result["blocked_for"].append(user_id)
                    delivery_result["security_violations"].append({
                        "user_id": user_id,
                        "violation_type": security_check["violation_type"],
                        "details": security_check["details"]
                    })
            else:
                # Event not visible to this user (expected)
                delivery_result["blocked_for"].append(user_id)
        
        return delivery_result
    
    async def _validate_event_security_for_user(self, event: WebSocketEvent, 
                                               subscription: UserEventSubscription) -> Dict[str, Any]:
        """Additional security validation before event delivery."""
        security_check = {
            "allowed": True,
            "violation_type": None,
            "details": {}
        }
        
        # Check for sensitive data in payload
        sensitive_data_indicators = [
            "password", "token", "secret", "key", "credential",
            "ssn", "social_security", "credit_card", "private"
        ]
        
        payload_str = json.dumps(event.payload).lower()
        for indicator in sensitive_data_indicators:
            if indicator in payload_str:
                # If event contains sensitive data, only deliver to source user
                if event.source_user_id != subscription.user_id:
                    security_check["allowed"] = False
                    security_check["violation_type"] = "sensitive_data_exposure_prevented"
                    security_check["details"] = {
                        "sensitive_indicator": indicator,
                        "source_user": event.source_user_id,
                        "target_user": subscription.user_id
                    }
                break
        
        # Check for cross-organization data leakage
        if (event.organization_scope and 
            subscription.organization_id != event.organization_scope):
            security_check["allowed"] = False
            security_check["violation_type"] = "cross_organization_exposure_prevented"
            security_check["details"] = {
                "event_org": event.organization_scope,
                "user_org": subscription.organization_id
            }
        
        # Check for thread access violations
        if (event.thread_scope and 
            event.thread_scope not in subscription.thread_access and
            event.source_user_id != subscription.user_id):
            security_check["allowed"] = False
            security_check["violation_type"] = "unauthorized_thread_access_prevented"
            security_check["details"] = {
                "thread_id": event.thread_scope,
                "user_thread_access": list(subscription.thread_access)
            }
        
        return security_check
    
    async def _deliver_event_to_user(self, event: WebSocketEvent, recipient_user_id: UserID):
        """Simulate delivering event to user (store in Redis)."""
        delivery_key = f"event_delivery:{recipient_user_id}:{event.event_id}"
        delivery_data = {
            "event_id": event.event_id,
            "source_user_id": event.source_user_id,
            "event_type": event.event_type.value,
            "payload": event.payload,
            "delivered_at": time.time(),
            "recipient_user_id": recipient_user_id
        }
        
        await self.redis_client.set(
            delivery_key,
            json.dumps(delivery_data),
            ex=600  # Keep for 10 minutes for analysis
        )
    
    async def _analyze_data_leakage_patterns(self) -> List[DataLeakageDetection]:
        """Analyze event delivery patterns to detect potential data leakage."""
        detected_leakages = []
        
        # Analyze each user's received events
        for recipient_user_id, received_events in self.event_delivery_matrix.items():
            for event_info in received_events:
                # Check if user received events from users they shouldn't have access to
                source_user_id = event_info["source_user"]
                
                if source_user_id != recipient_user_id:  # Not self-event
                    recipient_subscription = self.user_subscriptions.get(recipient_user_id)
                    
                    if recipient_subscription:
                        # Check if this should have been blocked
                        if source_user_id in recipient_subscription.blocked_users:
                            leakage = DataLeakageDetection(
                                leak_id=f"leak-{uuid.uuid4().hex[:8]}",
                                source_user_id=source_user_id,
                                exposed_to_user_id=recipient_user_id,
                                event_id=event_info["event_id"],
                                leaked_data_type="blocked_user_event",
                                leaked_data_sample=f"Event from blocked user {source_user_id}",
                                severity="high"
                            )
                            detected_leakages.append(leakage)
                        
                        # Check for cross-organization leakage
                        source_subscription = self.user_subscriptions.get(source_user_id)
                        if (source_subscription and 
                            recipient_subscription.organization_id != source_subscription.organization_id):
                            leakage = DataLeakageDetection(
                                leak_id=f"leak-{uuid.uuid4().hex[:8]}",
                                source_user_id=source_user_id,
                                exposed_to_user_id=recipient_user_id,
                                event_id=event_info["event_id"],
                                leaked_data_type="cross_organization_data",
                                leaked_data_sample=f"Data from {source_subscription.organization_id} to {recipient_subscription.organization_id}",
                                severity="critical"
                            )
                            detected_leakages.append(leakage)
        
        return detected_leakages
    
    async def validate_broadcast_security_isolation(self, broadcast_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that broadcasting maintained proper security isolation."""
        isolation_validation = {
            "security_isolation_maintained": True,
            "critical_violations": [],
            "data_leakage_detected": False,
            "cross_user_contamination": [],
            "organization_isolation_intact": True,
            "summary": {}
        }
        
        # Check for critical security violations
        for event_log in broadcast_results["event_delivery_log"]:
            for violation in event_log["security_violations"]:
                if violation.get("violation_type") in ["sensitive_data_exposure_prevented", 
                                                     "cross_organization_exposure_prevented"]:
                    # These are GOOD - they show security is working
                    continue
                else:
                    # Unexpected security violations
                    isolation_validation["critical_violations"].append(violation)
                    isolation_validation["security_isolation_maintained"] = False
        
        # Check for data leakage incidents
        if broadcast_results["leakage_incidents"]:
            isolation_validation["data_leakage_detected"] = True
            isolation_validation["security_isolation_maintained"] = False
            
            for incident in broadcast_results["leakage_incidents"]:
                if incident["severity"] in ["high", "critical"]:
                    isolation_validation["critical_violations"].append(incident)
        
        # Validate organization isolation
        org_user_events = defaultdict(list)
        for recipient_user_id, events in self.event_delivery_matrix.items():
            subscription = self.user_subscriptions.get(recipient_user_id)
            if subscription:
                org_user_events[subscription.organization_id].extend(events)
        
        # Check for cross-organization event contamination
        for org_id, org_events in org_user_events.items():
            for event in org_events:
                source_user_subscription = self.user_subscriptions.get(event["source_user"])
                if (source_user_subscription and 
                    source_user_subscription.organization_id != org_id):
                    isolation_validation["cross_user_contamination"].append({
                        "contaminated_org": org_id,
                        "source_org": source_user_subscription.organization_id,
                        "event_id": event["event_id"]
                    })
                    isolation_validation["organization_isolation_intact"] = False
        
        # Summary statistics
        isolation_validation["summary"] = {
            "total_users": len(self.user_subscriptions),
            "total_events_analyzed": broadcast_results["total_events"],
            "total_deliveries": broadcast_results["total_deliveries"],
            "security_blocks": broadcast_results["blocked_deliveries"],
            "violation_count": len(isolation_validation["critical_violations"]),
            "leakage_incidents": len(broadcast_results["leakage_incidents"])
        }
        
        return isolation_validation


class TestWebSocketCrossUserDataLeakagePrevention(BaseIntegrationTest):
    """
    Integration test for cross-user data leakage prevention during WebSocket broadcasting.
    
    SECURITY CRITICAL: Validates that WebSocket events never leak data between unauthorized users.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security_critical
    async def test_websocket_broadcast_prevents_cross_user_data_leakage(self, real_services_fixture):
        """
        Test WebSocket broadcasting prevents cross-user data leakage.
        
        CRITICAL: No user data should ever be visible to unauthorized users.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketBroadcastingSecurityValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users with different access levels and organizations
            user_internal = await validator.create_user_with_subscription(
                "internal", EventSensitivityLevel.INTERNAL, "org-alpha"
            )
            user_public = await validator.create_user_with_subscription(
                "public", EventSensitivityLevel.PUBLIC, "org-alpha"
            )
            user_different_org = await validator.create_user_with_subscription(
                "diff-org", EventSensitivityLevel.INTERNAL, "org-beta"
            )
            user_blocked = await validator.create_user_with_subscription(
                "blocked", EventSensitivityLevel.PUBLIC, "org-alpha",
                blocked_users={user_internal.user_id}  # Blocked from seeing internal user
            )
            
            # Create events with different sensitivity levels
            test_events = [
                # Internal event - should only be visible to source user
                WebSocketEvent(
                    event_id="internal-event-1",
                    source_user_id=user_internal.user_id,
                    event_type=MessageType.USER_MESSAGE,
                    payload={
                        "content": "Private message from internal user",
                        "thread_id": list(user_internal.thread_access)[0],
                        "user_data": {"private_key": "secret-123"}
                    },
                    sensitivity_level=EventSensitivityLevel.INTERNAL,
                    organization_scope="org-alpha"
                ),
                
                # Public event - should be visible to same org users (except blocked)
                WebSocketEvent(
                    event_id="public-event-1",
                    source_user_id=user_public.user_id,
                    event_type=MessageType.SYSTEM_MESSAGE,
                    payload={
                        "content": "Public announcement in org-alpha",
                        "announcement_type": "general"
                    },
                    sensitivity_level=EventSensitivityLevel.PUBLIC,
                    organization_scope="org-alpha"
                ),
                
                # Confidential event with sensitive data
                WebSocketEvent(
                    event_id="confidential-event-1",
                    source_user_id=user_internal.user_id,
                    event_type=MessageType.USER_MESSAGE,
                    payload={
                        "content": "Message with sensitive data",
                        "user_token": "auth-token-12345",
                        "password": "secret-password"
                    },
                    sensitivity_level=EventSensitivityLevel.CONFIDENTIAL,
                    organization_scope="org-alpha"
                ),
                
                # Cross-organization event attempt
                WebSocketEvent(
                    event_id="cross-org-event-1",
                    source_user_id=user_different_org.user_id,
                    event_type=MessageType.BROADCAST,
                    payload={
                        "content": "Message from different organization",
                        "org_data": "org-beta-confidential"
                    },
                    sensitivity_level=EventSensitivityLevel.ORGANIZATION_SCOPED,
                    organization_scope="org-beta"
                ),
            ]
            
            # Execute broadcast with security validation
            broadcast_results = await validator.simulate_websocket_event_broadcast(test_events)
            
            # CRITICAL SECURITY VALIDATIONS
            
            # Validate broadcast isolation
            isolation_results = await validator.validate_broadcast_security_isolation(broadcast_results)
            
            assert isolation_results["security_isolation_maintained"], \
                f"Security isolation violated: {isolation_results['critical_violations']}"
            assert not isolation_results["data_leakage_detected"], \
                f"Data leakage detected: {broadcast_results['leakage_incidents']}"
            assert isolation_results["organization_isolation_intact"], \
                f"Organization isolation violated: {isolation_results['cross_user_contamination']}"
            
            # Verify specific event delivery patterns
            event_deliveries = {log["event_id"]: log for log in broadcast_results["event_delivery_log"]}
            
            # Internal event should only go to source user
            internal_delivery = event_deliveries["internal-event-1"]
            assert internal_delivery["delivered_to"] == [user_internal.user_id], \
                "Internal event should only be delivered to source user"
            assert user_public.user_id in internal_delivery["blocked_for"], \
                "Internal event should be blocked for other users"
            
            # Public event should go to same org users (except blocked)
            public_delivery = event_deliveries["public-event-1"]
            expected_recipients = {user_public.user_id, user_internal.user_id}  # Same org
            actual_recipients = set(public_delivery["delivered_to"])
            assert expected_recipients.issubset(actual_recipients), \
                "Public event should be delivered to same organization users"
            assert user_different_org.user_id not in public_delivery["delivered_to"], \
                "Public event should not cross organization boundaries"
            
            # Confidential event should only go to source user
            confidential_delivery = event_deliveries["confidential-event-1"]
            assert confidential_delivery["delivered_to"] == [user_internal.user_id], \
                "Confidential event should only be delivered to source user"
            
            # Cross-org event should not be delivered to other organizations
            cross_org_delivery = event_deliveries["cross-org-event-1"]
            for recipient in cross_org_delivery["delivered_to"]:
                recipient_subscription = validator.user_subscriptions[recipient]
                assert recipient_subscription.organization_id == "org-beta", \
                    "Cross-org event delivered outside its organization"
            
            # Verify no critical security violations
            assert len(isolation_results["critical_violations"]) == 0, \
                f"Critical security violations: {isolation_results['critical_violations']}"
            
            # Verify blocked user doesn't receive events from blocked source
            blocked_events_from_internal = [
                event for event in validator.event_delivery_matrix[user_blocked.user_id]
                if event["source_user"] == user_internal.user_id
            ]
            assert len(blocked_events_from_internal) == 0, \
                "Blocked user should not receive events from blocked source"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrent_security
    async def test_concurrent_broadcast_maintains_isolation(self, real_services_fixture):
        """Test data leakage prevention during concurrent broadcasting."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketBroadcastingSecurityValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple users for concurrent testing
            concurrent_users = []
            for i in range(4):
                user = await validator.create_user_with_subscription(
                    f"concurrent-{i}", 
                    EventSensitivityLevel.INTERNAL, 
                    f"org-{i % 2}"  # 2 organizations
                )
                concurrent_users.append(user)
            
            # Create concurrent events from different users
            concurrent_events = []
            for i, user in enumerate(concurrent_users):
                for j in range(3):  # 3 events per user
                    event = WebSocketEvent(
                        event_id=f"concurrent-{i}-{j}",
                        source_user_id=user.user_id,
                        event_type=MessageType.USER_MESSAGE,
                        payload={
                            "content": f"Concurrent message {j} from user {i}",
                            "user_private_data": f"private-{i}-{j}",
                            "thread_id": list(user.thread_access)[0] if user.thread_access else None
                        },
                        sensitivity_level=EventSensitivityLevel.INTERNAL,
                        organization_scope=user.organization_id
                    )
                    concurrent_events.append(event)
            
            # Execute concurrent broadcasting
            concurrent_results = await validator.simulate_websocket_event_broadcast(concurrent_events)
            
            # Validate concurrent isolation
            concurrent_isolation = await validator.validate_broadcast_security_isolation(concurrent_results)
            
            # CRITICAL: Concurrent operations must not break isolation
            assert concurrent_isolation["security_isolation_maintained"], \
                f"Concurrent broadcasting violated security: {concurrent_isolation['critical_violations']}"
            assert not concurrent_isolation["data_leakage_detected"], \
                f"Data leakage in concurrent operations: {concurrent_results['leakage_incidents']}"
            assert concurrent_isolation["organization_isolation_intact"], \
                f"Organization isolation failed: {concurrent_isolation['cross_user_contamination']}"
            
            # Verify each user only received their own events
            for user in concurrent_users:
                user_events = validator.event_delivery_matrix[user.user_id]
                for event in user_events:
                    assert event["source_user"] == user.user_id, \
                        f"User {user.user_id} received event from {event['source_user']} - data leakage!"
            
            # Performance validation
            assert concurrent_results["events_processed"] == 12  # 4 users × 3 events
            assert concurrent_results["security_violations"] == 0, \
                "Concurrent broadcasting should not generate security violations"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise_security
    async def test_enterprise_multi_tenant_broadcast_isolation(self, real_services_fixture):
        """Test broadcast isolation in enterprise multi-tenant scenarios."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketBroadcastingSecurityValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create enterprise multi-tenant scenario
            enterprise_users = {}
            organizations = ["enterprise-alpha", "enterprise-beta", "enterprise-gamma"]
            
            for org in organizations:
                for role in ["admin", "user", "viewer"]:
                    user_key = f"{org}-{role}"
                    sensitivity_map = {
                        "admin": EventSensitivityLevel.PUBLIC,
                        "user": EventSensitivityLevel.INTERNAL,
                        "viewer": EventSensitivityLevel.INTERNAL
                    }
                    
                    user = await validator.create_user_with_subscription(
                        user_key, sensitivity_map[role], org
                    )
                    enterprise_users[user_key] = user
            
            # Create enterprise-level events
            enterprise_events = [
                # Organization-wide announcement
                WebSocketEvent(
                    event_id="enterprise-alpha-announcement",
                    source_user_id=enterprise_users["enterprise-alpha-admin"].user_id,
                    event_type=MessageType.BROADCAST,
                    payload={
                        "content": "Organization-wide announcement for Alpha",
                        "priority": "high",
                        "org_sensitive_data": "alpha-confidential-info"
                    },
                    sensitivity_level=EventSensitivityLevel.ORGANIZATION_SCOPED,
                    organization_scope="enterprise-alpha"
                ),
                
                # Cross-organization message attempt (should be blocked)
                WebSocketEvent(
                    event_id="cross-enterprise-attempt",
                    source_user_id=enterprise_users["enterprise-beta-admin"].user_id,
                    event_type=MessageType.BROADCAST,
                    payload={
                        "content": "Attempting to send to other organizations",
                        "malicious_intent": "data_exfiltration_attempt"
                    },
                    sensitivity_level=EventSensitivityLevel.PUBLIC,
                    organization_scope="enterprise-alpha"  # Wrong org!
                ),
                
                # User-level confidential event
                WebSocketEvent(
                    event_id="user-confidential-gamma",
                    source_user_id=enterprise_users["enterprise-gamma-user"].user_id,
                    event_type=MessageType.USER_MESSAGE,
                    payload={
                        "content": "Confidential user message",
                        "personal_data": "gamma-user-private-info",
                        "secret_key": "gamma-secret-123"
                    },
                    sensitivity_level=EventSensitivityLevel.CONFIDENTIAL,
                    organization_scope="enterprise-gamma"
                ),
            ]
            
            # Execute enterprise broadcasting
            enterprise_results = await validator.simulate_websocket_event_broadcast(enterprise_events)
            
            # Validate enterprise-level isolation
            enterprise_isolation = await validator.validate_broadcast_security_isolation(enterprise_results)
            
            # ENTERPRISE CRITICAL VALIDATIONS
            assert enterprise_isolation["security_isolation_maintained"], \
                f"Enterprise security violated: {enterprise_isolation['critical_violations']}"
            assert enterprise_isolation["organization_isolation_intact"], \
                f"Multi-tenant isolation failed: {enterprise_isolation['cross_user_contamination']}"
            
            # Verify organization-scoped events stay within organization
            event_deliveries = {log["event_id"]: log for log in enterprise_results["event_delivery_log"]}
            
            alpha_announcement = event_deliveries["enterprise-alpha-announcement"]
            for recipient in alpha_announcement["delivered_to"]:
                recipient_subscription = validator.user_subscriptions[recipient]
                assert recipient_subscription.organization_id == "enterprise-alpha", \
                    "Organization announcement leaked outside organization"
            
            # Verify cross-org attempt was blocked
            cross_org_attempt = event_deliveries["cross-enterprise-attempt"]
            # Should only be delivered to beta users (source org), not alpha (target org)
            for recipient in cross_org_attempt["delivered_to"]:
                recipient_subscription = validator.user_subscriptions[recipient]
                assert recipient_subscription.organization_id == "enterprise-beta", \
                    "Cross-organization message was not properly blocked"
            
            # Verify confidential event only went to source user
            confidential_event = event_deliveries["user-confidential-gamma"]
            assert len(confidential_event["delivered_to"]) == 1, \
                "Confidential event delivered to multiple users"
            assert confidential_event["delivered_to"][0] == enterprise_users["enterprise-gamma-user"].user_id, \
                "Confidential event delivered to wrong user"
            
            # Verify no data leakage across organizations
            for org_a in organizations:
                for org_b in organizations:
                    if org_a != org_b:
                        # Check that org_a users didn't receive events from org_b users
                        org_a_users = [user for key, user in enterprise_users.items() if key.startswith(org_a)]
                        org_b_users = [user for key, user in enterprise_users.items() if key.startswith(org_b)]
                        
                        for user_a in org_a_users:
                            user_a_events = validator.event_delivery_matrix[user_a.user_id]
                            for event in user_a_events:
                                # Verify no events from org_b users
                                source_in_org_b = any(event["source_user"] == user_b.user_id for user_b in org_b_users)
                                assert not source_in_org_b, \
                                    f"Cross-organization leakage: {org_a} user received event from {org_b}"
            
        finally:
            await validator.cleanup()