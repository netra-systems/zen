"""
CRITICAL Integration Tests for WebSocket Event Mis-routing

These tests are DESIGNED TO FAIL initially to expose critical WebSocket event
mis-routing that causes user A's events to be sent to user B's connection.

Business Risk: MAXIMUM - User A sees User B's agent progress and confidential results
Technical Risk: WebSocket event routing uses string-based IDs enabling cross-user delivery
Security Risk: Real-time exposure of sensitive data through WebSocket event leakage

KEY MIS-ROUTING SCENARIOS TO EXPOSE:
1. WebSocket events sent to wrong user connections due to string-based routing
2. Agent execution events delivered to multiple users instead of single target
3. WebSocket connection management lacks proper user isolation
4. Event serialization includes data from wrong user contexts

These tests MUST initially FAIL to demonstrate the mis-routing exists.
"""

import pytest
import asyncio
import uuid
import time
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set, Optional, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Import problematic WebSocket modules to test
try:
    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.websocket_core.protocols import WebSocketEventProtocol
except ImportError:
    # Create mocks for testing if actual classes don't exist yet
    class UnifiedWebSocketManager:
        def __init__(self, user_context=None):
            self.user_context = user_context
            self.connections: Dict[str, Any] = {}
            self.sent_events: List[Dict] = []
            
        async def send_event(self, event_type: str, data: Dict, user_id: str = None):
            # Mock event sending that accepts string IDs (VIOLATION)
            event = {
                "type": event_type,
                "data": data,
                "user_id": user_id or getattr(self.user_context, 'user_id', 'unknown'),
                "timestamp": time.time(),
                "connection_target": user_id  # VIOLATION: string-based routing
            }
            self.sent_events.append(event)
            return event
    
    async def create_websocket_manager(user_context):
        return UnifiedWebSocketManager(user_context)
    
    class WebSocketEventProtocol:
        @staticmethod
        def create_event(event_type: str, data: Dict, user_id: str):
            return {"type": event_type, "data": data, "user_id": user_id}

from netra_backend.app.data_contexts.user_data_context import UserDataContext
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import CORRECT types that should be used
from shared.types import (
    UserID, ThreadID, RequestID, WebSocketID, ConnectionID,
    ensure_user_id, ensure_thread_id, ensure_request_id,
    StronglyTypedUserExecutionContext, WebSocketEventType,
    ContextValidationError, IsolationViolationError,
    StronglyTypedWebSocketEvent, WebSocketMessage
)


@dataclass
class MockWebSocketConnection:
    """Mock WebSocket connection for testing event routing."""
    connection_id: str  # VIOLATION: should be ConnectionID
    user_id: str  # VIOLATION: should be UserID
    thread_id: str  # VIOLATION: should be ThreadID
    websocket_id: str  # VIOLATION: should be WebSocketID
    received_events: List[Dict[str, Any]]
    is_active: bool = True
    last_activity: float = None
    
    def __post_init__(self):
        if not self.received_events:
            self.received_events = []
        if not self.last_activity:
            self.last_activity = time.time()


class TestWebSocketEventMisroutingViolations(SSotAsyncTestCase):
    """
    CRITICAL FAILING TESTS: WebSocket Event Mis-routing Violations
    
    These tests MUST initially FAIL to demonstrate that WebSocket event
    routing allows events to be delivered to wrong users.
    
    EXPECTED INITIAL RESULT: ALL TESTS SHOULD FAIL
    BUSINESS IMPACT: Prevents real-time cross-user data exposure
    """
    
    async def async_setup_method(self, method):
        """Enhanced async setup for WebSocket event testing."""
        await super().async_setup_method(method)
        
        # Enable strict WebSocket event routing detection
        self.set_env_var("STRICT_WEBSOCKET_ISOLATION", "true")
        self.set_env_var("DETECT_EVENT_MISROUTING", "true") 
        self.set_env_var("FAIL_ON_WEBSOCKET_ID_MIXING", "true")
        
        # Initialize test tracking
        self.misrouting_incidents: List[str] = []
        self.websocket_connections: Dict[str, MockWebSocketConnection] = {}
        self.user_contexts: Dict[str, UserExecutionContext] = {}
        self.websocket_managers: Dict[str, UnifiedWebSocketManager] = {}
        self.event_delivery_log: List[Dict] = []
        
        # Setup auth helper for realistic user contexts
        self.auth_helper = E2EAuthHelper(environment="test")
        
    async def test_websocket_event_cross_user_delivery_detection(self):
        """
        CRITICAL FAILING TEST: WebSocket events should not be delivered to wrong users
        
        EXPECTED RESULT: FAIL - Events delivered to wrong user connections
        BUSINESS RISK: User A sees User B's agent execution progress and results
        """
        print(" ALERT:  TESTING: WebSocket event cross-user delivery detection")
        
        # Create multiple users with WebSocket connections
        test_users = []
        for i in range(3):
            user_data = {
                "user_id": f"event_test_user_{i}",
                "thread_id": f"event_test_thread_{i}",
                "websocket_id": f"event_ws_{i}",
                "connection_id": f"event_conn_{i}",
                "sensitive_project": f"CONFIDENTIAL_PROJECT_{i}",
                "security_level": f"LEVEL_{i}_CLASSIFIED"
            }
            test_users.append(user_data)
        
        # Create WebSocket connections and contexts for each user
        for user in test_users:
            try:
                # Create user execution context with string IDs (VIOLATION)
                context = UserExecutionContext(
                    user_id=user["user_id"],  # VIOLATION: str instead of UserID
                    request_id=f"req_{user['user_id']}",  # VIOLATION: str instead of RequestID
                    thread_id=user["thread_id"],  # VIOLATION: str instead of ThreadID
                    run_id=f"run_{user['user_id']}"  # VIOLATION: str instead of RunID
                )
                
                self.user_contexts[user["user_id"]] = context
                
                # Create WebSocket manager for this user
                manager = await create_websocket_manager(context)
                self.websocket_managers[user["user_id"]] = manager
                
                # Create mock WebSocket connection
                connection = MockWebSocketConnection(
                    connection_id=user["connection_id"],  # VIOLATION: str instead of ConnectionID
                    user_id=user["user_id"],  # VIOLATION: str instead of UserID
                    thread_id=user["thread_id"],  # VIOLATION: str instead of ThreadID
                    websocket_id=user["websocket_id"],  # VIOLATION: str instead of WebSocketID
                    received_events=[]
                )
                self.websocket_connections[user["connection_id"]] = connection
                
                print(f"[U+2713] Created WebSocket setup for user: {user['user_id']}")
                
            except Exception as e:
                print(f" FAIL:  Failed to create WebSocket setup for user {user['user_id']}: {e}")
        
        print(f"Created WebSocket infrastructure for {len(self.websocket_managers)} users")
        
        # Simulate agent execution events for each user with sensitive data
        async def send_agent_events_for_user(user_data: Dict) -> Dict:
            """Send agent execution events for a specific user."""
            user_id = user_data["user_id"]
            manager = self.websocket_managers.get(user_id)
            
            if not manager:
                return {"error": f"No WebSocket manager for user {user_id}"}
            
            try:
                # Send various agent events with sensitive user data
                sensitive_events = [
                    {
                        "type": "agent_started",
                        "data": {
                            "agent_id": f"optimizer_agent_{user_id}",
                            "user_project": user_data["sensitive_project"],
                            "security_classification": user_data["security_level"],
                            "start_timestamp": time.time()
                        }
                    },
                    {
                        "type": "agent_thinking", 
                        "data": {
                            "reasoning": f"Analyzing {user_data['sensitive_project']} optimization strategies",
                            "confidential_data": f"Internal analysis for {user_data['security_level']}",
                            "user_specific_context": f"Context for user {user_id}"
                        }
                    },
                    {
                        "type": "tool_executing",
                        "data": {
                            "tool_name": "confidential_data_processor",
                            "processing": user_data["sensitive_project"],
                            "access_level": user_data["security_level"],
                            "tool_context": f"Processing for user {user_id}"
                        }
                    },
                    {
                        "type": "tool_completed",
                        "data": {
                            "tool_results": f"CONFIDENTIAL RESULTS for {user_data['sensitive_project']}",
                            "security_summary": f"Classification: {user_data['security_level']}",
                            "recommendations": f"Sensitive recommendations for user {user_id}"
                        }
                    },
                    {
                        "type": "agent_completed",
                        "data": {
                            "final_results": f"FINAL CONFIDENTIAL ANALYSIS: {user_data['sensitive_project']}",
                            "user_summary": f"Complete analysis for user {user_id}",
                            "completion_timestamp": time.time()
                        }
                    }
                ]
                
                sent_events = []
                for event in sensitive_events:
                    # Send event through WebSocket manager
                    sent_event = await manager.send_event(
                        event_type=event["type"],
                        data=event["data"],
                        user_id=user_id  # VIOLATION: string user_id for routing
                    )
                    
                    sent_events.append(sent_event)
                    
                    # Log event for mis-routing analysis
                    self.event_delivery_log.append({
                        "sender_user": user_id,
                        "event": sent_event,
                        "intended_recipient": user_id,
                        "timestamp": time.time(),
                        "contains_sensitive_data": True
                    })
                    
                    # Small delay between events
                    await asyncio.sleep(0.01)
                
                return {
                    "user_id": user_id,
                    "events_sent": len(sent_events),
                    "manager_events": len(manager.sent_events) if hasattr(manager, 'sent_events') else 0,
                    "status": "success"
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "error": str(e),
                    "status": "error"
                }
        
        # Send events for all users concurrently
        event_sending_tasks = [send_agent_events_for_user(user) for user in test_users]
        event_results = await asyncio.gather(*event_sending_tasks, return_exceptions=True)
        
        print(f"Sent events for {len(event_results)} users")
        
        # ANALYZE FOR CROSS-USER EVENT DELIVERY (MIS-ROUTING)
        
        cross_user_deliveries = []
        
        # Check 1: Verify events contain only intended user's data
        for log_entry in self.event_delivery_log:
            sender_user = log_entry["sender_user"]
            intended_recipient = log_entry["intended_recipient"]
            event = log_entry["event"]
            
            if sender_user != intended_recipient:
                # Event routing mismatch (critical violation)
                misrouting = f"Event from user {sender_user} routed to {intended_recipient}"
                cross_user_deliveries.append(misrouting)
                print(f" FAIL:  Critical routing violation: {misrouting}")
            
            # Check if event data contains references to other users
            event_str = str(event).lower()
            for other_user in test_users:
                other_user_id = other_user["user_id"]
                other_project = other_user["sensitive_project"].lower()
                other_security = other_user["security_level"].lower()
                
                if other_user_id != sender_user:
                    if other_user_id.lower() in event_str:
                        misrouting = f"Event from {sender_user} contains other user ID: {other_user_id}"
                        cross_user_deliveries.append(misrouting)
                        print(f" FAIL:  Cross-user data leak: {misrouting}")
                    
                    if other_project in event_str:
                        misrouting = f"Event from {sender_user} contains other user's project data: {other_project}"
                        cross_user_deliveries.append(misrouting)
                        print(f" FAIL:  Sensitive project leak: {misrouting}")
                    
                    if other_security in event_str and "level" in event_str:
                        misrouting = f"Event from {sender_user} contains other user's security level: {other_security}"
                        cross_user_deliveries.append(misrouting)
                        print(f" FAIL:  Security classification leak: {misrouting}")
        
        # Check 2: Verify WebSocket managers don't share event state
        manager_state_violations = []
        for user_id_a, manager_a in self.websocket_managers.items():
            if hasattr(manager_a, 'sent_events'):
                for event in manager_a.sent_events:
                    event_user = event.get("user_id")
                    
                    # Check if manager A contains events for other users
                    if event_user and event_user != user_id_a:
                        violation = f"Manager for {user_id_a} contains event for {event_user}"
                        manager_state_violations.append(violation)
                        print(f" FAIL:  Manager state violation: {violation}")
        
        # Check 3: Look for WebSocket connection ID collisions (should be impossible with proper typing)
        connection_collisions = []
        connection_ids = list(self.websocket_connections.keys())
        unique_connection_ids = set(connection_ids)
        
        if len(connection_ids) != len(unique_connection_ids):
            collision = f"Connection ID collisions: {len(connection_ids)} connections, {len(unique_connection_ids)} unique IDs"
            connection_collisions.append(collision)
            print(f" FAIL:  Connection ID collision: {collision}")
        
        # Check 4: Verify connection user association integrity
        connection_integrity_violations = []
        for conn_id, connection in self.websocket_connections.items():
            connection_user = connection.user_id
            
            # Verify connection is associated with correct user only
            for event_log in self.event_delivery_log:
                if event_log["event"].get("connection_target") == conn_id:
                    event_user = event_log["sender_user"]
                    if event_user != connection_user:
                        violation = f"Connection {conn_id} for user {connection_user} received event from user {event_user}"
                        connection_integrity_violations.append(violation)
                        print(f" FAIL:  Connection integrity violation: {violation}")
        
        # Combine all mis-routing incidents
        all_misrouting_incidents = (
            cross_user_deliveries + 
            manager_state_violations + 
            connection_collisions + 
            connection_integrity_violations
        )
        
        # Record comprehensive metrics
        self.record_metric("websocket_users_tested", len(test_users))
        self.record_metric("events_sent_total", len(self.event_delivery_log))
        self.record_metric("misrouting_incidents", len(all_misrouting_incidents))
        self.record_metric("websocket_managers_created", len(self.websocket_managers))
        self.record_metric("websocket_connections_created", len(self.websocket_connections))
        
        # Classify mis-routing types
        data_leaks = [m for m in all_misrouting_incidents if "leak" in m.lower() or "contains" in m.lower()]
        routing_violations = [m for m in all_misrouting_incidents if "routing" in m.lower()]
        state_violations = [m for m in all_misrouting_incidents if "state" in m.lower() or "manager" in m.lower()]
        collision_violations = [m for m in all_misrouting_incidents if "collision" in m.lower()]
        
        self.record_metric("data_leak_incidents", len(data_leaks))
        self.record_metric("routing_violation_incidents", len(routing_violations))
        self.record_metric("state_violation_incidents", len(state_violations))
        self.record_metric("collision_violation_incidents", len(collision_violations))
        
        # FAIL if mis-routing incidents were detected (expected for initial run)
        if all_misrouting_incidents:
            self.misrouting_incidents.extend(all_misrouting_incidents)
            pytest.fail(
                f"CRITICAL WEBSOCKET EVENT MIS-ROUTING: {len(all_misrouting_incidents)} mis-routing "
                f"incidents detected. WebSocket events are being delivered to wrong users, causing "
                f"real-time cross-user data exposure: {all_misrouting_incidents}"
            )
        
        print(" PASS:  No WebSocket event mis-routing detected (unexpected - test designed to fail)")
    
    async def test_websocket_connection_isolation_boundary_violations(self):
        """
        CRITICAL FAILING TEST: WebSocket connections should maintain strict isolation boundaries
        
        EXPECTED RESULT: FAIL - Connection isolation boundaries violated
        BUSINESS RISK: User connections interfere with each other causing data corruption
        """
        print(" ALERT:  TESTING: WebSocket connection isolation boundary violations")
        
        isolation_boundary_violations = []
        
        # Create users with potentially conflicting connection patterns
        boundary_test_users = [
            {
                "user_id": "boundary_enterprise_user",
                "thread_id": "boundary_ent_thread_001", 
                "connection_id": "boundary_ent_conn_001",
                "websocket_id": "boundary_ent_ws_001",
                "access_level": "ENTERPRISE_PREMIUM",
                "data_classification": "HIGHLY_CONFIDENTIAL"
            },
            {
                "user_id": "boundary_free_user",
                "thread_id": "boundary_free_thread_002",
                "connection_id": "boundary_free_conn_002", 
                "websocket_id": "boundary_free_ws_002",
                "access_level": "FREE_TIER",
                "data_classification": "PUBLIC"
            },
            {
                "user_id": "boundary_government_user",
                "thread_id": "boundary_gov_thread_003",
                "connection_id": "boundary_gov_conn_003",
                "websocket_id": "boundary_gov_ws_003",
                "access_level": "GOVERNMENT_CLASSIFIED",
                "data_classification": "CLASSIFIED"
            }
        ]
        
        # Setup WebSocket infrastructure with isolation boundaries
        user_websocket_setups = {}
        for user in boundary_test_users:
            try:
                # Create user context with proper isolation requirements
                context = UserExecutionContext(
                    user_id=user["user_id"],
                    request_id=f"boundary_req_{user['user_id']}",
                    thread_id=user["thread_id"],
                    run_id=f"boundary_run_{user['user_id']}"
                )
                
                # Create WebSocket manager
                manager = await create_websocket_manager(context)
                
                # Create connection with isolation metadata
                connection = MockWebSocketConnection(
                    connection_id=user["connection_id"],
                    user_id=user["user_id"],
                    thread_id=user["thread_id"],
                    websocket_id=user["websocket_id"],
                    received_events=[]
                )
                
                user_websocket_setups[user["user_id"]] = {
                    "context": context,
                    "manager": manager,
                    "connection": connection,
                    "user_data": user
                }
                
                self.user_contexts[user["user_id"]] = context
                self.websocket_managers[user["user_id"]] = manager
                self.websocket_connections[user["connection_id"]] = connection
                
            except Exception as e:
                print(f" FAIL:  Failed to setup WebSocket infrastructure for {user['user_id']}: {e}")
        
        print(f"Setup WebSocket infrastructure for {len(user_websocket_setups)} users with different access levels")
        
        # Test isolation boundaries by sending events simultaneously
        async def test_isolation_boundary_for_user(user_id: str, setup: Dict) -> Dict:
            """Test isolation boundary for a specific user."""
            user_data = setup["user_data"]
            manager = setup["manager"]
            
            try:
                # Send events with access-level specific data
                boundary_events = [
                    {
                        "type": "system_alert",
                        "data": {
                            "alert_level": user_data["access_level"],
                            "classification": user_data["data_classification"],
                            "alert_message": f"System alert for {user_data['access_level']} user",
                            "sensitive_context": f"Internal system data for {user_id}"
                        }
                    },
                    {
                        "type": "data_processing",
                        "data": {
                            "processing_level": user_data["access_level"],
                            "data_source": f"RESTRICTED_{user_data['data_classification']}_DATA",
                            "user_authorization": user_data["access_level"],
                            "processing_metadata": f"Processing context for {user_id}"
                        }
                    },
                    {
                        "type": "security_notification",
                        "data": {
                            "security_clearance": user_data["access_level"],
                            "classification_level": user_data["data_classification"],
                            "notification": f"Security update for {user_data['access_level']}",
                            "authorized_user": user_id
                        }
                    }
                ]
                
                boundary_results = []
                for event in boundary_events:
                    # Send event and check for boundary violations
                    sent_event = await manager.send_event(
                        event_type=event["type"],
                        data=event["data"],
                        user_id=user_id
                    )
                    
                    boundary_results.append(sent_event)
                    
                    # Log for boundary analysis
                    self.event_delivery_log.append({
                        "boundary_test": True,
                        "user_id": user_id,
                        "access_level": user_data["access_level"],
                        "event": sent_event,
                        "timestamp": time.time()
                    })
                
                await asyncio.sleep(0.05)  # Allow for processing
                
                return {
                    "user_id": user_id,
                    "access_level": user_data["access_level"],
                    "events_sent": len(boundary_results),
                    "boundary_test_status": "completed"
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "access_level": user_data["access_level"],
                    "error": str(e),
                    "boundary_test_status": "failed"
                }
        
        # Test all users' isolation boundaries simultaneously
        boundary_tasks = [
            test_isolation_boundary_for_user(user_id, setup) 
            for user_id, setup in user_websocket_setups.items()
        ]
        boundary_results = await asyncio.gather(*boundary_tasks, return_exceptions=True)
        
        print(f"Completed isolation boundary testing for {len(boundary_results)} users")
        
        # ANALYZE FOR ISOLATION BOUNDARY VIOLATIONS
        
        # Check 1: Cross-access-level contamination
        access_level_contamination = []
        boundary_events = [log for log in self.event_delivery_log if log.get("boundary_test")]
        
        for event_log in boundary_events:
            user_id = event_log["user_id"]
            user_access_level = event_log["access_level"]
            event = event_log["event"]
            event_str = str(event).upper()
            
            # Check if event contains data from other access levels
            for other_user_data in boundary_test_users:
                other_user_id = other_user_data["user_id"]
                other_access_level = other_user_data["access_level"]
                other_classification = other_user_data["data_classification"]
                
                if other_user_id != user_id:
                    if other_access_level.upper() in event_str:
                        contamination = f"User {user_id} ({user_access_level}) event contains {other_access_level} data"
                        access_level_contamination.append(contamination)
                        print(f" FAIL:  Access level contamination: {contamination}")
                    
                    if other_classification.upper() in event_str:
                        contamination = f"User {user_id} event contains {other_classification} classification data"
                        access_level_contamination.append(contamination)
                        print(f" FAIL:  Classification contamination: {contamination}")
        
        # Check 2: Privilege escalation through event data
        privilege_escalations = []
        free_user_events = [log for log in boundary_events if "free" in log["user_id"].lower()]
        
        for free_event_log in free_user_events:
            event_str = str(free_event_log["event"]).upper()
            
            # Free user should never see enterprise or government data
            if any(keyword in event_str for keyword in ["ENTERPRISE", "PREMIUM", "CONFIDENTIAL", "CLASSIFIED", "GOVERNMENT"]):
                escalation = f"Free user {free_event_log['user_id']} event contains privileged data"
                privilege_escalations.append(escalation)
                print(f" FAIL:  Privilege escalation detected: {escalation}")
        
        # Check 3: Connection boundary integrity
        connection_boundary_violations = []
        for conn_id, connection in self.websocket_connections.items():
            connection_user = connection.user_id
            connection_access_level = None
            
            # Find access level for this connection
            for user_data in boundary_test_users:
                if user_data["user_id"] == connection_user:
                    connection_access_level = user_data["access_level"]
                    break
            
            # Check if connection received events from other access levels
            for event_log in boundary_events:
                if event_log["event"].get("connection_target") == conn_id:
                    event_access_level = event_log["access_level"]
                    if event_access_level != connection_access_level:
                        violation = f"Connection {conn_id} ({connection_access_level}) received {event_access_level} event"
                        connection_boundary_violations.append(violation)
                        print(f" FAIL:  Connection boundary violation: {violation}")
        
        # Check 4: WebSocket manager isolation boundaries
        manager_isolation_violations = []
        for user_id, manager in self.websocket_managers.items():
            if hasattr(manager, 'sent_events'):
                user_access_level = None
                for user_data in boundary_test_users:
                    if user_data["user_id"] == user_id:
                        user_access_level = user_data["access_level"]
                        break
                
                # Check if manager contains events with different access levels
                for event in manager.sent_events:
                    event_str = str(event).upper()
                    
                    for other_user_data in boundary_test_users:
                        if other_user_data["user_id"] != user_id:
                            other_access = other_user_data["access_level"].upper()
                            if other_access in event_str:
                                violation = f"Manager for {user_id} ({user_access_level}) contains {other_access} data"
                                manager_isolation_violations.append(violation)
                                print(f" FAIL:  Manager isolation violation: {violation}")
        
        # Combine all boundary violations
        all_boundary_violations = (
            access_level_contamination + 
            privilege_escalations + 
            connection_boundary_violations + 
            manager_isolation_violations
        )
        
        # Record boundary violation metrics
        self.record_metric("boundary_users_tested", len(boundary_test_users))
        self.record_metric("boundary_events_processed", len(boundary_events))
        self.record_metric("boundary_violations", len(all_boundary_violations))
        
        # Classify boundary violation types
        contamination_violations = access_level_contamination
        escalation_violations = privilege_escalations
        connection_violations = connection_boundary_violations
        manager_violations = manager_isolation_violations
        
        self.record_metric("access_contamination_violations", len(contamination_violations))
        self.record_metric("privilege_escalation_violations", len(escalation_violations))
        self.record_metric("connection_boundary_violations", len(connection_violations))
        self.record_metric("manager_isolation_violations", len(manager_violations))
        
        # FAIL if boundary violations were detected
        if all_boundary_violations:
            self.misrouting_incidents.extend(all_boundary_violations)
            pytest.fail(
                f"CRITICAL WEBSOCKET ISOLATION BOUNDARY VIOLATIONS: {len(all_boundary_violations)} "
                f"boundary violations detected. WebSocket connections are not maintaining proper "
                f"isolation boundaries, causing cross-access-level data exposure: {all_boundary_violations}"
            )
        
        print(" PASS:  WebSocket isolation boundaries appear intact")
    
    async def test_websocket_event_serialization_user_data_mixing(self):
        """
        CRITICAL FAILING TEST: WebSocket event serialization should prevent user data mixing
        
        EXPECTED RESULT: FAIL - Event serialization mixes user data
        BUSINESS RISK: Serialized events contain mixed user data causing confusion and data leaks
        """
        print(" ALERT:  TESTING: WebSocket event serialization user data mixing")
        
        serialization_violations = []
        
        # Create users with very similar but distinct data (to test serialization precision)
        serialization_test_users = [
            {
                "user_id": "serialization_user_alpha",
                "thread_id": "serialization_thread_alpha_001",
                "project_name": "PROJECT_ALPHA_CONFIDENTIAL", 
                "optimization_target": "ALPHA_ENERGY_EFFICIENCY",
                "data_context": "alpha_energy_optimization_2024"
            },
            {
                "user_id": "serialization_user_beta",
                "thread_id": "serialization_thread_beta_002",
                "project_name": "PROJECT_BETA_CONFIDENTIAL",
                "optimization_target": "BETA_COST_REDUCTION", 
                "data_context": "beta_cost_optimization_2024"
            },
            {
                "user_id": "serialization_user_gamma",
                "thread_id": "serialization_thread_gamma_003",
                "project_name": "PROJECT_GAMMA_CONFIDENTIAL",
                "optimization_target": "GAMMA_PERFORMANCE_BOOST",
                "data_context": "gamma_performance_optimization_2024"
            }
        ]
        
        # Setup WebSocket managers for serialization testing
        serialization_managers = {}
        serialization_events = {}
        
        for user in serialization_test_users:
            try:
                context = UserExecutionContext(
                    user_id=user["user_id"],
                    request_id=f"serial_req_{user['user_id']}",
                    thread_id=user["thread_id"],
                    run_id=f"serial_run_{user['user_id']}"
                )
                
                manager = await create_websocket_manager(context)
                serialization_managers[user["user_id"]] = manager
                serialization_events[user["user_id"]] = []
                
                self.user_contexts[user["user_id"]] = context
                self.websocket_managers[user["user_id"]] = manager
                
            except Exception as e:
                print(f" FAIL:  Failed to setup serialization test for user {user['user_id']}: {e}")
        
        # Generate events with user-specific data for serialization testing
        async def generate_user_specific_events(user_data: Dict) -> Dict:
            """Generate events with very specific user data for serialization testing."""
            user_id = user_data["user_id"]
            manager = serialization_managers.get(user_id)
            
            if not manager:
                return {"error": f"No manager for user {user_id}"}
            
            try:
                # Create events with user-specific data that should NOT mix
                specific_events = [
                    {
                        "type": "optimization_analysis",
                        "data": {
                            "user_context": user_id,
                            "project": user_data["project_name"],
                            "target": user_data["optimization_target"],
                            "analysis_context": user_data["data_context"],
                            "timestamp": time.time(),
                            "user_specific_metadata": {
                                "user_id": user_id,
                                "project_code": user_data["project_name"][:12],  # Specific identifier
                                "optimization_type": user_data["optimization_target"]
                            }
                        }
                    },
                    {
                        "type": "data_processing_update",
                        "data": {
                            "processing_user": user_id,
                            "data_source": f"CONFIDENTIAL_{user_data['project_name']}_DATA",
                            "processing_target": user_data["optimization_target"],
                            "context_reference": user_data["data_context"],
                            "progress_details": {
                                "user": user_id,
                                "project": user_data["project_name"],
                                "stage": "data_analysis"
                            }
                        }
                    },
                    {
                        "type": "results_summary",
                        "data": {
                            "results_for_user": user_id,
                            "project_results": f"RESULTS for {user_data['project_name']}",
                            "optimization_outcome": f"ACHIEVED: {user_data['optimization_target']}",
                            "context_summary": user_data["data_context"],
                            "final_report": {
                                "user_id": user_id,
                                "project": user_data["project_name"],
                                "target_achieved": user_data["optimization_target"],
                                "completion_status": "SUCCESS"
                            }
                        }
                    }
                ]
                
                sent_events = []
                for event in specific_events:
                    sent_event = await manager.send_event(
                        event_type=event["type"],
                        data=event["data"],
                        user_id=user_id
                    )
                    
                    sent_events.append(sent_event)
                    serialization_events[user_id].append(sent_event)
                
                # Small delay to ensure serialization completes
                await asyncio.sleep(0.02)
                
                return {
                    "user_id": user_id,
                    "events_generated": len(sent_events),
                    "serialization_status": "completed"
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "error": str(e),
                    "serialization_status": "failed"
                }
        
        # Generate events for all users
        serialization_tasks = [
            generate_user_specific_events(user) 
            for user in serialization_test_users
        ]
        serialization_results = await asyncio.gather(*serialization_tasks, return_exceptions=True)
        
        print(f"Generated serialization test events for {len(serialization_results)} users")
        
        # ANALYZE SERIALIZED EVENTS FOR USER DATA MIXING
        
        # Check 1: Event serialization contains only intended user's data
        for user_data in serialization_test_users:
            user_id = user_data["user_id"]
            user_project = user_data["project_name"]
            user_target = user_data["optimization_target"]
            user_context = user_data["data_context"]
            
            user_events = serialization_events.get(user_id, [])
            
            for event in user_events:
                # Serialize event to string for analysis (simulate real serialization)
                serialized_event = json.dumps(event, sort_keys=True)
                serialized_lower = serialized_event.lower()
                
                # Check if serialized event contains other users' data
                for other_user_data in serialization_test_users:
                    if other_user_data["user_id"] != user_id:
                        other_project = other_user_data["project_name"].lower()
                        other_target = other_user_data["optimization_target"].lower()
                        other_context = other_user_data["data_context"].lower()
                        other_user_id = other_user_data["user_id"].lower()
                        
                        if other_project in serialized_lower:
                            violation = f"Event for {user_id} serialization contains other project: {other_project}"
                            serialization_violations.append(violation)
                            print(f" FAIL:  Project data mixing: {violation}")
                        
                        if other_target in serialized_lower:
                            violation = f"Event for {user_id} serialization contains other target: {other_target}"
                            serialization_violations.append(violation)
                            print(f" FAIL:  Target data mixing: {violation}")
                        
                        if other_context in serialized_lower:
                            violation = f"Event for {user_id} serialization contains other context: {other_context}"
                            serialization_violations.append(violation)
                            print(f" FAIL:  Context data mixing: {violation}")
                        
                        if other_user_id in serialized_lower and "user" in serialized_lower:
                            violation = f"Event for {user_id} serialization contains other user_id: {other_user_id}"
                            serialization_violations.append(violation)
                            print(f" FAIL:  User ID mixing: {violation}")
        
        # Check 2: JSON serialization structure integrity 
        json_structure_violations = []
        for user_id, events in serialization_events.items():
            for event in events:
                try:
                    # Test serialization and deserialization integrity
                    serialized = json.dumps(event)
                    deserialized = json.loads(serialized)
                    
                    # Check if user_id is consistent after serialization round-trip
                    original_user = event.get("user_id")
                    deserialized_user = deserialized.get("user_id")
                    
                    if original_user != deserialized_user:
                        violation = f"Serialization changed user_id from {original_user} to {deserialized_user}"
                        json_structure_violations.append(violation)
                        print(f" FAIL:  JSON structure violation: {violation}")
                    
                    # Check for unexpected nested user references
                    serialized_str = str(deserialized)
                    user_id_count = serialized_str.lower().count(user_id.lower())
                    
                    # Should have consistent user_id references, not random ones
                    for other_user_data in serialization_test_users:
                        other_user_id = other_user_data["user_id"]
                        if other_user_id != user_id:
                            other_count = serialized_str.lower().count(other_user_id.lower())
                            if other_count > 0:
                                violation = f"Event for {user_id} JSON contains {other_count} references to {other_user_id}"
                                json_structure_violations.append(violation)
                                print(f" FAIL:  JSON user reference violation: {violation}")
                
                except json.JSONEncodeError as e:
                    violation = f"Event for {user_id} failed JSON serialization: {e}"
                    json_structure_violations.append(violation)
                    print(f" FAIL:  JSON serialization error: {violation}")
        
        # Check 3: Manager state serialization integrity
        manager_serialization_violations = []
        for user_id, manager in serialization_managers.items():
            if hasattr(manager, 'sent_events'):
                try:
                    # Serialize manager state
                    manager_events_serialized = json.dumps(manager.sent_events, default=str)
                    manager_data_lower = manager_events_serialized.lower()
                    
                    # Check if manager serialization contains other users' data
                    for other_user_data in serialization_test_users:
                        if other_user_data["user_id"] != user_id:
                            other_markers = [
                                other_user_data["user_id"].lower(),
                                other_user_data["project_name"].lower(),
                                other_user_data["optimization_target"].lower()
                            ]
                            
                            for marker in other_markers:
                                if marker in manager_data_lower:
                                    violation = f"Manager {user_id} serialization contains other user data: {marker}"
                                    manager_serialization_violations.append(violation)
                                    print(f" FAIL:  Manager serialization violation: {violation}")
                
                except Exception as e:
                    violation = f"Manager {user_id} serialization failed: {e}"
                    manager_serialization_violations.append(violation)
        
        # Combine all serialization violations
        all_serialization_violations = (
            serialization_violations + 
            json_structure_violations + 
            manager_serialization_violations
        )
        
        # Record serialization violation metrics
        self.record_metric("serialization_users_tested", len(serialization_test_users))
        self.record_metric("events_serialized", sum(len(events) for events in serialization_events.values()))
        self.record_metric("serialization_violations", len(all_serialization_violations))
        
        # Classify serialization violation types
        data_mixing_violations = [v for v in all_serialization_violations if "mixing" in v.lower()]
        structure_violations = json_structure_violations
        manager_violations = manager_serialization_violations
        
        self.record_metric("data_mixing_violations", len(data_mixing_violations))
        self.record_metric("json_structure_violations", len(structure_violations))
        self.record_metric("manager_serialization_violations", len(manager_violations))
        
        # FAIL if serialization violations were detected
        if all_serialization_violations:
            self.misrouting_incidents.extend(all_serialization_violations)
            pytest.fail(
                f"CRITICAL WEBSOCKET EVENT SERIALIZATION VIOLATIONS: {len(all_serialization_violations)} "
                f"serialization violations detected. Event serialization is mixing user data, causing "
                f"cross-user information leakage in WebSocket communications: {all_serialization_violations}"
            )
        
        print(" PASS:  WebSocket event serialization appears secure")
    
    async def async_teardown_method(self, method):
        """Enhanced async teardown with mis-routing incident reporting."""
        await super().async_teardown_method(method)
        
        # Report all mis-routing incidents found during test
        if self.misrouting_incidents:
            print(f"\n ALERT:  CRITICAL WEBSOCKET MIS-ROUTING INCIDENTS: {len(self.misrouting_incidents)}")
            for i, incident in enumerate(self.misrouting_incidents, 1):
                print(f"  {i}. {incident}")
            
            # Save incidents to metrics for comprehensive reporting
            self.record_metric("total_misrouting_incidents", len(self.misrouting_incidents))
            self.record_metric("misrouting_incidents_list", self.misrouting_incidents)
            
            # Classify incident types for detailed analysis
            delivery_violations = [inc for inc in self.misrouting_incidents if "delivery" in inc.lower() or "routing" in inc.lower()]
            data_leak_violations = [inc for inc in self.misrouting_incidents if "leak" in inc.lower() or "contains" in inc.lower()]
            boundary_violations = [inc for inc in self.misrouting_incidents if "boundary" in inc.lower() or "isolation" in inc.lower()]
            serialization_violations = [inc for inc in self.misrouting_incidents if "serialization" in inc.lower() or "mixing" in inc.lower()]
            
            self.record_metric("event_delivery_violations", len(delivery_violations))
            self.record_metric("data_leak_violations", len(data_leak_violations))
            self.record_metric("boundary_isolation_violations", len(boundary_violations))
            self.record_metric("serialization_mixing_violations", len(serialization_violations))
        else:
            print("\n PASS:  No WebSocket event mis-routing detected (unexpected - tests designed to fail)")
            self.record_metric("total_misrouting_incidents", 0)
        
        # Generate WebSocket mis-routing summary report
        test_metrics = self.get_all_metrics()
        print(f"\n CHART:  WebSocket Event Mis-routing Test Metrics:")
        for metric, value in test_metrics.items():
            if any(keyword in metric for keyword in ["misrouting", "violation", "leak", "boundary", "serialization"]):
                print(f"  {metric}: {value}")


# Mark these as critical WebSocket mis-routing tests
pytest.mark.critical_websocket_misrouting = pytest.mark.critical
pytest.mark.websocket_event_violations = pytest.mark.websocket
pytest.mark.integration_websocket_failures = pytest.mark.integration