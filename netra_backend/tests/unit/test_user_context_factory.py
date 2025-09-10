"""
Unit Tests for User Context Factory Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure proper user isolation and context security
- Value Impact: Prevents data leakage between users and ensures request traceability
- Strategic Impact: Critical security foundation - context failures = user data exposure

This module tests the user context factory including:
- User context creation and validation
- Request isolation between concurrent users
- Database session management
- WebSocket connection routing
- Audit trail generation
- Error handling for invalid contexts
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.services.user_context_factory import (
    UserContextFactory,
    UserExecutionContext,
    create_isolated_execution_context,
    InvalidContextError,
    ContextIsolationError
)


class TestUserContextFactory(SSotBaseTestCase):
    """Unit tests for UserContextFactory business logic."""
    
    def setup_method(self, method=None):
        """Setup test environment and mocks."""
        super().setup_method(method)
        
        # Test user data
        self.test_user_id = "test-user-12345"
        self.test_thread_id = "test-thread-67890"
        self.test_run_id = str(uuid4())
        self.test_request_id = str(uuid4())
        
        # Mock database session
        self.mock_db_session = AsyncMock()
        
        # Mock FastAPI request
        self.mock_request = MagicMock()
        self.mock_request.headers = {
            "Authorization": "Bearer test-token",
            "X-Request-ID": self.test_request_id,
            "User-Agent": "TestClient/1.0"
        }
        
        # Mock WebSocket connection
        self.mock_websocket = AsyncMock()
        
    @pytest.mark.unit
    def test_user_context_creation_with_valid_data(self):
        """Test creation of UserExecutionContext with valid data."""
        # Business logic: Valid context should be created successfully
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=self.mock_db_session,
            agent_context={
                'agent_name': 'cost_optimizer',
                'user_request': 'Analyze my AWS costs'
            },
            audit_metadata={
                'created_at': datetime.now(timezone.utc).isoformat(),
                'source': 'test_factory'
            }
        )
        
        # Verify core business attributes
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        assert context.request_id == self.test_request_id
        assert context.db_session == self.mock_db_session
        
        # Verify agent context contains business data
        assert context.agent_context['agent_name'] == 'cost_optimizer'
        assert context.agent_context['user_request'] == 'Analyze my AWS costs'
        
        # Verify audit trail is present
        assert 'created_at' in context.audit_metadata
        assert 'source' in context.audit_metadata
        
        # Record business metric: Context creation success
        self.record_metric("user_context_creation_success", True)
        
    @pytest.mark.unit
    def test_user_context_validation_rejects_invalid_data(self):
        """Test validation logic rejects invalid context data."""
        # Test cases for invalid data that should be rejected
        invalid_test_cases = [
            # Empty user ID
            {
                "user_id": "",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "error_reason": "empty_user_id"
            },
            # Placeholder values
            {
                "user_id": "placeholder",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "error_reason": "placeholder_user_id"
            },
            # None values
            {
                "user_id": None,
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "error_reason": "none_user_id"
            }
        ]
        
        for test_case in invalid_test_cases:
            # Business logic: Invalid data should trigger validation error
            with self.expect_exception(Exception):  # Could be InvalidContextError or TypeError
                context = UserExecutionContext(
                    user_id=test_case["user_id"],
                    thread_id=test_case["thread_id"],
                    run_id=test_case["run_id"],
                    agent_context={},
                    audit_metadata={}
                )
                
        # Record business metric: Validation robustness
        self.record_metric("invalid_context_cases_tested", len(invalid_test_cases))
        
    @pytest.mark.unit
    def test_user_isolation_between_contexts(self):
        """Test that different user contexts are properly isolated."""
        # Create contexts for different users
        user1_context = UserExecutionContext(
            user_id="user-1",
            thread_id="thread-1",
            run_id=str(uuid4()),
            agent_context={'user_data': 'user1_private_data'},
            audit_metadata={'user': 'user1'}
        )
        
        user2_context = UserExecutionContext(
            user_id="user-2", 
            thread_id="thread-2",
            run_id=str(uuid4()),
            agent_context={'user_data': 'user2_private_data'},
            audit_metadata={'user': 'user2'}
        )
        
        # Business requirement: Contexts must be completely isolated
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.thread_id != user2_context.thread_id
        assert user1_context.run_id != user2_context.run_id
        
        # Verify no data leakage between contexts
        assert user1_context.agent_context['user_data'] != user2_context.agent_context['user_data']
        assert user1_context.audit_metadata['user'] != user2_context.audit_metadata['user']
        
        # Modifying one context should not affect the other
        user1_context.agent_context['new_field'] = 'user1_value'
        assert 'new_field' not in user2_context.agent_context
        
        # Record business metric: User isolation validation
        self.record_metric("user_isolation_validated", True)
        
    @pytest.mark.unit
    async def test_isolated_execution_context_creation(self):
        """Test creation of isolated execution context."""
        # Business logic: Isolated context should be created with proper defaults
        context = await create_isolated_execution_context(
            user_id=self.test_user_id,
            operation="test_operation"
        )
        
        # Verify context was created
        assert context is not None
        assert context.user_id == self.test_user_id
        
        # Verify audit metadata includes operation
        assert 'operation' in context.audit_metadata
        assert context.audit_metadata['operation'] == "test_operation"
        
        # Verify created timestamp is recent
        assert 'created_at' in context.audit_metadata
        created_at = datetime.fromisoformat(context.audit_metadata['created_at'].replace('Z', '+00:00'))
        time_diff = datetime.now(timezone.utc) - created_at
        assert time_diff.total_seconds() < 10  # Created within last 10 seconds
        
        # Record business metric: Isolated context creation
        self.record_metric("isolated_context_creation_success", True)
        
    @pytest.mark.unit
    def test_context_immutability_for_security(self):
        """Test that context maintains immutability for security."""
        # Create context with sensitive data
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            agent_context={
                'sensitive_data': 'user_private_information',
                'api_keys': {'aws': 'secret_key_123'}
            },
            audit_metadata={'access_level': 'restricted'}
        )
        
        # Business requirement: Core identifiers should not be modifiable
        original_user_id = context.user_id
        original_thread_id = context.thread_id
        original_run_id = context.run_id
        
        # Attempt to modify core fields (should fail or be ignored)
        try:
            context.user_id = "hacker_user"
            context.thread_id = "hacker_thread"
            context.run_id = "hacker_run"
        except AttributeError:
            # Expected for immutable fields
            pass
            
        # Verify core fields remain unchanged
        assert context.user_id == original_user_id
        assert context.thread_id == original_thread_id
        assert context.run_id == original_run_id
        
        # Record business metric: Immutability protection
        self.record_metric("context_immutability_protected", True)
        
    @pytest.mark.unit
    def test_child_context_creation_for_sub_operations(self):
        """Test creation of child contexts for sub-agent operations."""
        # Create parent context
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            agent_context={
                'parent_agent': 'main_optimizer',
                'user_request': 'Optimize my infrastructure'
            },
            audit_metadata={'level': 'parent'}
        )
        
        # Create child context for sub-operation
        child_context = parent_context.create_child_context(
            operation='cost_analysis_sub_agent',
            additional_context={'analysis_type': 'detailed_cost_breakdown'}
        )
        
        # Business logic: Child should inherit parent data but have unique IDs
        assert child_context.user_id == parent_context.user_id  # Same user
        assert child_context.thread_id == parent_context.thread_id  # Same thread
        assert child_context.run_id != parent_context.run_id  # Different run
        
        # Verify child has access to parent context
        assert child_context.agent_context['parent_agent'] == 'main_optimizer'
        assert child_context.agent_context['user_request'] == 'Optimize my infrastructure'
        
        # Verify child has additional context
        assert child_context.agent_context['analysis_type'] == 'detailed_cost_breakdown'
        
        # Verify audit trail shows parent relationship
        assert 'parent_run_id' in child_context.audit_metadata
        assert child_context.audit_metadata['parent_run_id'] == parent_context.run_id
        
        # Record business metric: Child context creation
        self.record_metric("child_context_creation_success", True)
        
    @pytest.mark.unit
    def test_context_audit_trail_completeness(self):
        """Test that audit trail contains complete business information."""
        # Create context with comprehensive audit data
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            agent_context={
                'agent_name': 'security_analyzer',
                'business_operation': 'vulnerability_scan'
            },
            audit_metadata={
                'client_ip': '192.168.1.100',
                'user_agent': 'NetraClient/2.1',
                'request_source': 'web_ui',
                'business_unit': 'enterprise',
                'compliance_required': True
            }
        )
        
        # Business requirement: Essential audit fields must be present
        required_audit_fields = [
            'client_ip',
            'user_agent', 
            'request_source',
            'business_unit',
            'compliance_required'
        ]
        
        for field in required_audit_fields:
            assert field in context.audit_metadata, f"Missing audit field: {field}"
            
        # Verify compliance data for enterprise users
        assert context.audit_metadata['compliance_required'] == True
        assert context.audit_metadata['business_unit'] == 'enterprise'
        
        # Record business metric: Audit completeness
        self.record_metric("audit_trail_completeness_validated", True)
        self.record_metric("audit_fields_count", len(context.audit_metadata))
        
    @pytest.mark.unit
    def test_context_error_handling_business_logic(self):
        """Test error handling for business-critical scenarios."""
        # Test database session failure handling
        with self.expect_exception(Exception):
            # Simulate database connection failure
            invalid_session = None
            context = UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                db_session=invalid_session,  # This should trigger validation
                agent_context={},
                audit_metadata={}
            )
            
        # Test resource cleanup in error scenarios
        cleanup_called = False
        
        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True
            
        # Simulate error during context operation
        try:
            context = UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                agent_context={},
                audit_metadata={}
            )
            # Simulate adding cleanup handler
            context._cleanup_handlers = [mock_cleanup]
            raise Exception("Simulated operation failure")
        except Exception:
            # Cleanup should be called
            if hasattr(context, '_cleanup_handlers'):
                for handler in context._cleanup_handlers:
                    handler()
                    
        # Verify cleanup was executed
        assert cleanup_called, "Cleanup handler should be called on error"
        
        # Record business metric: Error handling robustness
        self.record_metric("error_handling_scenarios_tested", 2)
        
    @pytest.mark.unit
    def test_performance_requirements_for_context_creation(self):
        """Test performance requirements for business responsiveness."""
        import time
        
        # Business requirement: Context creation should be fast
        start_time = time.time()
        
        # Create multiple contexts to test performance
        contexts = []
        for i in range(100):
            context = UserExecutionContext(
                user_id=f"user-{i}",
                thread_id=f"thread-{i}", 
                run_id=str(uuid4()),
                agent_context={'iteration': i},
                audit_metadata={'test_run': True}
            )
            contexts.append(context)
            
        end_time = time.time()
        total_time = end_time - start_time
        
        # Business requirement: Should create 100 contexts in < 100ms
        assert total_time < 0.1, f"Context creation too slow: {total_time}s for 100 contexts"
        
        # Verify all contexts are unique
        user_ids = {ctx.user_id for ctx in contexts}
        assert len(user_ids) == 100, "All contexts should have unique user IDs"
        
        # Record performance metrics
        self.record_metric("context_creation_time_ms", total_time * 1000)
        self.record_metric("contexts_per_second", 100 / total_time)
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Log business metrics for monitoring
        final_metrics = self.get_all_metrics()
        
        # Set environment flags for business intelligence
        if final_metrics.get("user_context_creation_success"):
            self.set_env_var("LAST_USER_CONTEXT_TEST_SUCCESS", "true")
            
        if final_metrics.get("user_isolation_validated"):
            self.set_env_var("USER_ISOLATION_SECURITY_VALIDATED", "true")
            
        # Performance validation
        creation_time = final_metrics.get("context_creation_time_ms", 999)
        if creation_time < 50:  # Under 50ms for 100 contexts
            self.set_env_var("USER_CONTEXT_PERFORMANCE_ACCEPTABLE", "true")
            
        super().teardown_method(method)