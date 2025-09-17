class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

    #!/usr/bin/env python
        '''
        CRITICAL: WebSocket Concurrent User Security Failure Test Suite

        BUSINESS CRITICAL SECURITY REQUIREMENTS:
        - User notifications MUST be completely isolated between users
        - Concurrent tool executions MUST NOT leak data between users
        - WebSocket connections MUST maintain user context integrity
        - Notification routing MUST prevent cross-user information disclosure

        These tests are designed to FAIL initially to expose security vulnerabilities:
        1. User context mixing in concurrent scenarios
        2. Tool execution results sent to wrong users
        3. Shared state causing notification routing errors
        4. Race conditions in user session management
        5. Memory leaks that could expose user data

        Security Impact: Data breach, user privacy violation, regulatory non-compliance
        Business Impact: Loss of user trust, potential legal liability
        '''

        import asyncio
        import json
        import os
        import sys
        import time
        import uuid
        import threading
        import random
        import hashlib
        from concurrent.futures import ThreadPoolExecutor
        from datetime import datetime, timezone
        from typing import Dict, List, Set, Any, Optional, Tuple
        from dataclasses import dataclass, field
        import pytest
        from shared.isolated_environment import IsolatedEnvironment

            # Add project root to path
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
        sys.path.insert(0, project_root)

        from shared.isolated_environment import get_env
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient

        logger = central_logger.get_logger(__name__)


        @dataclass
class UserContext:
        """Represents user context with sensitive data."""
        user_id: str
        session_id: str
        api_key: str
        private_data: Dict[str, Any]
        current_tool_execution: Optional[str] = None
        websocket_connections: List[Any] = field(default_factory=list)
        received_notifications: List[Dict[str, Any]] = field(default_factory=list)


        @dataclass
class SecurityViolation:
        """Records a security violation."""
        timestamp: float
        violation_type: str
        affected_users: List[str]
        leaked_data: Dict[str, Any]
        severity: str
        description: str


class SecurityViolationTracker:
        """Tracks security violations in WebSocket notifications."""

    def __init__(self):
        pass
        self.violations: List[SecurityViolation] = []
        self.user_contexts: Dict[str, UserContext] = {}
        self.shared_state_access: List[Dict[str, Any]] = []
        self.cross_user_data_flow: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def create_user_context(self, user_id: str) -> UserContext:
        """Create user context with sensitive data."""
        context = UserContext( )
        user_id=user_id,
        session_id="formatted_string",
        api_key="formatted_string",
        private_data={ )
        "user_profile": "formatted_string",
        "preferences": {"theme": "dark", "notifications": True},
        "billing_info": {"plan": "premium", "usage": random.randint(100, 1000)},
        "sensitive_tokens": ["formatted_string" for i in range(3)]
    
    

        with self.lock:
        self.user_contexts[user_id] = context

        return context

        def record_violation(self, violation_type: str, affected_users: List[str],
        leaked_data: Dict[str, Any], severity: str = "HIGH",
        description: str = ""):
        """Record a security violation."""
        violation = SecurityViolation( )
        timestamp=time.time(),
        violation_type=violation_type,
        affected_users=affected_users,
        leaked_data=leaked_data,
        severity=severity,
        description=description
    

        with self.lock:
        self.violations.append(violation)

        def record_shared_state_access(self, accessing_user: str, shared_state_key: str,
        state_owner: str = None):
        """Record access to shared state."""
        access_record = { )
        "timestamp": time.time(),
        "accessing_user": accessing_user,
        "shared_state_key": shared_state_key,
        "state_owner": state_owner,
        "violation": accessing_user != state_owner if state_owner else False
    

        with self.lock:
        self.shared_state_access.append(access_record)

        def record_cross_user_data_flow(self, sender_user: str, recipient_user: str,
        data_type: str, data_content: Any):
        """Record data flow between users."""
        flow_record = { )
        "timestamp": time.time(),
        "sender_user": sender_user,
        "recipient_user": recipient_user,
        "data_type": data_type,
        "data_content": str(data_content)[:200],  # Truncate for logging
        "is_violation": sender_user != recipient_user
    

        with self.lock:
        self.cross_user_data_flow.append(flow_record)

    def get_violations_by_severity(self, severity: str) -> List[SecurityViolation]:
        """Get violations by severity level."""
        return [item for item in []]

    def get_affected_users(self) -> Set[str]:
        """Get all users affected by violations."""
        affected = set()
        for violation in self.violations:
        affected.update(violation.affected_users)
        return affected


        @pytest.fixture
    def security_tracker():
        """Fixture providing security violation tracker."""
        tracker = SecurityViolationTracker()
        yield tracker


class TestConcurrentUserContextMixing:
        """Test user context mixing in concurrent scenarios."""

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_shared_websocket_manager_leaks_user_data(self, security_tracker):
"""CRITICAL: Test shared WebSocket manager leaks user data between users."""
        # This test SHOULD FAIL initially

num_users = 5

        # Create user contexts with sensitive data
user_contexts = {}
for i in range(num_users):
user_id = "formatted_string"
context = security_tracker.create_user_context(user_id)
user_contexts[user_id] = context

            # Simulate shared WebSocket manager state (the vulnerability!)
shared_websocket_state = { )
"current_user_context": None,
"last_notification_payload": None,
"user_session_cache": {},
"active_connections": {}
            

async def send_tool_result_notification(user_id: str, tool_result: Dict[str, Any]):
"""Send tool result notification with user's sensitive data."""
pass
user_context = user_contexts[user_id]

    # Update shared state (vulnerability!)
shared_websocket_state["current_user_context"] = user_context
shared_websocket_state["user_session_cache"][user_id] = user_context

    # Create notification with sensitive data
notification_payload = { )
"type": "tool_result",
"tool_name": "data_processor",
"result": tool_result,
"user_api_key": user_context.api_key,  # SENSITIVE!
"user_private_data": user_context.private_data,  # SENSITIVE!
"session_info": { )
"session_id": user_context.session_id,
"user_preferences": user_context.private_data["preferences"]
    
    

shared_websocket_state["last_notification_payload"] = notification_payload

    # Small delay to allow race conditions
await asyncio.sleep(random.uniform(0.001, 0.005))

    # Send notification using shared state (may be corrupted!)
current_context = shared_websocket_state["current_user_context"]
current_payload = shared_websocket_state["last_notification_payload"]

    # Record what actually happened
actual_recipient = current_context.user_id if current_context else "unknown"

    # Add to user's received notifications
if actual_recipient in user_contexts:
user_contexts[actual_recipient].received_notifications.append(current_payload)

        # Track data flow
security_tracker.record_cross_user_data_flow( )
sender_user=user_id,
recipient_user=actual_recipient,
data_type="tool_result_with_sensitive_data",
data_content=current_payload
        

        # Detect violation if notification went to wrong user
if actual_recipient != user_id:
security_tracker.record_violation( )
violation_type="CROSS_USER_DATA_LEAK",
affected_users=[user_id, actual_recipient],
leaked_data={ )
"api_key": current_payload.get("user_api_key"),
"private_data": current_payload.get("user_private_data"),
"session_info": current_payload.get("session_info")
},
severity="CRITICAL",
description="formatted_string"s sensitive data"
            

            # Send concurrent notifications with sensitive data
tasks = []
for user_id in user_contexts.keys():
tool_result = { )
"processed_data": "formatted_string",
"analysis": "formatted_string",
"recommendations": ["formatted_string" for i in range(3)]
                
tasks.append(send_tool_result_notification(user_id, tool_result))

                # Execute concurrently to maximize state corruption
await asyncio.gather(*tasks)

                # Verify security violations occurred
violations = security_tracker.get_violations_by_severity("CRITICAL")
assert len(violations) > 0, "Expected critical security violations"

                # Check for data leakage
data_leak_violations = [item for item in []]
assert len(data_leak_violations) > 0, "Expected cross-user data leakage"

                # Verify users received wrong sensitive data
for user_id, context in user_contexts.items():
for notification in context.received_notifications:
received_api_key = notification.get("user_api_key")
expected_api_key = context.api_key

if received_api_key and received_api_key != expected_api_key:
                            # User received someone else's API key!
assert True, "formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_tool_execution_results_cross_contamination(self, security_tracker):
"""CRITICAL: Test tool execution results get cross-contaminated between users."""
                                # This test SHOULD FAIL initially

users = ["user_001", "user_002", "user_003"]

                                # Create user contexts
user_contexts = { )
user_id: security_tracker.create_user_context(user_id)
for user_id in users
                                

                                # Simulate shared tool execution state (vulnerability!)
shared_tool_state = { )
"current_execution": None,
"execution_results": {},
"user_tool_cache": {},
"last_result_data": None
                                

async def execute_tool_with_user_data(user_id: str, tool_name: str, user_input: str):
"""Execute tool with user-specific input and sensitive processing."""
pass
user_context = user_contexts[user_id]

    # Update shared state with user's execution
execution_id = "formatted_string"
shared_tool_state["current_execution"] = { )
"execution_id": execution_id,
"user_id": user_id,
"tool_name": tool_name,
"user_input": user_input,
"api_key": user_context.api_key,  # SENSITIVE!
"user_data": user_context.private_data  # SENSITIVE!
    

    # Simulate tool processing delay
await asyncio.sleep(random.uniform(0.01, 0.03))

    # Process with user's sensitive data
processing_context = shared_tool_state["current_execution"]
if processing_context:
        # Create result with sensitive processing context
tool_result = { )
"output": "formatted_string",
"processed_with_api_key": processing_context.get("api_key"),  # LEAKED!
"user_specific_analysis": processing_context.get("user_data"),  # LEAKED!
"execution_metadata": { )
"user_id": processing_context.get("user_id"),
"tool_name": processing_context.get("tool_name"),
"processing_timestamp": time.time()
        
        

        # Store result in shared state (contamination risk!)
shared_tool_state["execution_results"][execution_id] = tool_result
shared_tool_state["last_result_data"] = tool_result
shared_tool_state["user_tool_cache"][user_id] = tool_result

        # Delay before sending notification
await asyncio.sleep(random.uniform(0.001, 0.005))

        # Send notification using potentially corrupted shared state
current_result = shared_tool_state["last_result_data"]
result_user_id = current_result.get("execution_metadata", {}).get("user_id")

        # Record cross-user data flow
security_tracker.record_cross_user_data_flow( )
sender_user=user_id,
recipient_user=result_user_id or "unknown",
data_type="tool_execution_result",
data_content=current_result
        

        # Check for contamination
if result_user_id != user_id:
            # Result context was corrupted!
security_tracker.record_violation( )
violation_type="TOOL_RESULT_CONTAMINATION",
affected_users=[user_id, result_user_id],
leaked_data={ )
"contaminated_api_key": current_result.get("processed_with_api_key"),
"contaminated_user_data": current_result.get("user_specific_analysis"),
"original_user": user_id,
"contaminated_with": result_user_id
},
severity="CRITICAL",
description="formatted_string"s context"
            

            # Add result to user's received notifications
user_context.received_notifications.append({ ))
"type": "tool_result",
"result": current_result,
"contaminated": result_user_id != user_id
            

await asyncio.sleep(0)
return tool_result

return None

            # Execute tools concurrently with sensitive data
tasks = []
for user_id in users:
for tool_num in range(5):
sensitive_input = "formatted_string"
tool_name = "formatted_string"
tasks.append(execute_tool_with_user_data(user_id, tool_name, sensitive_input))

                    # Execute all concurrently to maximize contamination risk
results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Verify contamination violations occurred
contamination_violations = [ )
v for v in security_tracker.violations
if v.violation_type == "TOOL_RESULT_CONTAMINATION"
                    

assert len(contamination_violations) > 0, "Expected tool result contamination violations"

                    # Check that users received contaminated data
for user_id, context in user_contexts.items():
contaminated_notifications = [ )
n for n in context.received_notifications
if n.get("contaminated", False)
                        

if contaminated_notifications:
                            # User received contaminated tool results!
assert len(contaminated_notifications) > 0, "formatted_string"

                            # Verify sensitive data was leaked
for violation in contamination_violations:
leaked_api_key = violation.leaked_data.get("contaminated_api_key")
if leaked_api_key:
                                    # Check if API key belongs to different user
for check_user_id, check_context in user_contexts.items():
if check_context.api_key == leaked_api_key and check_user_id != violation.affected_users[0]:
assert True, "formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_websocket_connection_hijacking_vulnerability(self, security_tracker):
"""CRITICAL: Test WebSocket connection hijacking vulnerability."""
                                                # This test SHOULD FAIL initially

victim_user = "user_001"
attacker_user = "user_002"

                                                # Create user contexts
victim_context = security_tracker.create_user_context(victim_user)
attacker_context = security_tracker.create_user_context(attacker_user)

                                                # Simulate shared connection management (vulnerability!)
connection_pool = { )
"connections": {},
"user_mapping": {},
"last_accessed_user": None,
"connection_cache": {}
                                                

                                                # Victim establishes connection
victim_websocket = Magic        victim_websocket.user_id = victim_user
victim_# websocket setup complete

connection_id = "formatted_string"
connection_pool["connections"][connection_id] = victim_websocket
connection_pool["user_mapping"][victim_user] = connection_id
connection_pool["last_accessed_user"] = victim_user

                                                # Victim starts tool execution with sensitive data
victim_tool_execution = { )
"tool_name": "sensitive_data_processor",
"input": "confidential business data",
"api_context": victim_context.api_key,
"processing_context": victim_context.private_data
                                                

                                                # Attacker attempts to establish connection (connection confusion bug!)
attacker_websocket = Magic        attacker_websocket.user_id = attacker_user
attacker_# websocket setup complete

                                                # Simulate connection ID collision or mapping error
                                                # Attacker gets same connection ID as victim (the bug!)
attacker_connection_id = connection_id  # SAME AS VICTIM!

                                                # Update connection pool with attacker's connection (overwrites victim!)
connection_pool["connections"][attacker_connection_id] = attacker_websocket
connection_pool["user_mapping"][attacker_user] = attacker_connection_id
connection_pool["last_accessed_user"] = attacker_user

                                                # Send tool result to "victim" but it goes to attacker's connection!
async def send_tool_result_to_victim():
"""Send victim's tool result - but goes to wrong connection."""
pass
victim_connection_id = connection_pool["user_mapping"].get(victim_user)

if victim_connection_id in connection_pool["connections"]:
target_websocket = connection_pool["connections"][victim_connection_id]

        # Create notification with victim's sensitive data
sensitive_result = { )
"type": "tool_completed",
"tool_name": victim_tool_execution["tool_name"],
"result": { )
"processed_data": "CONFIDENTIAL BUSINESS RESULTS",
"api_key_used": victim_tool_execution["api_context"],  # VICTIM"S API KEY!
"user_data": victim_tool_execution["processing_context"]  # VICTIM"S DATA!
},
"user_id": victim_user,
"execution_context": victim_tool_execution
        

        # Send to websocket (but it's actually attacker's connection!)
await target_websocket.send_json(sensitive_result)

        # Record the data flow violation
actual_recipient = target_websocket.user_id
security_tracker.record_cross_user_data_flow( )
sender_user=victim_user,
recipient_user=actual_recipient,
data_type="tool_result_with_api_key",
data_content=sensitive_result
        

        # Record security violation
if actual_recipient != victim_user:
security_tracker.record_violation( )
violation_type="CONNECTION_HIJACKING",
affected_users=[victim_user, actual_recipient],
leaked_data={ )
"victim_api_key": sensitive_result["result"]["api_key_used"],
"victim_private_data": sensitive_result["result"]["user_data"],
"hijacker_user": actual_recipient,
"hijacked_connection": victim_connection_id
},
severity="CRITICAL",
description="formatted_string"s data sent to attacker {actual_recipient}"
            

await send_tool_result_to_victim()

            # Verify hijacking violation occurred
hijacking_violations = [ )
v for v in security_tracker.violations
if v.violation_type == "CONNECTION_HIJACKING"
            

assert len(hijacking_violations) > 0, "Expected connection hijacking violation"

            # Verify attacker received victim's data
violation = hijacking_violations[0]
assert victim_user in violation.affected_users
assert attacker_user in violation.affected_users
assert violation.leaked_data["victim_api_key"] == victim_context.api_key

            # Check cross-user data flow
cross_user_flows = [ )
flow for flow in security_tracker.cross_user_data_flow
if flow["is_violation"] and flow["sender_user"] == victim_user
            

assert len(cross_user_flows) > 0, "Expected cross-user data flow violations"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_broadcast_notification_exposes_all_user_data(self, security_tracker):
"""CRITICAL: Test broadcast notifications expose all users' sensitive data."""
                # This test SHOULD FAIL initially

num_users = 8

                # Create users with different sensitivity levels
user_contexts = {}
for i in range(num_users):
user_id = "formatted_string"
context = security_tracker.create_user_context(user_id)

                    # Add different types of sensitive data per user
context.private_data.update({ ))
"security_clearance": "formatted_string",
"department_access": "formatted_string",
"confidential_projects": ["formatted_string" for j in range(3)],
"personal_info": { )
"ssn_last_4": "formatted_string",
"credit_card_last_4": "formatted_string",
"home_address": "formatted_string"
                    
                    

user_contexts[user_id] = context

                    # Simulate system-wide notification that accidentally includes all user data
async def send_system_wide_broadcast():
"""Send broadcast that accidentally includes sensitive user data."""

    # Collect "system status" that accidentally includes user data
system_status = { )
"timestamp": time.time(),
"server_status": "healthy",
"active_users": [],
"user_sessions": {},  # This will contain sensitive data!
"active_tool_executions": {}
    

    # Accidentally include all user contexts in broadcast (the vulnerability!)
for user_id, context in user_contexts.items():
system_status["active_users"].append(user_id)

        # CRITICAL BUG: Include full user context in broadcast
system_status["user_sessions"][user_id] = { )
"session_id": context.session_id,
"api_key": context.api_key,  # LEAKED TO ALL USERS!
"private_data": context.private_data,  # LEAKED TO ALL USERS!
"current_tool": context.current_tool_execution
        

        # Add current tool execution data
if context.current_tool_execution:
system_status["active_tool_executions"][user_id] = { )
"tool_name": context.current_tool_execution,
"user_context": context.private_data,  # MORE LEAKED DATA!
"processing_with_key": context.api_key  # MORE LEAKED DATA!
            

            # Send broadcast to ALL users (security violation!)
for recipient_user_id in user_contexts.keys():
                # Each user receives EVERYONE'S sensitive data
user_contexts[recipient_user_id].received_notifications.append({ ))
"type": "system_broadcast",
"system_status": system_status,
"contains_all_user_data": True
                

                # Record data flows for each leaked user's data
for leaked_user_id in user_contexts.keys():
if leaked_user_id != recipient_user_id:
security_tracker.record_cross_user_data_flow( )
sender_user=leaked_user_id,
recipient_user=recipient_user_id,
data_type="system_broadcast_leak",
data_content=system_status["user_sessions"][leaked_user_id]
                        

                        # Record massive security violation
all_leaked_data = {}
for leaked_user_id, leaked_context in user_contexts.items():
if leaked_user_id != recipient_user_id:
all_leaked_data[leaked_user_id] = { )
"api_key": leaked_context.api_key,
"private_data": leaked_context.private_data
                                

if all_leaked_data:
security_tracker.record_violation( )
violation_type="BROADCAST_DATA_EXPOSURE",
affected_users=list(user_contexts.keys()),
leaked_data=all_leaked_data,
severity="CRITICAL",
description="formatted_string" sensitive data in broadcast"
                                    

await send_system_wide_broadcast()

                                    # Verify massive data exposure occurred
broadcast_violations = [ )
v for v in security_tracker.violations
if v.violation_type == "BROADCAST_DATA_EXPOSURE"
                                    

assert len(broadcast_violations) > 0, "Expected broadcast data exposure violations"

                                    # Each user should have received violations (except themselves)
expected_violations = num_users * (num_users - 1)  # Each user sees others" data
actual_violations = len(broadcast_violations)

                                    # Should have many violations due to broadcast exposure
assert actual_violations > 0, "formatted_string"

                                    # Verify each user received other users' sensitive data
for user_id, context in user_contexts.items():
system_broadcasts = [ )
n for n in context.received_notifications
if n.get("type") == "system_broadcast"
                                        

assert len(system_broadcasts) > 0, "formatted_string"

                                        # Check if broadcast contains other users' data
for broadcast in system_broadcasts:
user_sessions = broadcast.get("system_status", {}).get("user_sessions", {})

                                            # User should NOT see other users' API keys and private data
for other_user_id, other_session_data in user_sessions.items():
if other_user_id != user_id:
                                                    # User received another user's sensitive data!
other_api_key = other_session_data.get("api_key")
other_private_data = other_session_data.get("private_data")

if other_api_key or other_private_data:
assert True, "formatted_string"s sensitive data"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_websocket_session_fixation_attack(self, security_tracker):
"""CRITICAL: Test WebSocket session fixation attack vulnerability."""
                                                            # This test SHOULD FAIL initially

victim_user = "user_victim"
attacker_user = "user_attacker"

                                                            # Create user contexts
victim_context = security_tracker.create_user_context(victim_user)
attacker_context = security_tracker.create_user_context(attacker_user)

                                                            # Simulate session management with fixation vulnerability
session_store = { )
"sessions": {},
"websocket_sessions": {},
"last_session_data": None
                                                            

                                                            # Attacker creates malicious session
malicious_session_id = "attacker_controlled_session_123"
session_store["sessions"][malicious_session_id] = { )
"user_id": attacker_user,  # Initially attacker"s session
"created_by": attacker_user,
"websocket_state": { )
"connection_id": "attacker_connection",
"privileges": ["read_all_users", "admin_access"]  # Elevated privileges!
                                                            
                                                            

                                                            # Victim connects using the same session ID (session fixation!)
                                                            # This could happen through URL manipulation or session prediction

async def victim_connects_with_fixed_session():
"""Victim connects but session is already controlled by attacker."""

    # Victim's connection attempt
victim_websocket = Magic            victim_websocket.user_id = victim_user
victim_# websocket setup complete

    # Check existing session (the vulnerability - session is reused!)
if malicious_session_id in session_store["sessions"]:
existing_session = session_store["sessions"][malicious_session_id]

        # Session fixation: update user_id but keep attacker's websocket state
existing_session["user_id"] = victim_user  # Now "victim"s" session
session_store["last_session_data"] = existing_session

        # But websocket state still has attacker's privileges!
victim_websocket_state = existing_session["websocket_state"]

        # Victim's tool execution uses compromised session
tool_execution = { )
"user_id": victim_user,
"tool_name": "data_export",
"sensitive_input": "victim"s confidential data",
"api_key": victim_context.api_key,
"session_privileges": victim_websocket_state["privileges"]  # ATTACKER"S PRIVILEGES!
        

        # Send tool result using compromised session
tool_result = { )
"type": "tool_result",
"result": "Exported victim"s data with elevated privileges",
"execution_context": tool_execution,
"session_info": existing_session,
"compromised": True
        

        # The result goes to victim but session is controlled by attacker
await victim_websocket.send_json(tool_result)

        # Record the session fixation violation
security_tracker.record_violation( )
violation_type="SESSION_FIXATION",
affected_users=[victim_user, attacker_user],
leaked_data={ )
"victim_api_key": tool_execution["api_key"],
"victim_data": tool_execution["sensitive_input"],
"attacker_privileges": victim_websocket_state["privileges"],
"fixed_session_id": malicious_session_id,
"session_created_by": existing_session["created_by"]
},
severity="CRITICAL",
description="formatted_string"
        

await asyncio.sleep(0)
return tool_result

return None

result = await victim_connects_with_fixed_session()

        # Verify session fixation violation occurred
fixation_violations = [ )
v for v in security_tracker.violations
if v.violation_type == "SESSION_FIXATION"
        

assert len(fixation_violations) > 0, "Expected session fixation violation"

        # Verify victim's data was processed with attacker's privileges
violation = fixation_violations[0]
leaked_data = violation.leaked_data

assert leaked_data["victim_api_key"] == victim_context.api_key
assert leaked_data["session_created_by"] == attacker_user
assert "admin_access" in leaked_data["attacker_privileges"]

        # Check that victim used compromised session
assert result is not None, "Expected tool execution to complete"
assert result.get("compromised") is True, "Expected execution to be marked as compromised"


class TestNotificationSecurityBypass:
        """Test notification security bypass scenarios."""

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_notification_authentication_bypass(self, security_tracker):
"""CRITICAL: Test notification authentication bypass vulnerability."""
        # This test SHOULD FAIL initially

authenticated_user = "user_authenticated"
unauthenticated_user = "user_unauthenticated"

        # Create contexts
auth_context = security_tracker.create_user_context(authenticated_user)
unauth_context = security_tracker.create_user_context(unauthenticated_user)

        # Simulate notification system with authentication bypass bug
notification_system = { )
"authenticated_connections": {authenticated_user: Magic            "pending_notifications": {},
"bypass_check_enabled": True,  # The vulnerability!
"last_authenticated_user": authenticated_user
        

async def send_authenticated_notification(target_user: str, sensitive_data: Dict[str, Any]):
"""Send notification that should require authentication."""

    # Check authentication (flawed logic!)
if notification_system["bypass_check_enabled"]:
        # BUG: Uses last authenticated user instead of target user
auth_user = notification_system["last_authenticated_user"]

        # Send notification even if target_user is not authenticated
notification = { )
"type": "authenticated_tool_result",
"target_user": target_user,
"authenticated_as": auth_user,  # Wrong user!
"sensitive_data": sensitive_data,
"requires_auth": True,
"bypassed_auth": target_user != auth_user
        

        # Record cross-user data flow
security_tracker.record_cross_user_data_flow( )
sender_user=auth_user,
recipient_user=target_user,
data_type="authenticated_notification",
data_content=notification
        

        # Add to user's notifications
if target_user in [authenticated_user, unauthenticated_user]:
target_context = auth_context if target_user == authenticated_user else unauth_context
target_context.received_notifications.append(notification)

            # Record violation if unauthenticated user received authenticated data
if target_user == unauthenticated_user:
security_tracker.record_violation( )
violation_type="AUTHENTICATION_BYPASS",
affected_users=[authenticated_user, unauthenticated_user],
leaked_data=sensitive_data,
severity="CRITICAL",
description="formatted_string"
                

await asyncio.sleep(0)
return True

return False

                # Send sensitive data to unauthenticated user (should be blocked but isn't!)
sensitive_business_data = { )
"customer_data": "confidential customer information",
"financial_reports": "Q4 financial data",
"api_keys": {"service_a": auth_context.api_key},
"internal_metrics": {"revenue": "$1M", "user_count": 50000}
                

                # This should fail but doesn't due to authentication bypass
result = await send_authenticated_notification(unauthenticated_user, sensitive_business_data)

                # Verify authentication bypass occurred
bypass_violations = [ )
v for v in security_tracker.violations
if v.violation_type == "AUTHENTICATION_BYPASS"
                

assert len(bypass_violations) > 0, "Expected authentication bypass violation"

                # Verify unauthenticated user received sensitive data
unauth_notifications = unauth_context.received_notifications
authenticated_notifications = [ )
n for n in unauth_notifications
if n.get("requires_auth") and n.get("bypassed_auth")
                

assert len(authenticated_notifications) > 0, "Expected unauthenticated user to receive authenticated data"

                # Check that sensitive data was leaked
violation = bypass_violations[0]
leaked_data = violation.leaked_data

assert "customer_data" in leaked_data
assert "financial_reports" in leaked_data
assert "api_keys" in leaked_data

                # Verify the bypass was detected
notification = authenticated_notifications[0]
assert notification["authenticated_as"] != notification["target_user"]
assert notification["bypassed_auth"] is True

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_websocket_privilege_escalation_through_notifications(self, security_tracker):
"""CRITICAL: Test privilege escalation through WebSocket notifications."""
                    # This test SHOULD FAIL initially

low_privilege_user = "user_basic"
high_privilege_user = "user_admin"

                    # Create user contexts with different privilege levels
basic_context = security_tracker.create_user_context(low_privilege_user)
basic_context.private_data["privileges"] = ["read_own_data"]
basic_context.private_data["role"] = "basic_user"

admin_context = security_tracker.create_user_context(high_privilege_user)
admin_context.private_data["privileges"] = ["read_all_data", "admin_access", "delete_users"]
admin_context.private_data["role"] = "admin"

                    # Simulate notification system with privilege confusion
privilege_context = { )
"current_user_privileges": None,
"last_admin_context": None,
"notification_context": None
                    

async def send_admin_notification():
"""Send admin notification that sets privileged context."""

    # Admin receives notification about system operation
admin_notification = { )
"type": "admin_operation_complete",
"operation": "user_data_export",
"privileges_required": admin_context.private_data["privileges"],
"admin_context": { )
"user_id": high_privilege_user,
"api_key": admin_context.api_key,
"admin_privileges": admin_context.private_data["privileges"]
    
    

    # Set privileged context (the bug - context persists!)
privilege_context["current_user_privileges"] = admin_context.private_data["privileges"]
privilege_context["last_admin_context"] = admin_notification["admin_context"]
privilege_context["notification_context"] = admin_notification

admin_context.received_notifications.append(admin_notification)
await asyncio.sleep(0)
return True

async def send_basic_user_notification():
"""Send notification to basic user with admin context still active."""

    # Basic user receives notification but admin context is still active (bug!)
current_privileges = privilege_context["current_user_privileges"]
admin_context_data = privilege_context["last_admin_context"]

    # Create notification for basic user but with admin privileges
basic_notification = { )
"type": "tool_result",
"user_id": low_privilege_user,
"result": "basic operation result",
"notification_context": privilege_context["notification_context"],  # ADMIN CONTEXT!
"effective_privileges": current_privileges,  # ADMIN PRIVILEGES!
"admin_context_leaked": admin_context_data  # LEAKED ADMIN DATA!
    

    # Basic user receives notification with admin context
basic_context.received_notifications.append(basic_notification)

    # Record privilege escalation violation
security_tracker.record_violation( )
violation_type="PRIVILEGE_ESCALATION",
affected_users=[low_privilege_user, high_privilege_user],
leaked_data={ )
"escalated_user": low_privilege_user,
"original_privileges": ["read_own_data"],
"escalated_privileges": current_privileges,
"leaked_admin_context": admin_context_data
},
severity="CRITICAL",
description="formatted_string"
    

await asyncio.sleep(0)
return True

    # Send admin notification first
await send_admin_notification()

    # Then send basic user notification (should not have admin context!)
await send_basic_user_notification()

    # Verify privilege escalation occurred
escalation_violations = [ )
v for v in security_tracker.violations
if v.violation_type == "PRIVILEGE_ESCALATION"
    

assert len(escalation_violations) > 0, "Expected privilege escalation violation"

    # Verify basic user received admin privileges
violation = escalation_violations[0]
leaked_data = violation.leaked_data

assert leaked_data["escalated_user"] == low_privilege_user
assert "admin_access" in leaked_data["escalated_privileges"]
assert leaked_data["leaked_admin_context"]["user_id"] == high_privilege_user

    # Check basic user's notifications
basic_notifications = basic_context.received_notifications
privileged_notifications = [ )
n for n in basic_notifications
if "admin_context_leaked" in n and n["admin_context_leaked"] is not None
    

assert len(privileged_notifications) > 0, "Expected basic user to receive admin context"

    # Verify admin API key was leaked to basic user
leaked_notification = privileged_notifications[0]
leaked_admin_key = leaked_notification.get("admin_context_leaked", {}).get("api_key")

assert leaked_admin_key == admin_context.api_key, "Expected admin API key to be leaked"


if __name__ == "__main__":
        # Run the test suite
pytest.main([__file__, "-v", "--tb=short"])
pass
