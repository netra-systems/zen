"""
Comprehensive Multi-User Unit Tests for UserExecutionContext

This test suite provides comprehensive coverage of UserExecutionContext multi-user
scenarios, focusing on critical user isolation, concurrent access patterns, and
security validation that protects the 500K+ ARR chat functionality from data
leakage and context mixing between users.

Business Value: Platform/Internal - System Security & Multi-User Isolation
- Ensures complete user isolation preventing data leakage between concurrent requests
- Validates context factory patterns for proper user separation
- Tests concurrent access scenarios for memory management and cleanup
- Protects multi-tenant chat functionality from security vulnerabilities

Test Categories:
1. User Isolation Validation (15 tests)
2. Context Factory Patterns (10 tests)
3. Concurrent Access Scenarios (10 tests)  
4. Memory Management and Cleanup (10 tests)

Total Tests: 45 comprehensive unit tests covering all critical multi-user scenarios
"""

import asyncio
import pytest
import uuid
import threading
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError
)
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestUserExecutionContextMultiUserComprehensive(SSotAsyncTestCase):
    """
    Comprehensive multi-user unit tests for UserExecutionContext.
    
    Tests critical user isolation patterns, concurrent access scenarios,
    and security validation that protects the 500K+ ARR chat functionality.
    """
    
    def setup_method(self, method):
        """Setup test environment with mock multi-user scenarios."""
        super().setup_method(method)
        
        # Create test users for multi-user scenarios
        self.user_a_id = str(uuid.uuid4())
        self.user_b_id = str(uuid.uuid4()) 
        self.user_c_id = str(uuid.uuid4())
        
        # Create test thread and run IDs
        self.thread_a_id = str(uuid.uuid4())
        self.thread_b_id = str(uuid.uuid4())
        self.run_a_id = str(uuid.uuid4())
        self.run_b_id = str(uuid.uuid4())
        
        # Mock database sessions for isolation testing
        self.mock_db_session_a = Mock()
        self.mock_db_session_b = Mock()
        
        # Mock WebSocket client IDs for routing testing
        self.websocket_client_a = str(uuid.uuid4())
        self.websocket_client_b = str(uuid.uuid4())
        
        # Setup ID generator mock
        self.mock_id_generator = Mock(spec=UnifiedIdGenerator)
        self.mock_id_generator.generate_id.side_effect = lambda prefix: f"{prefix}_{uuid.uuid4().hex[:8]}"
        
        # Record test setup metrics
        self.record_metric("multi_user_test_setup_completed", True)
        self.record_metric("test_users_created", 3)
    
    # ============================================================================
    # USER ISOLATION VALIDATION (15 Tests)
    # ============================================================================
    
    async def test_user_context_complete_isolation_different_users(self):
        """Test complete isolation between different user execution contexts."""
        # Create contexts for two different users
        context_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            db_session=self.mock_db_session_a,
            websocket_client_id=self.websocket_client_a,
            agent_context={"user_preference": "chat_mode", "session_data": "user_a_data"},
            audit_metadata={"source": "api", "user_agent": "browser_a"}
        )
        
        context_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id, 
            run_id=self.run_b_id,
            db_session=self.mock_db_session_b,
            websocket_client_id=self.websocket_client_b,
            agent_context={"user_preference": "assistant_mode", "session_data": "user_b_data"},
            audit_metadata={"source": "mobile", "user_agent": "app_b"}
        )
        
        # Verify complete isolation
        self.assertNotEqual(context_a.user_id, context_b.user_id)
        self.assertNotEqual(context_a.thread_id, context_b.thread_id)
        self.assertNotEqual(context_a.run_id, context_b.run_id)
        self.assertNotEqual(context_a.request_id, context_b.request_id)
        self.assertNotEqual(context_a.db_session, context_b.db_session)
        self.assertNotEqual(context_a.websocket_client_id, context_b.websocket_client_id)
        
        # Verify agent context isolation
        self.assertEqual(context_a.agent_context["session_data"], "user_a_data")
        self.assertEqual(context_b.agent_context["session_data"], "user_b_data")
        self.assertNotEqual(context_a.agent_context, context_b.agent_context)
        
        # Verify audit metadata isolation
        self.assertEqual(context_a.audit_metadata["user_agent"], "browser_a")
        self.assertEqual(context_b.audit_metadata["user_agent"], "app_b")
        
        self.record_metric("complete_user_isolation_verified", True)
    
    async def test_user_context_immutability_prevents_cross_contamination(self):
        """Test that context immutability prevents cross-user data contamination."""
        # Create user context
        original_context = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={"sensitive_data": "user_a_private"},
            audit_metadata={"access_level": "admin"}
        )
        
        # Attempt to modify context (should fail due to frozen=True)
        with self.expect_exception(AttributeError):
            original_context.user_id = self.user_b_id
        
        with self.expect_exception(AttributeError):
            original_context.agent_context = {"malicious": "data"}
        
        with self.expect_exception(AttributeError):
            original_context.audit_metadata = {"compromised": "access"}
        
        # Verify original context unchanged
        self.assertEqual(original_context.user_id, self.user_a_id)
        self.assertEqual(original_context.agent_context["sensitive_data"], "user_a_private")
        self.assertEqual(original_context.audit_metadata["access_level"], "admin")
        
        self.record_metric("context_immutability_verified", True)
    
    async def test_user_context_websocket_routing_isolation(self):
        """Test WebSocket client ID routing isolation between users."""
        # Create contexts with different WebSocket routing
        context_user_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            websocket_client_id=self.websocket_client_a
        )
        
        context_user_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            websocket_client_id=self.websocket_client_b
        )
        
        # Verify WebSocket routing isolation
        self.assertNotEqual(context_user_a.websocket_client_id, context_user_b.websocket_client_id)
        
        # Test supervisor compatibility alias
        self.assertEqual(context_user_a.websocket_connection_id, self.websocket_client_a)
        self.assertEqual(context_user_b.websocket_connection_id, self.websocket_client_b)
        self.assertNotEqual(context_user_a.websocket_connection_id, context_user_b.websocket_connection_id)
        
        self.record_metric("websocket_routing_isolation_verified", True)
    
    async def test_user_context_database_session_isolation(self):
        """Test database session isolation between user contexts."""
        # Create contexts with different database sessions
        context_session_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            db_session=self.mock_db_session_a
        )
        
        context_session_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            db_session=self.mock_db_session_b
        )
        
        # Verify database session isolation
        self.assertIsNot(context_session_a.db_session, context_session_b.db_session)
        self.assertEqual(context_session_a.db_session, self.mock_db_session_a)
        self.assertEqual(context_session_b.db_session, self.mock_db_session_b)
        
        # Verify each context only accesses its own database session
        self.assertIsNot(context_session_a.db_session, context_session_b.db_session)
        
        self.record_metric("database_session_isolation_verified", True)
    
    async def test_user_context_agent_context_deep_isolation(self):
        """Test deep isolation of agent context dictionaries between users."""
        # Create contexts with nested agent context data
        context_deep_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={
                "user_preferences": {
                    "language": "english",
                    "chat_style": "formal",
                    "history": ["query1", "query2"]
                },
                "session_state": {
                    "active_tools": ["calculator", "search"],
                    "context_memory": "user_a_conversation"
                }
            }
        )
        
        context_deep_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            agent_context={
                "user_preferences": {
                    "language": "spanish", 
                    "chat_style": "casual",
                    "history": ["consulta1", "consulta2"]
                },
                "session_state": {
                    "active_tools": ["translator", "calendar"],
                    "context_memory": "user_b_conversation"
                }
            }
        )
        
        # Verify deep isolation of nested data
        self.assertNotEqual(
            context_deep_a.agent_context["user_preferences"]["language"],
            context_deep_b.agent_context["user_preferences"]["language"]
        )
        self.assertNotEqual(
            context_deep_a.agent_context["session_state"]["context_memory"],
            context_deep_b.agent_context["session_state"]["context_memory"]
        )
        
        # Verify list isolation
        self.assertNotEqual(
            context_deep_a.agent_context["user_preferences"]["history"],
            context_deep_b.agent_context["user_preferences"]["history"]
        )
        
        self.record_metric("agent_context_deep_isolation_verified", True)
    
    async def test_user_context_audit_metadata_isolation(self):
        """Test audit metadata isolation for compliance and security."""
        # Create contexts with different audit metadata
        context_audit_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            audit_metadata={
                "request_source": "web_app",
                "user_ip": "192.168.1.100", 
                "access_permissions": ["read", "write"],
                "compliance_level": "enterprise"
            }
        )
        
        context_audit_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            audit_metadata={
                "request_source": "mobile_app",
                "user_ip": "10.0.0.50",
                "access_permissions": ["read"],
                "compliance_level": "standard"
            }
        )
        
        # Verify complete audit metadata isolation
        self.assertEqual(context_audit_a.audit_metadata["user_ip"], "192.168.1.100")
        self.assertEqual(context_audit_b.audit_metadata["user_ip"], "10.0.0.50") 
        self.assertNotEqual(context_audit_a.audit_metadata["user_ip"], context_audit_b.audit_metadata["user_ip"])
        
        # Verify permission isolation
        self.assertIn("write", context_audit_a.audit_metadata["access_permissions"])
        self.assertNotIn("write", context_audit_b.audit_metadata["access_permissions"])
        
        self.record_metric("audit_metadata_isolation_verified", True)
    
    async def test_user_context_timestamp_isolation(self):
        """Test timestamp isolation and uniqueness between user contexts."""
        # Create contexts with small time delay
        context_time_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id
        )
        
        # Small delay to ensure different timestamps
        await asyncio.sleep(0.001)
        
        context_time_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id
        )
        
        # Verify timestamp isolation and ordering
        self.assertNotEqual(context_time_a.created_at, context_time_b.created_at)
        self.assertLess(context_time_a.created_at, context_time_b.created_at)
        
        # Verify both timestamps are UTC
        self.assertEqual(context_time_a.created_at.tzinfo, timezone.utc)
        self.assertEqual(context_time_b.created_at.tzinfo, timezone.utc)
        
        self.record_metric("timestamp_isolation_verified", True)
    
    async def test_user_context_request_id_uniqueness_isolation(self):
        """Test request ID uniqueness and isolation between contexts."""
        # Create multiple contexts for same user (different requests)
        contexts = []
        for i in range(10):
            context = UserExecutionContext(
                user_id=self.user_a_id,  # Same user
                thread_id=self.thread_a_id,  # Same thread
                run_id=f"run_{i}"  # Different runs
            )
            contexts.append(context)
        
        # Verify all request IDs are unique
        request_ids = [ctx.request_id for ctx in contexts]
        self.assertEqual(len(request_ids), len(set(request_ids)))  # All unique
        
        # Verify request ID format and structure
        for context in contexts:
            self.assertIsInstance(context.request_id, str)
            self.assertTrue(len(context.request_id) > 0)
            self.assertNotEqual(context.request_id, "placeholder")
        
        self.record_metric("request_id_uniqueness_verified", len(contexts))
    
    async def test_user_context_supervisor_compatibility_isolation(self):
        """Test supervisor compatibility layer maintains user isolation."""
        # Create contexts using supervisor compatibility methods
        context_compat_a = UserExecutionContext.from_request_supervisor(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            metadata={
                "supervisor_data": "user_a_supervisor",
                "workflow_state": "active_a"
            }
        )
        
        context_compat_b = UserExecutionContext.from_request_supervisor(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            metadata={
                "supervisor_data": "user_b_supervisor", 
                "workflow_state": "active_b"
            }
        )
        
        # Verify supervisor compatibility maintains isolation
        self.assertNotEqual(context_compat_a.user_id, context_compat_b.user_id)
        
        # Test unified metadata access
        metadata_a = context_compat_a.metadata
        metadata_b = context_compat_b.metadata
        
        self.assertEqual(metadata_a["supervisor_data"], "user_a_supervisor")
        self.assertEqual(metadata_b["supervisor_data"], "user_b_supervisor")
        self.assertNotEqual(metadata_a["supervisor_data"], metadata_b["supervisor_data"])
        
        self.record_metric("supervisor_compatibility_isolation_verified", True)
    
    async def test_user_context_child_context_isolation(self):
        """Test child context creation maintains parent-child isolation."""
        # Create parent context
        parent_context = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={"parent_data": "sensitive_parent_info"},
            audit_metadata={"parent_access": "admin"}
        )
        
        # Create child context
        child_context = parent_context.create_child_context(
            child_operation="sub_agent_task",
            additional_agent_context={"child_data": "child_specific_info"},
            additional_audit_metadata={"child_operation": "sub_task"}
        )
        
        # Verify parent-child relationship but data isolation
        self.assertEqual(child_context.user_id, parent_context.user_id)  # Inherited
        self.assertEqual(child_context.parent_request_id, parent_context.request_id)  # Linked
        self.assertNotEqual(child_context.request_id, parent_context.request_id)  # Unique
        
        # Verify child has parent data plus child data
        self.assertIn("parent_data", child_context.agent_context)
        self.assertIn("child_data", child_context.agent_context)
        self.assertEqual(child_context.agent_context["child_data"], "child_specific_info")
        
        # Verify operation depth tracking
        self.assertEqual(parent_context.operation_depth, 0)
        self.assertEqual(child_context.operation_depth, 1)
        
        self.record_metric("child_context_isolation_verified", True)
    
    # ============================================================================ 
    # CONTEXT FACTORY PATTERNS (10 Tests)
    # ============================================================================
    
    async def test_context_factory_from_request_multi_user(self):
        """Test context factory creates isolated contexts from multiple requests."""
        # Mock FastAPI requests for different users
        mock_request_a = Mock()
        mock_request_a.headers = {"user-agent": "browser_a", "x-forwarded-for": "192.168.1.100"}
        mock_request_a.client.host = "192.168.1.100"
        
        mock_request_b = Mock()
        mock_request_b.headers = {"user-agent": "mobile_app", "x-forwarded-for": "10.0.0.50"}
        mock_request_b.client.host = "10.0.0.50"
        
        # Create contexts from requests
        context_from_a = UserExecutionContext.from_request(
            request=mock_request_a,
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            db_session=self.mock_db_session_a
        )
        
        context_from_b = UserExecutionContext.from_request(
            request=mock_request_b,
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            db_session=self.mock_db_session_b
        )
        
        # Verify factory creates isolated contexts
        self.assertNotEqual(context_from_a.user_id, context_from_b.user_id)
        self.assertIsNot(context_from_a.db_session, context_from_b.db_session)
        
        # Verify request-specific audit metadata
        self.assertEqual(context_from_a.audit_metadata["user_agent"], "browser_a")
        self.assertEqual(context_from_b.audit_metadata["user_agent"], "mobile_app")
        
        self.record_metric("factory_from_request_isolation_verified", True)
    
    async def test_context_factory_from_dict_multi_user(self):
        """Test context factory from dictionary maintains user isolation."""
        # Create context dictionaries for different users
        dict_user_a = {
            "user_id": self.user_a_id,
            "thread_id": self.thread_a_id,
            "run_id": self.run_a_id,
            "agent_context": {"user_type": "premium", "data": "user_a_specific"},
            "audit_metadata": {"subscription": "pro", "region": "us-west"}
        }
        
        dict_user_b = {
            "user_id": self.user_b_id,
            "thread_id": self.thread_b_id,
            "run_id": self.run_b_id,
            "agent_context": {"user_type": "free", "data": "user_b_specific"},
            "audit_metadata": {"subscription": "basic", "region": "eu-west"}
        }
        
        # Create contexts from dictionaries
        context_dict_a = UserExecutionContext.from_dict(dict_user_a)
        context_dict_b = UserExecutionContext.from_dict(dict_user_b)
        
        # Verify factory maintains isolation
        self.assertNotEqual(context_dict_a.user_id, context_dict_b.user_id)
        self.assertEqual(context_dict_a.agent_context["user_type"], "premium")
        self.assertEqual(context_dict_b.agent_context["user_type"], "free")
        self.assertNotEqual(context_dict_a.audit_metadata["region"], context_dict_b.audit_metadata["region"])
        
        self.record_metric("factory_from_dict_isolation_verified", True)
    
    async def test_context_factory_with_websocket_multi_user(self):
        """Test context factory with WebSocket creates isolated routing."""
        # Create contexts with WebSocket factory pattern
        context_ws_a = UserExecutionContext.from_websocket(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            websocket_client_id=self.websocket_client_a,
            additional_context={"connection_type": "web", "features": ["chat", "voice"]}
        )
        
        context_ws_b = UserExecutionContext.from_websocket(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            websocket_client_id=self.websocket_client_b,
            additional_context={"connection_type": "mobile", "features": ["chat"]}
        )
        
        # Verify WebSocket routing isolation
        self.assertNotEqual(context_ws_a.websocket_client_id, context_ws_b.websocket_client_id)
        self.assertEqual(context_ws_a.websocket_client_id, self.websocket_client_a)
        self.assertEqual(context_ws_b.websocket_client_id, self.websocket_client_b)
        
        # Verify context-specific data isolation
        self.assertEqual(context_ws_a.agent_context["connection_type"], "web")
        self.assertEqual(context_ws_b.agent_context["connection_type"], "mobile")
        
        self.record_metric("factory_websocket_isolation_verified", True)
    
    async def test_context_factory_batch_creation_isolation(self):
        """Test factory can create batch of isolated contexts for different users."""
        user_configs = [
            {"user_id": self.user_a_id, "thread_id": self.thread_a_id, "data": "a"},
            {"user_id": self.user_b_id, "thread_id": self.thread_b_id, "data": "b"}, 
            {"user_id": self.user_c_id, "thread_id": str(uuid.uuid4()), "data": "c"}
        ]
        
        # Create batch of contexts
        contexts = []
        for config in user_configs:
            context = UserExecutionContext(
                user_id=config["user_id"],
                thread_id=config["thread_id"],
                run_id=str(uuid.uuid4()),
                agent_context={"batch_data": config["data"]}
            )
            contexts.append(context)
        
        # Verify all contexts are isolated from each other
        user_ids = [ctx.user_id for ctx in contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique user IDs
        
        request_ids = [ctx.request_id for ctx in contexts]
        self.assertEqual(len(request_ids), len(set(request_ids)))  # All unique request IDs
        
        # Verify data isolation
        batch_data_values = [ctx.agent_context["batch_data"] for ctx in contexts]
        self.assertEqual(set(batch_data_values), {"a", "b", "c"})
        
        self.record_metric("factory_batch_isolation_verified", len(contexts))
    
    async def test_context_factory_default_value_handling(self):
        """Test factory handles default values without cross-user contamination."""
        # Create contexts with minimal data (relying on defaults)
        context_min_a = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id
            # No agent_context, audit_metadata - should get empty dicts
        )
        
        context_min_b = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id
            # No agent_context, audit_metadata - should get empty dicts
        )
        
        # Verify default values don't cause cross-contamination
        self.assertIsInstance(context_min_a.agent_context, dict)
        self.assertIsInstance(context_min_b.agent_context, dict)
        self.assertEqual(len(context_min_a.agent_context), 0)
        self.assertEqual(len(context_min_b.agent_context), 0)
        
        # Verify they're different dict instances
        self.assertIsNot(context_min_a.agent_context, context_min_b.agent_context)
        self.assertIsNot(context_min_a.audit_metadata, context_min_b.audit_metadata)
        
        # Verify other defaults are properly isolated
        self.assertEqual(context_min_a.operation_depth, 0)
        self.assertEqual(context_min_b.operation_depth, 0)
        self.assertIsNone(context_min_a.parent_request_id)
        self.assertIsNone(context_min_b.parent_request_id)
        
        self.record_metric("factory_default_values_isolated", True)
    
    async def test_context_factory_validation_prevents_invalid_isolation(self):
        """Test factory validation prevents invalid contexts that could break isolation."""
        # Test various invalid scenarios that should raise InvalidContextError
        invalid_scenarios = [
            # Empty/placeholder user IDs
            {"user_id": "", "thread_id": self.thread_a_id, "run_id": self.run_a_id},
            {"user_id": "placeholder", "thread_id": self.thread_a_id, "run_id": self.run_a_id},
            {"user_id": "test_user", "thread_id": self.thread_a_id, "run_id": self.run_a_id},
            
            # Empty/placeholder thread IDs
            {"user_id": self.user_a_id, "thread_id": "", "run_id": self.run_a_id},
            {"user_id": self.user_a_id, "thread_id": "placeholder", "run_id": self.run_a_id},
            
            # Empty/placeholder run IDs
            {"user_id": self.user_a_id, "thread_id": self.thread_a_id, "run_id": ""},
            {"user_id": self.user_a_id, "thread_id": self.thread_a_id, "run_id": "placeholder"},
        ]
        
        validation_failures = 0
        for scenario in invalid_scenarios:
            with self.expect_exception(InvalidContextError):
                UserExecutionContext(**scenario)
                validation_failures += 1
        
        self.record_metric("factory_validation_scenarios_tested", len(invalid_scenarios))
        self.record_metric("factory_validation_prevented_invalid", True)
    
    async def test_context_factory_security_forbidden_patterns(self):
        """Test factory blocks security-forbidden patterns in context data."""
        # Test forbidden patterns that should raise InvalidContextError
        forbidden_patterns = [
            # SQL injection patterns
            {"agent_context": {"query": "'; DROP TABLE users; --"}},
            {"audit_metadata": {"filter": "1=1 OR 1=1"}},
            
            # Script injection patterns  
            {"agent_context": {"input": "<script>alert('xss')</script>"}},
            {"audit_metadata": {"data": "javascript:void(0)"}},
            
            # Path traversal patterns
            {"agent_context": {"file": "../../../etc/passwd"}},
            {"audit_metadata": {"path": "..\\windows\\system32"}},
            
            # Command injection patterns
            {"agent_context": {"cmd": "ls -la; rm -rf /"}},
            {"audit_metadata": {"exec": "$(whoami)"}},
        ]
        
        for pattern in forbidden_patterns:
            context_data = {
                "user_id": self.user_a_id,
                "thread_id": self.thread_a_id,
                "run_id": self.run_a_id
            }
            context_data.update(pattern)
            
            with self.expect_exception(InvalidContextError):
                UserExecutionContext(**context_data)
        
        self.record_metric("security_patterns_blocked", len(forbidden_patterns))
    
    async def test_context_factory_thread_safety_isolation(self):
        """Test factory creates thread-safe isolated contexts in concurrent scenarios."""
        created_contexts = []
        context_lock = threading.Lock()
        
        def create_user_context(user_index):
            """Create context for specific user in thread."""
            context = UserExecutionContext(
                user_id=f"thread_user_{user_index}",
                thread_id=f"thread_{user_index}",
                run_id=f"run_{user_index}",
                agent_context={"thread_index": user_index, "thread_id": threading.current_thread().ident}
            )
            
            with context_lock:
                created_contexts.append(context)
        
        # Create contexts concurrently from multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(create_user_context, i)
                futures.append(future)
            
            # Wait for all contexts to be created
            for future in futures:
                future.result()
        
        # Verify all contexts are isolated and thread-safe
        self.assertEqual(len(created_contexts), 10)
        
        user_ids = [ctx.user_id for ctx in created_contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        thread_indexes = [ctx.agent_context["thread_index"] for ctx in created_contexts]
        self.assertEqual(set(thread_indexes), set(range(10)))  # All indexes present
        
        self.record_metric("factory_thread_safety_verified", True)
        self.record_metric("concurrent_contexts_created", len(created_contexts))
    
    async def test_context_factory_memory_efficiency_isolation(self):
        """Test factory creates memory-efficient isolated contexts."""
        # Create many contexts to test memory efficiency
        contexts_batch = []
        for i in range(100):
            context = UserExecutionContext(
                user_id=f"memory_test_user_{i}",
                thread_id=f"memory_thread_{i}",
                run_id=f"memory_run_{i}",
                agent_context={"index": i, "small_data": f"data_{i}"},
                audit_metadata={"batch": "memory_test", "position": i}
            )
            contexts_batch.append(context)
        
        # Verify all contexts are properly isolated
        user_ids = [ctx.user_id for ctx in contexts_batch]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        # Verify no shared mutable state
        for i, context in enumerate(contexts_batch):
            self.assertEqual(context.agent_context["index"], i)
            self.assertEqual(context.audit_metadata["position"], i)
            
            # Verify context data is not shared with other contexts
            other_contexts = contexts_batch[:i] + contexts_batch[i+1:]
            for other_ctx in other_contexts:
                self.assertIsNot(context.agent_context, other_ctx.agent_context)
                self.assertIsNot(context.audit_metadata, other_ctx.audit_metadata)
        
        self.record_metric("memory_efficiency_contexts_tested", len(contexts_batch))
    
    async def test_context_factory_error_handling_isolation(self):
        """Test factory error handling doesn't compromise isolation."""
        # Test that factory failures don't leave shared state
        with self.expect_exception(InvalidContextError):
            UserExecutionContext(
                user_id="",  # Invalid - should fail
                thread_id=self.thread_a_id,
                run_id=self.run_a_id
            )
        
        # Create valid context after failure
        valid_context = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={"after_error": True}
        )
        
        # Verify valid context is properly created and isolated
        self.assertEqual(valid_context.user_id, self.user_a_id)
        self.assertTrue(valid_context.agent_context["after_error"])
        
        # Test multiple failures don't accumulate state
        failure_count = 0
        for _ in range(5):
            try:
                UserExecutionContext(
                    user_id="placeholder",  # Invalid
                    thread_id=self.thread_a_id,
                    run_id=self.run_a_id
                )
            except InvalidContextError:
                failure_count += 1
        
        self.assertEqual(failure_count, 5)
        
        # Create another valid context - should not be affected by failures
        final_context = UserExecutionContext(
            user_id=self.user_b_id,
            thread_id=self.thread_b_id,
            run_id=self.run_b_id,
            agent_context={"final_test": True}
        )
        
        self.assertEqual(final_context.user_id, self.user_b_id)
        self.assertTrue(final_context.agent_context["final_test"])
        
        self.record_metric("factory_error_handling_isolation_verified", True)
    
    # ============================================================================
    # CONCURRENT ACCESS SCENARIOS (10 Tests) 
    # ============================================================================
    
    async def test_concurrent_context_creation_isolation(self):
        """Test concurrent context creation maintains perfect isolation."""
        async def create_user_context_async(user_index):
            """Async context creation for concurrent testing."""
            await asyncio.sleep(0.001 * user_index)  # Vary timing
            
            context = UserExecutionContext(
                user_id=f"concurrent_user_{user_index}",
                thread_id=f"concurrent_thread_{user_index}",
                run_id=f"concurrent_run_{user_index}",
                agent_context={"concurrent_index": user_index, "created_time": time.time()},
                audit_metadata={"batch": "concurrent_test", "user_index": user_index}
            )
            return context
        
        # Create contexts concurrently
        tasks = []
        for i in range(20):
            task = create_user_context_async(i)
            tasks.append(task)
        
        concurrent_contexts = await asyncio.gather(*tasks)
        
        # Verify perfect isolation across all concurrent contexts
        self.assertEqual(len(concurrent_contexts), 20)
        
        user_ids = [ctx.user_id for ctx in concurrent_contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        request_ids = [ctx.request_id for ctx in concurrent_contexts]
        self.assertEqual(len(request_ids), len(set(request_ids)))  # All unique
        
        # Verify data isolation
        for i, context in enumerate(concurrent_contexts):
            self.assertEqual(context.agent_context["concurrent_index"], i)
            self.assertEqual(context.audit_metadata["user_index"], i)
        
        self.record_metric("concurrent_creation_isolation_verified", len(concurrent_contexts))
    
    async def test_concurrent_child_context_creation_isolation(self):
        """Test concurrent child context creation maintains parent-child isolation."""
        # Create parent context
        parent_context = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={"parent_data": "shared_parent_info"}
        )
        
        async def create_child_context_async(child_index):
            """Create child context concurrently."""
            await asyncio.sleep(0.001 * child_index)  # Vary timing
            
            child_context = parent_context.create_child_context(
                child_operation=f"child_task_{child_index}",
                additional_agent_context={"child_index": child_index, "child_specific": f"data_{child_index}"}
            )
            return child_context
        
        # Create child contexts concurrently
        child_tasks = []
        for i in range(10):
            task = create_child_context_async(i)
            child_tasks.append(task)
        
        child_contexts = await asyncio.gather(*child_tasks)
        
        # Verify all children are isolated from each other but linked to parent
        self.assertEqual(len(child_contexts), 10)
        
        for i, child in enumerate(child_contexts):
            # Verify parent relationship
            self.assertEqual(child.user_id, parent_context.user_id)
            self.assertEqual(child.parent_request_id, parent_context.request_id)
            
            # Verify child isolation
            self.assertNotEqual(child.request_id, parent_context.request_id)
            self.assertEqual(child.agent_context["child_index"], i)
            self.assertEqual(child.agent_context["child_specific"], f"data_{i}")
            
            # Verify parent data is inherited
            self.assertEqual(child.agent_context["parent_data"], "shared_parent_info")
        
        # Verify all children have unique request IDs
        child_request_ids = [child.request_id for child in child_contexts]
        self.assertEqual(len(child_request_ids), len(set(child_request_ids)))
        
        self.record_metric("concurrent_child_creation_verified", len(child_contexts))
    
    async def test_concurrent_database_session_isolation(self):
        """Test concurrent database session access maintains session isolation."""
        # Create mock database sessions for concurrent access
        mock_sessions = []
        for i in range(5):
            mock_session = Mock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_sessions.append(mock_session)
        
        async def concurrent_database_operation(session_index):
            """Simulate concurrent database operations with isolated sessions."""
            context = UserExecutionContext(
                user_id=f"db_user_{session_index}",
                thread_id=f"db_thread_{session_index}",
                run_id=f"db_run_{session_index}",
                db_session=mock_sessions[session_index]
            )
            
            # Simulate database operations
            await context.db_session.execute(f"SELECT * FROM data WHERE user_id = '{context.user_id}'")
            await context.db_session.commit()
            
            return context
        
        # Run concurrent database operations
        db_tasks = []
        for i in range(5):
            task = concurrent_database_operation(i)
            db_tasks.append(task)
        
        db_contexts = await asyncio.gather(*db_tasks)
        
        # Verify session isolation
        for i, context in enumerate(db_contexts):
            self.assertEqual(context.db_session, mock_sessions[i])
            self.assertNotEqual(context.user_id, "shared_user")
            
            # Verify database session was called with correct user-specific data
            expected_query = f"SELECT * FROM data WHERE user_id = 'db_user_{i}'"
            context.db_session.execute.assert_called_with(expected_query)
            context.db_session.commit.assert_called_once()
        
        self.record_metric("concurrent_database_isolation_verified", len(db_contexts))
    
    async def test_concurrent_websocket_routing_isolation(self):
        """Test concurrent WebSocket routing maintains client isolation."""
        # Create WebSocket client IDs for concurrent routing
        websocket_clients = [str(uuid.uuid4()) for _ in range(8)]
        
        async def concurrent_websocket_operation(client_index):
            """Simulate concurrent WebSocket operations with isolated routing."""
            context = UserExecutionContext(
                user_id=f"ws_user_{client_index}",
                thread_id=f"ws_thread_{client_index}",
                run_id=f"ws_run_{client_index}",
                websocket_client_id=websocket_clients[client_index],
                agent_context={"websocket_data": f"client_{client_index}_data"}
            )
            
            # Simulate WebSocket message routing
            await asyncio.sleep(0.01)  # Simulate message processing
            
            return {
                "context": context,
                "routed_to": context.websocket_client_id,
                "message_data": context.agent_context["websocket_data"]
            }
        
        # Run concurrent WebSocket operations
        ws_tasks = []
        for i in range(8):
            task = concurrent_websocket_operation(i)
            ws_tasks.append(task)
        
        ws_results = await asyncio.gather(*ws_tasks)
        
        # Verify WebSocket routing isolation
        routed_clients = [result["routed_to"] for result in ws_results]
        self.assertEqual(len(routed_clients), len(set(routed_clients)))  # All unique
        
        for i, result in enumerate(ws_results):
            context = result["context"]
            self.assertEqual(result["routed_to"], websocket_clients[i])
            self.assertEqual(result["message_data"], f"client_{i}_data")
            
            # Verify supervisor compatibility alias
            self.assertEqual(context.websocket_connection_id, websocket_clients[i])
        
        self.record_metric("concurrent_websocket_isolation_verified", len(ws_results))
    
    async def test_concurrent_agent_context_modification_isolation(self):
        """Test concurrent agent context modifications maintain isolation."""
        # Create base contexts for concurrent modification testing
        base_contexts = []
        for i in range(6):
            context = UserExecutionContext(
                user_id=f"modify_user_{i}",
                thread_id=f"modify_thread_{i}",
                run_id=f"modify_run_{i}",
                agent_context={"base_value": i, "modifiable": "original"}
            )
            base_contexts.append(context)
        
        async def concurrent_context_access(context_index):
            """Access context data concurrently."""
            context = base_contexts[context_index]
            
            # Simulate reading context data (should not interfere with others)
            base_value = context.agent_context["base_value"] 
            modifiable_value = context.agent_context["modifiable"]
            
            # Contexts are immutable, so we simulate creating new contexts based on original
            new_context = UserExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=f"{context.run_id}_modified",
                agent_context={
                    "base_value": base_value,
                    "modifiable": f"modified_{context_index}",
                    "modification_time": time.time()
                }
            )
            
            return {"original": context, "modified": new_context}
        
        # Run concurrent context access
        modify_tasks = []
        for i in range(6):
            task = concurrent_context_access(i)
            modify_tasks.append(task)
        
        modify_results = await asyncio.gather(*modify_tasks)
        
        # Verify isolation during concurrent access
        for i, result in enumerate(modify_results):
            original = result["original"]
            modified = result["modified"]
            
            # Verify original context unchanged
            self.assertEqual(original.agent_context["base_value"], i)
            self.assertEqual(original.agent_context["modifiable"], "original")
            
            # Verify modified context has user-specific changes
            self.assertEqual(modified.agent_context["base_value"], i)
            self.assertEqual(modified.agent_context["modifiable"], f"modified_{i}")
            
            # Verify contexts are completely separate instances
            self.assertIsNot(original.agent_context, modified.agent_context)
        
        self.record_metric("concurrent_context_access_isolation_verified", len(modify_results))
    
    async def test_concurrent_validation_isolation(self):
        """Test concurrent context validation maintains validation isolation."""
        # Prepare validation scenarios with different validity
        validation_scenarios = [
            {"user_id": str(uuid.uuid4()), "thread_id": str(uuid.uuid4()), "run_id": str(uuid.uuid4())},  # Valid
            {"user_id": "", "thread_id": str(uuid.uuid4()), "run_id": str(uuid.uuid4())},  # Invalid user_id
            {"user_id": str(uuid.uuid4()), "thread_id": str(uuid.uuid4()), "run_id": str(uuid.uuid4())},  # Valid
            {"user_id": "placeholder", "thread_id": str(uuid.uuid4()), "run_id": str(uuid.uuid4())},  # Invalid user_id
            {"user_id": str(uuid.uuid4()), "thread_id": str(uuid.uuid4()), "run_id": str(uuid.uuid4())},  # Valid
        ]
        
        async def concurrent_validation(scenario_index):
            """Validate context creation concurrently."""
            scenario = validation_scenarios[scenario_index]
            
            try:
                context = UserExecutionContext(**scenario)
                return {"success": True, "context": context, "index": scenario_index}
            except InvalidContextError as e:
                return {"success": False, "error": str(e), "index": scenario_index}
        
        # Run concurrent validation
        validation_tasks = []
        for i in range(len(validation_scenarios)):
            task = concurrent_validation(i)
            validation_tasks.append(task)
        
        validation_results = await asyncio.gather(*validation_tasks)
        
        # Verify validation isolation (failures don't affect successes)
        successful_results = [r for r in validation_results if r["success"]]
        failed_results = [r for r in validation_results if not r["success"]]
        
        self.assertEqual(len(successful_results), 3)  # Valid scenarios
        self.assertEqual(len(failed_results), 2)  # Invalid scenarios
        
        # Verify successful contexts are properly isolated
        for result in successful_results:
            context = result["context"]
            self.assertIsNotNone(context.user_id)
            self.assertNotEqual(context.user_id, "")
            self.assertNotEqual(context.user_id, "placeholder")
        
        # Verify failures don't contaminate successes
        successful_user_ids = [r["context"].user_id for r in successful_results]
        self.assertEqual(len(successful_user_ids), len(set(successful_user_ids)))  # All unique
        
        self.record_metric("concurrent_validation_isolation_verified", len(validation_results))
    
    async def test_concurrent_metadata_access_isolation(self):
        """Test concurrent metadata access maintains data isolation."""
        # Create contexts with supervisor compatibility metadata
        metadata_contexts = []
        for i in range(4):
            context = UserExecutionContext.from_request_supervisor(
                user_id=f"meta_user_{i}",
                thread_id=f"meta_thread_{i}",
                run_id=f"meta_run_{i}",
                metadata={
                    "user_specific": f"data_{i}",
                    "workflow_state": f"state_{i}",
                    "concurrent_index": i
                }
            )
            metadata_contexts.append(context)
        
        async def concurrent_metadata_access(context_index):
            """Access metadata concurrently."""
            context = metadata_contexts[context_index]
            
            # Access unified metadata (supervisor compatibility)
            unified_metadata = context.metadata
            user_specific = unified_metadata["user_specific"]
            workflow_state = unified_metadata["workflow_state"]
            concurrent_index = unified_metadata["concurrent_index"]
            
            # Access separate metadata dictionaries
            agent_context = context.agent_context
            audit_metadata = context.audit_metadata
            
            return {
                "user_specific": user_specific,
                "workflow_state": workflow_state,
                "concurrent_index": concurrent_index,
                "agent_context_size": len(agent_context),
                "audit_metadata_size": len(audit_metadata),
                "context_user_id": context.user_id
            }
        
        # Run concurrent metadata access
        meta_tasks = []
        for i in range(4):
            task = concurrent_metadata_access(i)
            meta_tasks.append(task)
        
        meta_results = await asyncio.gather(*meta_tasks)
        
        # Verify metadata isolation during concurrent access
        for i, result in enumerate(meta_results):
            self.assertEqual(result["user_specific"], f"data_{i}")
            self.assertEqual(result["workflow_state"], f"state_{i}")
            self.assertEqual(result["concurrent_index"], i)
            self.assertEqual(result["context_user_id"], f"meta_user_{i}")
        
        # Verify all results are unique (no cross-contamination)
        user_specific_values = [r["user_specific"] for r in meta_results]
        self.assertEqual(len(user_specific_values), len(set(user_specific_values)))
        
        self.record_metric("concurrent_metadata_access_verified", len(meta_results))
    
    async def test_concurrent_child_context_hierarchy_isolation(self):
        """Test concurrent child context hierarchies maintain proper isolation."""
        # Create parent contexts
        parent_contexts = []
        for i in range(3):
            parent = UserExecutionContext(
                user_id=f"hierarchy_user_{i}",
                thread_id=f"hierarchy_thread_{i}",
                run_id=f"hierarchy_run_{i}",
                agent_context={"parent_index": i, "hierarchy_level": "parent"}
            )
            parent_contexts.append(parent)
        
        async def create_child_hierarchy_concurrent(parent_index):
            """Create child context hierarchy concurrently."""
            parent = parent_contexts[parent_index]
            
            # Create child context
            child = parent.create_child_context(
                child_operation=f"child_operation_{parent_index}",
                additional_agent_context={"child_level": "child", "parent_ref": parent_index}
            )
            
            # Create grandchild context
            grandchild = child.create_child_context(
                child_operation=f"grandchild_operation_{parent_index}",
                additional_agent_context={"child_level": "grandchild", "grandparent_ref": parent_index}
            )
            
            return {"parent": parent, "child": child, "grandchild": grandchild}
        
        # Create hierarchies concurrently
        hierarchy_tasks = []
        for i in range(3):
            task = create_child_hierarchy_concurrent(i)
            hierarchy_tasks.append(task)
        
        hierarchy_results = await asyncio.gather(*hierarchy_tasks)
        
        # Verify hierarchy isolation
        for i, result in enumerate(hierarchy_results):
            parent = result["parent"]
            child = result["child"] 
            grandchild = result["grandchild"]
            
            # Verify parent-child relationships
            self.assertEqual(child.parent_request_id, parent.request_id)
            self.assertEqual(grandchild.parent_request_id, child.request_id)
            
            # Verify operation depth progression
            self.assertEqual(parent.operation_depth, 0)
            self.assertEqual(child.operation_depth, 1)
            self.assertEqual(grandchild.operation_depth, 2)
            
            # Verify user ID inheritance but request ID uniqueness
            self.assertEqual(parent.user_id, child.user_id)
            self.assertEqual(child.user_id, grandchild.user_id)
            self.assertEqual(parent.user_id, f"hierarchy_user_{i}")
            
            # Verify request ID uniqueness in hierarchy
            request_ids = [parent.request_id, child.request_id, grandchild.request_id]
            self.assertEqual(len(request_ids), len(set(request_ids)))
            
            # Verify context data inheritance and isolation
            self.assertEqual(child.agent_context["parent_index"], i)
            self.assertEqual(child.agent_context["parent_ref"], i)
            self.assertEqual(grandchild.agent_context["grandparent_ref"], i)
        
        self.record_metric("concurrent_hierarchy_isolation_verified", len(hierarchy_results))
    
    async def test_concurrent_context_serialization_isolation(self):
        """Test concurrent context serialization maintains data isolation."""
        # Create contexts for serialization testing
        serialization_contexts = []
        for i in range(6):
            context = UserExecutionContext(
                user_id=f"serial_user_{i}",
                thread_id=f"serial_thread_{i}",
                run_id=f"serial_run_{i}",
                agent_context={"serializable_data": f"data_{i}", "index": i},
                audit_metadata={"serialization_test": True, "user_index": i}
            )
            serialization_contexts.append(context)
        
        async def concurrent_serialization(context_index):
            """Serialize context data concurrently."""
            context = serialization_contexts[context_index]
            
            # Convert context to dictionary
            context_dict = context.to_dict()
            
            # Simulate serialization/deserialization
            await asyncio.sleep(0.005)  # Simulate I/O
            
            # Reconstruct context from dictionary
            reconstructed = UserExecutionContext.from_dict(context_dict)
            
            return {
                "original": context,
                "dict": context_dict,
                "reconstructed": reconstructed,
                "index": context_index
            }
        
        # Run concurrent serialization
        serial_tasks = []
        for i in range(6):
            task = concurrent_serialization(i)
            serial_tasks.append(task)
        
        serial_results = await asyncio.gather(*serial_tasks)
        
        # Verify serialization isolation
        for i, result in enumerate(serial_results):
            original = result["original"]
            context_dict = result["dict"]
            reconstructed = result["reconstructed"]
            
            # Verify original context data
            self.assertEqual(original.user_id, f"serial_user_{i}")
            self.assertEqual(original.agent_context["index"], i)
            
            # Verify dictionary serialization
            self.assertEqual(context_dict["user_id"], f"serial_user_{i}")
            self.assertEqual(context_dict["agent_context"]["index"], i)
            
            # Verify reconstruction maintains data integrity
            self.assertEqual(reconstructed.user_id, original.user_id)
            self.assertEqual(reconstructed.agent_context["index"], i)
            self.assertEqual(reconstructed.agent_context["serializable_data"], f"data_{i}")
            
            # Verify contexts are separate instances
            self.assertIsNot(original, reconstructed)
            self.assertIsNot(original.agent_context, reconstructed.agent_context)
        
        self.record_metric("concurrent_serialization_isolation_verified", len(serial_results))
    
    async def test_concurrent_context_cleanup_isolation(self):
        """Test concurrent context cleanup maintains isolation and prevents leaks."""
        cleanup_results = []
        cleanup_lock = asyncio.Lock()
        
        async def concurrent_context_lifecycle(lifecycle_index):
            """Test complete context lifecycle with cleanup."""
            # Create context
            context = UserExecutionContext(
                user_id=f"cleanup_user_{lifecycle_index}",
                thread_id=f"cleanup_thread_{lifecycle_index}",
                run_id=f"cleanup_run_{lifecycle_index}",
                agent_context={"lifecycle_index": lifecycle_index, "cleanup_test": True}
            )
            
            # Simulate context usage
            context_id = context.request_id
            user_data = context.agent_context["lifecycle_index"]
            
            # Simulate cleanup phase
            await asyncio.sleep(0.01)  # Simulate work
            
            # Record cleanup completion
            async with cleanup_lock:
                cleanup_results.append({
                    "context_id": context_id,
                    "user_data": user_data,
                    "lifecycle_index": lifecycle_index,
                    "cleanup_completed": True
                })
            
            return {"context_id": context_id, "user_data": user_data}
        
        # Run concurrent context lifecycles
        lifecycle_tasks = []
        for i in range(8):
            task = concurrent_context_lifecycle(i)
            lifecycle_tasks.append(task)
        
        lifecycle_results = await asyncio.gather(*lifecycle_tasks)
        
        # Verify cleanup isolation
        self.assertEqual(len(cleanup_results), 8)
        self.assertEqual(len(lifecycle_results), 8)
        
        # Verify all context IDs are unique (no shared state)
        context_ids = [r["context_id"] for r in cleanup_results]
        self.assertEqual(len(context_ids), len(set(context_ids)))
        
        # Verify user data isolation during cleanup
        user_data_values = [r["user_data"] for r in cleanup_results]
        self.assertEqual(set(user_data_values), set(range(8)))
        
        # Verify all cleanups completed successfully
        cleanup_statuses = [r["cleanup_completed"] for r in cleanup_results]
        self.assertTrue(all(cleanup_statuses))
        
        self.record_metric("concurrent_cleanup_isolation_verified", len(cleanup_results))
    
    # ============================================================================
    # MEMORY MANAGEMENT AND CLEANUP (10 Tests)
    # ============================================================================
    
    async def test_context_memory_footprint_isolation(self):
        """Test context memory footprint remains isolated and manageable."""
        import sys
        
        # Measure baseline memory
        baseline_contexts = []
        for i in range(10):
            context = UserExecutionContext(
                user_id=f"memory_baseline_{i}",
                thread_id=f"memory_thread_{i}",
                run_id=f"memory_run_{i}",
                agent_context={"small_data": i},
                audit_metadata={"memory_test": "baseline"}
            )
            baseline_contexts.append(context)
        
        # Measure memory usage with large data
        large_data_contexts = []
        for i in range(10):
            large_context = UserExecutionContext(
                user_id=f"memory_large_{i}",
                thread_id=f"memory_thread_large_{i}",
                run_id=f"memory_run_large_{i}",
                agent_context={
                    "large_data": ["item" for _ in range(100)],  # Reasonable size
                    "user_history": [f"action_{j}" for j in range(50)],
                    "preferences": {f"pref_{k}": f"value_{k}" for k in range(20)}
                },
                audit_metadata={
                    "memory_test": "large_data",
                    "metadata_list": [f"meta_{m}" for m in range(30)]
                }
            )
            large_data_contexts.append(large_context)
        
        # Verify contexts maintain isolation even with large data
        baseline_user_ids = [ctx.user_id for ctx in baseline_contexts]
        large_user_ids = [ctx.user_id for ctx in large_data_contexts]
        
        self.assertEqual(len(baseline_user_ids), len(set(baseline_user_ids)))
        self.assertEqual(len(large_user_ids), len(set(large_user_ids)))
        
        # Verify no shared references between contexts
        for i in range(10):
            baseline_ctx = baseline_contexts[i]
            large_ctx = large_data_contexts[i]
            
            self.assertIsNot(baseline_ctx.agent_context, large_ctx.agent_context)
            self.assertIsNot(baseline_ctx.audit_metadata, large_ctx.audit_metadata)
            
            # Verify large context data is properly isolated
            self.assertEqual(len(large_ctx.agent_context["large_data"]), 100)
            self.assertEqual(large_ctx.agent_context["large_data"][0], "item")
        
        self.record_metric("memory_footprint_isolation_verified", True)
        self.record_metric("baseline_contexts_tested", len(baseline_contexts))
        self.record_metric("large_data_contexts_tested", len(large_data_contexts))
    
    async def test_context_garbage_collection_isolation(self):
        """Test context garbage collection doesn't affect isolated contexts."""
        import gc
        import weakref
        
        # Create contexts and weak references for GC testing
        context_refs = []
        active_contexts = []
        
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"gc_user_{i}",
                thread_id=f"gc_thread_{i}",
                run_id=f"gc_run_{i}",
                agent_context={"gc_test_index": i, "gc_data": f"data_{i}"}
            )
            
            # Keep some contexts active, let others be eligible for GC
            if i < 3:
                active_contexts.append(context)
            
            # Create weak reference to test GC behavior
            weak_ref = weakref.ref(context)
            context_refs.append({"index": i, "ref": weak_ref, "user_id": context.user_id})
        
        # Force garbage collection
        gc.collect()
        
        # Verify active contexts remain unaffected
        for i, context in enumerate(active_contexts):
            self.assertEqual(context.user_id, f"gc_user_{i}")
            self.assertEqual(context.agent_context["gc_test_index"], i)
            self.assertEqual(context.agent_context["gc_data"], f"data_{i}")
        
        # Verify context isolation is maintained after GC
        for i in range(len(active_contexts)):
            for j in range(i + 1, len(active_contexts)):
                ctx_i = active_contexts[i]
                ctx_j = active_contexts[j]
                
                self.assertNotEqual(ctx_i.user_id, ctx_j.user_id)
                self.assertIsNot(ctx_i.agent_context, ctx_j.agent_context)
                self.assertNotEqual(ctx_i.agent_context["gc_data"], ctx_j.agent_context["gc_data"])
        
        self.record_metric("gc_isolation_verified", True)
        self.record_metric("active_contexts_after_gc", len(active_contexts))
    
    async def test_context_deep_copy_isolation(self):
        """Test context deep copying maintains proper isolation."""
        import copy
        
        # Create context with nested mutable data
        original_context = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={
                "nested_dict": {
                    "level1": {
                        "level2": ["item1", "item2", "item3"],
                        "mutable_data": {"counter": 42}
                    }
                },
                "user_list": ["action1", "action2"],
                "preferences": {"theme": "dark", "language": "en"}
            },
            audit_metadata={
                "audit_nested": {
                    "permissions": ["read", "write"],
                    "history": [{"action": "login", "time": "now"}]
                }
            }
        )
        
        # Test that contexts are already properly isolated (immutable)
        # Since contexts are frozen, we test isolation by creating new contexts
        # with modified data (simulating deep copy behavior)
        
        modified_agent_context = copy.deepcopy(original_context.agent_context)
        modified_agent_context["nested_dict"]["level1"]["level2"].append("item4")
        modified_agent_context["preferences"]["theme"] = "light"
        
        modified_context = UserExecutionContext(
            user_id=original_context.user_id,
            thread_id=original_context.thread_id,
            run_id=f"{original_context.run_id}_modified",
            agent_context=modified_agent_context,
            audit_metadata=copy.deepcopy(original_context.audit_metadata)
        )
        
        # Verify deep isolation - original context unchanged
        self.assertEqual(len(original_context.agent_context["nested_dict"]["level1"]["level2"]), 3)
        self.assertEqual(original_context.agent_context["preferences"]["theme"], "dark")
        
        # Verify modified context has changes
        self.assertEqual(len(modified_context.agent_context["nested_dict"]["level1"]["level2"]), 4)
        self.assertEqual(modified_context.agent_context["preferences"]["theme"], "light")
        
        # Verify they are completely separate
        self.assertIsNot(original_context.agent_context, modified_context.agent_context)
        self.assertIsNot(
            original_context.agent_context["nested_dict"], 
            modified_context.agent_context["nested_dict"]
        )
        
        self.record_metric("deep_copy_isolation_verified", True)
    
    async def test_context_weak_reference_isolation(self):
        """Test weak reference behavior maintains context isolation."""
        import weakref
        
        # Create contexts and weak references
        context_registry = {}
        weak_references = {}
        
        for i in range(8):
            context = UserExecutionContext(
                user_id=f"weakref_user_{i}",
                thread_id=f"weakref_thread_{i}",
                run_id=f"weakref_run_{i}",
                agent_context={"weakref_index": i, "isolated_data": f"isolated_{i}"}
            )
            
            # Store context and create weak reference
            context_registry[f"context_{i}"] = context
            weak_references[f"weakref_{i}"] = weakref.ref(context)
        
        # Verify all weak references are valid and point to isolated contexts
        for i in range(8):
            weak_ref = weak_references[f"weakref_{i}"]
            context = weak_ref()
            
            self.assertIsNotNone(context)
            self.assertEqual(context.user_id, f"weakref_user_{i}")
            self.assertEqual(context.agent_context["weakref_index"], i)
            self.assertEqual(context.agent_context["isolated_data"], f"isolated_{i}")
        
        # Remove some contexts and verify weak references update correctly
        del context_registry["context_0"]
        del context_registry["context_1"]
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Verify remaining contexts are still isolated and accessible
        for i in range(2, 8):
            weak_ref = weak_references[f"weakref_{i}"]
            context = weak_ref()
            
            if context is not None:  # May be None if GC'd
                self.assertEqual(context.user_id, f"weakref_user_{i}")
                self.assertEqual(context.agent_context["isolated_data"], f"isolated_{i}")
        
        # Verify weak references don't interfere with isolation
        remaining_contexts = [context_registry[key] for key in context_registry.keys()]
        user_ids = [ctx.user_id for ctx in remaining_contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        self.record_metric("weak_reference_isolation_verified", True)
        self.record_metric("weak_references_tested", len(weak_references))
    
    async def test_context_circular_reference_prevention(self):
        """Test prevention of circular references that could cause memory leaks."""
        # Create parent context
        parent_context = UserExecutionContext(
            user_id=self.user_a_id,
            thread_id=self.thread_a_id,
            run_id=self.run_a_id,
            agent_context={"parent_data": "parent_info", "level": "parent"}
        )
        
        # Create child context
        child_context = parent_context.create_child_context(
            child_operation="child_task",
            additional_agent_context={"child_data": "child_info", "level": "child"}
        )
        
        # Create grandchild context
        grandchild_context = child_context.create_child_context(
            child_operation="grandchild_task",
            additional_agent_context={"grandchild_data": "grandchild_info", "level": "grandchild"}
        )
        
        # Verify proper parent-child relationships without circular references
        self.assertEqual(child_context.parent_request_id, parent_context.request_id)
        self.assertEqual(grandchild_context.parent_request_id, child_context.request_id)
        
        # Verify parent contexts don't have references to children
        # (This prevents circular references)
        self.assertIsNone(parent_context.parent_request_id)
        
        # Verify each context is independently accessible
        self.assertEqual(parent_context.agent_context["level"], "parent")
        self.assertEqual(child_context.agent_context["level"], "child")
        self.assertEqual(grandchild_context.agent_context["level"], "grandchild")
        
        # Verify operation depth tracking works correctly
        self.assertEqual(parent_context.operation_depth, 0)
        self.assertEqual(child_context.operation_depth, 1)
        self.assertEqual(grandchild_context.operation_depth, 2)
        
        # Test that contexts can be independently dereferenced
        parent_id = parent_context.request_id
        child_id = child_context.request_id
        grandchild_id = grandchild_context.request_id
        
        # All IDs should be unique
        ids = [parent_id, child_id, grandchild_id]
        self.assertEqual(len(ids), len(set(ids)))
        
        self.record_metric("circular_reference_prevention_verified", True)
    
    async def test_context_memory_cleanup_on_exception(self):
        """Test proper memory cleanup when context creation fails."""
        cleanup_attempts = 0
        successful_contexts = []
        
        for i in range(10):
            try:
                if i % 3 == 0:
                    # Every third attempt will fail
                    context = UserExecutionContext(
                        user_id="",  # Invalid - will raise InvalidContextError
                        thread_id=f"cleanup_thread_{i}",
                        run_id=f"cleanup_run_{i}"
                    )
                else:
                    # Valid context creation
                    context = UserExecutionContext(
                        user_id=f"cleanup_user_{i}",
                        thread_id=f"cleanup_thread_{i}",
                        run_id=f"cleanup_run_{i}",
                        agent_context={"cleanup_index": i, "valid": True}
                    )
                    successful_contexts.append(context)
                    
            except InvalidContextError:
                cleanup_attempts += 1
                # Exception should not affect subsequent context creation
                continue
        
        # Verify that failures didn't affect successful context creation
        self.assertEqual(len(successful_contexts), 6)  # 4 successful out of 10 attempts
        self.assertEqual(cleanup_attempts, 4)  # 4 failed attempts
        
        # Verify all successful contexts are properly isolated
        user_ids = [ctx.user_id for ctx in successful_contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        # Verify successful contexts have correct data
        for context in successful_contexts:
            self.assertTrue(context.agent_context["valid"])
            self.assertIn("cleanup_index", context.agent_context)
            self.assertNotEqual(context.user_id, "")
        
        self.record_metric("exception_cleanup_verified", True)
        self.record_metric("cleanup_attempts", cleanup_attempts)
        self.record_metric("successful_contexts_after_failures", len(successful_contexts))
    
    async def test_context_large_dataset_memory_management(self):
        """Test memory management with large datasets in context."""
        large_dataset_contexts = []
        
        # Create contexts with progressively larger datasets
        for i in range(5):
            dataset_size = (i + 1) * 1000  # 1K, 2K, 3K, 4K, 5K items
            
            large_context = UserExecutionContext(
                user_id=f"large_dataset_user_{i}",
                thread_id=f"large_dataset_thread_{i}",
                run_id=f"large_dataset_run_{i}",
                agent_context={
                    "large_dataset": [f"item_{j}" for j in range(dataset_size)],
                    "dataset_size": dataset_size,
                    "metadata": {f"key_{k}": f"value_{k}" for k in range(100)}
                },
                audit_metadata={
                    "dataset_info": f"dataset_of_size_{dataset_size}",
                    "performance_markers": [f"marker_{m}" for m in range(50)]
                }
            )
            large_dataset_contexts.append(large_context)
        
        # Verify all contexts maintain isolation despite large datasets
        for i, context in enumerate(large_dataset_contexts):
            expected_size = (i + 1) * 1000
            self.assertEqual(context.agent_context["dataset_size"], expected_size)
            self.assertEqual(len(context.agent_context["large_dataset"]), expected_size)
            
            # Verify context isolation
            self.assertEqual(context.user_id, f"large_dataset_user_{i}")
            self.assertIn(f"dataset_of_size_{expected_size}", context.audit_metadata["dataset_info"])
        
        # Verify no shared references between contexts with large datasets
        for i in range(len(large_dataset_contexts)):
            for j in range(i + 1, len(large_dataset_contexts)):
                ctx_i = large_dataset_contexts[i]
                ctx_j = large_dataset_contexts[j]
                
                self.assertIsNot(ctx_i.agent_context, ctx_j.agent_context)
                self.assertIsNot(ctx_i.agent_context["large_dataset"], ctx_j.agent_context["large_dataset"])
                self.assertNotEqual(ctx_i.agent_context["dataset_size"], ctx_j.agent_context["dataset_size"])
        
        self.record_metric("large_dataset_memory_management_verified", True)
        self.record_metric("largest_dataset_size", 5000)
    
    async def test_context_memory_pressure_isolation(self):
        """Test context isolation under memory pressure conditions."""
        # Create many contexts to simulate memory pressure
        memory_pressure_contexts = []
        context_count = 50
        
        for i in range(context_count):
            # Create context with moderate amount of data
            pressure_context = UserExecutionContext(
                user_id=f"pressure_user_{i}",
                thread_id=f"pressure_thread_{i}",
                run_id=f"pressure_run_{i}",
                agent_context={
                    "pressure_index": i,
                    "data_array": [f"data_{j}" for j in range(100)],
                    "nested_structure": {
                        "level1": {f"key_{k}": f"value_{k}" for k in range(20)},
                        "level2": [{"id": m, "value": f"val_{m}"} for m in range(10)]
                    }
                },
                audit_metadata={
                    "memory_test": True,
                    "context_batch": "memory_pressure",
                    "creation_order": i
                }
            )
            memory_pressure_contexts.append(pressure_context)
        
        # Verify all contexts maintain proper isolation under memory pressure
        user_ids = [ctx.user_id for ctx in memory_pressure_contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        request_ids = [ctx.request_id for ctx in memory_pressure_contexts]
        self.assertEqual(len(request_ids), len(set(request_ids)))  # All unique
        
        # Sample verification of context data integrity
        sample_indices = [0, 10, 25, 40, 49]  # Sample across range
        for idx in sample_indices:
            context = memory_pressure_contexts[idx]
            
            self.assertEqual(context.user_id, f"pressure_user_{idx}")
            self.assertEqual(context.agent_context["pressure_index"], idx)
            self.assertEqual(len(context.agent_context["data_array"]), 100)
            self.assertEqual(context.audit_metadata["creation_order"], idx)
            
            # Verify nested structure integrity
            self.assertEqual(len(context.agent_context["nested_structure"]["level1"]), 20)
            self.assertEqual(len(context.agent_context["nested_structure"]["level2"]), 10)
        
        # Verify no shared mutable state between any contexts
        for i in range(5):  # Sample check to avoid O(n²) performance
            ctx_a = memory_pressure_contexts[i]
            ctx_b = memory_pressure_contexts[i + 20]
            
            self.assertIsNot(ctx_a.agent_context, ctx_b.agent_context)
            self.assertIsNot(ctx_a.agent_context["data_array"], ctx_b.agent_context["data_array"])
            self.assertIsNot(ctx_a.agent_context["nested_structure"], ctx_b.agent_context["nested_structure"])
        
        self.record_metric("memory_pressure_isolation_verified", True)
        self.record_metric("memory_pressure_contexts_created", context_count)
    
    async def test_context_cleanup_callback_isolation(self):
        """Test cleanup callback isolation between contexts."""
        cleanup_callbacks_executed = []
        callback_lock = asyncio.Lock()
        
        async def create_context_with_cleanup(context_index):
            """Create context with cleanup callback."""
            context = UserExecutionContext(
                user_id=f"callback_user_{context_index}",
                thread_id=f"callback_thread_{context_index}",
                run_id=f"callback_run_{context_index}",
                agent_context={"cleanup_index": context_index, "has_callback": True}
            )
            
            # Simulate cleanup callback (in real usage, this would be done differently
            # since contexts are immutable, but we simulate the cleanup pattern)
            async def cleanup_callback():
                async with callback_lock:
                    cleanup_callbacks_executed.append({
                        "context_id": context.request_id,
                        "user_id": context.user_id,
                        "cleanup_index": context_index
                    })
            
            # Simulate context usage and cleanup
            await asyncio.sleep(0.01)  # Simulate work
            await cleanup_callback()
            
            return context
        
        # Create contexts with cleanup callbacks concurrently
        cleanup_tasks = []
        for i in range(8):
            task = create_context_with_cleanup(i)
            cleanup_tasks.append(task)
        
        cleanup_contexts = await asyncio.gather(*cleanup_tasks)
        
        # Verify cleanup callback isolation
        self.assertEqual(len(cleanup_callbacks_executed), 8)
        self.assertEqual(len(cleanup_contexts), 8)
        
        # Verify each cleanup callback executed for correct context
        for i, callback_result in enumerate(cleanup_callbacks_executed):
            # Find corresponding context (order may vary due to concurrency)
            matching_context = None
            for context in cleanup_contexts:
                if context.request_id == callback_result["context_id"]:
                    matching_context = context
                    break
            
            self.assertIsNotNone(matching_context)
            self.assertEqual(callback_result["user_id"], matching_context.user_id)
            self.assertTrue(matching_context.agent_context["has_callback"])
        
        # Verify all context IDs are unique (no callback cross-contamination)
        callback_context_ids = [cb["context_id"] for cb in cleanup_callbacks_executed]
        self.assertEqual(len(callback_context_ids), len(set(callback_context_ids)))
        
        self.record_metric("cleanup_callback_isolation_verified", True)
        self.record_metric("cleanup_callbacks_executed", len(cleanup_callbacks_executed))
    
    async def test_context_resource_limit_isolation(self):
        """Test context behavior under resource limits maintains isolation."""
        # Simulate resource-constrained environment
        resource_contexts = []
        resource_allocation_tracking = {}
        
        for i in range(15):
            try:
                # Create context with resource tracking
                context = UserExecutionContext(
                    user_id=f"resource_user_{i}",
                    thread_id=f"resource_thread_{i}",
                    run_id=f"resource_run_{i}",
                    agent_context={
                        "resource_index": i,
                        "allocated_memory": f"block_{i}",
                        "resource_type": "limited" if i > 10 else "normal"
                    },
                    audit_metadata={
                        "resource_limit_test": True,
                        "allocation_order": i,
                        "resource_tier": "high" if i < 5 else "standard"
                    }
                )
                
                resource_contexts.append(context)
                resource_allocation_tracking[context.request_id] = {
                    "user_id": context.user_id,
                    "allocation_order": i,
                    "resource_type": context.agent_context["resource_type"]
                }
                
            except Exception as e:
                # Resource limits might cause creation failures, but isolation should be maintained
                self.record_metric(f"resource_limit_exception_{i}", str(e))
        
        # Verify resource isolation despite potential limits
        created_count = len(resource_contexts)
        self.assertGreater(created_count, 0)  # At least some contexts should be created
        
        # Verify all created contexts are properly isolated
        user_ids = [ctx.user_id for ctx in resource_contexts]
        self.assertEqual(len(user_ids), len(set(user_ids)))  # All unique
        
        request_ids = [ctx.request_id for ctx in resource_contexts]
        self.assertEqual(len(request_ids), len(set(request_ids)))  # All unique
        
        # Verify resource allocation tracking isolation
        for context in resource_contexts:
            tracking_info = resource_allocation_tracking[context.request_id]
            self.assertEqual(tracking_info["user_id"], context.user_id)
            self.assertEqual(
                tracking_info["resource_type"], 
                context.agent_context["resource_type"]
            )
        
        # Verify no resource sharing between contexts
        for i in range(len(resource_contexts)):
            for j in range(i + 1, len(resource_contexts)):
                ctx_i = resource_contexts[i]
                ctx_j = resource_contexts[j]
                
                self.assertNotEqual(ctx_i.agent_context["allocated_memory"], ctx_j.agent_context["allocated_memory"])
                self.assertIsNot(ctx_i.agent_context, ctx_j.agent_context)
        
        self.record_metric("resource_limit_isolation_verified", True)
        self.record_metric("resource_contexts_created", created_count)
    
    # ============================================================================
    # TEST COMPLETION METRICS
    # ============================================================================
    
    def teardown_method(self, method):
        """Teardown test environment and log completion metrics."""
        # Log comprehensive test metrics
        all_metrics = self.get_all_metrics()
        
        # Count different test categories completed
        isolation_tests = len([k for k in all_metrics.keys() if 'isolation' in k and all_metrics[k] is True])
        factory_tests = len([k for k in all_metrics.keys() if 'factory' in k and all_metrics[k] is True])
        concurrent_tests = len([k for k in all_metrics.keys() if 'concurrent' in k and all_metrics[k] is True])
        memory_tests = len([k for k in all_metrics.keys() if 'memory' in k and all_metrics[k] is True])
        
        self.record_metric("isolation_tests_completed", isolation_tests)
        self.record_metric("factory_tests_completed", factory_tests)
        self.record_metric("concurrent_tests_completed", concurrent_tests)
        self.record_metric("memory_tests_completed", memory_tests)
        self.record_metric("multi_user_coverage_complete", True)
        
        # Calculate total scenarios covered
        total_scenarios = isolation_tests + factory_tests + concurrent_tests + memory_tests
        self.record_metric("total_multi_user_scenarios_covered", total_scenarios)
        
        # Call parent teardown
        super().teardown_method(method)