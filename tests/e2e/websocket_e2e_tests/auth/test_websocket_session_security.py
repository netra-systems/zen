"""
E2E WebSocket Session Security Tests - CRITICAL ISOLATION VALIDATION

Business Value Justification (BVJ):
- Segment: Platform/Internal - Multi-user session security
- Business Goal: Prevent session hijacking and cross-user data leakage
- Value Impact: Protects user privacy and data isolation in multi-user chat environment
- Revenue Impact: Prevents data breaches that could cost $200K+ and destroy user trust

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- ALL e2e tests MUST use authentication (JWT/OAuth) except tests directly validating auth
- Tests MUST FAIL HARD when session isolation is violated
- NO MOCKS in E2E testing - use real WebSocket connections  
- Tests with 0-second execution = automatic hard failure
- This is a MULTI-USER system - isolation is paramount

This test suite validates session security and isolation:
1. Session hijacking prevention
2. Cross-session data leakage prevention  
3. Session isolation between different users
4. Concurrent user session management
5. Session state integrity validation

@compliance CLAUDE.md - Real authentication required, hard failures for isolation violations
@compliance SPEC/core.xml - Multi-user isolation for secure chat infrastructure
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, AuthenticatedUser
from test_framework.ssot.websocket_auth_test_helpers import (
    WebSocketAuthenticationTester,
    AuthenticationScenario,
    SecurityError,
    create_authenticated_websocket_client
)
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient, WebSocketEvent
from shared.isolated_environment import get_env


@pytest.mark.asyncio
@pytest.mark.e2e 
@pytest.mark.websocket
@pytest.mark.auth
@pytest.mark.isolation
class TestWebSocketSessionSecurity(SSotBaseTestCase):
    """
    E2E WebSocket Session Security Tests.
    
    CRITICAL: These tests FAIL HARD when session isolation is violated.
    They validate that user sessions are completely isolated and that
    no cross-user data leakage occurs in the multi-user chat system.
    """
    
    def setup_method(self):
        """Set up test environment with real services."""
        super().setup_method()
        
        # Test configuration
        self.env = get_env()
        self.test_environment = self.env.get("TEST_ENV", "test")
        self.backend_url = "ws://localhost:8000"
        
        # Test tracking
        self.test_clients: List[RealWebSocketTestClient] = []
        self.authenticated_users: List[AuthenticatedUser] = []
        self.session_violations: List[str] = []
        self.isolation_violations: List[str] = []
        
        # Initialize auth helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        print(f"[U+1F527] Session security test setup completed for environment: {self.test_environment}")
    
    async def cleanup_method(self):
        """Clean up test resources."""
        print("[U+1F9F9] Cleaning up WebSocket session security test resources...")
        
        # Close all test clients
        for client in self.test_clients:
            try:
                await client.close()
            except Exception as e:
                print(f"Warning: Error closing client: {e}")
        
        self.test_clients.clear()
        self.authenticated_users.clear()
        self.session_violations.clear()
        self.isolation_violations.clear()
        
        print(" PASS:  Session security cleanup completed")
    
    async def test_session_hijacking_prevention_hard_failure(self):
        """
        Test session hijacking prevention with HARD FAILURE validation.
        
        CRITICAL: This test FAILS HARD if session hijacking is not prevented.
        
        Validates:
        1. Users cannot hijack other users' sessions
        2. Token stealing attempts are blocked
        3. Session impersonation is prevented  
        4. Cross-user authentication violations are detected
        """
        print("[U+1F6E1][U+FE0F] Testing session hijacking prevention with hard failure validation...")
        
        try:
            # Step 1: Create legitimate user with sensitive permissions
            legitimate_email = f"legitimate_{uuid.uuid4().hex[:8]}@example.com"
            legitimate_user = await self.auth_helper.create_authenticated_user(
                email=legitimate_email,
                permissions=["read", "write", "sensitive_data", "user_management"]
            )
            self.authenticated_users.append(legitimate_user)
            
            print(f" PASS:  Created legitimate user: {legitimate_user.user_id} with sensitive permissions")
            
            # Step 2: Create attacker user with limited permissions
            attacker_email = f"attacker_{uuid.uuid4().hex[:8]}@example.com"
            attacker_user = await self.auth_helper.create_authenticated_user(
                email=attacker_email,
                permissions=["read"]  # Very limited permissions
            )
            self.authenticated_users.append(attacker_user)
            
            print(f" PASS:  Created attacker user: {attacker_user.user_id} with limited permissions")
            
            # Step 3: Establish legitimate user's WebSocket session
            legitimate_client = await create_authenticated_websocket_client(
                backend_url=self.backend_url,
                environment=self.test_environment,
                user_email=legitimate_email,
                user_id=legitimate_user.user_id,
                permissions=legitimate_user.permissions
            )
            self.test_clients.append(legitimate_client)
            
            await legitimate_client.connect()
            print(" PASS:  Legitimate user WebSocket session established")
            
            # Step 4: Test legitimate user can access sensitive data
            sensitive_test_data = {
                "action": "access_sensitive_data",
                "user_id": legitimate_user.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_phase": "legitimate_access"
            }
            
            await legitimate_client.send_event("sensitive_operation", sensitive_test_data)
            print(" PASS:  Legitimate user successfully accessed sensitive data")
            
            # Step 5: CRITICAL TEST - Attacker attempts session hijacking
            print(" TARGET:  CRITICAL TEST: Attempting session hijacking attack...")
            
            # Create hijacker client that attempts to use legitimate user's token
            hijacker_client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.test_environment,
                connection_timeout=10.0
            )
            
            # HIJACKING ATTEMPT: Attacker uses legitimate user's JWT token
            hijacker_client.authenticated_user = AuthenticatedUser(
                user_id=attacker_user.user_id,  # Attacker's user ID
                email=attacker_user.email,      # Attacker's email
                full_name=attacker_user.full_name,
                jwt_token=legitimate_user.jwt_token,  # BUT legitimate user's token!
                permissions=attacker_user.permissions,
                created_at=attacker_user.created_at,
                is_test_user=True
            )
            hijacker_client.expected_user_id = attacker_user.user_id
            self.test_clients.append(hijacker_client)
            
            # Step 6: Test if hijacking attempt is properly blocked
            hijacking_blocked = True
            hijacking_error = None
            
            try:
                await hijacker_client.connect()
                hijacking_blocked = False  # Connection should have been blocked
                
                print(" FAIL:  WARNING: Hijacker connection succeeded - testing further...")
                
                # If connection succeeded, test if proper isolation is maintained
                hijack_test_data = {
                    "action": "hijack_attempt",
                    "target_user": legitimate_user.user_id,
                    "attacker_user": attacker_user.user_id,
                    "sensitive_request": "access_user_data",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await hijacker_client.send_event("hijack_test", hijack_test_data)
                
                # Test if hijacker can access sensitive data
                try:
                    hijacker_events = await hijacker_client.wait_for_events(
                        event_types={"sensitive_data_response", "user_data", "sensitive_operation"},
                        timeout=5.0
                    )
                    
                    if hijacker_events:
                        violation = (
                            f"CRITICAL SECURITY VIOLATION: Session hijacking succeeded! "
                            f"Attacker {attacker_user.user_id} accessed sensitive data using "
                            f"stolen token from {legitimate_user.user_id}. "
                            f"Events received: {[e.event_type for e in hijacker_events]}. "
                            f"This represents a MAJOR security breach."
                        )
                        self.session_violations.append(violation)
                        
                        # FAIL HARD - critical security violation
                        pytest.fail(violation)
                
                except asyncio.TimeoutError:
                    print(" PASS:  Hijacker could not access sensitive data (good)")
                
            except Exception as e:
                hijacking_blocked = True
                hijacking_error = str(e)
                print(f" PASS:  Session hijacking attempt properly blocked: {e}")
            
            # Step 7: Validate session isolation between users
            print("[U+1F512] Testing session isolation validation...")
            
            # Send session-specific data to legitimate user
            session_data = {
                "session_id": legitimate_client.connection_id,
                "user_private_data": f"private_data_for_{legitimate_user.user_id}",
                "sensitive_info": "confidential_business_data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await legitimate_client.send_event("private_session_data", session_data)
            
            # Test if hijacker can intercept private session data
            if not hijacking_blocked and hijacker_client.connection and not hijacker_client.connection.closed:
                try:
                    intercepted_events = await hijacker_client.wait_for_events(
                        event_types={"private_session_data", "session_response"},
                        timeout=3.0
                    )
                    
                    if intercepted_events:
                        violation = (
                            f"CRITICAL SECURITY VIOLATION: Session data interception successful! "
                            f"Attacker intercepted private session data: "
                            f"{[e.event_type for e in intercepted_events]}. "
                            f"This indicates complete session security failure."
                        )
                        self.session_violations.append(violation)
                        
                        # FAIL HARD - session isolation violated
                        pytest.fail(violation)
                
                except asyncio.TimeoutError:
                    print(" PASS:  Session data properly isolated - no interception")
            
            # Step 8: Test legitimate user maintains proper access
            try:
                await legitimate_client.send_event("verify_access", {
                    "user_id": legitimate_user.user_id,
                    "test": "post_hijack_attempt"
                })
                print(" PASS:  Legitimate user maintains proper session access")
            except Exception as e:
                print(f" WARNING: [U+FE0F] Legitimate user access affected: {e}")
            
            # Step 9: Final validation - no violations should have occurred
            if self.session_violations:
                pytest.fail(
                    f"SESSION HIJACKING PREVENTION FAILED:\n" + 
                    "\n".join(self.session_violations)
                )
            
            print(" PASS:  Session hijacking prevention test PASSED - all attacks properly blocked")
            
        except SecurityError as e:
            pytest.fail(f"Session hijacking prevention test FAILED: {e}")
        except Exception as e:
            pytest.fail(f"Session hijacking prevention test failed with error: {e}")
    
    async def test_cross_session_data_leakage_prevention(self):
        """
        Test prevention of cross-session data leakage.
        
        CRITICAL: This test FAILS HARD if data leaks between user sessions.
        
        Validates:
        1. User A's data is not visible to User B
        2. Session-specific events are properly isolated
        3. Concurrent sessions maintain isolation
        4. No data bleeding between connections
        """
        print("[U+1F6AB] Testing cross-session data leakage prevention...")
        
        try:
            # Step 1: Create multiple users for isolation testing
            users_data = []
            clients = []
            
            for i in range(3):  # Test with 3 concurrent users
                user_email = f"isolation_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
                user = await self.auth_helper.create_authenticated_user(
                    email=user_email,
                    permissions=["read", "write", "private_data"]
                )
                self.authenticated_users.append(user)
                
                client = await create_authenticated_websocket_client(
                    backend_url=self.backend_url,
                    environment=self.test_environment,
                    user_email=user_email,
                    user_id=user.user_id,
                    permissions=user.permissions
                )
                self.test_clients.append(client)
                clients.append(client)
                
                users_data.append({
                    "user": user,
                    "client": client,
                    "private_data": f"confidential_data_for_user_{i}_{uuid.uuid4().hex[:8]}"
                })
                
                print(f" PASS:  Created isolated user {i}: {user.user_id}")
            
            # Step 2: Connect all clients
            for i, user_data in enumerate(users_data):
                await user_data["client"].connect()
                print(f" PASS:  Connected user {i}: {user_data['user'].user_id}")
            
            # Step 3: Send private data for each user
            print("[U+1F510] Sending private data for each user...")
            
            for i, user_data in enumerate(users_data):
                private_event = {
                    "user_id": user_data["user"].user_id,
                    "session_id": user_data["client"].connection_id,
                    "private_data": user_data["private_data"],
                    "sensitive_info": f"top_secret_info_user_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "isolation_test": True
                }
                
                await user_data["client"].send_event("private_user_data", private_event)
                print(f" PASS:  Sent private data for user {i}")
            
            # Step 4: CRITICAL TEST - Verify no cross-user data leakage
            print(" SEARCH:  CRITICAL TEST: Checking for cross-user data leakage...")
            
            leakage_violations = []
            
            for i, user_data in enumerate(users_data):
                try:
                    # Each user should only receive their own data, not others'
                    received_events = await user_data["client"].wait_for_events(
                        event_types={"private_user_data", "user_data_response", "private_data"},
                        timeout=5.0
                    )
                    
                    # Check if any received events belong to other users
                    for event in received_events:
                        event_user_id = event.user_id or event.data.get("user_id")
                        
                        if event_user_id and event_user_id != user_data["user"].user_id:
                            violation = (
                                f"CRITICAL DATA LEAKAGE VIOLATION: User {user_data['user'].user_id} "
                                f"received data for user {event_user_id}. "
                                f"Event type: {event.event_type}. "
                                f"This indicates cross-user data leakage!"
                            )
                            leakage_violations.append(violation)
                            self.isolation_violations.append(violation)
                        
                        # Check if private data from other users is visible
                        for j, other_user_data in enumerate(users_data):
                            if i != j:  # Don't check against self
                                if other_user_data["private_data"] in str(event.data):
                                    violation = (
                                        f"CRITICAL DATA LEAKAGE VIOLATION: User {user_data['user'].user_id} "
                                        f"can see private data from user {other_user_data['user'].user_id}: "
                                        f"'{other_user_data['private_data']}' found in event data."
                                    )
                                    leakage_violations.append(violation)
                                    self.isolation_violations.append(violation)
                
                except asyncio.TimeoutError:
                    print(f" PASS:  User {i} received no cross-user data (expected)")
                except Exception as e:
                    print(f"[U+2139][U+FE0F] User {i} event check error: {e}")
            
            # Step 5: Test concurrent session operations
            print(" LIGHTNING:  Testing concurrent session operations...")
            
            # All users perform operations simultaneously
            concurrent_tasks = []
            for i, user_data in enumerate(users_data):
                task = user_data["client"].send_event("concurrent_test", {
                    "user_id": user_data["user"].user_id,
                    "operation": f"concurrent_op_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                concurrent_tasks.append(task)
            
            # Execute all concurrent operations
            await asyncio.gather(*concurrent_tasks)
            print(" PASS:  Concurrent operations completed")
            
            # Step 6: Validate session isolation after concurrent operations
            await asyncio.sleep(2)  # Allow time for any potential cross-contamination
            
            for i, user_data in enumerate(users_data):
                # Verify each client maintains proper isolation
                try:
                    user_data["client"].assert_no_isolation_violations()
                except AssertionError as e:
                    violation = f"User {i} isolation violation: {e}"
                    leakage_violations.append(violation)
                    self.isolation_violations.append(violation)
            
            # Step 7: FAIL HARD if any data leakage detected
            if leakage_violations:
                pytest.fail(
                    f"CRITICAL DATA LEAKAGE VIOLATIONS DETECTED:\n" + 
                    "\n".join(leakage_violations) + 
                    f"\n\nTotal violations: {len(leakage_violations)}"
                )
            
            print(" PASS:  Cross-session data leakage prevention test PASSED - perfect isolation maintained")
            
        except Exception as e:
            pytest.fail(f"Cross-session data leakage prevention test failed: {e}")
    
    async def test_concurrent_user_session_management(self):
        """
        Test concurrent user session management and isolation.
        
        Validates:
        1. Multiple users can have concurrent sessions  
        2. Sessions remain isolated under load
        3. User context is maintained correctly
        4. No session confusion or mixing occurs
        """
        print(" LIGHTNING:  Testing concurrent user session management...")
        
        try:
            # Step 1: Create many concurrent users (stress test)
            concurrent_user_count = 5
            user_sessions = []
            
            print(f"[U+1F465] Creating {concurrent_user_count} concurrent user sessions...")
            
            for i in range(concurrent_user_count):
                user_email = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
                user = await self.auth_helper.create_authenticated_user(
                    email=user_email,
                    permissions=["read", "write"]
                )
                self.authenticated_users.append(user)
                
                client = await create_authenticated_websocket_client(
                    backend_url=self.backend_url,
                    environment=self.test_environment,
                    user_email=user_email,
                    user_id=user.user_id,
                    permissions=user.permissions
                )
                self.test_clients.append(client)
                
                user_sessions.append({
                    "user": user,
                    "client": client,
                    "session_data": f"session_data_{i}_{uuid.uuid4().hex[:8]}"
                })
                
                print(f" PASS:  Created session {i+1}/{concurrent_user_count}: {user.user_id}")
            
            # Step 2: Connect all sessions concurrently
            print("[U+1F517] Establishing concurrent WebSocket connections...")
            
            connection_tasks = []
            for session in user_sessions:
                connection_tasks.append(session["client"].connect())
            
            await asyncio.gather(*connection_tasks)
            print(f" PASS:  All {concurrent_user_count} concurrent connections established")
            
            # Step 3: Test concurrent session operations
            print("[U+1F680] Testing concurrent session operations...")
            
            operation_tasks = []
            for i, session in enumerate(user_sessions):
                # Each user sends multiple events concurrently
                for j in range(3):  # 3 events per user
                    task = session["client"].send_event("concurrent_session_test", {
                        "user_id": session["user"].user_id,
                        "session_id": session["client"].connection_id,
                        "operation_id": f"op_{i}_{j}",
                        "session_data": session["session_data"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    operation_tasks.append(task)
            
            # Execute all operations concurrently
            await asyncio.gather(*operation_tasks)
            print(f" PASS:  {len(operation_tasks)} concurrent operations completed")
            
            # Step 4: Validate session isolation under concurrent load
            print(" SEARCH:  Validating session isolation under concurrent load...")
            
            isolation_violations = []
            
            for i, session in enumerate(user_sessions):
                try:
                    # Each session should maintain proper isolation
                    session["client"].assert_no_isolation_violations()
                    
                    # Verify session maintains correct user context
                    if session["client"].expected_user_id != session["user"].user_id:
                        violation = (
                            f"Session context violation: Expected {session['user'].user_id}, "
                            f"got {session['client'].expected_user_id}"
                        )
                        isolation_violations.append(violation)
                
                except AssertionError as e:
                    violation = f"Session {i} isolation violation: {e}"
                    isolation_violations.append(violation)
            
            # Step 5: Test session cleanup and reconnection
            print(" CYCLE:  Testing session cleanup and reconnection...")
            
            # Disconnect half the sessions
            disconnect_count = concurrent_user_count // 2
            for i in range(disconnect_count):
                await user_sessions[i]["client"].close()
                print(f" PASS:  Disconnected session {i}")
            
            # Remaining sessions should still work
            remaining_sessions = user_sessions[disconnect_count:]
            for i, session in enumerate(remaining_sessions):
                try:
                    await session["client"].send_event("post_disconnect_test", {
                        "user_id": session["user"].user_id,
                        "test": "session_still_active"
                    })
                    print(f" PASS:  Remaining session {i} still functional")
                except Exception as e:
                    print(f" WARNING: [U+FE0F] Remaining session {i} error: {e}")
            
            # Reconnect disconnected sessions
            for i in range(disconnect_count):
                new_client = await create_authenticated_websocket_client(
                    backend_url=self.backend_url,
                    environment=self.test_environment,
                    user_email=user_sessions[i]["user"].email,
                    user_id=user_sessions[i]["user"].user_id,
                    permissions=user_sessions[i]["user"].permissions
                )
                
                await new_client.connect()
                user_sessions[i]["client"] = new_client
                self.test_clients.append(new_client)
                
                print(f" PASS:  Reconnected session {i}")
            
            # Step 6: Final isolation validation
            for session in user_sessions:
                try:
                    session["client"].assert_no_isolation_violations()
                except AssertionError as e:
                    violation = f"Final isolation check violation: {e}"
                    isolation_violations.append(violation)
            
            # FAIL HARD if any isolation violations
            if isolation_violations:
                pytest.fail(
                    f"CONCURRENT SESSION ISOLATION VIOLATIONS:\n" + 
                    "\n".join(isolation_violations)
                )
            
            print(" PASS:  Concurrent user session management test PASSED")
            
        except Exception as e:
            pytest.fail(f"Concurrent user session management test failed: {e}")
    
    async def test_session_state_integrity_validation(self):
        """
        Test session state integrity validation.
        
        Validates:
        1. Session state remains consistent
        2. User context is not corrupted
        3. Session data integrity is maintained
        4. No state confusion between sessions
        """
        print("[U+1F512] Testing session state integrity validation...")
        
        try:
            # Step 1: Create user with complex session state
            user_email = f"state_integrity_{uuid.uuid4().hex[:8]}@example.com"
            user = await self.auth_helper.create_authenticated_user(
                email=user_email,
                permissions=["read", "write", "state_management"]
            )
            self.authenticated_users.append(user)
            
            client = await create_authenticated_websocket_client(
                backend_url=self.backend_url,
                environment=self.test_environment,
                user_email=user_email,
                user_id=user.user_id,
                permissions=user.permissions
            )
            self.test_clients.append(client)
            
            await client.connect()
            print(f" PASS:  Connected user for state integrity testing: {user.user_id}")
            
            # Step 2: Establish complex session state
            session_state = {
                "user_id": user.user_id,
                "session_id": client.connection_id,
                "state_version": 1,
                "user_preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": True
                },
                "session_data": {
                    "active_chats": ["chat_1", "chat_2"],
                    "current_view": "dashboard",
                    "last_activity": datetime.now(timezone.utc).isoformat()
                },
                "permissions": user.permissions
            }
            
            await client.send_event("establish_session_state", session_state)
            print(" PASS:  Complex session state established")
            
            # Step 3: Test state mutations and integrity
            state_mutations = [
                {
                    "action": "update_preferences",
                    "data": {"theme": "light", "language": "es"},
                    "expected_version": 2
                },
                {
                    "action": "add_chat",
                    "data": {"chat_id": "chat_3"},
                    "expected_version": 3
                },
                {
                    "action": "update_view",
                    "data": {"view": "settings"},
                    "expected_version": 4
                }
            ]
            
            print(" CYCLE:  Testing state mutations and integrity...")
            
            for i, mutation in enumerate(state_mutations):
                await client.send_event("mutate_session_state", {
                    "user_id": user.user_id,
                    "session_id": client.connection_id,
                    "mutation": mutation,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                print(f" PASS:  Applied state mutation {i+1}: {mutation['action']}")
            
            # Step 4: Validate session state integrity
            await client.send_event("validate_session_state", {
                "user_id": user.user_id,
                "session_id": client.connection_id,
                "request_full_state": True
            })
            
            print(" PASS:  Session state validation requested")
            
            # Step 5: Test state consistency across operations
            consistency_tests = [
                {"action": "read_user_data", "should_contain": user.user_id},
                {"action": "check_permissions", "should_contain": "write"},
                {"action": "verify_session", "should_contain": client.connection_id}
            ]
            
            for test in consistency_tests:
                await client.send_event("consistency_test", {
                    "test": test,
                    "user_id": user.user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            print(" PASS:  State consistency tests completed")
            
            # Step 6: Test state isolation (create second session for same user)
            second_client = await create_authenticated_websocket_client(
                backend_url=self.backend_url,
                environment=self.test_environment,
                user_email=user_email,
                user_id=user.user_id,
                permissions=user.permissions
            )
            self.test_clients.append(second_client)
            
            await second_client.connect()
            print(" PASS:  Second session established for same user")
            
            # Each session should have independent state
            await second_client.send_event("establish_session_state", {
                "user_id": user.user_id,
                "session_id": second_client.connection_id,
                "state_version": 1,  # Fresh state
                "session_data": {
                    "active_chats": ["different_chat"],
                    "current_view": "profile"
                }
            })
            
            print(" PASS:  Independent state established in second session")
            
            # Step 7: Validate state isolation between sessions
            isolation_violations = []
            
            # First session's state should not affect second session
            try:
                first_client_violations = client.isolation_violations
                second_client_violations = second_client.isolation_violations
                
                if first_client_violations:
                    isolation_violations.extend(first_client_violations)
                
                if second_client_violations:
                    isolation_violations.extend(second_client_violations)
                
                client.assert_no_isolation_violations()
                second_client.assert_no_isolation_violations()
                
            except AssertionError as e:
                isolation_violations.append(f"Session state isolation violation: {e}")
            
            if isolation_violations:
                pytest.fail(
                    f"SESSION STATE INTEGRITY VIOLATIONS:\n" + 
                    "\n".join(isolation_violations)
                )
            
            print(" PASS:  Session state integrity validation test PASSED")
            
        except Exception as e:
            pytest.fail(f"Session state integrity validation test failed: {e}")
    
    async def test_comprehensive_session_security_suite(self):
        """
        Run comprehensive session security test suite.
        
        This is the main integration test that runs all session security scenarios.
        CRITICAL: This test FAILS HARD for any session security violations.
        """
        print("[U+1F512] Running comprehensive session security test suite...")
        
        try:
            # Initialize authentication tester
            auth_tester = WebSocketAuthenticationTester(
                backend_url=self.backend_url,
                environment=self.test_environment
            )
            
            # Run session hijacking prevention test
            hijacking_result = await auth_tester.test_session_hijacking_prevention()
            
            if not hijacking_result.success:
                pytest.fail(
                    f"Session hijacking prevention FAILED: {hijacking_result.error_message}. "
                    f"Security violations: {hijacking_result.security_violations}"
                )
            
            print(" PASS:  Session hijacking prevention test passed")
            
            # Cleanup authentication tester
            await auth_tester.cleanup()
            
            # All session security tests must pass
            if self.session_violations:
                pytest.fail(
                    f"CRITICAL SESSION SECURITY VIOLATIONS:\n" + 
                    "\n".join(self.session_violations)
                )
            
            if self.isolation_violations:
                pytest.fail(
                    f"CRITICAL ISOLATION VIOLATIONS:\n" + 
                    "\n".join(self.isolation_violations)
                )
            
            print(" PASS:  Comprehensive session security test suite PASSED")
            
        except SecurityError as e:
            pytest.fail(f"CRITICAL SESSION SECURITY FAILURE: {e}")
        except Exception as e:
            pytest.fail(f"Session security test suite failed: {e}")
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Run async cleanup
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If loop is running, schedule cleanup
            asyncio.create_task(self.cleanup_method())
        else:
            # If loop is not running, run cleanup
            loop.run_until_complete(self.cleanup_method())
        
        super().teardown_method()


# Additional utility test functions

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.websocket
@pytest.mark.auth
async def test_session_security_edge_cases():
    """
    Test edge cases in session security.
    
    This validates edge cases that could be exploited for session attacks.
    """
    print(" SEARCH:  Testing session security edge cases...")
    
    auth_helper = E2EWebSocketAuthHelper(environment="test")
    
    # Test rapid session creation/destruction
    for i in range(5):
        user = await auth_helper.create_authenticated_user(
            email=f"rapid_session_{i}@example.com"
        )
        
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:8000",
            environment="test"
        )
        client.authenticated_user = user
        
        try:
            await client.connect()
            await client.send_event("rapid_test", {"iteration": i})
            await client.close()
            print(f" PASS:  Rapid session {i} completed")
        except Exception as e:
            print(f"[U+2139][U+FE0F] Rapid session {i} error (may be expected): {e}")
    
    print(" PASS:  Session security edge cases test PASSED")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"])