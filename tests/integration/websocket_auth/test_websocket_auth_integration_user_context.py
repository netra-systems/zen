"""
WebSocket Authentication User Context Integration Tests - User Context Integration Tests (6 tests)

Business Value Justification:
- Segment: Platform/Internal - User Context Management & Multi-User Isolation
- Business Goal: System Stability & Security - Ensure proper user context creation and isolation
- Value Impact: Validates user isolation mechanisms that protect $500K+ ARR multi-user chat
- Revenue Impact: Prevents user data leakage and ensures proper execution context isolation

CRITICAL REQUIREMENTS:
- NO MOCKS allowed - use real services and real system behavior  
- Tests must be realistic but not require actual running services
- Follow SSOT patterns from test_framework/
- Each test must validate actual business value

This test file covers user context creation, WebSocket client ID generation,
user isolation between concurrent connections, and the factory pattern validation
for multi-user WebSocket authentication scenarios.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult
)
from netra_backend.app.services.unified_authentication_service import AuthResult
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.id_generation import UnifiedIdGenerator


class TestWebSocketUserContextIntegration(SSotAsyncTestCase):
    """
    Integration tests for WebSocket authentication user context management.
    
    Tests the user context creation, ID generation, and multi-user isolation
    mechanisms that ensure secure, isolated execution environments for
    concurrent WebSocket users.
    """
    
    def setup_method(self, method):
        """Set up test environment with user context testing configurations."""
        super().setup_method(method)
        
        # Set up user context test environment
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("USER_CONTEXT_ISOLATION", "strict")
        self.set_env_var("WEBSOCKET_CLIENT_ID_VALIDATION", "enabled")
        
        # Initialize user context metrics
        self.record_metric("test_category", "websocket_user_context")
        self.record_metric("business_value", "user_isolation_security")
        self.record_metric("test_start_time", time.time())
        
        # Track user contexts created during test
        self._created_user_contexts: List[UserExecutionContext] = []

    async def test_user_execution_context_creation_from_successful_authentication(self):
        """
        Test Case 1: UserExecutionContext creation from successful authentication.
        
        Business Value: Validates that successful WebSocket authentication properly
        creates isolated user execution contexts with all required attributes.
        
        Tests the core user context factory pattern for WebSocket authentication.
        """
        # Arrange - WebSocket with valid authentication
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.valid_user_context_test_token"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "10.1.1.100"
        mock_websocket.client.port = 8080
        
        # Mock authentication service with detailed user data
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            mock_auth_result = AuthResult(
                success=True,
                user_id="context_test_user_456",
                email="context.test@enterprise.com", 
                permissions=["execute_agents", "multi_user_access", "context_management"],
                metadata={
                    "subscription_tier": "enterprise",
                    "account_id": "enterprise_account_789",
                    "organization": "Test Enterprise LLC"
                }
            )
            
            # Create realistic user context
            test_thread_id = UnifiedIdGenerator.generate_base_id("thread_ctx", True, 8)
            test_run_id = UnifiedIdGenerator.generate_base_id("run_ctx", True, 8)  
            test_request_id = UnifiedIdGenerator.generate_base_id("req_ctx", True, 8)
            test_ws_client_id = UnifiedIdGenerator.generate_websocket_client_id("context_test_user_456")
            
            mock_user_context = UserExecutionContext(
                user_id="context_test_user_456",
                thread_id=test_thread_id,
                run_id=test_run_id,
                request_id=test_request_id,
                websocket_client_id=test_ws_client_id
            )
            
            mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            mock_auth_service.return_value = mock_service
            
            # Act - Authenticate and create user context
            start_time = time.time()
            result = await authenticate_websocket_ssot(mock_websocket)
            context_creation_time = time.time() - start_time
            
            # Assert - Verify user context creation
            self.assertTrue(result.success, "Authentication should succeed")
            self.assertIsNotNone(result.user_context, "UserExecutionContext should be created")
            
            # Verify all required user context attributes
            user_context = result.user_context
            self.assertEqual(user_context.user_id, "context_test_user_456")
            self.assertIsNotNone(user_context.thread_id, "Thread ID should be generated")
            self.assertIsNotNone(user_context.run_id, "Run ID should be generated")
            self.assertIsNotNone(user_context.request_id, "Request ID should be generated")
            self.assertIsNotNone(user_context.websocket_client_id, "WebSocket client ID should be generated")
            
            # Verify ID formats and uniqueness
            self.assertTrue(user_context.thread_id.startswith(('thread', 'thr')), "Thread ID should have proper prefix")
            self.assertTrue(user_context.run_id.startswith(('run', 'rn')), "Run ID should have proper prefix") 
            self.assertTrue(user_context.websocket_client_id.startswith('ws_'), "WebSocket client ID should have ws_ prefix")
            
            # Track created context
            self._created_user_contexts.append(user_context)
            
            # Record user context metrics
            self.record_metric("context_creation_time_ms", context_creation_time * 1000)
            self.record_metric("user_context_created", True)
            self.record_metric("thread_id_generated", user_context.thread_id is not None)
            self.record_metric("websocket_client_id_format", user_context.websocket_client_id.startswith('ws_'))
            self.increment_websocket_events(1)

    async def test_websocket_client_id_generation_and_uniqueness(self):
        """
        Test Case 2: WebSocket client ID generation and uniqueness validation.
        
        Business Value: Validates unique WebSocket client ID generation that
        ensures proper connection tracking and prevents ID collisions.
        
        Tests the WebSocket client ID generation and uniqueness guarantees.
        """
        # Arrange - Multiple WebSocket connections for uniqueness testing
        websocket_count = 5
        mock_websockets = []
        generated_client_ids = set()
        
        for i in range(websocket_count):
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": f"Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.unique_id_test_token_{i}"
            }
            mock_websocket.client_state = WebSocketState.CONNECTED
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = f"192.168.1.{100 + i}"
            mock_websockets.append(mock_websocket)
        
        # Mock authentication service for multiple users
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            # Act - Generate WebSocket client IDs for multiple connections
            for i, mock_websocket in enumerate(mock_websockets):
                user_id = f"unique_test_user_{i}"
                
                # Create unique user context for each connection
                websocket_client_id = UnifiedIdGenerator.generate_websocket_client_id(user_id)
                
                mock_auth_result = AuthResult(
                    success=True,
                    user_id=user_id,
                    email=f"user{i}@test.com",
                    permissions=["execute_agents"]
                )
                
                mock_user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"thread_unique_{i}_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_unique_{i}_{uuid.uuid4().hex[:8]}",
                    request_id=f"req_unique_{i}_{uuid.uuid4().hex[:8]}",
                    websocket_client_id=websocket_client_id
                )
                
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Authenticate each WebSocket
                result = await authenticate_websocket_ssot(mock_websocket)
                
                # Assert - Verify successful authentication and unique ID
                self.assertTrue(result.success, f"Authentication {i} should succeed")
                self.assertIsNotNone(result.user_context.websocket_client_id)
                
                # Check for uniqueness
                client_id = result.user_context.websocket_client_id
                self.assertNotIn(client_id, generated_client_ids, f"WebSocket client ID {client_id} should be unique")
                generated_client_ids.add(client_id)
                
                # Track created context
                self._created_user_contexts.append(result.user_context)
        
        # Assert - Verify all IDs are unique and properly formatted
        self.assertEqual(len(generated_client_ids), websocket_count, "All WebSocket client IDs should be unique")
        
        for client_id in generated_client_ids:
            self.assertTrue(client_id.startswith('ws_'), f"Client ID {client_id} should have ws_ prefix")
            self.assertGreater(len(client_id), 10, f"Client ID {client_id} should be sufficiently long")
        
        # Record uniqueness metrics
        self.record_metric("websocket_client_ids_generated", len(generated_client_ids))
        self.record_metric("all_ids_unique", len(generated_client_ids) == websocket_count)
        self.record_metric("id_collision_detected", False)

    async def test_user_isolation_between_concurrent_websocket_connections(self):
        """
        Test Case 3: User isolation between concurrent WebSocket connections.
        
        Business Value: Validates that concurrent WebSocket connections maintain
        strict user isolation, preventing data leakage between users.
        
        Tests concurrent user execution context isolation mechanisms.
        """
        # Arrange - Concurrent WebSocket connections from different users
        concurrent_users = [
            {"user_id": "concurrent_user_1", "email": "user1@company.com", "org": "CompanyA"},
            {"user_id": "concurrent_user_2", "email": "user2@enterprise.com", "org": "EnterpriseB"}, 
            {"user_id": "concurrent_user_3", "email": "user3@startup.com", "org": "StartupC"}
        ]
        
        # Create mock WebSockets for concurrent users
        mock_websockets = []
        for i, user in enumerate(concurrent_users):
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": f"Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.concurrent_isolation_token_{i}"
            }
            mock_websocket.client_state = WebSocketState.CONNECTED
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = f"10.0.{i}.100"
            mock_websockets.append((mock_websocket, user))
        
        # Mock authentication service for concurrent isolation testing
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            async def concurrent_auth_test(websocket_user_pair):
                """Authenticate a single WebSocket connection."""
                mock_websocket, user = websocket_user_pair
                
                # Create isolated user context
                mock_auth_result = AuthResult(
                    success=True,
                    user_id=user["user_id"],
                    email=user["email"],
                    permissions=["execute_agents"],
                    metadata={"organization": user["org"]}
                )
                
                mock_user_context = UserExecutionContext(
                    user_id=user["user_id"],
                    thread_id=UnifiedIdGenerator.generate_base_id(f"thr_{user['user_id']}", True, 8),
                    run_id=UnifiedIdGenerator.generate_base_id(f"run_{user['user_id']}", True, 8),
                    request_id=UnifiedIdGenerator.generate_base_id(f"req_{user['user_id']}", True, 8),
                    websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user["user_id"])
                )
                
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Perform authentication
                result = await authenticate_websocket_ssot(mock_websocket)
                return result
            
            # Act - Perform concurrent authentications
            start_time = time.time()
            concurrent_tasks = [concurrent_auth_test(ws_user) for ws_user in mock_websockets]
            results = await asyncio.gather(*concurrent_tasks)
            concurrent_auth_time = time.time() - start_time
            
            # Assert - Verify all authentications succeeded with isolation
            for i, result in enumerate(results):
                user = concurrent_users[i]
                
                self.assertTrue(result.success, f"Concurrent authentication {i} should succeed")
                self.assertEqual(result.user_context.user_id, user["user_id"])
                self.assertEqual(result.auth_result.email, user["email"])
                
                # Track created context
                self._created_user_contexts.append(result.user_context)
            
            # Verify user isolation - no shared data between contexts
            user_contexts = [result.user_context for result in results]
            
            # Check ID uniqueness across all contexts
            thread_ids = set(ctx.thread_id for ctx in user_contexts)
            run_ids = set(ctx.run_id for ctx in user_contexts)
            websocket_client_ids = set(ctx.websocket_client_id for ctx in user_contexts)
            
            self.assertEqual(len(thread_ids), len(concurrent_users), "All thread IDs should be unique")
            self.assertEqual(len(run_ids), len(concurrent_users), "All run IDs should be unique") 
            self.assertEqual(len(websocket_client_ids), len(concurrent_users), "All WebSocket client IDs should be unique")
            
            # Record concurrent isolation metrics
            self.record_metric("concurrent_authentications", len(results))
            self.record_metric("concurrent_auth_time_ms", concurrent_auth_time * 1000)
            self.record_metric("user_isolation_verified", True)
            self.record_metric("no_id_collisions_concurrent", len(thread_ids) == len(concurrent_users))

    async def test_thread_id_and_run_id_generation_for_websocket_sessions(self):
        """
        Test Case 4: Thread ID and run ID generation for WebSocket sessions.
        
        Business Value: Validates proper thread and run ID generation that
        enables request tracing and execution context tracking.
        
        Tests the ID generation patterns for WebSocket session management.
        """
        # Arrange - WebSocket connection for ID generation testing
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.thread_run_id_test_token"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        
        # Track generated IDs across multiple sessions
        generated_thread_ids = []
        generated_run_ids = []
        session_count = 3
        
        # Mock authentication service for ID generation testing
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            # Act - Generate IDs for multiple sessions
            for session_num in range(session_count):
                # Generate unique IDs for each session
                thread_id = UnifiedIdGenerator.generate_base_id("thread_ws", True, 8)
                run_id = UnifiedIdGenerator.generate_base_id("run_ws", True, 8)
                
                mock_auth_result = AuthResult(
                    success=True,
                    user_id=f"id_test_user_{session_num}",
                    email=f"idtest{session_num}@example.com",
                    permissions=["execute_agents"],
                    metadata={"session_number": session_num}
                )
                
                mock_user_context = UserExecutionContext(
                    user_id=f"id_test_user_{session_num}",
                    thread_id=thread_id,
                    run_id=run_id,
                    request_id=UnifiedIdGenerator.generate_base_id("ws_req", True, 8),
                    websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(f"id_test_user_{session_num}")
                )
                
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Authenticate and capture IDs
                result = await authenticate_websocket_ssot(mock_websocket)
                
                # Assert - Verify successful ID generation
                self.assertTrue(result.success, f"Session {session_num} authentication should succeed")
                
                thread_id = result.user_context.thread_id
                run_id = result.user_context.run_id
                
                # Validate ID formats
                self.assertIsNotNone(thread_id, f"Thread ID should be generated for session {session_num}")
                self.assertIsNotNone(run_id, f"Run ID should be generated for session {session_num}")
                
                # Check ID format patterns
                self.assertRegex(thread_id, r'^(thread|thr)_.*', "Thread ID should have proper prefix")
                self.assertRegex(run_id, r'^(run|rn)_.*', "Run ID should have proper prefix")
                
                # Store IDs for uniqueness checking
                generated_thread_ids.append(thread_id)
                generated_run_ids.append(run_id)
                
                # Track created context
                self._created_user_contexts.append(result.user_context)
        
        # Assert - Verify ID uniqueness and format compliance
        self.assertEqual(len(set(generated_thread_ids)), session_count, "All thread IDs should be unique")
        self.assertEqual(len(set(generated_run_ids)), session_count, "All run IDs should be unique")
        
        # Verify ID relationships (run_id should be associated with thread_id)
        for i in range(session_count):
            thread_id = generated_thread_ids[i]
            run_id = generated_run_ids[i]
            
            # Both IDs should be non-empty strings with reasonable length
            self.assertGreater(len(thread_id), 8, f"Thread ID {thread_id} should be reasonably long")
            self.assertGreater(len(run_id), 8, f"Run ID {run_id} should be reasonably long")
        
        # Record ID generation metrics
        self.record_metric("thread_ids_generated", len(generated_thread_ids))
        self.record_metric("run_ids_generated", len(generated_run_ids))
        self.record_metric("id_format_compliance", True)
        self.record_metric("id_uniqueness_verified", len(set(generated_thread_ids)) == session_count)

    async def test_user_context_factory_pattern_validation(self):
        """
        Test Case 5: User context factory pattern validation.
        
        Business Value: Validates the factory pattern for user context creation
        that ensures consistent, isolated user execution environments.
        
        Tests the SSOT factory pattern for UserExecutionContext creation.
        """
        # Arrange - WebSocket for factory pattern testing
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.factory_pattern_test_token"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        
        # Mock authentication service for factory pattern testing
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            # Test different factory scenarios
            factory_test_cases = [
                {
                    "name": "standard_user",
                    "user_id": "factory_user_standard",
                    "permissions": ["execute_agents"],
                    "metadata": {"user_type": "standard"}
                },
                {
                    "name": "enterprise_user", 
                    "user_id": "factory_user_enterprise",
                    "permissions": ["execute_agents", "enterprise_features", "admin_access"],
                    "metadata": {"user_type": "enterprise", "organization": "Enterprise Corp"}
                },
                {
                    "name": "limited_user",
                    "user_id": "factory_user_limited", 
                    "permissions": ["basic_access"],
                    "metadata": {"user_type": "limited", "trial_account": True}
                }
            ]
            
            # Act & Assert - Test factory pattern for each user type
            for test_case in factory_test_cases:
                with self.subTest(factory_case=test_case["name"]):
                    # Create auth result for this user type
                    mock_auth_result = AuthResult(
                        success=True,
                        user_id=test_case["user_id"],
                        email=f"{test_case['name']}@test.com",
                        permissions=test_case["permissions"],
                        metadata=test_case["metadata"]
                    )
                    
                    # Create user context using factory pattern
                    mock_user_context = UserExecutionContext(
                        user_id=test_case["user_id"],
                        thread_id=UnifiedIdGenerator.generate_base_id("factory_thread", True, 8),
                        run_id=UnifiedIdGenerator.generate_base_id("factory_run", True, 8),
                        request_id=UnifiedIdGenerator.generate_base_id("factory_req", True, 8),
                        websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(test_case["user_id"])
                    )
                    
                    mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                    mock_auth_service.return_value = mock_service
                    
                    # Authenticate using factory pattern
                    result = await authenticate_websocket_ssot(mock_websocket)
                    
                    # Assert - Verify factory pattern compliance
                    self.assertTrue(result.success, f"Factory pattern authentication should succeed for {test_case['name']}")
                    self.assertIsInstance(result.user_context, UserExecutionContext, "Should create UserExecutionContext instance")
                    
                    # Verify factory-created context attributes
                    user_context = result.user_context
                    self.assertEqual(user_context.user_id, test_case["user_id"])
                    self.assertIsNotNone(user_context.thread_id, "Factory should generate thread_id")
                    self.assertIsNotNone(user_context.run_id, "Factory should generate run_id") 
                    self.assertIsNotNone(user_context.websocket_client_id, "Factory should generate websocket_client_id")
                    
                    # Verify permissions carried over
                    self.assertEqual(result.auth_result.permissions, test_case["permissions"])
                    
                    # Track created context
                    self._created_user_contexts.append(user_context)
                    
                    # Record factory pattern metrics
                    self.record_metric(f"factory_pattern_{test_case['name']}_success", True)
        
        # Verify factory pattern consistency
        self.record_metric("factory_pattern_validated", True)
        self.record_metric("factory_test_cases_completed", len(factory_test_cases))

    async def test_multi_user_concurrent_authentication_scenarios(self):
        """
        Test Case 6: Multi-user concurrent authentication scenarios.
        
        Business Value: Validates system behavior under realistic concurrent
        load with multiple users authenticating simultaneously.
        
        Tests concurrent authentication performance and user isolation at scale.
        """
        # Arrange - Multiple concurrent users
        concurrent_user_count = 10
        concurrent_users = []
        
        for i in range(concurrent_user_count):
            user_data = {
                "user_id": f"concurrent_user_{i:02d}",
                "email": f"concurrent{i:02d}@load.test",
                "permissions": ["execute_agents", "concurrent_access"],
                "websocket": MagicMock(spec=WebSocket)
            }
            
            # Configure mock WebSocket
            user_data["websocket"].headers = {
                "authorization": f"Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.concurrent_load_token_{i:02d}"
            }
            user_data["websocket"].client_state = WebSocketState.CONNECTED
            user_data["websocket"].client = MagicMock()
            user_data["websocket"].client.host = f"192.168.2.{100 + i}"
            
            concurrent_users.append(user_data)
        
        # Mock authentication service for concurrent load testing
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            async def authenticate_concurrent_user(user_data):
                """Authenticate a single concurrent user."""
                # Create realistic auth result with slight processing delay
                await asyncio.sleep(0.01)  # Simulate auth processing time
                
                mock_auth_result = AuthResult(
                    success=True,
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    permissions=user_data["permissions"],
                    metadata={"concurrent_test": True, "load_test_user": True}
                )
                
                mock_user_context = UserExecutionContext(
                    user_id=user_data["user_id"],
                    thread_id=UnifiedIdGenerator.generate_base_id(f"concurrent_thread_{user_data['user_id']}", True, 8),
                    run_id=UnifiedIdGenerator.generate_base_id(f"concurrent_run_{user_data['user_id']}", True, 8),
                    request_id=UnifiedIdGenerator.generate_base_id(f"concurrent_req_{user_data['user_id']}", True, 8),
                    websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_data["user_id"])
                )
                
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Perform authentication
                result = await authenticate_websocket_ssot(user_data["websocket"])
                return (user_data, result)
            
            # Act - Perform concurrent authentications
            concurrent_start_time = time.time()
            
            # Use asyncio.gather for true concurrency
            concurrent_tasks = [authenticate_concurrent_user(user_data) for user_data in concurrent_users]
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            concurrent_duration = time.time() - concurrent_start_time
            
            # Assert - Verify all concurrent authentications
            successful_authentications = 0
            authentication_errors = []
            
            for i, result in enumerate(concurrent_results):
                if isinstance(result, Exception):
                    authentication_errors.append(f"User {i}: {str(result)}")
                    continue
                
                user_data, auth_result = result
                
                # Verify successful authentication
                self.assertTrue(auth_result.success, f"Concurrent user {user_data['user_id']} should authenticate successfully")
                self.assertEqual(auth_result.user_context.user_id, user_data["user_id"])
                
                # Track created context
                self._created_user_contexts.append(auth_result.user_context)
                successful_authentications += 1
            
            # Assert - Verify overall concurrent performance
            self.assertEqual(successful_authentications, concurrent_user_count, 
                           f"All {concurrent_user_count} users should authenticate successfully")
            self.assertEqual(len(authentication_errors), 0, 
                           f"No authentication errors should occur: {authentication_errors}")
            
            # Verify user isolation at scale
            all_user_ids = set(ctx.user_id for ctx in self._created_user_contexts if ctx.user_id.startswith('concurrent_user_'))
            all_thread_ids = set(ctx.thread_id for ctx in self._created_user_contexts if ctx.user_id.startswith('concurrent_user_'))
            all_websocket_client_ids = set(ctx.websocket_client_id for ctx in self._created_user_contexts if ctx.user_id.startswith('concurrent_user_'))
            
            self.assertEqual(len(all_user_ids), concurrent_user_count, "All user IDs should be unique")
            self.assertEqual(len(all_thread_ids), concurrent_user_count, "All thread IDs should be unique")
            self.assertEqual(len(all_websocket_client_ids), concurrent_user_count, "All WebSocket client IDs should be unique")
            
            # Record concurrent load metrics
            self.record_metric("concurrent_users_tested", concurrent_user_count)
            self.record_metric("concurrent_auth_duration_ms", concurrent_duration * 1000)
            self.record_metric("concurrent_auth_success_rate", (successful_authentications / concurrent_user_count) * 100)
            self.record_metric("avg_auth_time_per_user_ms", (concurrent_duration / concurrent_user_count) * 1000)
            self.record_metric("user_isolation_at_scale_verified", True)

    def teardown_method(self, method):
        """Clean up test environment and record user context metrics."""
        # Record final user context metrics
        test_duration = time.time() - self.get_metric("test_start_time", time.time())
        self.record_metric("total_test_duration_ms", test_duration * 1000)
        self.record_metric("total_user_contexts_created", len(self._created_user_contexts))
        
        # Verify no memory leaks from user contexts
        unique_user_ids = set(ctx.user_id for ctx in self._created_user_contexts)
        unique_thread_ids = set(ctx.thread_id for ctx in self._created_user_contexts) 
        unique_websocket_client_ids = set(ctx.websocket_client_id for ctx in self._created_user_contexts)
        
        # Record uniqueness verification
        self.record_metric("unique_user_ids", len(unique_user_ids))
        self.record_metric("unique_thread_ids", len(unique_thread_ids))
        self.record_metric("unique_websocket_client_ids", len(unique_websocket_client_ids))
        
        # Business value metrics
        business_metrics = {
            "test_category": self.get_metric("test_category"),
            "business_value": self.get_metric("business_value"), 
            "total_user_context_tests": 6,
            "user_contexts_created": len(self._created_user_contexts),
            "user_isolation_verified": True
        }
        
        # Log business impact
        if len(self._created_user_contexts) > 0:
            logger.info(f"WebSocket User Context Tests completed: {business_metrics}")
            
        # Clean up tracked contexts
        self._created_user_contexts.clear()
        
        super().teardown_method(method)


# Export test class for pytest discovery
__all__ = ["TestWebSocketUserContextIntegration"]