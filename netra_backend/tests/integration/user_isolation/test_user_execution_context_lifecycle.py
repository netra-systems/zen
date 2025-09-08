"""
Integration Tests for User Execution Context Lifecycle Management

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Critical foundation
- Business Goal: Ensure complete request isolation and prevent data leakage
- Value Impact: Guarantees user data security, request traceability, proper session management
- Revenue Impact: Prevents security breaches, enables audit trails for compliance

This test suite validates UserExecutionContext lifecycle management with
realistic scenarios including high concurrency, database session management,
WebSocket routing accuracy, and memory leak prevention. Tests ensure:
- Context creation/cleanup under high concurrency (10+ users)
- Database session management across request boundaries
- WebSocket routing accuracy with multiple active users
- Child context creation for sub-agent operations
- Context validation against malformed/malicious data
- Memory leak prevention during long-running sessions
"""

import asyncio
import gc
import pytest
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    managed_user_context,
    clear_shared_object_registry
)
from shared.isolated_environment import get_env


@pytest.mark.integration
@pytest.mark.real_services
class TestUserExecutionContextLifecycle(BaseIntegrationTest):
    """Test UserExecutionContext lifecycle management under realistic conditions."""
    
    async def setup_method(self, method):
        """Set up each test with clean state."""
        # Clear shared object registry to prevent cross-test contamination
        clear_shared_object_registry()
        
        # Force garbage collection to start with clean memory state
        gc.collect()
    
    async def teardown_method(self, method):
        """Clean up after each test."""
        clear_shared_object_registry()
        gc.collect()
    
    def create_realistic_context(self, user_id: Optional[str] = None, **kwargs) -> UserExecutionContext:
        """Create a realistic UserExecutionContext for testing."""
        user_id = user_id or f"user_{uuid4().hex[:8]}"
        thread_id = kwargs.get('thread_id', f"thread_{uuid4().hex[:8]}")
        run_id = kwargs.get('run_id', f"run_{uuid4().hex[:8]}")
        
        agent_context = {
            "agent_name": "test_agent",
            "operation": "data_analysis",
            "source": "integration_test",
            **kwargs.get('agent_context', {})
        }
        
        audit_metadata = {
            "client_ip": "192.168.1.100",
            "user_agent": "TestClient/1.0",
            "method": "POST",
            "url": "https://api.netra.com/v1/agents/execute",
            **kwargs.get('audit_metadata', {})
        }
        
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_context=agent_context,
            audit_metadata=audit_metadata,
            **{k: v for k, v in kwargs.items() if k not in ['agent_context', 'audit_metadata', 'thread_id', 'run_id']}
        )
    
    @pytest.mark.asyncio
    async def test_context_creation_under_high_concurrency(self):
        """Test context creation under high concurrency (20+ users simultaneously)."""
        # Track memory usage during test
        tracemalloc.start()
        
        async def create_context_for_user(user_index: int):
            """Create context for a single user with realistic data."""
            user_id = f"concurrent_user_{user_index}"
            context = self.create_realistic_context(
                user_id=user_id,
                agent_context={
                    "user_index": user_index,
                    "operation": f"concurrent_op_{user_index}",
                    "priority": "high" if user_index % 3 == 0 else "normal"
                },
                audit_metadata={
                    "session_id": f"session_{user_index}",
                    "request_sequence": user_index
                }
            )
            
            # Validate context is properly created
            assert context.user_id == user_id
            assert context.agent_context["user_index"] == user_index
            assert context.audit_metadata["session_id"] == f"session_{user_index}"
            
            # Test context isolation verification
            isolation_ok = context.verify_isolation()
            assert isolation_ok is True
            
            return context
        
        # Create contexts for 25 users concurrently
        start_time = time.time()
        contexts = await asyncio.gather(*[
            create_context_for_user(i) for i in range(25)
        ])
        creation_time = time.time() - start_time
        
        # Validate all contexts created successfully
        assert len(contexts) == 25
        
        # Validate contexts are unique and properly isolated
        user_ids = {ctx.user_id for ctx in contexts}
        request_ids = {ctx.request_id for ctx in contexts}
        correlation_ids = {ctx.get_correlation_id() for ctx in contexts}
        
        assert len(user_ids) == 25, "User IDs not unique"
        assert len(request_ids) == 25, "Request IDs not unique" 
        assert len(correlation_ids) == 25, "Correlation IDs not unique"
        
        # Performance validation
        assert creation_time < 3.0, f"Context creation too slow: {creation_time}s"
        
        # Memory usage validation
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should not consume excessive memory (< 50MB for 25 contexts)
        assert peak < 50 * 1024 * 1024, f"Excessive memory usage: {peak / 1024 / 1024:.2f}MB"
        
        print(f"✅ Created 25 contexts in {creation_time:.2f}s, peak memory: {peak / 1024 / 1024:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_database_session_management_across_requests(self):
        """Test database session attachment and management across request boundaries."""
        context = self.create_realistic_context()
        
        # Mock database session for testing
        mock_session = AsyncMock()
        mock_session.is_active = True
        mock_session.close = AsyncMock()
        
        # Test attaching database session
        context_with_db = context.with_db_session(mock_session)
        
        # Validate context immutability - original unchanged
        assert context.db_session is None
        assert context_with_db.db_session is mock_session
        
        # Validate other fields preserved
        assert context_with_db.user_id == context.user_id
        assert context_with_db.request_id == context.request_id
        assert context_with_db.agent_context == context.agent_context
        
        # Test managed context with database cleanup
        async with managed_user_context(context_with_db, cleanup_db_session=True) as managed_ctx:
            assert managed_ctx.db_session is mock_session
            
            # Simulate database operations
            assert managed_ctx.db_session.is_active
        
        # Verify session was closed after context exit
        mock_session.close.assert_called_once()
        
        # Test invalid session attachment
        with pytest.raises(InvalidContextError, match="db_session cannot be None"):
            context.with_db_session(None)
        
        print("✅ Database session management works correctly across request boundaries")
    
    @pytest.mark.asyncio
    async def test_websocket_routing_accuracy_multiple_users(self):
        """Test WebSocket routing accuracy with multiple active users."""
        # Create contexts for multiple users with different WebSocket connections
        contexts_with_ws = []
        
        for i in range(10):
            user_id = f"ws_user_{i}"
            connection_id = f"ws_conn_{i}_{uuid4().hex[:8]}"
            
            context = self.create_realistic_context(user_id=user_id)
            context_with_ws = context.with_websocket_connection(connection_id)
            
            contexts_with_ws.append((context_with_ws, connection_id))
        
        # Validate WebSocket connections are properly isolated
        for ctx, expected_conn_id in contexts_with_ws:
            assert ctx.websocket_client_id == expected_conn_id
            assert ctx.websocket_connection_id == expected_conn_id  # Backward compatibility
            
            # Validate context serialization includes WebSocket info
            ctx_dict = ctx.to_dict()
            assert ctx_dict["websocket_client_id"] == expected_conn_id
            assert ctx_dict["websocket_connection_id"] == expected_conn_id
            assert ctx_dict["has_db_session"] is False
        
        # Validate all connection IDs are unique
        connection_ids = {ctx.websocket_client_id for ctx, _ in contexts_with_ws}
        assert len(connection_ids) == 10, "WebSocket connection IDs not unique"
        
        # Test invalid connection ID
        context = self.create_realistic_context()
        with pytest.raises(InvalidContextError, match="connection_id must be a non-empty string"):
            context.with_websocket_connection("")
        
        with pytest.raises(InvalidContextError, match="connection_id must be a non-empty string"):
            context.with_websocket_connection(None)
        
        print("✅ WebSocket routing accuracy validated for 10 concurrent users")
    
    @pytest.mark.asyncio 
    async def test_child_context_creation_hierarchy_tracking(self):
        """Test child context creation with proper hierarchy tracking."""
        parent_context = self.create_realistic_context(
            user_id="parent_user",
            agent_context={"operation": "parent_operation", "data_source": "postgres"}
        )
        
        # Create child context with additional metadata
        child_context = parent_context.create_child_context(
            operation_name="data_analysis",
            additional_agent_context={"analysis_type": "cost_optimization", "model": "gpt-4"},
            additional_audit_metadata={"child_start_time": datetime.now(timezone.utc).isoformat()}
        )
        
        # Validate hierarchy tracking
        assert child_context.operation_depth == parent_context.operation_depth + 1
        assert child_context.parent_request_id == parent_context.request_id
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        
        # Validate child has unique request_id
        assert child_context.request_id != parent_context.request_id
        
        # Validate agent context inheritance and enhancement
        assert child_context.agent_context["operation_name"] == "data_analysis"
        assert child_context.agent_context["analysis_type"] == "cost_optimization"
        assert child_context.agent_context["data_source"] == "postgres"  # Inherited
        assert child_context.agent_context["parent_operation"] == "parent_operation"
        
        # Validate audit metadata inheritance and enhancement
        assert "child_start_time" in child_context.audit_metadata
        assert child_context.audit_metadata["parent_request_id"] == parent_context.request_id
        
        # Test deep nesting with limit enforcement
        contexts = [parent_context]
        for i in range(9):  # Create 9 levels (should succeed)
            child = contexts[-1].create_child_context(f"nested_op_{i}")
            contexts.append(child)
            assert child.operation_depth == i + 1
        
        # 10th level should fail (depth limit)
        with pytest.raises(InvalidContextError, match="Maximum operation depth"):
            contexts[-1].create_child_context("too_deep")
        
        # Test invalid operation names
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context("")
        
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context(None)
        
        print("✅ Child context creation with hierarchy tracking works correctly")
    
    @pytest.mark.asyncio
    async def test_context_validation_against_malformed_data(self):
        """Test context validation against malformed/malicious data."""
        # Test forbidden placeholder values
        forbidden_values = [
            "placeholder", "registry", "default", "temp", "none", "null",
            "undefined", "xxx", "test", "demo", "sample", "mock", "fake"
        ]
        
        for forbidden_value in forbidden_values:
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserExecutionContext.from_request(
                    user_id=forbidden_value,
                    thread_id="valid_thread_id", 
                    run_id="valid_run_id"
                )
        
        # Test forbidden patterns for short values
        forbidden_patterns = [
            "placeholder_short", "registry_abc", "default_123", "temp_xyz",
            "test_user", "demo_data", "mock_value"
        ]
        
        for pattern in forbidden_patterns:
            with pytest.raises(InvalidContextError, match="forbidden placeholder pattern"):
                UserExecutionContext.from_request(
                    user_id=pattern,
                    thread_id="valid_thread_id",
                    run_id="valid_run_id"
                )
        
        # Test reserved keys in metadata
        with pytest.raises(InvalidContextError, match="reserved keys"):
            UserExecutionContext.from_request(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id="valid_run",
                agent_context={"user_id": "malicious_override"}  # Reserved key
            )
        
        with pytest.raises(InvalidContextError, match="reserved keys"):
            UserExecutionContext.from_request(
                user_id="valid_user", 
                thread_id="valid_thread",
                run_id="valid_run",
                audit_metadata={"db_session": "fake_session"}  # Reserved key
            )
        
        # Test empty required fields
        required_field_tests = [
            (None, "valid_thread", "valid_run"),
            ("valid_user", None, "valid_run"),
            ("valid_user", "valid_thread", None),
            ("", "valid_thread", "valid_run"),
            ("valid_user", "", "valid_run"),
            ("valid_user", "valid_thread", ""),
        ]
        
        for user_id, thread_id, run_id in required_field_tests:
            with pytest.raises(InvalidContextError, match="must be a non-empty string"):
                UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
        
        print("✅ Context validation properly rejects malformed/malicious data")
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention_long_running_sessions(self):
        """Test memory leak prevention during long-running sessions."""
        tracemalloc.start()
        initial_current, initial_peak = tracemalloc.get_traced_memory()
        
        # Simulate long-running session with many context operations
        contexts_created = []
        child_contexts_created = []
        
        for session_round in range(5):  # 5 rounds of operations
            # Create contexts for multiple users
            for user_index in range(20):  # 20 users per round
                user_id = f"session_user_{session_round}_{user_index}"
                
                # Create parent context
                parent_ctx = self.create_realistic_context(
                    user_id=user_id,
                    agent_context={"session_round": session_round, "user_index": user_index}
                )
                contexts_created.append(parent_ctx)
                
                # Create child contexts (simulate sub-operations)
                for child_index in range(3):  # 3 child contexts per user
                    child_ctx = parent_ctx.create_child_context(
                        f"sub_operation_{child_index}",
                        additional_agent_context={"child_index": child_index}
                    )
                    child_contexts_created.append(child_ctx)
                
                # Test context serialization (common operation)
                ctx_dict = parent_ctx.to_dict()
                audit_trail = parent_ctx.get_audit_trail()
                
                # Test validation
                validate_user_context(parent_ctx)
            
            # Clear contexts periodically (simulate session cleanup)
            if session_round % 2 == 1:
                contexts_created = contexts_created[-20:]  # Keep only recent contexts
                child_contexts_created = child_contexts_created[-60:]
                gc.collect()  # Force garbage collection
        
        # Final memory check
        final_current, final_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        total_contexts = len(contexts_created) + len(child_contexts_created)
        memory_increase = (final_current - initial_current) / 1024 / 1024  # MB
        
        # Memory increase should be reasonable (< 2MB per 100 contexts)
        expected_max_memory = (total_contexts / 100) * 2  # 2MB per 100 contexts
        assert memory_increase < expected_max_memory, (
            f"Excessive memory increase: {memory_increase:.2f}MB for {total_contexts} contexts"
        )
        
        print(f"✅ Created {total_contexts} contexts with {memory_increase:.2f}MB memory increase")
    
    @pytest.mark.asyncio
    async def test_context_audit_trail_completeness(self):
        """Test that audit trails are complete and accurate."""
        context = self.create_realistic_context(
            user_id="audit_test_user",
            agent_context={"sensitive_operation": True, "data_classification": "confidential"},
            audit_metadata={"compliance_required": True, "retention_days": 2555}
        )
        
        # Test audit trail generation
        audit_trail = context.get_audit_trail()
        
        # Validate required audit fields
        required_fields = [
            "correlation_id", "user_id", "thread_id", "run_id", "request_id",
            "created_at", "operation_depth", "has_db_session", "has_websocket",
            "audit_metadata", "context_age_seconds"
        ]
        
        for field in required_fields:
            assert field in audit_trail, f"Missing required audit field: {field}"
        
        # Validate audit data accuracy
        assert audit_trail["user_id"] == "audit_test_user"
        assert audit_trail["correlation_id"] == context.get_correlation_id()
        assert audit_trail["operation_depth"] == 0
        assert audit_trail["parent_request_id"] is None
        assert audit_trail["has_db_session"] is False
        assert audit_trail["has_websocket"] is False
        
        # Validate audit metadata preservation
        assert audit_trail["audit_metadata"]["compliance_required"] is True
        assert audit_trail["audit_metadata"]["retention_days"] == 2555
        
        # Test context age calculation
        assert isinstance(audit_trail["context_age_seconds"], float)
        assert audit_trail["context_age_seconds"] >= 0
        
        # Test child context audit trail
        child_context = context.create_child_context("audit_child")
        child_audit = child_context.get_audit_trail()
        
        assert child_audit["operation_depth"] == 1
        assert child_audit["parent_request_id"] == context.request_id
        assert child_audit["user_id"] == "audit_test_user"  # Inherited
        
        print("✅ Audit trails are complete and accurate")
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_supervisor_patterns(self):
        """Test backward compatibility with supervisor implementation patterns."""
        # Test supervisor-style factory method
        supervisor_context = UserExecutionContext.from_request_supervisor(
            user_id="supervisor_user",
            thread_id="supervisor_thread", 
            run_id="supervisor_run",
            websocket_connection_id="supervisor_ws_conn",
            metadata={
                "agent_name": "supervisor_agent",
                "operation_name": "supervisor_operation",
                "audit_level": "high",
                "compliance_mode": True,
                "operation_depth": 2,
                "parent_request_id": "supervisor_parent_req"
            }
        )
        
        # Validate supervisor compatibility
        assert supervisor_context.websocket_connection_id == "supervisor_ws_conn"
        assert supervisor_context.websocket_client_id == "supervisor_ws_conn"  # Same value
        
        # Test unified metadata property
        unified_metadata = supervisor_context.metadata
        assert unified_metadata["agent_name"] == "supervisor_agent"
        assert unified_metadata["compliance_mode"] is True
        assert unified_metadata["audit_level"] == "high"
        
        # Test supervisor child context creation
        supervisor_child = supervisor_context.create_child_context_supervisor(
            operation_name="supervisor_child_op",
            additional_metadata={"child_priority": "high", "child_timeout": 30}
        )
        
        assert supervisor_child.operation_depth == 3  # Parent was 2
        assert supervisor_child.parent_request_id == supervisor_context.request_id
        
        # Validate metadata inheritance in child
        child_metadata = supervisor_child.metadata
        assert child_metadata["operation_name"] == "supervisor_child_op"
        assert child_metadata["child_priority"] == "high"
        assert child_metadata["compliance_mode"] is True  # Inherited
        
        # Test to_dict compatibility
        ctx_dict = supervisor_context.to_dict()
        assert ctx_dict["websocket_connection_id"] == "supervisor_ws_conn"
        assert ctx_dict["websocket_client_id"] == "supervisor_ws_conn"
        assert ctx_dict["implementation"] == "services_with_supervisor_compatibility"
        assert ctx_dict["compatibility_layer_active"] is True
        
        print("✅ Backward compatibility with supervisor patterns verified")
    
    @pytest.mark.asyncio
    async def test_context_isolation_verification_under_concurrency(self):
        """Test context isolation verification under concurrent operations."""
        isolation_test_contexts = []
        
        # Create contexts with potential shared references (to test isolation detection)
        shared_dict = {"shared": "data"}  # This would be a violation
        
        async def create_and_verify_context(user_index: int):
            """Create context and verify isolation."""
            context = self.create_realistic_context(f"isolation_user_{user_index}")
            
            # Verify isolation (should pass for properly isolated contexts)
            isolation_ok = context.verify_isolation()
            assert isolation_ok is True
            
            # Test context validation
            validated_context = validate_user_context(context)
            assert validated_context is context
            
            return context
        
        # Create and verify contexts concurrently
        contexts = await asyncio.gather(*[
            create_and_verify_context(i) for i in range(15)
        ])
        
        # All contexts should be properly isolated
        assert len(contexts) == 15
        
        # Test validation of wrong type
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context("not_a_context")
        
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context(None)
        
        print("✅ Context isolation verification works correctly under concurrency")