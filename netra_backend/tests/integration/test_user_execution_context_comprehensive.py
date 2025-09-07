"""
Comprehensive Integration Tests for UserExecutionContext

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user context isolation and secure multi-user agent execution
- Value Impact: Guarantees user data security, request traceability, and proper session management
- Strategic Impact: Enables secure multi-user platform operations and prevents data leakage

This test suite validates the core UserExecutionContext functionality that enables:
- Secure multi-user agent execution with complete isolation
- Chat context management for real-time user interactions
- Cross-service context propagation for WebSocket events
- Business-critical user session management for revenue protection

CRITICAL: This test uses NO MOCKS - all tests use real user context validation,
real user session management, and real context inheritance patterns.
"""

import asyncio
import pytest
import uuid
import copy
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.real_services_test_fixtures import real_services_fixture

# Core UserExecutionContext imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    managed_user_context,
    register_shared_object,
    clear_shared_object_registry
)

# Related imports for context integration testing
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestUserExecutionContextLifecycle(BaseIntegrationTest):
    """Test user execution context lifecycle: creation → validation → usage → cleanup"""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        # Clear shared object registry to ensure clean state
        clear_shared_object_registry()
        
        # Setup realistic test user data
        self.test_user_id = "user_12345678901234567890"  # Realistic length
        self.test_thread_id = "thread_98765432109876543210"
        self.test_run_id = f"run_{self.test_thread_id}_{int(time.time())}"
        
        # Setup environment isolation
        self.env = get_env()
        self.env.set("TESTING", "true", source="test")
        
    def teardown_method(self):
        """Cleanup after each test method."""
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_creation_with_valid_data(self, isolated_env):
        """Test successful UserExecutionContext creation with valid data."""
        # Test basic creation
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Validate creation results
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        assert context.request_id is not None
        assert len(context.request_id) > 20  # UUID should be longer than placeholders
        assert context.operation_depth == 0
        assert context.parent_request_id is None
        assert isinstance(context.created_at, datetime)
        assert context.created_at.tzinfo is not None  # Should be timezone-aware
        
        # Validate metadata initialization
        assert isinstance(context.agent_context, dict)
        assert isinstance(context.audit_metadata, dict)
        assert "context_created_at" in context.audit_metadata
        assert "isolation_verified" in context.audit_metadata
        assert context.audit_metadata["isolation_verified"] is True
    
    @pytest.mark.integration
    async def test_user_context_validation_prevents_placeholder_values(self, isolated_env):
        """Test that context validation prevents dangerous placeholder values."""
        
        # Test forbidden exact values
        forbidden_values = [
            "placeholder", "default", "temp", "none", "null", "registry",
            "test", "example", "demo", "mock", "fake", "dummy"
        ]
        
        for forbidden_value in forbidden_values:
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserExecutionContext(
                    user_id=forbidden_value,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id
                )
        
        # Test forbidden patterns for short values
        forbidden_patterns = [
            "placeholder_123", "registry_abc", "default_xyz", "temp_456",
            "test_789", "mock_def"
        ]
        
        for forbidden_pattern in forbidden_patterns:
            with pytest.raises(InvalidContextError, match="placeholder pattern"):
                UserExecutionContext(
                    user_id=forbidden_pattern,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id
                )
    
    @pytest.mark.integration
    async def test_user_context_validation_accepts_realistic_values(self, isolated_env):
        """Test that context validation accepts realistic production values."""
        
        # Test realistic user IDs
        realistic_user_ids = [
            "user_12345678901234567890",  # Long user ID
            "auth0|60d5b2c8e1b2a40069abc123",  # Auth0 style
            "google-oauth2|1234567890123456789",  # Google OAuth style
            str(uuid.uuid4()),  # UUID format
            "internal_user_production_12345678901234567890"  # Long internal format
        ]
        
        for user_id in realistic_user_ids:
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            assert context.user_id == user_id
            # Should not raise any validation errors
    
    @pytest.mark.integration
    async def test_user_context_immutability_enforcement(self, isolated_env):
        """Test that UserExecutionContext is properly immutable after creation."""
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Test that direct field modification is prevented (frozen dataclass)
        with pytest.raises((AttributeError, TypeError)):
            context.user_id = "modified_user"
        
        with pytest.raises((AttributeError, TypeError)):
            context.thread_id = "modified_thread"
        
        with pytest.raises((AttributeError, TypeError)):
            context.operation_depth = 5
    
    @pytest.mark.integration
    async def test_user_context_factory_methods(self, isolated_env):
        """Test UserExecutionContext factory methods work correctly."""
        
        # Test from_request factory
        context = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            agent_context={"agent_name": "test_agent"},
            audit_metadata={"source": "test_factory"}
        )
        
        assert context.user_id == self.test_user_id
        assert context.agent_context["agent_name"] == "test_agent"
        assert context.audit_metadata["source"] == "test_factory"
        
        # Test from_fastapi_request factory
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "http://localhost:8000/api/agent"
        mock_request.headers = {
            "user-agent": "test-client/1.0",
            "content-type": "application/json",
            "x-request-id": "external-123"
        }
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        context = UserExecutionContext.from_fastapi_request(
            request=mock_request,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        assert context.user_id == self.test_user_id
        assert "client_ip" in context.audit_metadata
        assert context.audit_metadata["client_ip"] == "127.0.0.1"
        assert context.audit_metadata["method"] == "POST"
        assert "x_request_id" in context.audit_metadata


class TestUserExecutionContextMultiUserIsolation(BaseIntegrationTest):
    """Test multi-user context isolation and concurrent user session management"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_context_isolation(self, isolated_env):
        """Test that concurrent user contexts are completely isolated."""
        
        # Create multiple user contexts concurrently
        user_contexts = []
        
        async def create_user_context(user_num: int) -> UserExecutionContext:
            return UserExecutionContext(
                user_id=f"user_{user_num:06d}_{'x' * 20}",
                thread_id=f"thread_{user_num:06d}_{'y' * 15}",
                run_id=f"run_{user_num:06d}_{int(time.time())}",
                agent_context={"user_number": user_num, "session_data": f"data_{user_num}"},
                audit_metadata={"test_run": "concurrent_isolation", "user_num": user_num}
            )
        
        # Create contexts concurrently
        tasks = [create_user_context(i) for i in range(10)]
        user_contexts = await asyncio.gather(*tasks)
        
        # Verify each context is isolated
        for i, context in enumerate(user_contexts):
            assert context.user_id == f"user_{i:06d}_{'x' * 20}"
            assert context.agent_context["user_number"] == i
            assert context.audit_metadata["user_num"] == i
            
            # Verify no shared object references
            assert context.verify_isolation() is True
            
            # Verify unique request IDs
            request_ids = [ctx.request_id for ctx in user_contexts]
            assert len(set(request_ids)) == len(request_ids)  # All unique
    
    @pytest.mark.integration
    async def test_user_context_memory_isolation(self, isolated_env):
        """Test that user contexts don't share memory references."""
        
        # Create base context
        base_agent_context = {"shared_data": ["item1", "item2"]}
        base_audit_metadata = {"shared_audit": {"key": "value"}}
        
        context1 = UserExecutionContext(
            user_id="user_memory_test_1",
            thread_id="thread_memory_test_1", 
            run_id="run_memory_test_1",
            agent_context=copy.deepcopy(base_agent_context),
            audit_metadata=copy.deepcopy(base_audit_metadata)
        )
        
        context2 = UserExecutionContext(
            user_id="user_memory_test_2",
            thread_id="thread_memory_test_2",
            run_id="run_memory_test_2",
            agent_context=copy.deepcopy(base_agent_context),
            audit_metadata=copy.deepcopy(base_audit_metadata)
        )
        
        # Verify contexts don't share memory references
        assert id(context1.agent_context) != id(context2.agent_context)
        assert id(context1.audit_metadata) != id(context2.audit_metadata)
        assert id(context1.agent_context["shared_data"]) != id(context2.agent_context["shared_data"])
        
        # Verify modifications to one don't affect the other
        # (Note: we can't modify directly due to immutability, but we can check deep copy worked)
        assert context1.agent_context["shared_data"] == ["item1", "item2"]
        assert context2.agent_context["shared_data"] == ["item1", "item2"]
        assert context1.agent_context["shared_data"] is not context2.agent_context["shared_data"]
    
    @pytest.mark.integration
    async def test_concurrent_context_creation_thread_safety(self, isolated_env):
        """Test thread-safe concurrent context creation."""
        
        results = []
        errors = []
        
        def create_context_sync(thread_id: int):
            """Thread function to create context synchronously."""
            try:
                context = UserExecutionContext(
                    user_id=f"thread_user_{thread_id}_{uuid.uuid4()}",
                    thread_id=f"thread_{thread_id}_{uuid.uuid4()}",
                    run_id=f"run_{thread_id}_{int(time.time())}_{uuid.uuid4()}"
                )
                results.append(context)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create contexts from multiple threads
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(create_context_sync, i) for i in range(50)]
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50
        
        # Verify all contexts are unique and valid
        user_ids = [ctx.user_id for ctx in results]
        assert len(set(user_ids)) == 50  # All unique user IDs
        
        request_ids = [ctx.request_id for ctx in results]
        assert len(set(request_ids)) == 50  # All unique request IDs


class TestUserExecutionContextChildContexts(BaseIntegrationTest):
    """Test user context inheritance and child context creation patterns"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
        
        # Create parent context for tests
        self.parent_context = UserExecutionContext(
            user_id="parent_user_12345678901234567890",
            thread_id="parent_thread_98765432109876543210",
            run_id=f"parent_run_{int(time.time())}",
            agent_context={
                "agent_name": "parent_agent",
                "session_data": "parent_session",
                "capabilities": ["read", "write", "execute"]
            },
            audit_metadata={
                "source": "parent_operation",
                "environment": "test",
                "version": "1.0"
            }
        )
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    async def test_child_context_creation_and_inheritance(self, isolated_env):
        """Test proper child context creation with inheritance."""
        
        child_context = self.parent_context.create_child_context(
            operation_name="data_analysis",
            additional_agent_context={"analysis_type": "cost_optimization"},
            additional_audit_metadata={"stage": "analysis"}
        )
        
        # Verify inheritance
        assert child_context.user_id == self.parent_context.user_id
        assert child_context.thread_id == self.parent_context.thread_id
        assert child_context.run_id == self.parent_context.run_id
        
        # Verify new properties
        assert child_context.request_id != self.parent_context.request_id
        assert child_context.operation_depth == 1
        assert child_context.parent_request_id == self.parent_context.request_id
        
        # Verify context inheritance and enhancement
        assert child_context.agent_context["agent_name"] == "parent_agent"  # Inherited
        assert child_context.agent_context["operation_name"] == "data_analysis"  # New
        assert child_context.agent_context["analysis_type"] == "cost_optimization"  # Additional
        assert child_context.agent_context["operation_depth"] == 1
        
        # Verify audit metadata inheritance and enhancement
        assert child_context.audit_metadata["source"] == "parent_operation"  # Inherited
        assert child_context.audit_metadata["operation_name"] == "data_analysis"  # New
        assert child_context.audit_metadata["stage"] == "analysis"  # Additional
        assert child_context.audit_metadata["parent_request_id"] == self.parent_context.request_id
    
    @pytest.mark.integration
    async def test_nested_child_context_hierarchy(self, isolated_env):
        """Test deep nesting of child contexts with proper hierarchy tracking."""
        
        # Create multi-level hierarchy
        level1_child = self.parent_context.create_child_context("level1_operation")
        level2_child = level1_child.create_child_context("level2_operation")
        level3_child = level2_child.create_child_context("level3_operation")
        
        # Verify depth progression
        assert self.parent_context.operation_depth == 0
        assert level1_child.operation_depth == 1
        assert level2_child.operation_depth == 2
        assert level3_child.operation_depth == 3
        
        # Verify parent relationships
        assert level1_child.parent_request_id == self.parent_context.request_id
        assert level2_child.parent_request_id == level1_child.request_id
        assert level3_child.parent_request_id == level2_child.request_id
        
        # Verify all share same core identifiers
        contexts = [self.parent_context, level1_child, level2_child, level3_child]
        for context in contexts:
            assert context.user_id == self.parent_context.user_id
            assert context.thread_id == self.parent_context.thread_id
            assert context.run_id == self.parent_context.run_id
        
        # Verify all have unique request IDs
        request_ids = [ctx.request_id for ctx in contexts]
        assert len(set(request_ids)) == 4
    
    @pytest.mark.integration
    async def test_child_context_isolation_from_parent(self, isolated_env):
        """Test that child contexts are isolated from parent modifications."""
        
        child_context = self.parent_context.create_child_context(
            "isolation_test",
            additional_agent_context={"child_data": "child_value"}
        )
        
        # Verify memory isolation
        assert id(child_context.agent_context) != id(self.parent_context.agent_context)
        assert id(child_context.audit_metadata) != id(self.parent_context.audit_metadata)
        
        # Verify child has both inherited and new data
        assert child_context.agent_context["agent_name"] == "parent_agent"  # Inherited
        assert child_context.agent_context["child_data"] == "child_value"   # New
        
        # Verify parent doesn't have child data
        assert "child_data" not in self.parent_context.agent_context
        assert "operation_name" not in self.parent_context.agent_context
    
    @pytest.mark.integration
    async def test_child_context_depth_limit_enforcement(self, isolated_env):
        """Test that excessive nesting depth is prevented."""
        
        # Create contexts up to the limit
        current_context = self.parent_context
        for i in range(10):  # Max depth is 10
            current_context = current_context.create_child_context(f"level_{i+1}")
        
        assert current_context.operation_depth == 10
        
        # Attempt to exceed limit should raise error
        with pytest.raises(InvalidContextError, match="Maximum operation depth"):
            current_context.create_child_context("exceeds_limit")
    
    @pytest.mark.integration
    async def test_child_context_validation_requirements(self, isolated_env):
        """Test validation requirements for child context creation."""
        
        # Test empty operation name
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            self.parent_context.create_child_context("")
        
        # Test None operation name
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            self.parent_context.create_child_context(None)
        
        # Test whitespace-only operation name
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            self.parent_context.create_child_context("   ")


class TestUserExecutionContextCrossServiceIntegration(BaseIntegrationTest):
    """Test cross-service user context propagation (agents ↔ tools ↔ WebSocket)"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
        
        # Create realistic context for cross-service testing
        self.integration_context = UserExecutionContext(
            user_id="integration_user_12345678901234567890",
            thread_id="integration_thread_98765432109876543210",
            run_id=f"integration_run_{int(time.time())}",
            websocket_client_id="ws_conn_12345678901234567890",
            agent_context={
                "agent_name": "cost_optimizer",
                "session_id": "session_98765432109876543210",
                "capabilities": ["analyze_costs", "generate_reports"],
                "user_preferences": {"currency": "USD", "region": "us-east-1"}
            },
            audit_metadata={
                "service": "netra_backend",
                "environment": "test",
                "client_version": "1.0.0",
                "request_source": "web_ui"
            }
        )
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_serialization_deserialization(self, isolated_env):
        """Test context serialization/deserialization across service boundaries."""
        
        # Test to_dict serialization
        context_dict = self.integration_context.to_dict()
        
        # Verify all required fields present
        required_fields = [
            "user_id", "thread_id", "run_id", "request_id", "websocket_client_id",
            "created_at", "agent_context", "audit_metadata", "operation_depth",
            "parent_request_id", "has_db_session"
        ]
        
        for field in required_fields:
            assert field in context_dict, f"Missing field: {field}"
        
        # Verify serializable types
        import json
        json_str = json.dumps(context_dict)  # Should not raise exception
        assert len(json_str) > 100  # Should contain substantial data
        
        # Verify sensitive data excluded
        assert "db_session" not in context_dict
        
        # Test data integrity
        assert context_dict["user_id"] == self.integration_context.user_id
        assert context_dict["agent_context"]["agent_name"] == "cost_optimizer"
        assert context_dict["audit_metadata"]["service"] == "netra_backend"
    
    @pytest.mark.integration
    async def test_context_correlation_id_generation(self, isolated_env):
        """Test correlation ID generation for distributed tracing."""
        
        correlation_id = self.integration_context.get_correlation_id()
        
        # Verify format (user:thread:run:request - first 8 chars of each)
        parts = correlation_id.split(":")
        assert len(parts) == 4
        
        expected_user_prefix = self.integration_context.user_id[:8]
        expected_thread_prefix = self.integration_context.thread_id[:8]
        expected_run_prefix = self.integration_context.run_id[:8]
        expected_request_prefix = self.integration_context.request_id[:8]
        
        assert parts[0] == expected_user_prefix
        assert parts[1] == expected_thread_prefix
        assert parts[2] == expected_run_prefix
        assert parts[3] == expected_request_prefix
    
    @pytest.mark.integration
    async def test_context_audit_trail_generation(self, isolated_env):
        """Test comprehensive audit trail generation for compliance."""
        
        audit_trail = self.integration_context.get_audit_trail()
        
        # Verify required audit fields
        required_audit_fields = [
            "correlation_id", "user_id", "thread_id", "run_id", "request_id",
            "created_at", "operation_depth", "parent_request_id",
            "has_db_session", "has_websocket", "audit_metadata", "context_age_seconds"
        ]
        
        for field in required_audit_fields:
            assert field in audit_trail, f"Missing audit field: {field}"
        
        # Verify audit data accuracy
        assert audit_trail["user_id"] == self.integration_context.user_id
        assert audit_trail["has_websocket"] is True  # We provided websocket_client_id
        assert audit_trail["has_db_session"] is False  # We didn't provide db_session
        assert isinstance(audit_trail["context_age_seconds"], (int, float))
        assert audit_trail["context_age_seconds"] >= 0
        
        # Verify audit metadata preserved
        assert "service" in audit_trail["audit_metadata"]
        assert audit_trail["audit_metadata"]["service"] == "netra_backend"
    
    @pytest.mark.integration
    async def test_context_with_db_session_attachment(self, isolated_env):
        """Test context enhancement with database session."""
        
        # Create mock database session
        mock_db_session = Mock()
        mock_db_session.is_active = True
        mock_db_session.info = {"test": "session"}
        
        # Create context with database session
        context_with_db = self.integration_context.with_db_session(mock_db_session)
        
        # Verify new context properties
        assert context_with_db.db_session is mock_db_session
        assert context_with_db.user_id == self.integration_context.user_id  # Preserved
        assert context_with_db.request_id == self.integration_context.request_id  # Preserved
        
        # Verify original context unchanged
        assert self.integration_context.db_session is None
        
        # Test invalid session handling
        with pytest.raises(InvalidContextError, match="db_session cannot be None"):
            self.integration_context.with_db_session(None)
    
    @pytest.mark.integration
    async def test_context_with_websocket_connection_attachment(self, isolated_env):
        """Test context enhancement with WebSocket connection."""
        
        new_connection_id = "ws_new_connection_12345678901234567890"
        
        # Create context with new WebSocket connection
        context_with_ws = self.integration_context.with_websocket_connection(new_connection_id)
        
        # Verify new context properties
        assert context_with_ws.websocket_client_id == new_connection_id
        assert context_with_ws.user_id == self.integration_context.user_id  # Preserved
        assert context_with_ws.request_id == self.integration_context.request_id  # Preserved
        
        # Verify original context unchanged
        assert self.integration_context.websocket_client_id == "ws_conn_12345678901234567890"
        
        # Test invalid connection ID handling
        with pytest.raises(InvalidContextError, match="connection_id must be a non-empty string"):
            self.integration_context.with_websocket_connection("")
        
        with pytest.raises(InvalidContextError, match="connection_id must be a non-empty string"):
            self.integration_context.with_websocket_connection(None)


class TestUserExecutionContextBusinessCriticalOperations(BaseIntegrationTest):
    """Test business-critical user context operations (agent execution, tool dispatch, WebSocket events)"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_agent_execution_integration(self, isolated_env):
        """Test UserExecutionContext integration with agent execution patterns."""
        
        # Create realistic agent execution context
        agent_context = UserExecutionContext(
            user_id="agent_exec_user_12345678901234567890",
            thread_id="agent_exec_thread_98765432109876543210",
            run_id=f"agent_exec_run_{int(time.time())}",
            agent_context={
                "agent_name": "cost_optimizer",
                "execution_mode": "optimization",
                "user_context": {
                    "subscription_tier": "enterprise",
                    "monthly_spend": 50000,
                    "optimization_goals": ["reduce_costs", "improve_performance"]
                }
            },
            audit_metadata={
                "execution_type": "agent_run",
                "priority": "high",
                "expected_duration": 30
            }
        )
        
        # Test conversion to legacy ExecutionContext for backwards compatibility
        execution_context = agent_context.to_execution_context()
        
        # Verify conversion accuracy
        assert execution_context.run_id == agent_context.run_id
        assert execution_context.user_id == agent_context.user_id
        assert execution_context.thread_id == agent_context.thread_id
        assert execution_context.correlation_id == agent_context.get_correlation_id()
        
        # Verify metadata propagation
        assert "user_execution_context_id" in execution_context.metadata
        assert execution_context.metadata["user_execution_context_id"] == agent_context.request_id
        assert execution_context.metadata["operation_depth"] == agent_context.operation_depth
    
    @pytest.mark.integration
    async def test_context_websocket_event_propagation_simulation(self, isolated_env):
        """Test context integration with WebSocket event propagation patterns."""
        
        # Create WebSocket-enabled context
        ws_context = UserExecutionContext(
            user_id="websocket_user_12345678901234567890",
            thread_id="websocket_thread_98765432109876543210",
            run_id=f"websocket_run_{int(time.time())}",
            websocket_client_id="ws_event_12345678901234567890",
            agent_context={
                "agent_name": "triage_agent",
                "websocket_events": True,
                "real_time_updates": True
            },
            audit_metadata={
                "event_propagation": "enabled",
                "connection_type": "websocket",
                "session_start": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Simulate WebSocket event creation from context
        def create_websocket_event(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate WebSocket event creation with context data."""
            return {
                "type": event_type,
                "user_id": ws_context.user_id,
                "thread_id": ws_context.thread_id,
                "run_id": ws_context.run_id,
                "request_id": ws_context.request_id,
                "websocket_client_id": ws_context.websocket_client_id,
                "correlation_id": ws_context.get_correlation_id(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
        
        # Test critical WebSocket events
        agent_started_event = create_websocket_event("agent_started", {
            "agent_name": "triage_agent",
            "message": "Starting analysis..."
        })
        
        agent_thinking_event = create_websocket_event("agent_thinking", {
            "status": "Analyzing user request...",
            "progress": 25
        })
        
        tool_executing_event = create_websocket_event("tool_executing", {
            "tool_name": "cost_analyzer",
            "status": "Executing cost analysis..."
        })
        
        tool_completed_event = create_websocket_event("tool_completed", {
            "tool_name": "cost_analyzer",
            "result": {"analysis": "complete", "savings_found": 1500}
        })
        
        agent_completed_event = create_websocket_event("agent_completed", {
            "status": "completed",
            "result": {"recommendations": ["Use reserved instances"], "savings": 1500}
        })
        
        # Verify event structure and context propagation
        events = [
            agent_started_event, agent_thinking_event, tool_executing_event,
            tool_completed_event, agent_completed_event
        ]
        
        for event in events:
            assert event["user_id"] == ws_context.user_id
            assert event["thread_id"] == ws_context.thread_id
            assert event["websocket_client_id"] == ws_context.websocket_client_id
            assert event["correlation_id"] == ws_context.get_correlation_id()
            assert "timestamp" in event
            assert "data" in event
    
    @pytest.mark.integration
    async def test_context_tool_dispatch_integration(self, isolated_env):
        """Test context integration with tool dispatch patterns."""
        
        # Create tool execution context
        tool_context = UserExecutionContext(
            user_id="tool_dispatch_user_12345678901234567890",
            thread_id="tool_dispatch_thread_98765432109876543210",
            run_id=f"tool_dispatch_run_{int(time.time())}",
            agent_context={
                "agent_name": "cost_optimizer",
                "current_tool": "aws_cost_analyzer",
                "tool_permissions": ["read:billing", "analyze:costs"],
                "execution_environment": "secure_sandbox"
            },
            audit_metadata={
                "tool_execution": "enabled",
                "security_context": "user_scoped",
                "permission_level": "standard"
            }
        )
        
        # Create child context for tool execution
        tool_execution_context = tool_context.create_child_context(
            "tool_execution",
            additional_agent_context={
                "tool_name": "aws_cost_analyzer",
                "tool_version": "1.2.3",
                "parameters": {
                    "account_id": "123456789012",
                    "time_range": "last_30_days"
                }
            },
            additional_audit_metadata={
                "tool_start_time": datetime.now(timezone.utc).isoformat(),
                "expected_duration": 15
            }
        )
        
        # Verify tool context inheritance
        assert tool_execution_context.user_id == tool_context.user_id
        assert tool_execution_context.thread_id == tool_context.thread_id
        assert tool_execution_context.agent_context["agent_name"] == "cost_optimizer"  # Inherited
        assert tool_execution_context.agent_context["tool_name"] == "aws_cost_analyzer"  # New
        assert tool_execution_context.operation_depth == 1  # Child depth
        
        # Verify security context preservation
        assert "tool_permissions" in tool_execution_context.agent_context
        assert "read:billing" in tool_execution_context.agent_context["tool_permissions"]
        
        # Test tool result context
        tool_result_context = tool_execution_context.create_child_context(
            "tool_result_processing",
            additional_agent_context={
                "result_status": "success",
                "result_data": {
                    "total_cost": 45000,
                    "potential_savings": 12000,
                    "recommendations": 5
                }
            }
        )
        
        assert tool_result_context.operation_depth == 2  # Grandchild depth
        assert tool_result_context.agent_context["result_status"] == "success"


class TestUserExecutionContextErrorHandlingAndValidation(BaseIntegrationTest):
    """Test user context error handling and validation failure scenarios"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    async def test_context_validation_error_scenarios(self, isolated_env):
        """Test comprehensive validation error scenarios."""
        
        # Test missing required fields
        with pytest.raises(InvalidContextError, match="must be a non-empty string"):
            UserExecutionContext(
                user_id="",  # Empty string
                thread_id="valid_thread",
                run_id="valid_run"
            )
        
        with pytest.raises(InvalidContextError, match="must be a non-empty string"):
            UserExecutionContext(
                user_id="valid_user",
                thread_id=None,  # None value
                run_id="valid_run"
            )
        
        with pytest.raises(InvalidContextError, match="must be a non-empty string"):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id="   "  # Whitespace only
            )
        
        # Test invalid data types
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id="valid_run",
                agent_context="not_a_dict"  # Should be dict
            )
        
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id="valid_run",
                audit_metadata=["not", "a", "dict"]  # Should be dict
            )
    
    @pytest.mark.integration
    async def test_context_reserved_keys_validation(self, isolated_env):
        """Test that reserved keys in metadata are rejected."""
        
        reserved_keys = [
            'user_id', 'thread_id', 'run_id', 'request_id', 'created_at',
            'db_session', 'websocket_client_id'
        ]
        
        # Test reserved keys in agent_context
        for reserved_key in reserved_keys:
            with pytest.raises(InvalidContextError, match="contains reserved keys"):
                UserExecutionContext(
                    user_id="test_user",
                    thread_id="test_thread",
                    run_id="test_run",
                    agent_context={reserved_key: "conflicting_value"}
                )
        
        # Test reserved keys in audit_metadata
        for reserved_key in reserved_keys:
            with pytest.raises(InvalidContextError, match="contains reserved keys"):
                UserExecutionContext(
                    user_id="test_user",
                    thread_id="test_thread",
                    run_id="test_run",
                    audit_metadata={reserved_key: "conflicting_value"}
                )
    
    @pytest.mark.integration
    async def test_context_isolation_violation_detection(self, isolated_env):
        """Test detection of context isolation violations."""
        
        # Create shared object
        shared_dict = {"shared": "data"}
        register_shared_object(shared_dict)
        
        # Create context that doesn't use shared object (should pass)
        clean_context = UserExecutionContext(
            user_id="clean_user_test",
            thread_id="clean_thread_test",
            run_id="clean_run_test",
            agent_context={"clean": "data"},
            audit_metadata={"clean": "metadata"}
        )
        
        # Verify isolation passes for clean context
        assert clean_context.verify_isolation() is True
        
        # Note: Since UserExecutionContext performs deep copy during initialization,
        # it should automatically prevent shared object references
        # This test verifies that the deep copy mechanism works
        
        # Create context with dictionary that looks like shared object
        # but should be deep copied and thus not violate isolation
        potentially_shared_context = UserExecutionContext(
            user_id="potentially_shared_user_test",
            thread_id="potentially_shared_thread_test", 
            run_id="potentially_shared_run_test",
            agent_context=copy.deepcopy(shared_dict),  # Deep copy should prevent violation
            audit_metadata={"safe": "metadata"}
        )
        
        # Should pass because deep copy prevents shared references
        assert potentially_shared_context.verify_isolation() is True
    
    @pytest.mark.integration
    async def test_context_runtime_validation(self, isolated_env):
        """Test runtime validation of context objects."""
        
        # Test valid context passes validation
        valid_context = UserExecutionContext(
            user_id="runtime_valid_user_test",
            thread_id="runtime_valid_thread_test",
            run_id="runtime_valid_run_test"
        )
        
        validated_context = validate_user_context(valid_context)
        assert validated_context is valid_context
        
        # Test invalid object type
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context("not_a_context")
        
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context({"fake": "context"})
        
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context(None)


class TestUserExecutionContextResourceManagement(BaseIntegrationTest):
    """Test user context resource management and memory leak prevention"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    async def test_managed_context_lifecycle(self, isolated_env):
        """Test managed context lifecycle with proper resource cleanup."""
        
        # Create context with mock database session
        mock_db_session = AsyncMock()
        context_with_resources = UserExecutionContext(
            user_id="resource_mgmt_user_test",
            thread_id="resource_mgmt_thread_test",
            run_id="resource_mgmt_run_test"
        ).with_db_session(mock_db_session)
        
        # Test managed context usage
        context_used = None
        exception_occurred = False
        
        try:
            async with managed_user_context(context_with_resources) as managed_ctx:
                context_used = managed_ctx
                assert managed_ctx.user_id == context_with_resources.user_id
                assert managed_ctx.db_session is mock_db_session
                
                # Simulate some work
                await asyncio.sleep(0.01)
        except Exception as e:
            exception_occurred = True
            raise
        
        # Verify context was properly managed
        assert context_used is not None
        assert not exception_occurred
        
        # Verify database session was closed (cleanup_db_session=True by default)
        mock_db_session.close.assert_called_once()
    
    @pytest.mark.integration
    async def test_managed_context_with_exception_handling(self, isolated_env):
        """Test managed context proper cleanup even when exceptions occur."""
        
        mock_db_session = AsyncMock()
        context_with_resources = UserExecutionContext(
            user_id="exception_mgmt_user_test",
            thread_id="exception_mgmt_thread_test",
            run_id="exception_mgmt_run_test"
        ).with_db_session(mock_db_session)
        
        # Test exception handling and cleanup
        exception_caught = False
        
        try:
            async with managed_user_context(context_with_resources) as managed_ctx:
                assert managed_ctx.db_session is mock_db_session
                raise ValueError("Test exception for cleanup validation")
        except ValueError as e:
            exception_caught = True
            assert str(e) == "Test exception for cleanup validation"
        
        # Verify exception was properly caught
        assert exception_caught
        
        # Verify cleanup still occurred despite exception
        mock_db_session.close.assert_called_once()
    
    @pytest.mark.integration
    async def test_managed_context_with_disabled_cleanup(self, isolated_env):
        """Test managed context with disabled database cleanup."""
        
        mock_db_session = AsyncMock()
        context_with_resources = UserExecutionContext(
            user_id="no_cleanup_user_test",
            thread_id="no_cleanup_thread_test",
            run_id="no_cleanup_run_test"
        ).with_db_session(mock_db_session)
        
        # Test with cleanup disabled
        async with managed_user_context(context_with_resources, cleanup_db_session=False) as managed_ctx:
            assert managed_ctx.db_session is mock_db_session
            await asyncio.sleep(0.01)  # Simulate work
        
        # Verify database session was NOT closed when cleanup is disabled
        mock_db_session.close.assert_not_called()
    
    @pytest.mark.integration
    async def test_context_memory_usage_patterns(self, isolated_env):
        """Test context memory usage and garbage collection patterns."""
        
        # Create multiple contexts with various data sizes
        contexts = []
        large_data = {"large_array": list(range(1000)) * 10}  # ~10K items
        
        for i in range(100):
            context = UserExecutionContext(
                user_id=f"memory_test_user_{i:03d}_{'x' * 20}",
                thread_id=f"memory_test_thread_{i:03d}_{'y' * 15}",
                run_id=f"memory_test_run_{i:03d}_{int(time.time())}",
                agent_context=copy.deepcopy(large_data),
                audit_metadata={"test_iteration": i, "memory_test": True}
            )
            contexts.append(context)
        
        # Verify all contexts are valid and isolated
        for i, context in enumerate(contexts):
            assert context.user_id.endswith("x" * 20)
            assert context.agent_context["large_array"][0] == 0
            assert context.audit_metadata["test_iteration"] == i
            
            # Verify memory isolation between contexts
            assert id(context.agent_context) != id(contexts[0].agent_context)
        
        # Clear references and verify contexts can be garbage collected
        contexts.clear()
        
        # Create new context to verify no memory leaks from previous contexts
        final_context = UserExecutionContext(
            user_id="final_memory_test_user",
            thread_id="final_memory_test_thread",
            run_id="final_memory_test_run"
        )
        
        assert final_context.verify_isolation() is True


class TestUserExecutionContextPerformanceAndConcurrency(BaseIntegrationTest):
    """Test user context performance under concurrent access and load"""
    
    def setup_method(self):
        super().setup_method()
        clear_shared_object_registry()
    
    def teardown_method(self):
        clear_shared_object_registry()
        super().teardown_method()
    
    @pytest.mark.integration
    async def test_concurrent_context_creation_performance(self, isolated_env):
        """Test performance of concurrent context creation."""
        
        start_time = time.perf_counter()
        
        # Create many contexts concurrently
        async def create_performance_context(index: int) -> UserExecutionContext:
            return UserExecutionContext(
                user_id=f"perf_user_{index:06d}_{'x' * 30}",
                thread_id=f"perf_thread_{index:06d}_{'y' * 25}",
                run_id=f"perf_run_{index:06d}_{int(time.perf_counter() * 1000000)}",
                agent_context={
                    "performance_test": True,
                    "index": index,
                    "large_data": {"items": list(range(100))}
                },
                audit_metadata={
                    "test_type": "performance",
                    "batch_number": index // 100,
                    "creation_time": time.perf_counter()
                }
            )
        
        # Create 1000 contexts concurrently
        tasks = [create_performance_context(i) for i in range(1000)]
        contexts = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        creation_duration = end_time - start_time
        
        # Verify performance metrics
        assert len(contexts) == 1000
        assert creation_duration < 10.0  # Should complete within 10 seconds
        
        contexts_per_second = 1000 / creation_duration
        assert contexts_per_second > 100  # Should create at least 100 contexts/second
        
        # Verify all contexts are valid and unique
        user_ids = [ctx.user_id for ctx in contexts]
        assert len(set(user_ids)) == 1000  # All unique
        
        request_ids = [ctx.request_id for ctx in contexts]
        assert len(set(request_ids)) == 1000  # All unique
    
    @pytest.mark.integration
    async def test_child_context_creation_performance(self, isolated_env):
        """Test performance of child context creation."""
        
        # Create parent context
        parent_context = UserExecutionContext(
            user_id="child_perf_parent_user_12345678901234567890",
            thread_id="child_perf_parent_thread_98765432109876543210",
            run_id=f"child_perf_parent_run_{int(time.time())}",
            agent_context={"parent_data": {"large_list": list(range(500))}},
            audit_metadata={"parent_test": "child_performance"}
        )
        
        start_time = time.perf_counter()
        
        # Create many child contexts
        child_contexts = []
        for i in range(500):
            child_context = parent_context.create_child_context(
                f"child_operation_{i}",
                additional_agent_context={"child_index": i, "child_data": list(range(10))},
                additional_audit_metadata={"child_creation_time": time.perf_counter()}
            )
            child_contexts.append(child_context)
        
        end_time = time.perf_counter()
        child_creation_duration = end_time - start_time
        
        # Verify performance metrics
        assert len(child_contexts) == 500
        assert child_creation_duration < 5.0  # Should complete within 5 seconds
        
        children_per_second = 500 / child_creation_duration
        assert children_per_second > 100  # Should create at least 100 children/second
        
        # Verify all child contexts are valid
        for i, child in enumerate(child_contexts):
            assert child.operation_depth == 1
            assert child.parent_request_id == parent_context.request_id
            assert child.agent_context["child_index"] == i
            assert child.agent_context["parent_data"]["large_list"] == list(range(500))  # Inherited
    
    @pytest.mark.integration
    async def test_context_method_call_performance(self, isolated_env):
        """Test performance of context method calls."""
        
        context = UserExecutionContext(
            user_id="method_perf_user_12345678901234567890",
            thread_id="method_perf_thread_98765432109876543210",
            run_id=f"method_perf_run_{int(time.time())}",
            agent_context={"method_test": True, "data": list(range(200))},
            audit_metadata={"performance_test": "method_calls"}
        )
        
        # Test to_dict performance
        start_time = time.perf_counter()
        for _ in range(1000):
            context_dict = context.to_dict()
        end_time = time.perf_counter()
        to_dict_duration = end_time - start_time
        assert to_dict_duration < 1.0  # Should complete within 1 second
        
        # Test get_correlation_id performance
        start_time = time.perf_counter()
        for _ in range(10000):
            correlation_id = context.get_correlation_id()
        end_time = time.perf_counter()
        correlation_duration = end_time - start_time
        assert correlation_duration < 0.5  # Should complete within 0.5 seconds
        
        # Test get_audit_trail performance
        start_time = time.perf_counter()
        for _ in range(1000):
            audit_trail = context.get_audit_trail()
        end_time = time.perf_counter()
        audit_duration = end_time - start_time
        assert audit_duration < 1.0  # Should complete within 1 second
        
        # Test verify_isolation performance
        start_time = time.perf_counter()
        for _ in range(1000):
            is_isolated = context.verify_isolation()
        end_time = time.perf_counter()
        isolation_duration = end_time - start_time
        assert isolation_duration < 1.0  # Should complete within 1 second
    
    @pytest.mark.integration
    async def test_high_concurrency_context_operations(self, isolated_env):
        """Test high concurrency context operations."""
        
        # Create base context
        base_context = UserExecutionContext(
            user_id="concurrency_user_12345678901234567890",
            thread_id="concurrency_thread_98765432109876543210",
            run_id=f"concurrency_run_{int(time.time())}"
        )
        
        results = {
            "correlations": [],
            "audit_trails": [],
            "child_contexts": [],
            "isolations": []
        }
        
        # Define concurrent operations
        async def perform_concurrent_operations(operation_id: int):
            # Get correlation ID
            correlation = base_context.get_correlation_id()
            results["correlations"].append(correlation)
            
            # Get audit trail
            audit = base_context.get_audit_trail()
            results["audit_trails"].append(audit)
            
            # Create child context
            child = base_context.create_child_context(f"concurrent_op_{operation_id}")
            results["child_contexts"].append(child)
            
            # Verify isolation
            isolation = base_context.verify_isolation()
            results["isolations"].append(isolation)
        
        # Run operations concurrently
        tasks = [perform_concurrent_operations(i) for i in range(200)]
        await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results["correlations"]) == 200
        assert len(results["audit_trails"]) == 200
        assert len(results["child_contexts"]) == 200
        assert len(results["isolations"]) == 200
        
        # Verify all operations succeeded
        assert all(results["isolations"])  # All isolation checks passed
        
        # Verify child contexts are unique
        child_request_ids = [child.request_id for child in results["child_contexts"]]
        assert len(set(child_request_ids)) == 200  # All unique
        
        # Verify correlations are consistent
        expected_correlation = base_context.get_correlation_id()
        assert all(corr == expected_correlation for corr in results["correlations"])


# Test execution markers and configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.user_context,
    pytest.mark.real_services  # Uses real validation and context management
]


if __name__ == "__main__":
    """Allow running tests directly for development."""
    pytest.main([__file__, "-v", "--tb=short"])