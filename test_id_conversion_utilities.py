#!/usr/bin/env python3
"""
Test ID Conversion Utilities

This script validates the conversion utilities between UUID and structured ID formats,
ensuring they work correctly for the dual format migration system.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import uuid
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager, 
    IDType,
    convert_uuid_to_structured,
    convert_structured_to_uuid,
    validate_and_normalize_id
)

def test_uuid_to_structured_conversion():
    """Test conversion from UUID to structured format."""
    print("=== UUID to Structured Conversion Test ===\n")
    
    # Generate test UUIDs
    test_uuid1 = str(uuid.uuid4())
    test_uuid2 = str(uuid.uuid4())
    
    print(f"Test UUID 1: {test_uuid1}")
    print(f"Test UUID 2: {test_uuid2}")
    
    # Test conversion without prefix
    structured_user = convert_uuid_to_structured(test_uuid1, IDType.USER)
    structured_thread = convert_uuid_to_structured(test_uuid2, IDType.THREAD)
    
    print(f"UUID1 -> User ID: {structured_user}")
    print(f"UUID2 -> Thread ID: {structured_thread}")
    
    # Validate the results
    assert structured_user.startswith("user_"), f"User ID should start with 'user_': {structured_user}"
    assert structured_thread.startswith("thread_"), f"Thread ID should start with 'thread_': {structured_thread}"
    
    # Validate format
    user_parts = structured_user.split('_')
    thread_parts = structured_thread.split('_')
    
    assert len(user_parts) == 3, f"User ID should have 3 parts: {user_parts}"
    assert len(thread_parts) == 3, f"Thread ID should have 3 parts: {thread_parts}"
    
    assert user_parts[0] == "user", "First part should be 'user'"
    assert thread_parts[0] == "thread", "First part should be 'thread'"
    
    assert user_parts[1].isdigit(), "Second part should be numeric counter"
    assert thread_parts[1].isdigit(), "Second part should be numeric counter"
    
    assert len(user_parts[2]) == 8, "Third part should be 8 characters"
    assert len(thread_parts[2]) == 8, "Third part should be 8 characters"
    
    print("[PASS] UUID to structured conversion test PASSED\n")
    
    # Test with prefix
    prefixed_id = convert_uuid_to_structured(test_uuid1, IDType.AGENT, "req")
    print(f"UUID1 -> Agent ID with prefix: {prefixed_id}")
    assert prefixed_id.startswith("req_agent_"), f"Prefixed ID should start with 'req_agent_': {prefixed_id}"
    print("[PASS] Prefixed conversion test PASSED\n")
    
    return structured_user, structured_thread

def test_structured_to_uuid_conversion():
    """Test conversion from structured to UUID format."""
    print("=== Structured to UUID Conversion Test ===\n")
    
    # Create some structured IDs
    id_manager = UnifiedIDManager()
    user_id = id_manager.generate_id(IDType.USER)
    thread_id = id_manager.generate_id(IDType.THREAD)
    
    print(f"Structured User ID: {user_id}")
    print(f"Structured Thread ID: {thread_id}")
    
    # Convert to UUID format
    uuid_from_user = convert_structured_to_uuid(user_id)
    uuid_from_thread = convert_structured_to_uuid(thread_id)
    
    print(f"User ID -> UUID: {uuid_from_user}")
    print(f"Thread ID -> UUID: {uuid_from_thread}")
    
    # Validate the results
    assert uuid_from_user is not None, "User ID should convert to UUID"
    assert uuid_from_thread is not None, "Thread ID should convert to UUID"
    
    # Validate UUID format
    try:
        uuid.UUID(uuid_from_user)
        uuid.UUID(uuid_from_thread)
        print("[PASS] Generated UUIDs are valid format")
    except ValueError as e:
        assert False, f"Generated UUIDs should be valid: {e}"
    
    # Test with invalid structured ID
    invalid_uuid = convert_structured_to_uuid("invalid_id")
    assert invalid_uuid is None, "Invalid structured ID should return None"
    
    print("[PASS] Structured to UUID conversion test PASSED\n")
    
    return uuid_from_user, uuid_from_thread

def test_round_trip_conversion():
    """Test round-trip conversion (UUID -> Structured -> UUID)."""
    print("=== Round-trip Conversion Test ===\n")
    
    original_uuid = str(uuid.uuid4())
    print(f"Original UUID: {original_uuid}")
    
    # Convert to structured
    structured_id = convert_uuid_to_structured(original_uuid, IDType.USER)
    print(f"UUID -> Structured: {structured_id}")
    
    # Convert back to UUID
    recovered_uuid = convert_structured_to_uuid(structured_id)
    print(f"Structured -> UUID: {recovered_uuid}")
    
    # Note: This is a lossy conversion, so we can't expect exact match
    # But we can verify the first 8 hex characters match
    original_hex = original_uuid.replace('-', '')[:8]
    recovered_hex = recovered_uuid.replace('-', '')[:8] if recovered_uuid else ""
    
    print(f"Original hex prefix: {original_hex}")
    print(f"Recovered hex prefix: {recovered_hex}")
    
    assert original_hex.lower() == recovered_hex.lower(), \
        f"First 8 hex characters should match: {original_hex} vs {recovered_hex}"
    
    print("[PASS] Round-trip conversion maintains hex prefix\n")
    
    return original_uuid, structured_id, recovered_uuid

def test_validation_and_normalization():
    """Test ID validation and normalization."""
    print("=== Validation and Normalization Test ===\n")
    
    id_manager = UnifiedIDManager()
    
    # Test with UUID
    test_uuid = str(uuid.uuid4())
    print(f"Test UUID: {test_uuid}")
    
    is_valid, normalized = validate_and_normalize_id(test_uuid, IDType.USER)
    print(f"UUID validation: {is_valid}, normalized: {normalized}")
    
    assert is_valid, "UUID should be valid"
    assert normalized != test_uuid, "UUID should be normalized to structured format"
    assert normalized.startswith("user_"), "Normalized ID should be user type"
    
    # Test with structured ID
    user_id = id_manager.generate_id(IDType.USER)
    print(f"Structured User ID: {user_id}")
    
    is_valid2, normalized2 = validate_and_normalize_id(user_id, IDType.USER)
    print(f"Structured validation: {is_valid2}, normalized: {normalized2}")
    
    assert is_valid2, "Structured ID should be valid"
    assert normalized2 == user_id, "Registered structured ID should remain unchanged"
    
    # Test type mismatch
    is_valid3, normalized3 = validate_and_normalize_id(user_id, IDType.THREAD)
    print(f"Type mismatch validation: {is_valid3}, normalized: {normalized3}")
    
    assert not is_valid3, "Type mismatch should be invalid"
    assert normalized3 is None, "Invalid ID should have None normalized form"
    
    print("[PASS] Validation and normalization test PASSED\n")
    
    return True

def test_error_handling():
    """Test error handling for invalid inputs."""
    print("=== Error Handling Test ===\n")
    
    # Test invalid UUID conversion
    try:
        convert_uuid_to_structured("not-a-uuid", IDType.USER)
        assert False, "Should raise ValueError for invalid UUID"
    except ValueError as e:
        print(f"[PASS] Invalid UUID correctly raises ValueError: {e}")
    
    # Test invalid structured ID conversion
    result = convert_structured_to_uuid("not_a_structured_id")
    assert result is None, "Invalid structured ID should return None"
    print("[PASS] Invalid structured ID returns None")
    
    # Test edge cases
    edge_cases = ["", None, "   ", "a_b", "user_", "_1_abc123ef"]
    
    for case in edge_cases:
        try:
            result = convert_structured_to_uuid(case) if case is not None else None
            print(f"  {repr(case):20} -> {result}")
        except Exception as e:
            print(f"  {repr(case):20} -> Exception: {type(e).__name__}")
    
    print("[PASS] Error handling test PASSED\n")
    
    return True

if __name__ == "__main__":
    try:
        print("Starting ID Conversion Utilities Test Suite\n")
        
        # Run all tests
        structured_user, structured_thread = test_uuid_to_structured_conversion()
        uuid_from_user, uuid_from_thread = test_structured_to_uuid_conversion()
        original_uuid, structured_id, recovered_uuid = test_round_trip_conversion()
        test_validation_and_normalization()
        test_error_handling()
        
        print("[SUCCESS] All ID conversion utility tests PASSED!")
        print("The conversion utilities are working correctly for dual format migration.")
        sys.exit(0)
        
    except Exception as e:
        print(f"[ERROR] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)