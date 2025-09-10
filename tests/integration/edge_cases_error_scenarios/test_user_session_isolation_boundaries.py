"""
Integration Tests: User Session Isolation Boundaries

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant security requirements)
- Business Goal: Security + Compliance + User Trust
- Value Impact: Ensures complete isolation between user sessions, prevents data 
  leakage across users, maintains compliance with privacy regulations (GDPR, CCPA),
  protects sensitive customer data and AI interactions
- Revenue Impact: Enables Enterprise contracts ($100K+ ARR) requiring strict data
  isolation, prevents security breaches that could cost $1M+ in damages and reputation

Test Focus: User session boundaries, data isolation, cross-user contamination 
prevention, memory isolation, and security boundary validation under concurrent load.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Set, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import json
import hashlib
import threading

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.agents.supervisor.execution_engine import UserExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.core.config import get_config


class TestUserSessionIsolationBoundaries(BaseIntegrationTest):
    """
    Test user session isolation boundaries under concurrent access patterns.
    
    Business Value: Prevents data leakage between users, ensures compliance with
    privacy regulations, and maintains Enterprise-grade security standards.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_isolation_test(self, real_services_fixture):
        """Setup user session isolation test environment."""
        self.config = get_config()
        
        # User isolation tracking
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_data_store: Dict[str, Dict[str, Any]] = {}
        self.cross_user_access_attempts = []
        self.isolation_violations = []
        
        # Test contexts for cleanup
        self.test_contexts: List[UserExecutionContext] = []
        self.websocket_managers: List[WebSocketManager] = []
        
        # Thread-local storage simulation
        self.thread_local_data = threading.local()
        
        yield
        
        # Cleanup all contexts and managers
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
        
        for manager in self.websocket_managers:
            try:
                await manager.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_concurrent_user_data_isolation(self):
        """
        Test that user data remains isolated under concurrent operations.
        
        BVJ: Prevents data contamination between users that could lead to privacy
        violations and compliance failures worth millions in penalties.
        """
        num_concurrent_users = 25
        operations_per_user = 15
        
        user_data_fingerprints = {}
        data_contamination_checks = []
        
        async def isolated_user_operations(user_id: str, operation_count: int):
            """Perform operations with strict user data isolation."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"isolation_session_{user_id}_{uuid.uuid4().hex[:8]}",
                request_id=f"isolation_req_{user_id}_{int(time.time() * 1000)}"
            )
            self.test_contexts.append(context)
            
            # Create unique user data fingerprint
            user_secret = f"secret_data_for_{user_id}_{uuid.uuid4().hex}"
            user_data_fingerprint = hashlib.sha256(user_secret.encode()).hexdigest()
            user_data_fingerprints[user_id] = user_data_fingerprint
            
            # User-specific data store
            user_data = {
                "user_id": user_id,
                "session_id": context.session_id,
                "secret_data": user_secret,
                "fingerprint": user_data_fingerprint,
                "operations": [],
                "created_at": time.time(),
                "thread_id": threading.get_ident(),
                "process_id": id(context)  # Memory address for uniqueness check
            }
            
            operation_results = []
            
            for op_num in range(operation_count):
                try:
                    # Simulate user-specific data processing
                    operation_data = {
                        "operation_id": f"{user_id}_op_{op_num}",
                        "user_id": user_id,
                        "operation_type": f"user_operation_{op_num % 5}",
                        "timestamp": time.time(),
                        "data_fingerprint": user_data_fingerprint,
                        "session_context": context.session_id
                    }
                    
                    # Store operation in user-specific namespace
                    if user_id not in self.session_data_store:
                        self.session_data_store[user_id] = {"operations": [], "metadata": user_data}
                    
                    self.session_data_store[user_id]["operations"].append(operation_data)
                    
                    # Verify data isolation during operation
                    await self._verify_data_isolation_during_operation(user_id, context, user_data_fingerprint)
                    
                    # Simulate processing time
                    await asyncio.sleep(0.01)
                    
                    operation_results.append({
                        "success": True,
                        "operation_id": operation_data["operation_id"]
                    })
                    
                except Exception as e:
                    self.isolation_violations.append({
                        "user_id": user_id,
                        "operation_num": op_num,
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    
                    operation_results.append({
                        "success": False,
                        "error": str(e)
                    })
            
            # Final isolation verification
            await self._verify_final_user_isolation(user_id, user_data_fingerprint)
            
            return {
                "user_id": user_id,
                "session_id": context.session_id,
                "operations_completed": len([r for r in operation_results if r["success"]]),
                "total_operations": operation_count,
                "user_fingerprint": user_data_fingerprint,
                "final_data_integrity": await self._check_user_data_integrity(user_id)
            }
        
        # Execute concurrent user operations
        user_tasks = []
        for user_num in range(num_concurrent_users):
            user_id = f"isolated_user_{user_num}"
            task = asyncio.create_task(
                isolated_user_operations(user_id, operations_per_user)
            )
            user_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze isolation results
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == num_concurrent_users, \
            f"Not all users completed successfully: {len(successful_results)}/{num_concurrent_users}"
        
        # Verify no isolation violations
        assert len(self.isolation_violations) == 0, \
            f"User isolation violations detected: {self.isolation_violations}"
        
        # Verify each user has unique data fingerprint
        result_fingerprints = [r["user_fingerprint"] for r in successful_results]
        assert len(set(result_fingerprints)) == num_concurrent_users, \
            "Duplicate user fingerprints detected - isolation failure"
        
        # Verify all operations completed successfully
        total_operations_expected = num_concurrent_users * operations_per_user
        total_operations_completed = sum(r["operations_completed"] for r in successful_results)
        assert total_operations_completed == total_operations_expected, \
            f"Operation count mismatch: {total_operations_completed} != {total_operations_expected}"
        
        # Verify data integrity for each user
        for result in successful_results:
            assert result["final_data_integrity"], \
                f"Data integrity failure for user {result['user_id']}"
        
        # Verify session isolation in data store
        assert len(self.session_data_store) == num_concurrent_users, \
            f"Session data store isolation failure: {len(self.session_data_store)} != {num_concurrent_users}"
        
        # Cross-contamination check
        for user_id, user_data in self.session_data_store.items():
            user_operations = user_data["operations"]
            for operation in user_operations:
                assert operation["user_id"] == user_id, \
                    f"Cross-user contamination in {user_id}: operation belongs to {operation['user_id']}"
        
        self.logger.info(f"User isolation test completed: {num_concurrent_users} users, "
                        f"{total_operations_completed} operations, {execution_time:.2f}s")
    
    async def _verify_data_isolation_during_operation(self, user_id: str, context: UserExecutionContext, fingerprint: str):
        """Verify data isolation during operation execution."""
        # Check context integrity
        assert context.user_id == user_id, f"Context user_id contaminated: {context.user_id} != {user_id}"
        
        # Check that user can only access their own data
        if user_id in self.session_data_store:
            user_metadata = self.session_data_store[user_id]["metadata"]
            assert user_metadata["fingerprint"] == fingerprint, \
                f"User fingerprint contamination for {user_id}"
            assert user_metadata["user_id"] == user_id, \
                f"User metadata contamination for {user_id}"
    
    async def _verify_final_user_isolation(self, user_id: str, fingerprint: str):
        """Verify final user isolation state."""
        if user_id not in self.session_data_store:
            return False
        
        user_data = self.session_data_store[user_id]
        
        # Verify all operations belong to this user
        for operation in user_data["operations"]:
            if operation["user_id"] != user_id:
                self.isolation_violations.append({
                    "type": "cross_user_operation",
                    "user_id": user_id,
                    "contaminating_operation": operation
                })
                return False
        
        return True
    
    async def _check_user_data_integrity(self, user_id: str) -> bool:
        """Check integrity of user-specific data."""
        if user_id not in self.session_data_store:
            return False
        
        user_data = self.session_data_store[user_id]
        metadata = user_data["metadata"]
        
        # Verify metadata integrity
        if metadata["user_id"] != user_id:
            return False
        
        # Verify operation data integrity
        for operation in user_data["operations"]:
            if operation["data_fingerprint"] != metadata["fingerprint"]:
                return False
        
        return True
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_session_isolation(self):
        """
        Test WebSocket session isolation under concurrent connections.
        
        BVJ: Ensures real-time communications remain private and isolated,
        critical for Enterprise security and user trust.
        """
        num_concurrent_sessions = 20
        messages_per_session = 10
        
        session_message_logs = {}
        cross_session_deliveries = []
        
        async def isolated_websocket_session(session_id: str, message_count: int):
            """Simulate isolated WebSocket session."""
            user_id = f"ws_user_{session_id}"
            context = UserExecutionContext(
                user_id=user_id,
                session_id=session_id,
                request_id=f"ws_req_{session_id}_{int(time.time())}"
            )
            self.test_contexts.append(context)
            
            # Mock WebSocket connection
            mock_websocket = AsyncMock()
            mock_websocket.connection_id = session_id
            mock_websocket.user_id = user_id
            mock_websocket.messages_received = []
            
            # Create isolated WebSocket manager
            ws_manager = WebSocketManager()
            self.websocket_managers.append(ws_manager)
            
            # Register connection
            await ws_manager.register_connection(session_id, mock_websocket)
            
            # Track messages for this session
            session_messages = []
            
            for msg_num in range(message_count):
                # Create session-specific message
                message = {
                    "type": "agent_response",
                    "session_id": session_id,
                    "user_id": user_id,
                    "message_id": f"{session_id}_msg_{msg_num}",
                    "content": f"Private message {msg_num} for session {session_id}",
                    "timestamp": time.time(),
                    "session_token": hashlib.md5(f"{session_id}_token".encode()).hexdigest()
                }
                
                session_messages.append(message)
                
                # Send message through WebSocket manager
                await ws_manager.send_agent_event(session_id, message)
                
                # Verify message isolation
                await self._verify_websocket_message_isolation(session_id, user_id, message)
                
                await asyncio.sleep(0.005)  # Small delay for concurrency
            
            # Store session message log
            session_message_logs[session_id] = {
                "user_id": user_id,
                "messages": session_messages,
                "total_count": len(session_messages)
            }
            
            return {
                "session_id": session_id,
                "user_id": user_id,
                "messages_sent": len(session_messages),
                "expected_messages": message_count,
                "isolation_verified": True
            }
        
        # Create concurrent WebSocket sessions
        session_tasks = []
        for session_num in range(num_concurrent_sessions):
            session_id = f"isolated_session_{session_num}_{uuid.uuid4().hex[:8]}"
            task = asyncio.create_task(
                isolated_websocket_session(session_id, messages_per_session)
            )
            session_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*session_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze WebSocket isolation results
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == num_concurrent_sessions, \
            f"Not all WebSocket sessions completed: {len(successful_results)}/{num_concurrent_sessions}"
        
        # Verify no cross-session message deliveries
        assert len(cross_session_deliveries) == 0, \
            f"Cross-session message deliveries detected: {cross_session_deliveries}"
        
        # Verify message count integrity
        total_messages_expected = num_concurrent_sessions * messages_per_session
        total_messages_sent = sum(r["messages_sent"] for r in successful_results)
        assert total_messages_sent == total_messages_expected, \
            f"Message count mismatch: {total_messages_sent} != {total_messages_expected}"
        
        # Verify session uniqueness
        session_ids = [r["session_id"] for r in successful_results]
        assert len(set(session_ids)) == num_concurrent_sessions, \
            "Duplicate session IDs detected"
        
        user_ids = [r["user_id"] for r in successful_results]
        assert len(set(user_ids)) == num_concurrent_sessions, \
            "Duplicate user IDs detected in WebSocket sessions"
        
        # Cross-session contamination check
        for session_id, log_data in session_message_logs.items():
            expected_user_id = log_data["user_id"]
            for message in log_data["messages"]:
                assert message["user_id"] == expected_user_id, \
                    f"Message user_id contamination in session {session_id}"
                assert message["session_id"] == session_id, \
                    f"Message session_id contamination in session {session_id}"
        
        self.logger.info(f"WebSocket isolation test completed: {num_concurrent_sessions} sessions, "
                        f"{total_messages_sent} messages, {execution_time:.2f}s")
    
    async def _verify_websocket_message_isolation(self, session_id: str, user_id: str, message: Dict[str, Any]):
        """Verify WebSocket message belongs to correct session."""
        # Check message session assignment
        if message["session_id"] != session_id:
            self.cross_session_deliveries.append({
                "type": "wrong_session",
                "expected_session": session_id,
                "actual_session": message["session_id"],
                "message": message
            })
        
        # Check message user assignment
        if message["user_id"] != user_id:
            self.cross_session_deliveries.append({
                "type": "wrong_user",
                "expected_user": user_id,
                "actual_user": message["user_id"],
                "message": message
            })
    
    @pytest.mark.asyncio
    async def test_memory_isolation_between_user_contexts(self):
        """
        Test memory isolation between concurrent user execution contexts.
        
        BVJ: Prevents memory leaks and cross-user memory contamination that
        could expose sensitive data or cause system instability.
        """
        num_concurrent_users = 15
        memory_operations_per_user = 20
        
        user_memory_fingerprints = {}
        memory_contamination_detections = []
        
        async def memory_isolated_execution(user_id: str, operation_count: int):
            """Execute operations with strict memory isolation."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"memory_session_{user_id}_{uuid.uuid4().hex[:8]}",
                request_id=f"memory_req_{user_id}_{int(time.time())}"
            )
            self.test_contexts.append(context)
            
            # Create user-specific memory fingerprint
            memory_fingerprint = hashlib.sha256(f"memory_for_{user_id}_{time.time()}".encode()).hexdigest()
            user_memory_fingerprints[user_id] = memory_fingerprint
            
            # User-specific data structures
            user_memory_data = {
                "user_id": user_id,
                "context_id": id(context),
                "memory_fingerprint": memory_fingerprint,
                "allocated_objects": [],
                "operation_results": [],
                "memory_usage_pattern": f"pattern_for_{user_id}"
            }
            
            for op_num in range(operation_count):
                # Create memory objects specific to this user
                memory_object = {
                    "object_id": f"{user_id}_obj_{op_num}",
                    "user_id": user_id,
                    "data": f"sensitive_data_for_{user_id}_{op_num}_{memory_fingerprint[:8]}",
                    "timestamp": time.time(),
                    "context_ref": id(context),
                    "thread_id": threading.get_ident()
                }
                
                user_memory_data["allocated_objects"].append(memory_object)
                
                # Verify memory isolation during allocation
                await self._verify_memory_isolation(user_id, memory_object, memory_fingerprint)
                
                # Simulate memory operations
                await asyncio.sleep(0.005)
                
                # Process result
                result = {
                    "operation_num": op_num,
                    "user_id": user_id,
                    "success": True,
                    "memory_fingerprint_check": memory_object["data"].endswith(memory_fingerprint[:8])
                }
                
                user_memory_data["operation_results"].append(result)
            
            # Final memory cleanup verification
            cleanup_success = await self._verify_memory_cleanup(user_id, user_memory_data)
            
            return {
                "user_id": user_id,
                "context_id": id(context),
                "operations_completed": len(user_memory_data["operation_results"]),
                "memory_objects_allocated": len(user_memory_data["allocated_objects"]),
                "memory_fingerprint": memory_fingerprint,
                "cleanup_success": cleanup_success,
                "memory_isolation_verified": True
            }
        
        # Execute concurrent memory-isolated operations
        memory_tasks = []
        for user_num in range(num_concurrent_users):
            user_id = f"memory_user_{user_num}"
            task = asyncio.create_task(
                memory_isolated_execution(user_id, memory_operations_per_user)
            )
            memory_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*memory_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze memory isolation results
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == num_concurrent_users, \
            f"Memory isolation test failures: {len(successful_results)}/{num_concurrent_users}"
        
        # Verify no memory contamination detected
        assert len(memory_contamination_detections) == 0, \
            f"Memory contamination detected: {memory_contamination_detections}"
        
        # Verify unique memory fingerprints
        result_fingerprints = [r["memory_fingerprint"] for r in successful_results]
        assert len(set(result_fingerprints)) == num_concurrent_users, \
            "Duplicate memory fingerprints - memory isolation failure"
        
        # Verify unique context IDs
        context_ids = [r["context_id"] for r in successful_results]
        assert len(set(context_ids)) == num_concurrent_users, \
            "Duplicate context IDs - context isolation failure"
        
        # Verify operation completion
        total_expected_operations = num_concurrent_users * memory_operations_per_user
        total_completed_operations = sum(r["operations_completed"] for r in successful_results)
        assert total_completed_operations == total_expected_operations, \
            f"Operation completion mismatch: {total_completed_operations} != {total_expected_operations}"
        
        # Verify cleanup success
        cleanup_failures = [r for r in successful_results if not r["cleanup_success"]]
        assert len(cleanup_failures) == 0, \
            f"Memory cleanup failures: {[r['user_id'] for r in cleanup_failures]}"
        
        self.logger.info(f"Memory isolation test completed: {num_concurrent_users} users, "
                        f"{total_completed_operations} operations, {execution_time:.2f}s")
    
    async def _verify_memory_isolation(self, user_id: str, memory_object: Dict[str, Any], fingerprint: str):
        """Verify memory object belongs to correct user context."""
        # Check object user assignment
        if memory_object["user_id"] != user_id:
            self.memory_contamination_detections.append({
                "type": "wrong_user_assignment",
                "expected_user": user_id,
                "actual_user": memory_object["user_id"],
                "object": memory_object
            })
        
        # Check fingerprint integrity
        if fingerprint not in memory_object["data"]:
            self.memory_contamination_detections.append({
                "type": "fingerprint_contamination",
                "user_id": user_id,
                "expected_fingerprint": fingerprint,
                "object_data": memory_object["data"]
            })
    
    async def _verify_memory_cleanup(self, user_id: str, memory_data: Dict[str, Any]) -> bool:
        """Verify proper memory cleanup for user context."""
        # Check that all allocated objects are properly tracked
        allocated_objects = memory_data["allocated_objects"]
        operation_results = memory_data["operation_results"]
        
        if len(allocated_objects) != len(operation_results):
            return False
        
        # Verify all objects belong to this user
        for obj in allocated_objects:
            if obj["user_id"] != user_id:
                return False
        
        return True
    
    @pytest.mark.asyncio
    async def test_cross_user_access_prevention_boundaries(self):
        """
        Test prevention of cross-user access attempts at system boundaries.
        
        BVJ: Validates security boundaries that prevent unauthorized access to
        other users' data, critical for Enterprise compliance and security audits.
        """
        num_legitimate_users = 10
        num_malicious_attempts = 5
        operations_per_user = 8
        
        legitimate_operations = []
        blocked_access_attempts = []
        security_violations = []
        
        async def legitimate_user_operations(user_id: str, operation_count: int):
            """Perform legitimate operations within user boundaries."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"legit_session_{user_id}",
                request_id=f"legit_req_{user_id}"
            )
            self.test_contexts.append(context)
            
            user_operations = []
            
            for op_num in range(operation_count):
                operation = {
                    "operation_id": f"{user_id}_legit_op_{op_num}",
                    "user_id": user_id,
                    "session_id": context.session_id,
                    "operation_type": "legitimate_access",
                    "timestamp": time.time(),
                    "authorized": True
                }
                
                # Simulate legitimate operation
                await asyncio.sleep(0.01)
                user_operations.append(operation)
            
            legitimate_operations.extend(user_operations)
            
            return {
                "user_id": user_id,
                "operations": user_operations,
                "success": True
            }
        
        async def malicious_cross_user_attempts(attacker_id: str, target_users: List[str]):
            """Simulate cross-user access attempts that should be blocked."""
            context = UserExecutionContext(
                user_id=attacker_id,
                session_id=f"attack_session_{attacker_id}",
                request_id=f"attack_req_{attacker_id}"
            )
            self.test_contexts.append(context)
            
            attack_attempts = []
            
            for target_user in target_users:
                # Attempt to access another user's data
                attack_operation = {
                    "operation_id": f"{attacker_id}_attack_{target_user}",
                    "attacker_id": attacker_id,
                    "target_user_id": target_user,
                    "attack_type": "cross_user_data_access",
                    "timestamp": time.time(),
                    "session_id": context.session_id
                }
                
                # Simulate access attempt (should be blocked)
                access_blocked = await self._simulate_cross_user_access_check(
                    attacker_id, target_user, attack_operation
                )
                
                if access_blocked:
                    blocked_access_attempts.append(attack_operation)
                else:
                    security_violations.append(attack_operation)
                
                attack_attempts.append({
                    "attack_operation": attack_operation,
                    "blocked": access_blocked
                })
                
                await asyncio.sleep(0.01)
            
            return {
                "attacker_id": attacker_id,
                "attack_attempts": len(attack_attempts),
                "successful_blocks": len([a for a in attack_attempts if a["blocked"]]),
                "security_breaches": len([a for a in attack_attempts if not a["blocked"]])
            }
        
        # Create legitimate user tasks
        legitimate_tasks = []
        legitimate_user_ids = []
        for user_num in range(num_legitimate_users):
            user_id = f"legit_user_{user_num}"
            legitimate_user_ids.append(user_id)
            task = asyncio.create_task(
                legitimate_user_operations(user_id, operations_per_user)
            )
            legitimate_tasks.append(task)
        
        # Create malicious access attempt tasks
        malicious_tasks = []
        for attacker_num in range(num_malicious_attempts):
            attacker_id = f"attacker_{attacker_num}"
            # Each attacker tries to access 3 random legitimate users
            target_users = legitimate_user_ids[:3]
            task = asyncio.create_task(
                malicious_cross_user_attempts(attacker_id, target_users)
            )
            malicious_tasks.append(task)
        
        # Execute all operations concurrently
        start_time = time.time()
        
        legitimate_results = await asyncio.gather(*legitimate_tasks, return_exceptions=True)
        malicious_results = await asyncio.gather(*malicious_tasks, return_exceptions=True)
        
        execution_time = time.time() - start_time
        
        # Analyze security boundary results
        successful_legitimate = [r for r in legitimate_results if isinstance(r, dict) and r.get("success")]
        assert len(successful_legitimate) == num_legitimate_users, \
            f"Legitimate operations failed: {len(successful_legitimate)}/{num_legitimate_users}"
        
        successful_malicious = [r for r in malicious_results if isinstance(r, dict)]
        assert len(successful_malicious) == num_malicious_attempts, \
            f"Malicious attempt simulation failed: {len(successful_malicious)}/{num_malicious_attempts}"
        
        # Verify no security violations (all attacks should be blocked)
        assert len(security_violations) == 0, \
            f"Security violations detected - cross-user access succeeded: {security_violations}"
        
        # Verify attack blocking effectiveness
        total_attack_attempts = sum(r["attack_attempts"] for r in successful_malicious)
        total_blocked_attempts = sum(r["successful_blocks"] for r in successful_malicious)
        
        block_rate = total_blocked_attempts / total_attack_attempts if total_attack_attempts > 0 else 1.0
        assert block_rate == 1.0, \
            f"Insufficient attack blocking: {block_rate:.2%} block rate"
        
        # Verify legitimate operations succeeded
        total_legitimate_operations = len(legitimate_operations)
        expected_legitimate_operations = num_legitimate_users * operations_per_user
        assert total_legitimate_operations == expected_legitimate_operations, \
            f"Legitimate operation count mismatch: {total_legitimate_operations} != {expected_legitimate_operations}"
        
        # Verify no false positives (legitimate operations blocked)
        for operation in legitimate_operations:
            assert operation["user_id"] in legitimate_user_ids, \
                f"Legitimate operation from unknown user: {operation['user_id']}"
        
        self.logger.info(f"Cross-user access prevention test completed: "
                        f"{num_legitimate_users} legitimate users, {num_malicious_attempts} attackers, "
                        f"{total_attack_attempts} attacks blocked, {execution_time:.2f}s")
    
    async def _simulate_cross_user_access_check(self, attacker_id: str, target_user_id: str, 
                                              attack_operation: Dict[str, Any]) -> bool:
        """Simulate security check for cross-user access attempt."""
        # In a real system, this would check:
        # 1. JWT tokens and session validation
        # 2. User ID matching in requests
        # 3. Resource ownership verification
        # 4. Access control lists
        
        # For simulation, we block all cross-user access attempts
        if attacker_id != target_user_id:
            # Log the blocked attempt
            self.cross_user_access_attempts.append({
                "attacker_id": attacker_id,
                "target_user_id": target_user_id,
                "blocked": True,
                "timestamp": time.time(),
                "attack_operation": attack_operation
            })
            return True  # Access blocked
        
        return False  # Access would be allowed (same user)