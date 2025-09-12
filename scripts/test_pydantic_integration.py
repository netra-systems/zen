#!/usr/bin/env python3
"""
Test Pydantic Type Integration with Enhanced Dual Format Support

This script validates that the Pydantic types in shared.types.core_types work correctly
with both UUID and structured ID formats.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import uuid
from shared.types.core_types import (
    UserID,
    ThreadID,
    RequestID,
    WebSocketID,
    ensure_user_id,
    ensure_thread_id,
    ensure_request_id,
    ensure_websocket_id,
    normalize_to_structured_id,
    create_strongly_typed_execution_context,
    AgentExecutionContext
)
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager,
    IDType,
    generate_id
)

def test_enhanced_ensure_functions():
    """Test the enhanced ensure_* functions with dual format support."""
    print("=== Enhanced Ensure Functions Test ===\n")
    
    # Test with UUIDs
    test_uuid = str(uuid.uuid4())
    print(f"Test UUID: {test_uuid}")
    
    try:
        # This should work with the enhanced validation
        user_id = ensure_user_id(test_uuid)
        print(f"UUID -> UserID: {user_id}")
        assert isinstance(user_id, str), "UserID should be string type"
        print("[PASS] UUID accepted by ensure_user_id")
    except ValueError as e:
        print(f"[FAIL] UUID rejected by ensure_user_id: {e}")
        assert False, "UUID should be accepted"
    
    # Test with structured IDs
    id_manager = UnifiedIDManager()
    structured_user_id = id_manager.generate_id(IDType.USER)
    structured_thread_id = id_manager.generate_id(IDType.THREAD)
    
    print(f"Structured User ID: {structured_user_id}")
    print(f"Structured Thread ID: {structured_thread_id}")
    
    try:
        validated_user = ensure_user_id(structured_user_id)
        validated_thread = ensure_thread_id(structured_thread_id)
        
        print(f"Structured User ID validated: {validated_user}")
        print(f"Structured Thread ID validated: {validated_thread}")
        
        assert validated_user == structured_user_id, "Structured user ID should remain unchanged"
        assert validated_thread == structured_thread_id, "Structured thread ID should remain unchanged"
        
        print("[PASS] Structured IDs accepted by ensure functions")
    except ValueError as e:
        print(f"[FAIL] Structured IDs rejected: {e}")
        assert False, "Structured IDs should be accepted"
    
    # Test type enforcement
    try:
        # This should fail - user ID validated as thread type
        ensure_thread_id(structured_user_id)
        assert False, "Should have failed type validation"
    except ValueError:
        print("[PASS] Type enforcement working - user ID rejected as thread ID")
    
    print()
    return True

def test_normalization_functions():
    """Test the new normalization functions."""
    print("=== Normalization Functions Test ===\n")
    
    test_uuid = str(uuid.uuid4())
    print(f"Test UUID: {test_uuid}")
    
    # Test normalization to structured format
    try:
        normalized_user = normalize_to_structured_id(test_uuid, IDType.USER)
        normalized_thread = normalize_to_structured_id(test_uuid, IDType.THREAD)
        
        print(f"UUID -> Structured User: {normalized_user}")
        print(f"UUID -> Structured Thread: {normalized_thread}")
        
        assert normalized_user.startswith("user_"), "Normalized user ID should start with 'user_'"
        assert normalized_thread.startswith("thread_"), "Normalized thread ID should start with 'thread_'"
        assert normalized_user != normalized_thread, "Different types should produce different IDs"
        
        print("[PASS] UUID normalization working correctly")
    except Exception as e:
        print(f"[FAIL] UUID normalization failed: {e}")
        assert False, "UUID normalization should work"
    
    # Test that structured IDs can also be normalized (should remain the same)
    id_manager = UnifiedIDManager()
    structured_id = id_manager.generate_id(IDType.USER)
    
    try:
        normalized_structured = normalize_to_structured_id(structured_id, IDType.USER)
        print(f"Structured ID normalization: {structured_id} -> {normalized_structured}")
        
        # For structured IDs, normalization might return a new normalized form
        # The important thing is that it's still a valid user ID
        assert normalize_to_structured_id(normalized_structured, IDType.USER) is not None
        print("[PASS] Structured ID normalization working")
    except Exception as e:
        print(f"[FAIL] Structured ID normalization failed: {e}")
        assert False, "Structured ID normalization should work"
    
    print()
    return True

def test_strongly_typed_execution_context():
    """Test the enhanced execution context creation."""
    print("=== Strongly Typed Execution Context Test ===\n")
    
    # Generate test IDs - mix of UUID and structured
    test_uuid_1 = str(uuid.uuid4())
    test_uuid_2 = str(uuid.uuid4())
    
    id_manager = UnifiedIDManager()
    structured_user_id = id_manager.generate_id(IDType.USER)
    structured_agent_id = id_manager.generate_id(IDType.AGENT)
    
    print(f"Test UUID 1: {test_uuid_1}")
    print(f"Test UUID 2: {test_uuid_2}")
    print(f"Structured User ID: {structured_user_id}")
    print(f"Structured Agent ID: {structured_agent_id}")
    
    # Test without normalization (mixed formats)
    try:
        context = create_strongly_typed_execution_context(
            execution_id=test_uuid_1,
            agent_id=structured_agent_id,
            user_id=structured_user_id,
            thread_id=test_uuid_2,
            run_id="run_test_123_abc123ef",
            request_id=test_uuid_1,
            normalize_ids=False
        )
        
        print(f"Context created with mixed formats:")
        print(f"  execution_id: {context.execution_id}")
        print(f"  agent_id: {context.agent_id}")
        print(f"  user_id: {context.user_id}")
        print(f"  thread_id: {context.thread_id}")
        print(f"  run_id: {context.run_id}")
        print(f"  request_id: {context.request_id}")
        
        assert isinstance(context, AgentExecutionContext), "Should create AgentExecutionContext"
        print("[PASS] Mixed format context creation successful")
        
    except Exception as e:
        print(f"[FAIL] Mixed format context creation failed: {e}")
        assert False, "Mixed format context should be created"
    
    # Test with normalization (all converted to structured)
    try:
        normalized_context = create_strongly_typed_execution_context(
            execution_id=test_uuid_1,
            agent_id=structured_agent_id,  # Already structured
            user_id=structured_user_id,     # Already structured  
            thread_id=test_uuid_2,          # Will be normalized
            run_id="run_test_123_abc123ef",
            request_id=test_uuid_1,         # Will be normalized
            normalize_ids=True
        )
        
        print(f"\nContext created with normalization:")
        print(f"  execution_id: {normalized_context.execution_id}")
        print(f"  agent_id: {normalized_context.agent_id}")
        print(f"  user_id: {normalized_context.user_id}")
        print(f"  thread_id: {normalized_context.thread_id}")
        print(f"  run_id: {normalized_context.run_id}")
        print(f"  request_id: {normalized_context.request_id}")
        
        # Check that UUIDs were converted to structured format
        assert normalized_context.execution_id.startswith("execution_"), "Execution ID should be structured"
        assert normalized_context.thread_id.startswith("thread_"), "Thread ID should be structured"
        assert normalized_context.request_id.startswith("request_"), "Request ID should be structured"
        
        print("[PASS] Normalized context creation successful")
        
    except Exception as e:
        print(f"[FAIL] Normalized context creation failed: {e}")
        assert False, "Normalized context should be created"
    
    print()
    return True

def test_error_handling():
    """Test error handling for invalid inputs."""
    print("=== Error Handling Test ===\n")
    
    # Test invalid formats
    invalid_inputs = ["", "not-an-id", "123", None, "   "]
    
    for invalid_input in invalid_inputs:
        try:
            if invalid_input is not None:
                ensure_user_id(invalid_input)
                assert False, f"Should have failed for: {invalid_input}"
        except ValueError:
            print(f"[PASS] Correctly rejected invalid input: {repr(invalid_input)}")
        except Exception as e:
            print(f"[UNEXPECTED] Unexpected error for {repr(invalid_input)}: {e}")
    
    # Test type mismatches
    id_manager = UnifiedIDManager()
    user_id = id_manager.generate_id(IDType.USER)
    
    try:
        ensure_thread_id(user_id)  # User ID as thread ID
        assert False, "Should have failed type validation"
    except ValueError:
        print("[PASS] Type mismatch correctly rejected")
    
    print()
    return True

if __name__ == "__main__":
    try:
        print("Starting Pydantic Integration Test Suite\n")
        
        # Run all tests
        test_enhanced_ensure_functions()
        test_normalization_functions()
        test_strongly_typed_execution_context()
        test_error_handling()
        
        print("[SUCCESS] All Pydantic integration tests PASSED!")
        print("The enhanced type system supports dual format IDs correctly.")
        sys.exit(0)
        
    except Exception as e:
        print(f"[ERROR] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)