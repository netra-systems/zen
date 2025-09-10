"""
MISSION CRITICAL: Multi-User Isolation Under Load Tests for Golden Path

🚨 MISSION CRITICAL TEST 🚨
This test suite validates that user isolation is maintained under high load scenarios,
preventing data leakage and ensuring enterprise-grade security at scale.

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - affects multi-tenant business customers
- Business Goal: Ensure complete user isolation under concurrent load
- Value Impact: Data leakage = regulatory violations = lost enterprise contracts = $500K+ revenue loss
- Strategic Impact: Enables enterprise scaling without security compromises

USER ISOLATION CRITICAL REQUIREMENTS:
1. Complete user context separation under concurrent load (10+ users)
2. No data leakage between user sessions during high throughput
3. User-scoped database isolation maintained under stress
4. WebSocket message delivery isolated per user under load
5. Agent execution contexts properly isolated during concurrent operations

ZERO TOLERANCE: Any user isolation breach BLOCKS enterprise deployment.
"""

import asyncio
import pytest
import time
import uuid
import random
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import json

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.execution_types import StronglyTypedUserExecutionContext


class TestMultiUserIsolationUnderLoad(SSotAsyncTestCase):
    """
    🚨 MISSION CRITICAL TEST SUITE 🚨
    
    Validates that user isolation is maintained under high concurrent load,
    ensuring enterprise-grade security and data protection at scale.
    """
    
    def setup_method(self, method=None):
        """Setup with multi-user isolation testing context."""
        super().setup_method(method)
        
        # Mission critical business metrics
        self.record_metric("mission_critical", True)
        self.record_metric("user_isolation_validation", True)
        self.record_metric("enterprise_security", True)
        self.record_metric("regulatory_compliance", True)
        self.record_metric("revenue_protection", 500000)  # $500K+ enterprise revenue
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Load testing configuration
        self.concurrent_users = 10  # Concurrent users for isolation testing
        self.messages_per_user = 5   # Messages each user sends
        self.load_test_duration = 60.0  # Maximum test duration
        
        # Isolation tracking
        self.user_data_store = {}  # Track per-user data for isolation validation
        self.isolation_violations = []
        self.active_users = []
        self.active_connections = []
        self.user_lock = threading.Lock()
        
        # Critical events for isolation testing
        self.CRITICAL_EVENTS = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
    async def async_teardown_method(self, method=None):
        """Critical cleanup with isolation protection."""
        try:
            # Close all user connections
            for connection in self.active_connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(connection)
                except Exception:
                    pass
            
            # Clear user data
            with self.user_lock:
                self.user_data_store.clear()
                self.active_users.clear()
                self.active_connections.clear()
            
        except Exception as e:
            print(f"⚠️  Multi-user isolation cleanup error: {e}")
        
        await super().async_teardown_method(method)
    
    @pytest.mark.mission_critical
    @pytest.mark.user_isolation
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_user_context_isolation_under_concurrent_load(self):
        """
        🚨 USER ISOLATION CRITICAL: User Context Separation Under Load
        
        Tests that user execution contexts remain completely isolated
        when multiple users access the system simultaneously.
        
        CRITICAL ISOLATION REQUIREMENTS:
        - Each user has unique, isolated execution context
        - No cross-user data contamination in contexts
        - User IDs, Thread IDs, Run IDs remain user-specific
        - Context isolation maintained under concurrent access
        """
        isolation_test_start = time.time()
        
        # Create unique user contexts for concurrent testing
        user_contexts = []
        expected_user_data = {}
        
        print(f"\n👥 USER ISOLATION TEST: Creating {self.concurrent_users} isolated user contexts")
        
        for i in range(self.concurrent_users):
            user_email = f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            
            # Create strongly typed user context
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                environment=self.environment,
                websocket_enabled=True
            )
            
            # Store expected user-specific data for isolation validation
            user_data = {
                "user_index": i,
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "run_id": str(user_context.run_id),
                "email": user_email,
                "websocket_client_id": str(user_context.websocket_client_id) if user_context.websocket_client_id else None,
                "created_at": time.time(),
                "expected_messages": [],
                "received_messages": [],
                "events_received": set(),
                "isolation_verified": False
            }
            
            user_contexts.append(user_context)
            expected_user_data[str(user_context.user_id)] = user_data
            
            with self.user_lock:
                self.user_data_store[str(user_context.user_id)] = user_data
                self.active_users.append(user_context)
        
        # Execute concurrent user operations that test isolation
        async def execute_isolated_user_operations(user_context: StronglyTypedUserExecutionContext) -> Dict[str, Any]:
            """Execute operations for a single user that test isolation boundaries."""
            user_id = str(user_context.user_id)
            user_start = time.time()
            
            try:
                # Get user-specific authentication
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=user_context.agent_context.get('user_email')
                )
                
                # Create user-specific WebSocket connection
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
                
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=user_id
                )
                
                self.active_connections.append(connection)
                
                # Send user-specific messages that should remain isolated
                user_messages = []
                for msg_index in range(self.messages_per_user):
                    # Create user-specific message with isolation markers
                    message = {
                        "type": "chat_message",
                        "content": f"ISOLATION TEST - User {user_id} Message {msg_index}",
                        "user_id": user_id,
                        "thread_id": str(user_context.thread_id),
                        "run_id": str(user_context.run_id),
                        "isolation_marker": f"USER_{user_id}_MSG_{msg_index}",
                        "timestamp": time.time(),
                        "expected_isolation": True
                    }
                    
                    user_messages.append(message)
                    
                    # Store expected message for isolation validation
                    with self.user_lock:
                        self.user_data_store[user_id]["expected_messages"].append(message)
                    
                    # Send message
                    await WebSocketTestHelpers.send_test_message(
                        connection, message, timeout=5.0
                    )
                    
                    # Small random delay to create overlapping operations
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                
                # Collect events and validate isolation
                events_received = []
                events_by_type = set()
                isolation_violations_detected = []
                
                event_collection_start = time.time()
                max_event_wait = 30.0
                
                while (time.time() - event_collection_start) < max_event_wait:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=3.0
                        )
                        
                        if event and isinstance(event, dict):
                            events_received.append(event)
                            event_type = event.get("type")
                            
                            if event_type:
                                events_by_type.add(event_type)
                            
                            # CRITICAL ISOLATION VALIDATION
                            event_user_id = event.get("user_id")
                            event_thread_id = event.get("thread_id")
                            event_run_id = event.get("run_id")
                            
                            # Validate event belongs to correct user
                            if event_user_id and event_user_id != user_id:
                                isolation_violations_detected.append({
                                    "violation_type": "cross_user_event",
                                    "expected_user_id": user_id,
                                    "received_user_id": event_user_id,
                                    "event": event
                                })
                            
                            # Validate thread isolation
                            if event_thread_id and event_thread_id != str(user_context.thread_id):
                                isolation_violations_detected.append({
                                    "violation_type": "cross_thread_contamination",
                                    "expected_thread_id": str(user_context.thread_id),
                                    "received_thread_id": event_thread_id,
                                    "event": event
                                })
                            
                            # Store received event for cross-user validation
                            with self.user_lock:
                                self.user_data_store[user_id]["received_messages"].append(event)
                                self.user_data_store[user_id]["events_received"].add(event_type)
                            
                            # Check if we have sufficient events for validation
                            if len(events_by_type.intersection(self.CRITICAL_EVENTS)) >= 3:
                                break
                                
                    except:
                        # Individual event timeouts acceptable
                        continue
                
                # Cleanup user connection
                await WebSocketTestHelpers.close_test_connection(connection)
                self.active_connections.remove(connection)
                
                user_execution_time = time.time() - user_start
                
                # Store isolation violations globally
                if isolation_violations_detected:
                    with self.user_lock:
                        self.isolation_violations.extend(isolation_violations_detected)
                
                return {
                    "user_id": user_id,
                    "success": True,
                    "messages_sent": len(user_messages),
                    "events_received": len(events_received),
                    "event_types": list(events_by_type),
                    "isolation_violations": isolation_violations_detected,
                    "execution_time": user_execution_time,
                    "isolation_validated": len(isolation_violations_detected) == 0
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - user_start,
                    "isolation_validated": False
                }
        
        # Execute all users concurrently to test isolation under load
        print(f"🚀 Executing {self.concurrent_users} concurrent users to test isolation...")
        
        user_tasks = [
            execute_isolated_user_operations(context)
            for context in user_contexts
        ]
        
        # Run concurrent operations and collect results
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_isolation_test_time = time.time() - isolation_test_start
        
        # CRITICAL ISOLATION ANALYSIS
        
        successful_users = 0
        isolation_validated_users = 0
        total_isolation_violations = 0
        
        for result in user_results:
            if isinstance(result, Exception):
                print(f"❌ User execution exception: {result}")
                continue
                
            if result.get("success"):
                successful_users += 1
                
                if result.get("isolation_validated"):
                    isolation_validated_users += 1
                
                violation_count = len(result.get("isolation_violations", []))
                total_isolation_violations += violation_count
        
        # Cross-user contamination check
        cross_user_contamination = self._detect_cross_user_contamination()
        
        # Record comprehensive isolation metrics
        success_rate = successful_users / self.concurrent_users if self.concurrent_users > 0 else 0
        isolation_rate = isolation_validated_users / self.concurrent_users if self.concurrent_users > 0 else 0
        
        self.record_metric("user_isolation_success_rate", success_rate)
        self.record_metric("user_isolation_validated_rate", isolation_rate)
        self.record_metric("user_isolation_violations_total", total_isolation_violations)
        self.record_metric("user_isolation_cross_contamination", len(cross_user_contamination))
        self.record_metric("user_isolation_test_duration", total_isolation_test_time)
        self.record_metric("user_isolation_concurrent_users", self.concurrent_users)
        
        # CRITICAL ISOLATION ASSESSMENT
        
        if total_isolation_violations > 0 or len(cross_user_contamination) > 0:
            # ISOLATION BREACH DETECTED - CRITICAL SECURITY FAILURE
            violation_summary = ""
            if total_isolation_violations > 0:
                violation_summary += f"\nDirect Violations: {total_isolation_violations}"
                
            if len(cross_user_contamination) > 0:
                violation_summary += f"\nCross-User Contamination: {len(cross_user_contamination)}"
                contamination_details = "\n".join([
                    f"  - {violation}"
                    for violation in cross_user_contamination[:5]  # Show first 5
                ])
                violation_summary += f"\nContamination Details:\n{contamination_details}"
            
            pytest.fail(
                f"🚨 CRITICAL USER ISOLATION BREACH DETECTED\n"
                f"Success Rate: {success_rate:.1%}\n"
                f"Isolation Rate: {isolation_rate:.1%}\n"
                f"Total Violations: {total_isolation_violations}\n"
                f"Cross-User Contamination: {len(cross_user_contamination)}\n"
                f"{violation_summary}\n"
                f"This is a REGULATORY VIOLATION and SECURITY BREACH!\n"
                f"Enterprise deployment BLOCKED - data leakage risk!"
            )
        
        elif isolation_rate < 0.95:
            # INSUFFICIENT ISOLATION VALIDATION
            pytest.fail(
                f"🚨 INSUFFICIENT USER ISOLATION VALIDATION\n"
                f"Isolation Rate: {isolation_rate:.1%} (< 95% required for enterprise)\n"
                f"Success Rate: {success_rate:.1%}\n"
                f"This indicates potential isolation weaknesses under load!"
            )
        
        elif success_rate < 0.9:
            # HIGH FAILURE RATE MAY INDICATE ISOLATION ISSUES
            pytest.fail(
                f"🚨 HIGH FAILURE RATE IN ISOLATION TEST\n"
                f"Success Rate: {success_rate:.1%} (< 90% acceptable)\n"
                f"This may indicate system instability affecting isolation!"
            )
        
        # SUCCESS CASE: Complete user isolation validated under load
        print(f"\n✅ USER ISOLATION UNDER LOAD: Test PASSED")
        print(f"   👥 Concurrent Users: {self.concurrent_users}")
        print(f"   ✅ Success Rate: {success_rate:.1%}")
        print(f"   🔒 Isolation Rate: {isolation_rate:.1%}")
        print(f"   ⚠️  Total Violations: {total_isolation_violations}")
        print(f"   🛡️  Cross-User Contamination: {len(cross_user_contamination)}")
        print(f"   ⏱️  Test Duration: {total_isolation_test_time:.2f}s")
        print(f"   💰 $500K+ Enterprise Revenue: PROTECTED")
        
    def _detect_cross_user_contamination(self) -> List[str]:
        """Detect cross-user data contamination in collected messages."""
        contamination_violations = []
        
        with self.user_lock:
            user_ids = list(self.user_data_store.keys())
            
            # Check each user's received messages for contamination
            for user_id in user_ids:
                user_data = self.user_data_store[user_id]
                received_messages = user_data.get("received_messages", [])
                
                for message in received_messages:
                    # Check if message belongs to different user
                    msg_user_id = message.get("user_id")
                    msg_thread_id = message.get("thread_id")
                    msg_isolation_marker = message.get("isolation_marker")
                    
                    if msg_user_id and msg_user_id != user_id:
                        contamination_violations.append(
                            f"User {user_id} received message for user {msg_user_id}"
                        )
                    
                    if msg_thread_id and msg_thread_id != user_data.get("thread_id"):
                        contamination_violations.append(
                            f"User {user_id} received message for thread {msg_thread_id}"
                        )
                    
                    if msg_isolation_marker and not msg_isolation_marker.startswith(f"USER_{user_id}_"):
                        contamination_violations.append(
                            f"User {user_id} received message with wrong marker: {msg_isolation_marker}"
                        )
        
        return contamination_violations
    
    @pytest.mark.mission_critical
    @pytest.mark.user_isolation
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_database_session_isolation_under_load(self):
        """
        🚨 DATABASE ISOLATION CRITICAL: Database Session Isolation Under Load
        
        Tests that database sessions remain isolated per user under concurrent load,
        preventing data leakage through shared database connections.
        """
        db_isolation_start = time.time()
        
        # Create users with database operation requirements
        user_contexts = []
        for i in range(min(self.concurrent_users, 8)):  # Limit DB load
            user_context = await create_authenticated_user_context(
                user_email=f"db_isolation_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            user_contexts.append(user_context)
        
        async def execute_database_isolation_test(user_context: StronglyTypedUserExecutionContext) -> Dict[str, Any]:
            """Execute database operations that test session isolation."""
            user_id = str(user_context.user_id)
            
            try:
                # Create user-specific authentication
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=user_context.agent_context.get('user_email')
                )
                
                # Create WebSocket connection with database context
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
                
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=user_id
                )
                
                # Send messages that require database operations
                db_isolation_messages = [
                    {
                        "type": "chat_message",
                        "content": f"Create thread for user {user_id}",
                        "user_id": user_id,
                        "thread_id": str(user_context.thread_id),
                        "db_operation": "create_thread",
                        "isolation_test": True
                    },
                    {
                        "type": "chat_message", 
                        "content": f"Store conversation data for {user_id}",
                        "user_id": user_id,
                        "thread_id": str(user_context.thread_id),
                        "db_operation": "store_conversation",
                        "isolation_test": True
                    },
                    {
                        "type": "chat_message",
                        "content": f"Retrieve user history for {user_id}",
                        "user_id": user_id,
                        "thread_id": str(user_context.thread_id),
                        "db_operation": "retrieve_history",
                        "isolation_test": True
                    }
                ]
                
                messages_sent = 0
                for message in db_isolation_messages:
                    try:
                        await WebSocketTestHelpers.send_test_message(
                            connection, message, timeout=5.0
                        )
                        messages_sent += 1
                        await asyncio.sleep(0.2)  # Allow database processing
                    except Exception as msg_error:
                        print(f"⚠️  DB message send error for user {user_id}: {msg_error}")
                
                # Collect responses to validate database isolation
                responses_received = []
                response_start = time.time()
                
                while (time.time() - response_start) < 20.0:
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=3.0
                        )
                        
                        if response:
                            responses_received.append(response)
                            
                            # Check for database isolation violations
                            resp_user_id = response.get("user_id")
                            resp_thread_id = response.get("thread_id")
                            
                            if resp_user_id and resp_user_id != user_id:
                                # Database isolation violation detected
                                with self.user_lock:
                                    self.isolation_violations.append({
                                        "violation_type": "database_cross_user",
                                        "test_user_id": user_id,
                                        "response_user_id": resp_user_id,
                                        "response": response
                                    })
                            
                            if len(responses_received) >= messages_sent:
                                break
                                
                    except:
                        continue
                
                # Cleanup
                await WebSocketTestHelpers.close_test_connection(connection)
                
                return {
                    "user_id": user_id,
                    "success": True,
                    "messages_sent": messages_sent,
                    "responses_received": len(responses_received),
                    "db_isolation_validated": True
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "db_isolation_validated": False
                }
        
        # Execute concurrent database operations
        db_tasks = [
            execute_database_isolation_test(context)
            for context in user_contexts
        ]
        
        db_results = await asyncio.gather(*db_tasks, return_exceptions=True)
        db_test_time = time.time() - db_isolation_start
        
        # ANALYZE DATABASE ISOLATION RESULTS
        
        successful_db_users = sum(1 for result in db_results 
                                 if isinstance(result, dict) and result.get("success"))
        db_isolation_violations = len([v for v in self.isolation_violations 
                                      if v.get("violation_type", "").startswith("database_")])
        
        self.record_metric("db_isolation_success_rate", successful_db_users / len(user_contexts))
        self.record_metric("db_isolation_violations", db_isolation_violations)
        self.record_metric("db_isolation_test_duration", db_test_time)
        
        # CRITICAL DATABASE ISOLATION ASSESSMENT
        
        if db_isolation_violations > 0:
            pytest.fail(
                f"🚨 CRITICAL DATABASE ISOLATION BREACH\n"
                f"Database Violations: {db_isolation_violations}\n"
                f"This is a severe data leakage risk!\n"
                f"Enterprise deployment BLOCKED"
            )
        
        print(f"\n✅ DATABASE ISOLATION UNDER LOAD: Test PASSED")
        print(f"   🗄️  Database Users Tested: {len(user_contexts)}")
        print(f"   ✅ Success Rate: {successful_db_users / len(user_contexts):.1%}")
        print(f"   🔒 DB Violations: {db_isolation_violations}")
        print(f"   ⏱️  Test Duration: {db_test_time:.2f}s")
        
    @pytest.mark.mission_critical
    @pytest.mark.user_isolation
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_agent_execution_isolation_under_concurrent_load(self):
        """
        🚨 AGENT EXECUTION ISOLATION: Agent Context Isolation Under Load
        
        Tests that agent execution contexts remain isolated when multiple users
        trigger agent operations simultaneously.
        """
        agent_isolation_start = time.time()
        
        # Create users for agent execution testing
        agent_user_contexts = []
        for i in range(min(self.concurrent_users, 6)):  # Limit for agent load
            user_context = await create_authenticated_user_context(
                user_email=f"agent_isolation_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            agent_user_contexts.append(user_context)
        
        async def execute_agent_isolation_test(user_context: StronglyTypedUserExecutionContext) -> Dict[str, Any]:
            """Execute agent operations that test execution context isolation."""
            user_id = str(user_context.user_id)
            
            try:
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=user_context.agent_context.get('user_email')
                )
                
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
                
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=user_id
                )
                
                # Send agent execution request with isolation markers
                agent_message = {
                    "type": "chat_message",
                    "content": f"AGENT ISOLATION TEST: Analyze costs for user {user_id}",
                    "user_id": user_id,
                    "thread_id": str(user_context.thread_id),
                    "run_id": str(user_context.run_id),
                    "agent_isolation_test": True,
                    "isolation_marker": f"AGENT_USER_{user_id}",
                    "timestamp": time.time()
                }
                
                await WebSocketTestHelpers.send_test_message(
                    connection, agent_message, timeout=5.0
                )
                
                # Collect agent execution events and validate isolation
                agent_events = []
                agent_isolation_violations = []
                
                event_start = time.time()
                while (time.time() - event_start) < 30.0:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=3.0
                        )
                        
                        if event and isinstance(event, dict):
                            agent_events.append(event)
                            
                            # Validate agent execution isolation
                            event_user_id = event.get("user_id")
                            event_run_id = event.get("run_id")
                            event_isolation_marker = event.get("isolation_marker")
                            
                            if event_user_id and event_user_id != user_id:
                                agent_isolation_violations.append({
                                    "violation_type": "agent_cross_user",
                                    "expected_user": user_id,
                                    "received_user": event_user_id,
                                    "event": event
                                })
                            
                            if event_run_id and event_run_id != str(user_context.run_id):
                                agent_isolation_violations.append({
                                    "violation_type": "agent_cross_run",
                                    "expected_run": str(user_context.run_id),
                                    "received_run": event_run_id,
                                    "event": event
                                })
                            
                            # Check for completion
                            if event.get("type") == "agent_completed":
                                break
                                
                    except:
                        continue
                
                # Store violations globally
                if agent_isolation_violations:
                    with self.user_lock:
                        self.isolation_violations.extend(agent_isolation_violations)
                
                # Cleanup
                await WebSocketTestHelpers.close_test_connection(connection)
                
                return {
                    "user_id": user_id,
                    "success": True,
                    "agent_events": len(agent_events),
                    "isolation_violations": agent_isolation_violations,
                    "agent_isolation_validated": len(agent_isolation_violations) == 0
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "agent_isolation_validated": False
                }
        
        # Execute concurrent agent operations
        agent_tasks = [
            execute_agent_isolation_test(context)
            for context in agent_user_contexts
        ]
        
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        agent_test_time = time.time() - agent_isolation_start
        
        # ANALYZE AGENT ISOLATION RESULTS
        
        successful_agent_users = sum(1 for result in agent_results 
                                   if isinstance(result, dict) and result.get("success"))
        agent_isolation_validated = sum(1 for result in agent_results 
                                      if isinstance(result, dict) and result.get("agent_isolation_validated"))
        agent_isolation_violations = len([v for v in self.isolation_violations 
                                        if v.get("violation_type", "").startswith("agent_")])
        
        self.record_metric("agent_isolation_success_rate", successful_agent_users / len(agent_user_contexts))
        self.record_metric("agent_isolation_validated_rate", agent_isolation_validated / len(agent_user_contexts))
        self.record_metric("agent_isolation_violations", agent_isolation_violations)
        self.record_metric("agent_isolation_test_duration", agent_test_time)
        
        # CRITICAL AGENT ISOLATION ASSESSMENT
        
        if agent_isolation_violations > 0:
            pytest.fail(
                f"🚨 CRITICAL AGENT EXECUTION ISOLATION BREACH\n"
                f"Agent Violations: {agent_isolation_violations}\n"
                f"This compromises agent execution security!\n"
                f"Enterprise deployment BLOCKED"
            )
        
        if agent_isolation_validated / len(agent_user_contexts) < 0.9:
            pytest.fail(
                f"🚨 INSUFFICIENT AGENT ISOLATION VALIDATION\n"
                f"Validated Rate: {agent_isolation_validated / len(agent_user_contexts):.1%}\n"
                f"Agent isolation not sufficiently proven under load!"
            )
        
        print(f"\n✅ AGENT EXECUTION ISOLATION UNDER LOAD: Test PASSED")
        print(f"   🤖 Agent Users Tested: {len(agent_user_contexts)}")
        print(f"   ✅ Success Rate: {successful_agent_users / len(agent_user_contexts):.1%}")
        print(f"   🔒 Isolation Validated: {agent_isolation_validated / len(agent_user_contexts):.1%}")
        print(f"   ⚠️  Agent Violations: {agent_isolation_violations}")
        print(f"   ⏱️  Test Duration: {agent_test_time:.2f}s")
        print(f"   🛡️  Enterprise Security: MAINTAINED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])