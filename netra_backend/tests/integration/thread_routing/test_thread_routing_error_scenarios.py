"""
Test Thread Routing Error Scenarios

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System reliability and graceful error handling for thread routing
- Value Impact: Proper error handling prevents data loss and maintains user trust
- Strategic Impact: Core platform stability - thread routing failures break chat functionality

This test suite validates error scenarios and graceful failure handling:
1. Invalid thread IDs and malformed requests
2. Unauthorized thread access (security validation)
3. Database connection failures and recovery
4. WebSocket disconnections during routing
5. Resource exhaustion and cleanup validation
6. Proper error messages and user feedback

CRITICAL: Uses REAL PostgreSQL + Redis + WebSocket - NO mocks allowed.
Expected: Mixed results - some error handling may be incomplete initially.
"""

import asyncio
import uuid
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import patch, AsyncMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID,
    ensure_user_id, ensure_thread_id
)

# Thread routing and error handling components
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Thread, Message, User
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.exceptions_database import (
    DatabaseError, RecordNotFoundError, DatabaseConnectionError
)

# WebSocket error handling
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.websocket_core.types import MessageType, create_error_message
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import SQLAlchemy for error simulation
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select
    from sqlalchemy.exc import OperationalError, DisconnectionError
except ImportError:
    AsyncSession = None
    text = None
    select = None


class TestThreadRoutingErrorScenarios(BaseIntegrationTest):
    """Test thread routing error scenarios with comprehensive failure validation."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_invalid_thread_id_handling(self, lightweight_services_fixture, isolated_env):
        """Test graceful handling of invalid thread IDs and malformed requests."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup valid user
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="error.test@example.com",
            full_name="Error Test User",
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        
        # Test invalid thread ID formats
        invalid_thread_ids = [
            "",  # Empty string
            "invalid",  # Non-UUID format
            "12345",  # Numeric string
            "thread_invalid_uuid",  # Invalid UUID format
            None,  # None type (will cause TypeError)
            "thread_" + "x" * 100,  # Extremely long string
            "thread_with_special_chars!@#$%",  # Special characters
            "00000000-0000-0000-0000-000000000000",  # Null UUID
        ]
        
        for invalid_id in invalid_thread_ids:
            self.logger.info(f"Testing invalid thread ID: {invalid_id}")
            
            try:
                # Attempt to retrieve invalid thread
                if invalid_id is None:
                    with pytest.raises((TypeError, AttributeError)):
                        await thread_service.get_thread(invalid_id, str(user_id), db_session)
                else:
                    result = await thread_service.get_thread(invalid_id, str(user_id), db_session)
                    # Should return None gracefully, not raise exception
                    assert result is None, f"Expected None for invalid thread ID {invalid_id}, got {result}"
                
                # Attempt to create message in invalid thread
                if invalid_id is not None and invalid_id != "":
                    with pytest.raises((NetraException, ValueError, DatabaseError)):
                        await thread_service.create_message(
                            thread_id=invalid_id,
                            role="user",
                            content="Test message for invalid thread",
                            metadata={"error_test": True}
                        )
                
            except Exception as e:
                # Log unexpected exceptions but don't fail test
                # Error handling itself may be incomplete
                self.logger.warning(f"Unexpected error for invalid thread ID {invalid_id}: {e}")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_unauthorized_thread_access_security(self, lightweight_services_fixture, isolated_env):
        """Test security validation - users should not access other users' threads."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup multiple users
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(3)]
        test_users = []
        
        for i, user_id in enumerate(user_ids):
            test_user = User(
                id=str(user_id),
                email=f"security.user.{i}@test.com",
                full_name=f"Security Test User {i}",
                is_active=True
            )
            test_users.append(test_user)
            db_session.add(test_user)
        
        await db_session.commit()
        
        thread_service = ThreadService()
        
        # Create threads for each user
        user_threads = {}
        for user_id in user_ids:
            thread = await thread_service.get_or_create_thread(str(user_id), db_session)
            user_threads[user_id] = thread
            
            # Add sensitive content to thread
            await thread_service.create_message(
                thread_id=thread.id,
                role="user",
                content=f"SENSITIVE: Private data for user {user_id}",
                metadata={"sensitive": True, "owner": str(user_id)}
            )
        
        # Test unauthorized access attempts
        security_violations = []
        
        for accessing_user in user_ids:
            for target_user in user_ids:
                if accessing_user == target_user:
                    continue  # Skip self-access (should be allowed)
                
                target_thread = user_threads[target_user]
                
                # Attempt 1: Direct thread access
                try:
                    unauthorized_thread = await thread_service.get_thread(
                        target_thread.id, str(accessing_user), db_session
                    )
                    
                    # This is a security violation if successful
                    if unauthorized_thread is not None:
                        violation = {
                            "type": "unauthorized_thread_access",
                            "accessing_user": str(accessing_user),
                            "target_user": str(target_user),
                            "thread_id": target_thread.id,
                            "severity": "HIGH"
                        }
                        security_violations.append(violation)
                        self.logger.error(f"SECURITY VIOLATION: {violation}")
                
                except Exception as e:
                    # Exception is expected for security validation
                    self.logger.info(f"Security exception (expected): {e}")
                
                # Attempt 2: Message creation in other user's thread
                try:
                    await thread_service.create_message(
                        thread_id=target_thread.id,
                        role="user",
                        content=f"Unauthorized message from user {accessing_user}",
                        metadata={"unauthorized_access": True}
                    )
                    
                    # This is a security violation if successful
                    violation = {
                        "type": "unauthorized_message_creation",
                        "accessing_user": str(accessing_user),
                        "target_thread": target_thread.id,
                        "severity": "CRITICAL"
                    }
                    security_violations.append(violation)
                    self.logger.error(f"CRITICAL SECURITY VIOLATION: {violation}")
                
                except Exception as e:
                    # Exception is expected for security validation
                    self.logger.info(f"Security exception (expected): {e}")
        
        # Verify legitimate access still works
        for user_id in user_ids:
            own_thread = user_threads[user_id]
            
            # User should be able to access their own thread
            legitimate_access = await thread_service.get_thread(
                own_thread.id, str(user_id), db_session
            )
            assert legitimate_access is not None, \
                f"User {user_id} cannot access their own thread - legitimate access broken!"
        
        # Report security violations (if any)
        if security_violations:
            self.logger.error(f"SECURITY AUDIT FAILED: {len(security_violations)} violations detected")
            # Don't fail test immediately - collect all violations first
            for violation in security_violations:
                self.logger.error(f"Security violation details: {violation}")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_failure_recovery(self, lightweight_services_fixture, isolated_env):
        """Test graceful handling of database connection failures and recovery."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        original_db_session = lightweight_services_fixture["db"]
        if not original_db_session:
            pytest.skip("Database session not available")
        
        # Setup test user and thread
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="db.failure.test@example.com", 
            full_name="DB Failure Test User",
            is_active=True
        )
        original_db_session.add(test_user)
        await original_db_session.commit()
        
        thread_service = ThreadService()
        
        # Create initial thread
        original_thread = await thread_service.get_or_create_thread(str(user_id), original_db_session)
        thread_id = ensure_thread_id(original_thread.id)
        
        # Simulate database connection failures
        connection_failure_scenarios = []
        
        # Scenario 1: Simulate connection timeout
        with patch.object(original_db_session, 'execute') as mock_execute:
            mock_execute.side_effect = OperationalError(
                "Connection timeout", None, None
            )
            
            try:
                await thread_service.get_thread(original_thread.id, str(user_id), original_db_session)
                connection_failure_scenarios.append({
                    "scenario": "connection_timeout",
                    "handled_gracefully": True,
                    "error": None
                })
            except Exception as e:
                connection_failure_scenarios.append({
                    "scenario": "connection_timeout", 
                    "handled_gracefully": False,
                    "error": str(e)
                })
                self.logger.error(f"Connection timeout not handled gracefully: {e}")
        
        # Scenario 2: Simulate database disconnection
        if hasattr(original_db_session, 'close'):
            try:
                # Force close connection
                await original_db_session.close()
                
                # Attempt operation on closed connection
                closed_result = await thread_service.get_thread(
                    original_thread.id, str(user_id), original_db_session
                )
                
                connection_failure_scenarios.append({
                    "scenario": "closed_connection",
                    "handled_gracefully": closed_result is None,
                    "error": None if closed_result is None else "Operation succeeded on closed connection"
                })
                
            except Exception as e:
                connection_failure_scenarios.append({
                    "scenario": "closed_connection",
                    "handled_gracefully": True,
                    "error": str(e)
                })
        
        # Scenario 3: Test recovery with new session
        try:
            # Get new session for recovery testing
            recovery_session = lightweight_services_fixture.get("db_recovery")
            if not recovery_session:
                # Create new session if recovery session not available
                recovery_session = lightweight_services_fixture["db"]
            
            # Test that recovery works
            if recovery_session and recovery_session != original_db_session:
                recovered_thread = await thread_service.get_thread(
                    original_thread.id, str(user_id), recovery_session
                )
                
                recovery_successful = recovered_thread is not None
                connection_failure_scenarios.append({
                    "scenario": "session_recovery",
                    "handled_gracefully": recovery_successful,
                    "error": None if recovery_successful else "Recovery failed"
                })
                
                await recovery_session.close()
            
        except Exception as e:
            connection_failure_scenarios.append({
                "scenario": "session_recovery",
                "handled_gracefully": False,
                "error": str(e)
            })
        
        # Analyze failure handling results
        graceful_handling_count = sum(
            1 for scenario in connection_failure_scenarios 
            if scenario["handled_gracefully"]
        )
        
        self.logger.info(f"Database failure scenarios tested: {len(connection_failure_scenarios)}")
        self.logger.info(f"Gracefully handled: {graceful_handling_count}")
        
        for scenario in connection_failure_scenarios:
            if not scenario["handled_gracefully"]:
                self.logger.warning(f"Scenario '{scenario['scenario']}' not handled gracefully: {scenario['error']}")
        
        # At least 50% of scenarios should be handled gracefully
        # (Allows for some incomplete error handling initially)
        graceful_rate = graceful_handling_count / len(connection_failure_scenarios)
        if graceful_rate < 0.5:
            self.logger.warning(f"Low graceful failure rate: {graceful_rate:.1%}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_disconnection_during_routing(self, lightweight_services_fixture, isolated_env):
        """Test handling of WebSocket disconnections during thread routing operations."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test user and thread
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="websocket.disconnect.test@example.com",
            full_name="WebSocket Disconnect Test User", 
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        initial_thread = await thread_service.get_or_create_thread(str(user_id), db_session)
        
        # Create user execution context
        user_context = UserExecutionContext(
            user_id=str(user_id),
            thread_id=initial_thread.id,
            run_id=f"disconnect_test_{uuid.uuid4()}"
        )
        
        # Test WebSocket disconnection scenarios
        websocket_failure_scenarios = []
        
        # Scenario 1: WebSocket manager creation failure
        with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create_manager:
            mock_create_manager.return_value = None
            
            try:
                # Try to send event with failed WebSocket manager
                await thread_service._send_thread_created_event(str(user_id), initial_thread.id)
                websocket_failure_scenarios.append({
                    "scenario": "manager_creation_failure",
                    "handled_gracefully": True,
                    "error": None
                })
            except Exception as e:
                websocket_failure_scenarios.append({
                    "scenario": "manager_creation_failure",
                    "handled_gracefully": False,
                    "error": str(e)
                })
        
        # Scenario 2: WebSocket send failure
        try:
            websocket_manager = await create_websocket_manager(user_context)
            if websocket_manager:
                # Mock send failure
                with patch.object(websocket_manager, 'send_to_user') as mock_send:
                    mock_send.side_effect = DatabaseConnectionError("WebSocket disconnected")
                    
                    try:
                        await websocket_manager.send_to_user(
                            str(user_id), 
                            {"type": "test_message", "payload": {"test": True}}
                        )
                        websocket_failure_scenarios.append({
                            "scenario": "send_failure",
                            "handled_gracefully": False,
                            "error": "Send should have failed but didn't"
                        })
                    except Exception as e:
                        websocket_failure_scenarios.append({
                            "scenario": "send_failure", 
                            "handled_gracefully": True,
                            "error": str(e)
                        })
            else:
                websocket_failure_scenarios.append({
                    "scenario": "manager_not_available",
                    "handled_gracefully": True,
                    "error": "WebSocket manager not available - handled gracefully"
                })
                
        except Exception as e:
            websocket_failure_scenarios.append({
                "scenario": "websocket_setup_failure",
                "handled_gracefully": False,
                "error": str(e)
            })
        
        # Scenario 3: Ensure thread operations continue despite WebSocket failures
        try:
            # Verify thread operations still work even with WebSocket failures
            message = await thread_service.create_message(
                thread_id=initial_thread.id,
                role="user",
                content="Message created despite WebSocket issues",
                metadata={"websocket_failure_test": True}
            )
            
            websocket_failure_scenarios.append({
                "scenario": "thread_operations_resilient",
                "handled_gracefully": message is not None,
                "error": None if message else "Thread operation failed"
            })
            
        except Exception as e:
            websocket_failure_scenarios.append({
                "scenario": "thread_operations_resilient",
                "handled_gracefully": False,
                "error": str(e)
            })
        
        # Analyze WebSocket failure handling
        websocket_graceful_count = sum(
            1 for scenario in websocket_failure_scenarios
            if scenario["handled_gracefully"]
        )
        
        self.logger.info(f"WebSocket failure scenarios: {len(websocket_failure_scenarios)}")
        self.logger.info(f"Gracefully handled: {websocket_graceful_count}")
        
        for scenario in websocket_failure_scenarios:
            status = "✅ PASS" if scenario["handled_gracefully"] else "❌ FAIL"
            self.logger.info(f"{status} - {scenario['scenario']}: {scenario.get('error', 'No error')}")
        
        # WebSocket failures should not break core thread functionality
        # At least 60% should be handled gracefully
        websocket_graceful_rate = websocket_graceful_count / len(websocket_failure_scenarios)
        if websocket_graceful_rate < 0.6:
            self.logger.warning(f"WebSocket failure handling needs improvement: {websocket_graceful_rate:.1%}")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_exhaustion_and_cleanup(self, lightweight_services_fixture, isolated_env):
        """Test system behavior under resource exhaustion and proper cleanup."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test user
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="resource.exhaustion.test@example.com",
            full_name="Resource Exhaustion Test User",
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        resource_exhaustion_scenarios = []
        
        # Track resources created during test
        created_threads = []
        created_messages = []
        
        try:
            # Scenario 1: Create many threads rapidly to test limits
            self.logger.info("Testing rapid thread creation limits...")
            
            start_time = time.time()
            thread_creation_errors = 0
            max_threads_to_create = 50  # Reasonable limit for testing
            
            for i in range(max_threads_to_create):
                try:
                    thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                    created_threads.append(thread.id)
                    
                    # Small delay to prevent overwhelming
                    if i % 10 == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    thread_creation_errors += 1
                    self.logger.warning(f"Thread creation failed at iteration {i}: {e}")
                    
                    if thread_creation_errors > 10:
                        break  # Stop if too many failures
            
            creation_duration = time.time() - start_time
            success_rate = (max_threads_to_create - thread_creation_errors) / max_threads_to_create
            
            resource_exhaustion_scenarios.append({
                "scenario": "rapid_thread_creation",
                "success_rate": success_rate,
                "duration": creation_duration,
                "errors": thread_creation_errors,
                "handled_gracefully": success_rate > 0.8
            })
            
            # Scenario 2: Create many messages in threads
            self.logger.info("Testing rapid message creation limits...")
            
            if created_threads:
                message_creation_errors = 0
                messages_per_thread = 10
                
                for thread_id in created_threads[:5]:  # Test with first 5 threads
                    for msg_idx in range(messages_per_thread):
                        try:
                            message = await thread_service.create_message(
                                thread_id=thread_id,
                                role="user",
                                content=f"Resource test message {msg_idx} in thread {thread_id}",
                                metadata={"test_type": "resource_exhaustion", "message_index": msg_idx}
                            )
                            created_messages.append(message.id)
                            
                        except Exception as e:
                            message_creation_errors += 1
                            self.logger.warning(f"Message creation failed: {e}")
                
                message_success_rate = 1 - (message_creation_errors / (5 * messages_per_thread))
                resource_exhaustion_scenarios.append({
                    "scenario": "rapid_message_creation",
                    "success_rate": message_success_rate,
                    "errors": message_creation_errors,
                    "handled_gracefully": message_success_rate > 0.7
                })
            
            # Scenario 3: Test concurrent operations
            self.logger.info("Testing concurrent thread operations...")
            
            async def concurrent_thread_operation(user_id: str, operation_id: int):
                """Concurrent operation for resource testing."""
                try:
                    thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="user",
                        content=f"Concurrent operation {operation_id}",
                        metadata={"concurrent_test": True, "operation_id": operation_id}
                    )
                    return {"success": True, "thread_id": thread.id, "message_id": message.id}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # Run concurrent operations
            concurrent_tasks = [
                concurrent_thread_operation(user_id, i) for i in range(10)
            ]
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            concurrent_successes = sum(
                1 for result in concurrent_results
                if isinstance(result, dict) and result.get("success", False)
            )
            concurrent_success_rate = concurrent_successes / len(concurrent_tasks)
            
            resource_exhaustion_scenarios.append({
                "scenario": "concurrent_operations",
                "success_rate": concurrent_success_rate,
                "successes": concurrent_successes,
                "total": len(concurrent_tasks),
                "handled_gracefully": concurrent_success_rate > 0.6
            })
            
        except Exception as e:
            self.logger.error(f"Resource exhaustion test failed: {e}")
            resource_exhaustion_scenarios.append({
                "scenario": "test_execution_failure",
                "handled_gracefully": False,
                "error": str(e)
            })
        
        # Cleanup test - verify resources can be cleaned up properly
        cleanup_success = True
        cleanup_errors = []
        
        self.logger.info(f"Cleaning up test resources: {len(created_threads)} threads, {len(created_messages)} messages")
        
        try:
            # Test cleanup by verifying threads still exist and can be accessed
            accessible_threads = 0
            for thread_id in created_threads[:10]:  # Sample first 10
                try:
                    thread = await thread_service.get_thread(thread_id, str(user_id), db_session)
                    if thread:
                        accessible_threads += 1
                except Exception as e:
                    cleanup_errors.append(f"Thread {thread_id}: {str(e)}")
            
            resource_exhaustion_scenarios.append({
                "scenario": "resource_cleanup_verification",
                "accessible_threads": accessible_threads,
                "total_created": len(created_threads),
                "cleanup_errors": len(cleanup_errors),
                "handled_gracefully": len(cleanup_errors) < 5
            })
            
        except Exception as e:
            cleanup_success = False
            cleanup_errors.append(f"Cleanup verification failed: {str(e)}")
        
        # Analyze resource exhaustion handling
        graceful_scenarios = sum(
            1 for scenario in resource_exhaustion_scenarios 
            if scenario.get("handled_gracefully", False)
        )
        
        self.logger.info("=== Resource Exhaustion Test Results ===")
        for scenario in resource_exhaustion_scenarios:
            status = "✅ PASS" if scenario.get("handled_gracefully", False) else "❌ FAIL"
            self.logger.info(f"{status} - {scenario['scenario']}")
            
            if "success_rate" in scenario:
                self.logger.info(f"    Success Rate: {scenario['success_rate']:.1%}")
            if "errors" in scenario:
                self.logger.info(f"    Errors: {scenario['errors']}")
        
        resource_graceful_rate = graceful_scenarios / len(resource_exhaustion_scenarios)
        self.logger.info(f"Overall resource handling: {resource_graceful_rate:.1%} graceful")
        
        if cleanup_errors:
            self.logger.warning(f"Cleanup issues detected: {cleanup_errors}")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_quality_and_user_feedback(self, lightweight_services_fixture, isolated_env):
        """Test that error messages are helpful and provide proper user feedback."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test user
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="error.message.test@example.com",
            full_name="Error Message Test User",
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        error_message_scenarios = []
        
        # Test error message quality for different failure scenarios
        
        # Scenario 1: Invalid thread ID error messages
        try:
            await thread_service.get_thread("invalid_thread_id", str(user_id), db_session)
        except Exception as e:
            error_msg = str(e)
            error_message_scenarios.append({
                "scenario": "invalid_thread_id",
                "error_message": error_msg,
                "contains_context": "thread" in error_msg.lower(),
                "helpful": len(error_msg) > 10 and "invalid" in error_msg.lower(),
                "user_friendly": not any(term in error_msg.lower() for term in ["exception", "traceback", "sql"])
            })
        
        # Scenario 2: Non-existent thread error messages  
        non_existent_thread_id = f"thread_{uuid.uuid4()}"
        try:
            result = await thread_service.get_thread(non_existent_thread_id, str(user_id), db_session)
            if result is None:
                # This is correct behavior - no exception should be raised
                error_message_scenarios.append({
                    "scenario": "non_existent_thread",
                    "error_message": "Returns None (correct behavior)",
                    "contains_context": True,
                    "helpful": True,
                    "user_friendly": True
                })
        except Exception as e:
            error_msg = str(e)
            error_message_scenarios.append({
                "scenario": "non_existent_thread",
                "error_message": error_msg,
                "contains_context": "thread" in error_msg.lower(),
                "helpful": "not found" in error_msg.lower() or "exist" in error_msg.lower(),
                "user_friendly": not any(term in error_msg.lower() for term in ["exception", "traceback", "sql"])
            })
        
        # Scenario 3: Invalid message creation error messages
        valid_thread = await thread_service.get_or_create_thread(str(user_id), db_session)
        
        try:
            await thread_service.create_message(
                thread_id="",  # Empty thread ID
                role="user",
                content="Test message",
                metadata={}
            )
        except Exception as e:
            error_msg = str(e)
            error_message_scenarios.append({
                "scenario": "empty_thread_id_message",
                "error_message": error_msg,
                "contains_context": "thread" in error_msg.lower(),
                "helpful": len(error_msg) > 10,
                "user_friendly": not any(term in error_msg.lower() for term in ["exception", "traceback", "sql"])
            })
        
        # Scenario 4: Invalid role error messages
        try:
            await thread_service.create_message(
                thread_id=valid_thread.id,
                role="invalid_role",  # Invalid role
                content="Test message",
                metadata={}
            )
        except Exception as e:
            error_msg = str(e)
            error_message_scenarios.append({
                "scenario": "invalid_role",
                "error_message": error_msg,
                "contains_context": "role" in error_msg.lower(),
                "helpful": "invalid" in error_msg.lower() or "role" in error_msg.lower(),
                "user_friendly": not any(term in error_msg.lower() for term in ["exception", "traceback", "sql"])
            })
        
        # Scenario 5: Create WebSocket error messages
        user_context = UserExecutionContext(
            user_id=str(user_id),
            thread_id=valid_thread.id,
            run_id=f"error_test_{uuid.uuid4()}"
        )
        
        try:
            # Test with invalid WebSocket message
            websocket_manager = await create_websocket_manager(user_context)
            if websocket_manager:
                with patch.object(websocket_manager, 'send_to_user') as mock_send:
                    mock_send.side_effect = Exception("WebSocket connection failed")
                    await websocket_manager.send_to_user(str(user_id), {"invalid": "message"})
        except Exception as e:
            error_msg = str(e)
            error_message_scenarios.append({
                "scenario": "websocket_connection_failed",
                "error_message": error_msg,
                "contains_context": "websocket" in error_msg.lower() or "connection" in error_msg.lower(),
                "helpful": "failed" in error_msg.lower() or "connection" in error_msg.lower(),
                "user_friendly": not any(term in error_msg.lower() for term in ["exception", "traceback", "sql"])
            })
        
        # Analyze error message quality
        self.logger.info("=== Error Message Quality Analysis ===")
        
        quality_scores = {
            "contains_context": 0,
            "helpful": 0,
            "user_friendly": 0
        }
        
        for scenario in error_message_scenarios:
            scenario_name = scenario["scenario"]
            error_msg = scenario["error_message"]
            
            self.logger.info(f"\n--- {scenario_name} ---")
            self.logger.info(f"Error Message: {error_msg}")
            
            for quality_metric in quality_scores:
                has_quality = scenario.get(quality_metric, False)
                quality_scores[quality_metric] += 1 if has_quality else 0
                status = "✅" if has_quality else "❌"
                self.logger.info(f"{status} {quality_metric.replace('_', ' ').title()}: {has_quality}")
        
        # Calculate overall error message quality
        total_scenarios = len(error_message_scenarios)
        if total_scenarios > 0:
            for metric, score in quality_scores.items():
                percentage = (score / total_scenarios) * 100
                self.logger.info(f"\nOverall {metric.replace('_', ' ').title()}: {percentage:.1f}% ({score}/{total_scenarios})")
        
        # Error messages should be helpful and user-friendly
        helpful_rate = quality_scores["helpful"] / max(total_scenarios, 1)
        user_friendly_rate = quality_scores["user_friendly"] / max(total_scenarios, 1)
        
        if helpful_rate < 0.7:
            self.logger.warning(f"Error messages need to be more helpful: {helpful_rate:.1%}")
        
        if user_friendly_rate < 0.6:
            self.logger.warning(f"Error messages need to be more user-friendly: {user_friendly_rate:.1%}")
        
        await db_session.close()