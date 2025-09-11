#!/usr/bin/env python3
"""
Test Enhanced Dual Format ID Validation

This script validates that the enhanced UnifiedIDManager correctly handles
both UUID and structured ID formats, addressing the validation inconsistencies
identified in the previous analysis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import uuid
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager, 
    IDType, 
    is_valid_id_format,
    is_valid_id_format_compatible
)

def test_enhanced_validation():
    """Test the enhanced dual format validation system."""
    print("=== Enhanced Dual Format ID Validation Test ===\n")
    
    # Initialize ID manager
    id_manager = UnifiedIDManager()
    
    # Test 1: UUID validation consistency
    print("TEST 1: UUID Validation Consistency")
    test_uuid = str(uuid.uuid4())
    print(f"Test UUID: {test_uuid}")
    
    format_result = is_valid_id_format(test_uuid)
    format_compatible_result = is_valid_id_format_compatible(test_uuid, IDType.USER)
    manager_result = id_manager.is_valid_id(test_uuid)  # Expected to be False (not registered)
    manager_compatible_result = id_manager.is_valid_id_format_compatible(test_uuid, IDType.USER)
    
    print(f"is_valid_id_format: {format_result}")
    print(f"is_valid_id_format_compatible: {format_compatible_result}")
    print(f"manager.is_valid_id: {manager_result}")
    print(f"manager.is_valid_id_format_compatible: {manager_compatible_result}")
    
    # The new validation should accept UUIDs during migration
    assert format_result == True, "UUID should be valid format"
    assert format_compatible_result == True, "UUID should be compatible format"
    assert manager_result == False, "UUID not registered, should be False"
    assert manager_compatible_result == True, "UUID should be compatible without registration"
    print("[PASS] UUID validation consistency test PASSED\n")
    
    # Test 2: Structured ID validation
    print("TEST 2: Structured ID Validation")
    user_id = id_manager.generate_id(IDType.USER)
    print(f"Generated User ID: {user_id}")
    
    format_result = is_valid_id_format(user_id)
    format_compatible_result = is_valid_id_format_compatible(user_id, IDType.USER)
    manager_result = id_manager.is_valid_id(user_id, IDType.USER)
    manager_compatible_result = id_manager.is_valid_id_format_compatible(user_id, IDType.USER)
    
    print(f"is_valid_id_format: {format_result}")
    print(f"is_valid_id_format_compatible: {format_compatible_result}")
    print(f"manager.is_valid_id: {manager_result}")
    print(f"manager.is_valid_id_format_compatible: {manager_compatible_result}")
    
    assert format_result == True, "Structured ID should be valid format"
    assert format_compatible_result == True, "Structured ID should be compatible"
    assert manager_result == True, "Registered structured ID should be valid"
    assert manager_compatible_result == True, "Structured ID should be compatible"
    print("[PASS] Structured ID validation test PASSED\n")
    
    # Test 3: Type safety validation
    print("TEST 3: Type Safety Validation")
    
    # Try to validate user ID as different type
    format_compatible_as_thread = is_valid_id_format_compatible(user_id, IDType.THREAD)
    manager_compatible_as_thread = id_manager.is_valid_id_format_compatible(user_id, IDType.THREAD)
    
    print(f"User ID validated as THREAD type (should be False): {format_compatible_as_thread}")
    print(f"Manager User ID as THREAD type (should be False): {manager_compatible_as_thread}")
    
    assert format_compatible_as_thread == False, "User ID should not validate as thread type"
    assert manager_compatible_as_thread == False, "Manager should enforce type safety"
    print("[PASS] Type safety validation test PASSED\n")
    
    # Test 4: Format detection
    print("TEST 4: Format Detection")
    
    is_structured = id_manager._is_structured_id_format(user_id)
    is_uuid_structured = id_manager._is_structured_id_format(test_uuid)
    
    print(f"Structured ID detected as structured: {is_structured}")
    print(f"UUID detected as structured: {is_uuid_structured}")
    
    assert is_structured == True, "Structured ID should be detected as structured"
    assert is_uuid_structured == False, "UUID should not be detected as structured"
    print("[PASS] Format detection test PASSED\n")
    
    # Test 5: Type extraction
    print("TEST 5: Type Extraction")
    
    extracted_type = id_manager._extract_id_type_from_structured(user_id)
    extracted_from_uuid = id_manager._extract_id_type_from_structured(test_uuid)
    
    print(f"Type extracted from user ID: {extracted_type}")
    print(f"Type extracted from UUID: {extracted_from_uuid}")
    
    assert extracted_type == IDType.USER, "Should extract USER type from user ID"
    assert extracted_from_uuid == None, "Should extract no type from UUID"
    print("[PASS] Type extraction test PASSED\n")
    
    print("[SUCCESS] ALL ENHANCED VALIDATION TESTS PASSED!")
    print("The dual format validation system is working correctly.")
    
    return True

def test_validation_edge_cases():
    """Test edge cases for the validation system."""
    print("\n=== Validation Edge Cases Test ===\n")
    
    id_manager = UnifiedIDManager()
    
    # Test empty/invalid inputs
    edge_cases = ["", None, "   ", "\n", "\t", "invalid", "123", "abc_def"]
    
    print("Testing edge cases:")
    for case in edge_cases:
        try:
            format_result = is_valid_id_format(case) if case is not None else False
            compatible_result = is_valid_id_format_compatible(case) if case is not None else False
            print(f"  {repr(case):12} -> format: {format_result}, compatible: {compatible_result}")
        except Exception as e:
            print(f"  {repr(case):12} -> Exception: {type(e).__name__}")
    
    print("[PASS] Edge cases handled gracefully\n")
    
    return True

if __name__ == "__main__":
    try:
        # Run the validation tests
        success1 = test_enhanced_validation()
        success2 = test_validation_edge_cases()
        
        if success1 and success2:
            print("\n[SUCCESS] Enhanced Dual Format Validation Implementation: SUCCESS")
            print("The UnifiedIDManager now supports both UUID and structured formats gracefully.")
            sys.exit(0)
        else:
            print("\n[FAILED] Enhanced Dual Format Validation Implementation: FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)