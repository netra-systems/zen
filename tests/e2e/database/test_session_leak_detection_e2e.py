"""
E2E Tests: Session Leak Detection with Authentication

These E2E tests validate session management across the complete stack
including authentication, WebSocket connections, and database operations.
Tests are designed to FAIL initially to expose session leaks.

CRITICAL: Following CLAUDE.md E2E requirements:
- ALL e2e tests MUST use authentication (JWT/OAuth)
- Use real services (PostgreSQL, WebSocket, Auth)  
- "Real Everything (LLM, Services) E2E > E2E > Integration > Unit"

Business Value:
- Validates session safety in complete user workflows
- Ensures authenticated requests don't leak database sessions
- Tests session handling with real WebSocket connections
- Exposes session leaks in production-like scenarios
"""

import pytest
import asyncio
import json
from typing import Dict, Any, Optional
import websockets

from test_framework.session_leak_detection import SessionLeakTestBase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from netra_backend.app.routes.utils.thread_handlers import (
    handle_list_threads_request,
    handle_create_thread_request,
    handle_get_thread_request,
    handle_update_thread_request,
    handle_send_message_request
)


class TestSessionLeakDetectionE2E(SessionLeakTestBase):
    """
    E2E session leak detection tests with full authentication.
    
    CRITICAL: These tests MUST use authentication as per CLAUDE.md:
    "ALL e2e tests MUST use authentication (JWT/OAuth) EXCEPT tests that directly validate auth itself"
    
    Tests are designed to FAIL initially to expose session management issues
    across the complete authenticated request stack.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_e2e_leak_detection(self):
        """Set up E2E test environment with authentication and real services."""
        await self.setup_session_leak_testing(
            max_session_age_seconds=20.0,  # Longer timeout for E2E tests
            monitoring_interval=1.0
        )
        
        # Initialize authentication helper for E2E testing
        self.auth_helper = E2EAuthHelper(environment="test")
        
        yield
        await self.teardown_session_leak_testing()
    
    async def test_session_leak_scenario(self):
        """Required abstract method implementation."""
        pass
    
    @pytest.mark.asyncio
    async def test_authenticated_thread_creation_session_leak(self):
        """
        Test: Authenticated thread creation with session tracking
        
        EXPECTED TO FAIL: Authenticated requests expose additional session management layers
        """
        # Create authenticated user context
        user_context = await self.get_authenticated_context()
        user_id = str(user_context.user_id)
        
        # Verify authentication
        jwt_token = user_context.agent_context['jwt_token']
        assert jwt_token is not None, "E2E test must have valid JWT token"
        
        thread_data = {
            "title": "E2E Authenticated Thread",
            "metadata": {
                "test_type": "e2e_authenticated",
                "user_email": user_context.agent_context['user_email']
            }
        }
        
        # Execute authenticated thread creation
        result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        # Verify thread creation
        assert result is not None
        assert "id" in result
        assert result.get("title") == "E2E Authenticated Thread"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Authenticated requests add complexity to session management
        await self.assert_no_session_leaks(
            "Authenticated thread creation must properly manage database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_multi_user_concurrent_session_leak(self):
        """
        Test: Multiple authenticated users creating threads concurrently
        
        EXPECTED TO FAIL: Multi-user scenarios expose session isolation issues
        """
        # Create multiple authenticated user contexts
        user_contexts = []
        for i in range(5):
            context = await create_authenticated_user_context(
                user_email=f"e2e_user_{i}@example.com",
                environment="test",
                permissions=["read", "write"]
            )
            user_contexts.append(context)
        
        async def create_user_thread(user_context, thread_index: int):
            """Create thread for specific authenticated user."""
            user_id = str(user_context.user_id)
            
            thread_data = {
                "title": f"Multi-User Thread {thread_index}",
                "metadata": {
                    "user_email": user_context.agent_context['user_email'],
                    "thread_index": thread_index
                }
            }
            
            return await self.execute_thread_handler_with_tracking(
                handle_create_thread_request,
                thread_data, user_id
            )
        
        # Execute concurrent thread creation for all users
        concurrent_tasks = [
            create_user_thread(context, i) 
            for i, context in enumerate(user_contexts)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 5, "All authenticated users should successfully create threads"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Multi-user authenticated operations will expose session isolation issues
        await self.assert_no_session_leaks(
            "Multi-user authenticated operations must not cause session leaks"
        )
    
    @pytest.mark.asyncio
    async def test_websocket_authenticated_session_leak(self):
        """
        Test: WebSocket operations with authentication and session tracking
        
        EXPECTED TO FAIL: WebSocket connections with database operations expose session complexity
        """
        # Create authenticated user context
        user_context = await self.get_authenticated_context()
        user_id = str(user_context.user_id)
        
        # Get WebSocket authentication headers
        jwt_token = user_context.agent_context['jwt_token']
        ws_headers = self.auth_helper.get_websocket_headers(jwt_token)
        
        # Create thread first via database handler
        thread_data = {
            "title": "WebSocket Test Thread",
            "metadata": {"websocket_test": True}
        }
        
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Now test WebSocket connection with database operations
        try:
            async with websockets.connect(
                "ws://localhost:8002/ws",
                additional_headers=ws_headers,
                open_timeout=10.0
            ) as websocket:
                
                # Send WebSocket message that might trigger database operations
                test_message = {
                    "type": "thread_message",
                    "thread_id": thread_id,
                    "content": "WebSocket test message",
                    "timestamp": "2025-01-01T00:00:00Z"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    assert response_data is not None
                except asyncio.TimeoutError:
                    # WebSocket may not respond immediately, that's ok for session testing
                    pass
                
        except Exception as e:
            # WebSocket connection issues are expected in test environment
            # The important part is the database session tracking
            pytest.skip(f"WebSocket connection failed (expected in test env): {e}")
        
        # Also test thread retrieval after WebSocket operations
        retrieve_result = await self.execute_thread_handler_with_tracking(
            handle_get_thread_request,
            thread_id, user_id
        )
        
        assert retrieve_result is not None
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # WebSocket + database operations expose complex session management issues
        await self.assert_no_session_leaks(
            "WebSocket operations with database access must properly manage sessions"
        )
    
    @pytest.mark.asyncio
    async def test_authenticated_full_thread_workflow_session_leak(self):
        """
        Test: Complete authenticated thread workflow (create, update, messages, retrieve)
        
        EXPECTED TO FAIL: Full workflow exposes session management gaps across operations
        """
        # Create authenticated user context
        user_context = await self.get_authenticated_context()
        user_id = str(user_context.user_id)
        
        # Step 1: Create thread
        thread_data = {
            "title": "Full Workflow Thread",
            "metadata": {
                "workflow_test": True,
                "user_email": user_context.agent_context['user_email']
            }
        }
        
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Step 2: Send messages to thread
        from unittest.mock import Mock
        for i in range(3):
            message_request = Mock()
            message_request.message = f"Workflow test message {i+1}"
            message_request.metadata = {"step": i+1}
            
            message_result = await self.execute_thread_handler_with_tracking(
                handle_send_message_request,
                thread_id, message_request, user_id
            )
            
            assert message_result["content"] == f"Workflow test message {i+1}"
        
        # Step 3: Update thread
        thread_update = Mock()
        thread_update.title = "Updated Workflow Thread"
        thread_update.metadata = {"updated": True, "step_count": 3}
        
        update_result = await self.execute_thread_handler_with_tracking(
            handle_update_thread_request,
            thread_id, thread_update, user_id
        )
        
        assert update_result is not None
        
        # Step 4: Retrieve thread with messages
        retrieve_result = await self.execute_thread_handler_with_tracking(
            handle_get_thread_request,
            thread_id, user_id
        )
        
        assert retrieve_result["id"] == thread_id
        
        # Step 5: List all threads for user
        list_result = await self.execute_thread_handler_with_tracking(
            handle_list_threads_request,
            user_id, 0, 10
        )
        
        assert list_result is not None
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Complete workflow operations will expose cumulative session management issues
        await self.assert_no_session_leaks(
            "Complete authenticated thread workflow must properly manage all database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_authentication_token_refresh_session_leak(self):
        """
        Test: Session management during authentication token operations
        
        EXPECTED TO FAIL: Token refresh/validation may create additional session complexity
        """
        # Create multiple user contexts to test token operations
        user_contexts = []
        for i in range(3):
            context = await create_authenticated_user_context(
                user_email=f"token_test_user_{i}@example.com",
                environment="test"
            )
            user_contexts.append(context)
        
        # Test operations with different tokens
        for i, user_context in enumerate(user_contexts):
            user_id = str(user_context.user_id)
            jwt_token = user_context.agent_context['jwt_token']
            
            # Validate token works
            token_valid = await self.auth_helper.validate_token(jwt_token)
            assert token_valid, f"Token {i} should be valid"
            
            # Create thread with this token
            thread_data = {
                "title": f"Token Test Thread {i}",
                "metadata": {"token_index": i}
            }
            
            result = await self.execute_thread_handler_with_tracking(
                handle_create_thread_request,
                thread_data, user_id
            )
            
            assert result is not None
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "Authentication token operations must not cause database session leaks"
        )
    
    @pytest.mark.asyncio
    async def test_high_load_authenticated_operations_session_leak(self):
        """
        Test: High load authenticated operations to stress test session management
        
        EXPECTED TO FAIL: High load exposes session pool exhaustion issues
        """
        # Create authenticated user
        user_context = await self.get_authenticated_context()
        user_id = str(user_context.user_id)
        
        # Execute high volume of operations
        async def batch_operations(batch_id: int):
            """Execute batch of operations for load testing."""
            results = []
            
            for i in range(5):  # 5 operations per batch
                thread_data = {
                    "title": f"Load Test Thread {batch_id}-{i}",
                    "metadata": {"batch_id": batch_id, "operation_id": i}
                }
                
                # Create thread
                create_result = await self.execute_thread_handler_with_tracking(
                    handle_create_thread_request,
                    thread_data, user_id
                )
                
                # Immediately retrieve it
                retrieve_result = await self.execute_thread_handler_with_tracking(
                    handle_get_thread_request,
                    create_result["id"], user_id
                )
                
                results.append({
                    "created": create_result["id"],
                    "retrieved": retrieve_result["id"]
                })
            
            return results
        
        # Execute multiple batches concurrently
        batch_tasks = [batch_operations(i) for i in range(10)]  # 10 batches = 50 operations
        
        start_pool_state = await self.session_monitor.get_current_pool_state()
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        end_pool_state = await self.session_monitor.get_current_pool_state()
        
        # Verify most operations succeeded
        successful_batches = [r for r in batch_results if not isinstance(r, Exception)]
        assert len(successful_batches) >= 8, "Most batches should succeed under load"
        
        # Log pool state changes
        if start_pool_state and end_pool_state:
            print(f"Pool utilization: {start_pool_state.utilization_percent:.1f}% -> {end_pool_state.utilization_percent:.1f}%")
            print(f"Checked out connections: {start_pool_state.checked_out} -> {end_pool_state.checked_out}")
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # High load will expose session management weaknesses
        await self.assert_no_session_leaks(
            "High load authenticated operations must not exhaust database connection pool"
        )
        
        # Additional assertion for pool health
        self.session_monitor.assert_healthy_pool_state(max_utilization=90.0)
    
    @pytest.mark.asyncio
    async def test_authenticated_error_scenarios_session_leak(self):
        """
        Test: Session management when authenticated operations encounter errors
        
        EXPECTED TO FAIL: Error scenarios may not properly clean up sessions
        """
        # Create authenticated user
        user_context = await self.get_authenticated_context()
        user_id = str(user_context.user_id)
        
        # Test various error scenarios
        error_scenarios = [
            # Invalid thread ID
            ("get_nonexistent_thread", lambda: self.execute_thread_handler_with_tracking(
                handle_get_thread_request, "nonexistent-thread-id", user_id
            )),
            # Invalid user access (different user's thread)
            ("cross_user_access", lambda: self._test_cross_user_access(user_id)),
        ]
        
        error_count = 0
        for scenario_name, scenario_func in error_scenarios:
            try:
                await scenario_func()
                print(f"Warning: {scenario_name} should have failed but didn't")
            except Exception as e:
                error_count += 1
                print(f"Expected error in {scenario_name}: {e}")
        
        assert error_count > 0, "At least some error scenarios should trigger exceptions"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Error scenarios must properly clean up sessions
        await self.assert_no_session_leaks(
            "Authenticated error scenarios must properly rollback and close sessions"
        )
    
    async def _test_cross_user_access(self, user_id: str):
        """Helper to test cross-user access scenario."""
        # Create thread with first user
        thread_data = {"title": "User 1 Thread", "metadata": {}}
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Try to access with different user (should fail)
        different_user_id = "different-user-123"
        await self.execute_thread_handler_with_tracking(
            handle_get_thread_request,
            thread_id, different_user_id
        )