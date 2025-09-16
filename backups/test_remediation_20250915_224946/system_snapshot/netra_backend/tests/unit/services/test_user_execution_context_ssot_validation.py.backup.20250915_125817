"""
Unit Tests for UserExecutionContext SSOT Validation Failures

These tests are DESIGNED TO FAIL initially to prove SSOT validation issues
exist in the UserExecutionContext implementation. The tests demonstrate
specific SSOT violations that prevent proper context creation and validation.

Test Categories:
1. Context Creation SSOT Validation - Missing or invalid context data
2. ID Generation SSOT - Inconsistent ID generation patterns across factories
3. Context Validation SSOT - Invalid context validation that lets bad data through
4. Factory Integration SSOT - Context factory method validation failures
5. Session Management SSOT - Database session and lifecycle violations

Expected Outcomes:
- All tests should FAIL initially with specific SSOT error messages  
- Failures demonstrate the context validation problems affecting golden path
- Error messages provide concrete evidence of SSOT validation violations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    InvalidContextError,
    ContextIsolationError
)


class TestUserExecutionContextSSotValidation:
    """Test SSOT validation failures in UserExecutionContext."""
    
    def test_user_context_requires_valid_user_id_ssot_validation(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce valid user_id SSOT requirement.
        
        SSOT Issue: Context allows empty/None user_id, violating SSOT validation pattern.
        Expected Failure: Context should reject empty or None user_id values.
        """
        # This should FAIL with SSOT validation error
        with pytest.raises(InvalidContextError, match="user_id"):
            UserExecutionContext(
                user_id="",  # SSOT violation: empty user_id
                thread_id="valid_thread",
                run_id="valid_run",
                request_id="valid_request"
            )
    
    def test_user_context_thread_id_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce valid thread_id SSOT requirement.
        
        SSOT Issue: Context allows invalid thread_id formats, violating SSOT pattern.
        Expected Failure: Context should validate thread_id format and content.
        """
        # This should FAIL - invalid thread_id format should be rejected
        with pytest.raises(InvalidContextError, match="thread_id"):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="",  # SSOT violation: empty thread_id
                run_id="valid_run", 
                request_id="valid_request"
            )
    
    def test_user_context_run_id_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce valid run_id SSOT requirement.
        
        SSOT Issue: Context allows invalid run_id values, violating SSOT pattern.
        Expected Failure: Context should validate run_id uniqueness and format.
        """
        # This should FAIL - invalid run_id should be rejected
        with pytest.raises(InvalidContextError, match="run_id"):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id="",  # SSOT violation: empty run_id
                request_id="valid_request"
            )
    
    def test_user_context_request_id_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce valid request_id SSOT requirement.
        
        SSOT Issue: Context allows invalid request_id values, violating SSOT pattern.
        Expected Failure: Context should validate request_id uniqueness and format.
        """
        # This should FAIL - invalid request_id should be rejected  
        with pytest.raises(InvalidContextError, match="request_id"):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread", 
                run_id="valid_run",
                request_id=""  # SSOT violation: empty request_id
            )
    
    def test_validate_user_context_function_ssot_enforcement_failure(self):
        """
        TEST DESIGNED TO FAIL: validate_user_context should enforce SSOT validation.
        
        SSOT Issue: validate_user_context allows invalid contexts to pass through.
        Expected Failure: Should reject contexts with SSOT violations.
        """
        invalid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request",
            # Missing required fields for SSOT compliance
            db_session=None,
            created_at=None  # SSOT violation: None created_at
        )
        
        # This should FAIL - context with None created_at should be rejected
        with pytest.raises(InvalidContextError, match="created_at"):
            validate_user_context(invalid_context)
    
    def test_context_immutability_ssot_enforcement_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce immutability SSOT requirement.
        
        SSOT Issue: Context allows modification after creation, violating SSOT pattern.
        Expected Failure: Should prevent modification of context fields.
        """
        context = UserExecutionContext(
            user_id="test_user", 
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # This should FAIL - context should be immutable (frozen=True)
        with pytest.raises(AttributeError, match="can't set attribute"):
            context.user_id = "modified_user"  # SSOT violation: mutation attempt
    
    def test_context_child_creation_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Child context creation should enforce SSOT validation.
        
        SSOT Issue: Child context creation doesn't validate parent context properly.
        Expected Failure: Should reject child creation from invalid parent context.
        """
        # Create invalid parent context
        invalid_parent = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            request_id="test_request",
            operation_depth=-1  # SSOT violation: negative depth
        )
        
        # This should FAIL - child creation from invalid parent should be rejected
        with pytest.raises(InvalidContextError, match="operation_depth"):
            invalid_parent.create_child_context(
                new_run_id="child_run",
                operation_type="test_operation"
            )
    
    def test_context_websocket_client_id_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should validate websocket_client_id SSOT format.
        
        SSOT Issue: Context allows invalid websocket_client_id formats.
        Expected Failure: Should validate websocket_client_id format and validity.
        """
        # This should FAIL - invalid websocket_client_id format should be rejected
        with pytest.raises(InvalidContextError, match="websocket_client_id"):
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run", 
                request_id="test_request",
                websocket_client_id="invalid format"  # SSOT violation: invalid format
            )
    
    def test_context_db_session_ssot_isolation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce database session SSOT isolation.
        
        SSOT Issue: Context doesn't validate database session isolation properly.
        Expected Failure: Should reject contexts sharing database sessions.
        """
        shared_session = Mock()  # Mock database session
        
        # Create two contexts with same session (SSOT violation)
        context1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1",
            run_id="run1",
            request_id="request1", 
            db_session=shared_session
        )
        
        # This should FAIL - shared session violates SSOT isolation
        with pytest.raises(ContextIsolationError, match="shared session"):
            context2 = UserExecutionContext(
                user_id="user2",
                thread_id="thread2",
                run_id="run2",
                request_id="request2",
                db_session=shared_session  # SSOT violation: shared session
            )
    
    def test_context_agent_context_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should validate agent_context SSOT structure.
        
        SSOT Issue: Context allows invalid agent_context data structures.
        Expected Failure: Should validate agent_context contains required SSOT fields.
        """
        # This should FAIL - agent_context missing required SSOT fields
        invalid_agent_context = {
            "invalid_field": "value"
            # Missing required SSOT fields
        }
        
        with pytest.raises(InvalidContextError, match="agent_context"):
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_request",
                agent_context=invalid_agent_context  # SSOT violation: invalid structure
            )
    
    def test_context_audit_metadata_ssot_compliance_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce audit_metadata SSOT compliance.
        
        SSOT Issue: Context allows audit_metadata without required compliance fields.
        Expected Failure: Should validate audit_metadata contains SSOT audit fields.
        """
        # This should FAIL - audit_metadata missing required SSOT compliance fields
        invalid_audit_metadata = {
            "some_field": "value"
            # Missing required SSOT audit fields like created_by, operation_id, etc.
        }
        
        with pytest.raises(InvalidContextError, match="audit_metadata"):
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_request", 
                audit_metadata=invalid_audit_metadata  # SSOT violation: missing audit fields
            )
    
    def test_context_factory_from_request_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory method should enforce SSOT request validation.
        
        SSOT Issue: from_request factory method doesn't validate request structure.
        Expected Failure: Should reject requests missing SSOT required fields.
        """
        # Mock invalid request object
        invalid_request = Mock()
        invalid_request.state = Mock()
        invalid_request.state.user = None  # SSOT violation: missing user
        
        # This should FAIL - request without user should be rejected
        with pytest.raises(InvalidContextError, match="user"):
            UserExecutionContext.from_request(invalid_request)
    
    def test_context_operation_depth_ssot_limits_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should enforce operation_depth SSOT limits.
        
        SSOT Issue: Context allows unlimited operation depth, violating SSOT limits.
        Expected Failure: Should reject contexts exceeding maximum operation depth.
        """
        # This should FAIL - operation_depth exceeding SSOT limits should be rejected
        with pytest.raises(InvalidContextError, match="operation_depth"):
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_request",
                operation_depth=1000  # SSOT violation: exceeds maximum depth
            )
    
    def test_context_parent_request_id_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should validate parent_request_id SSOT consistency.
        
        SSOT Issue: Context allows invalid parent_request_id values.
        Expected Failure: Should validate parent_request_id format and existence.
        """
        # This should FAIL - invalid parent_request_id should be rejected
        with pytest.raises(InvalidContextError, match="parent_request_id"):
            UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_request",
                parent_request_id="invalid_format",  # SSOT violation: invalid format
                operation_depth=1
            )
    
    def test_context_metadata_property_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Context metadata property should maintain SSOT consistency.
        
        SSOT Issue: metadata property doesn't properly merge agent_context and audit_metadata.
        Expected Failure: Should maintain consistent view of merged metadata.
        """
        agent_context = {"agent_field": "agent_value"}
        audit_metadata = {"audit_field": "audit_value"}
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            request_id="test_request",
            agent_context=agent_context,
            audit_metadata=audit_metadata
        )
        
        # This should FAIL if metadata property SSOT consistency is violated
        metadata = context.metadata
        
        assert "agent_field" in metadata, \
            "SSOT violation: agent_context not merged into metadata property"
        assert "audit_field" in metadata, \
            "SSOT violation: audit_metadata not merged into metadata property"
        assert metadata["agent_field"] == "agent_value", \
            "SSOT violation: agent_context values not preserved in metadata"
        assert metadata["audit_field"] == "audit_value", \
            "SSOT violation: audit_metadata values not preserved in metadata"
    
    def test_context_websocket_connection_id_alias_ssot_failure(self):
        """
        TEST DESIGNED TO FAIL: Context should maintain websocket_connection_id alias SSOT.
        
        SSOT Issue: websocket_connection_id property doesn't properly alias websocket_client_id.
        Expected Failure: Should maintain SSOT consistency between aliases.
        """
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request",
            websocket_client_id="test_websocket_id"
        )
        
        # This should FAIL if SSOT alias consistency is violated
        assert context.websocket_connection_id == context.websocket_client_id, \
            "SSOT violation: websocket_connection_id alias not consistent with websocket_client_id"