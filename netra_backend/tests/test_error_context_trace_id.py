"""Test ErrorContext trace_id field requirements and validation.

This test verifies that ErrorContext instances are created correctly
with required trace_id field, fixing the validation error:
"1 validation error for ErrorContext trace_id Field required [type=missing]"
"""

import pytest
from pydantic import ValidationError
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.schemas.shared_types import ErrorContext


class TestErrorContextTraceId:
    """Test suite for ErrorContext trace_id field validation."""
    
    def test_error_context_with_explicit_trace_id(self):
        """Test that ErrorContext accepts explicit trace_id."""
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="test_operation",
            component="TestComponent"
        )
        assert context.trace_id == "test-trace-123"
        assert context.operation == "test_operation"
        assert context.component == "TestComponent"
    
    def test_error_context_with_generated_trace_id(self):
        """Test that ErrorContext can generate trace_id."""
        trace_id = ErrorContext.generate_trace_id()
        context = ErrorContext(
            trace_id=trace_id,
            operation="test_operation",
            component="TestComponent"
        )
        assert context.trace_id == trace_id
        assert context.trace_id.startswith("trace_")
        assert len(context.trace_id) > 10
    
    def test_error_context_default_factory(self):
        """Test that ErrorContext uses default_factory for trace_id when not provided."""
        # When trace_id is not in the kwargs at all, default_factory should work
        context = ErrorContext(operation="test_op")
        assert context.trace_id is not None
        assert context.trace_id.startswith("trace_")
        assert context.operation == "test_op"
    
    def test_error_context_all_fields(self):
        """Test ErrorContext with all fields populated."""
        context = ErrorContext(
            trace_id=ErrorContext.generate_trace_id(),
            operation="full_test",
            user_id="user123",
            correlation_id="corr456",
            request_id="req789",
            session_id="sess000",
            agent_name="TestAgent",
            operation_name="test_op_name",
            run_id="run111",
            retry_count=2,
            max_retries=5,
            details={"key": "value"},
            additional_data={"extra": "data"},
            component="TestComponent",
            severity="ERROR",
            error_code="E001"
        )
        
        assert context.trace_id is not None
        assert context.operation == "full_test"
        assert context.user_id == "user123"
        assert context.correlation_id == "corr456"
        assert context.component == "TestComponent"
    
    def test_data_helper_agent_pattern(self):
        """Test the pattern used in DataHelperAgent."""
        # This pattern was failing before the fix
        context = ErrorContext(
            trace_id=ErrorContext.generate_trace_id(),
            operation="data_request_generation",
            details={"run_id": "test_run_123", "error_type": "TestError"},
            component="DataHelperAgent"
        )
        
        assert context.trace_id is not None
        assert context.operation == "data_request_generation"
        assert context.component == "DataHelperAgent"
        assert context.details["run_id"] == "test_run_123"
    
    def test_example_handler_pattern(self):
        """Test the pattern used in ExampleMessageHandler."""
        # This pattern was failing before the fix
        context = ErrorContext(
            trace_id=ErrorContext.generate_trace_id(),
            operation='validation',
            user_id='user456',
            correlation_id='msg789',
            details={'category': 'test_category', 'processing_stage': 'validation'},
            component='ExampleMessageHandler'
        )
        
        assert context.trace_id is not None
        assert context.operation == "validation"
        assert context.user_id == "user456"
        assert context.correlation_id == "msg789"
        assert context.component == "ExampleMessageHandler"
        assert context.details["processing_stage"] == "validation"
    
    def test_actions_agent_pattern(self):
        """Test the pattern used in ActionsToMeetGoalsSubAgent."""
        context = ErrorContext(
            trace_id=ErrorContext.generate_trace_id(),
            operation="action_plan_execution",
            details={"run_id": "run_456", "stream_updates": True, "error": "Test error"},
            component="ActionsToMeetGoalsSubAgent"
        )
        
        assert context.trace_id is not None
        assert context.operation == "action_plan_execution"
        assert context.component == "ActionsToMeetGoalsSubAgent"
        assert context.details["run_id"] == "run_456"
    
    def test_trace_id_uniqueness(self):
        """Test that generated trace_ids are unique."""
        trace_ids = set()
        for _ in range(100):
            trace_id = ErrorContext.generate_trace_id()
            assert trace_id not in trace_ids, "Duplicate trace_id generated"
            trace_ids.add(trace_id)
        
        assert len(trace_ids) == 100
    
    def test_error_context_serialization(self):
        """Test that ErrorContext can be serialized and deserialized."""
        original = ErrorContext(
            trace_id=ErrorContext.generate_trace_id(),
            operation="serialize_test",
            component="TestComponent",
            details={"test": "data"}
        )
        
        # Serialize to dict
        serialized = original.model_dump()
        assert "trace_id" in serialized
        assert serialized["operation"] == "serialize_test"
        
        # Deserialize back
        restored = ErrorContext(**serialized)
        assert restored.trace_id == original.trace_id
        assert restored.operation == original.operation
        assert restored.component == original.component


if __name__ == "__main__":
    # Run the tests
    test_suite = TestErrorContextTraceId()
    
    print("Running ErrorContext trace_id validation tests...")
    
    # Run each test
    tests = [
        test_suite.test_error_context_with_explicit_trace_id,
        test_suite.test_error_context_with_generated_trace_id,
        test_suite.test_error_context_default_factory,
        test_suite.test_error_context_all_fields,
        test_suite.test_data_helper_agent_pattern,
        test_suite.test_example_handler_pattern,
        test_suite.test_actions_agent_pattern,
        test_suite.test_trace_id_uniqueness,
        test_suite.test_error_context_serialization
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f" PASS:  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f" FAIL:  {test.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("[U+2728] All tests passed! ErrorContext trace_id issue is fixed.")
    else:
        print(" WARNING: [U+FE0F] Some tests failed. Please review the errors above.")